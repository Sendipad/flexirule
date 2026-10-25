/* global afterEach */
import { isConsoleRegressionMessage } from "../support/regression_guards.mjs";

describe("FlexiRule builder regression coverage", () => {
	let ruleName;
	let capturedConsoleMessages = [];

	function defaultRuleActions() {
		return [
			{
				action_id: "root",
				action_label: "Start",
				action_type: "Entry Action",
				is_enabled: 1,
				next_step_if_true: "node_end",
			},
			{
				action_id: "node_end",
				action_label: "End",
				action_type: "Stop",
				operation: "Success",
				is_enabled: 1,
			},
		];
	}

	const DEFAULT_AUDIT_REASON = "Cypress regression test: audited Fetch Records access";

	function queryRecordsActions({ count = 1, auditReason = DEFAULT_AUDIT_REASON } = {}) {
		const actions = [
			{
				action_id: "root",
				action_label: "Start",
				action_type: "Entry Action",
				is_enabled: 1,
				next_step_if_true: "query_1",
			},
		];

		for (let index = 1; index <= count; index += 1) {
			actions.push({
				action_id: `query_${index}`,
				action_label: `Fetch Records ${index}`,
				action_type: "Query Records",
				operation: "Fetch Records",
				reference_doctype: "Contact",
				is_enabled: 1,
				ignore_permissions: 1,
				permission_audit_reason: auditReason,
				config: JSON.stringify({
					filters: [],
					fields: ["name"],
					result_shape: "document_names",
					limit_mode: "custom",
					limit: 20,
					offset: 0,
					distinct: false,
					order_by: "",
					group_by: "",
				}),
				next_step_if_true: index < count ? `query_${index + 1}` : "node_end",
			});
		}

		actions.push({
			action_id: "node_end",
			action_label: "End",
			action_type: "Stop",
			operation: "Success",
			is_enabled: 1,
		});
		return actions;
	}

	function createRuleAndOpenBuilder(actions = defaultRuleActions()) {
		const suffix = Date.now().toString() + "_" + Math.floor(Math.random() * 1000);
		ruleName = "Cypress_Regression_" + suffix;

		return cy
			.window()
			.then((win) =>
				win.frappe.call({
					method: "frappe.client.insert",
					args: {
						doc: {
							doctype: "Rule",
							rule_name: ruleName,
							document_type: "Contact",
							trigger_event: "After Save",
							trigger_type: "DocType Event",
							is_active: 0,
							actions,
						},
					},
				})
			)
			.then((response) => {
				ruleName = response?.message?.name || ruleName;
				return cy.window().then((win) => win.frappe.set_route("Form", "Rule", ruleName));
			})
			.then(() => cy.contains("button", "Visual Builder", { timeout: 30000 }).click())
			.then(() => cy.get(".vue-flow", { timeout: 30000 }).should("be.visible"))
			.then(() =>
				cy.get(".vue-flow__node", { timeout: 30000 }).should("have.length.at.least", 2)
			);
	}

	function suppressSchemaRefreshConfirmation() {
		cy.window().then((win) => {
			const originalConfirm = win.frappe.confirm;
			if (!originalConfirm || originalConfirm.isSinonStub) return;

			// This confirmation is unrelated to the behaviors covered by these tests.
			// Resolve it as "Skip" through Frappe's callback instead of racing its
			// Bootstrap transition with Cypress's modal visibility assertions.
			cy.stub(win.frappe, "confirm").callsFake(
				(message, onConfirm, onReject, primaryLabel, secondaryLabel) => {
					if (/refresh the output schema/i.test(String(message))) {
						onReject?.();
						return;
					}
					return originalConfirm.call(
						win.frappe,
						message,
						onConfirm,
						onReject,
						primaryLabel,
						secondaryLabel
					);
				}
			);
		});
	}

	function openActionConfig(label, skipSchemaRefresh = false) {
		if (skipSchemaRefresh) suppressSchemaRefreshConfirmation();

		cy.contains(".vue-flow__node", label, { timeout: 15000 })
			.should("be.visible")
			.dblclick({ force: true });

		cy.get(".config-modal-container", { timeout: 15000 }).should("be.visible");
	}

	function setFetchRecordsLimit(value) {
		cy.contains(".config-modal-container .fxr-label", "Custom Limit", { timeout: 15000 })
			.closest(".fxr-control")
			.find("input.fxr-input")
			.should("be.visible")
			.clear()
			.type(String(value))
			.should("have.value", String(value));
	}

	function parsedActionConfig(doc, actionId) {
		const action = doc.actions.find((row) => row.action_id === actionId);
		expect(action, `persisted action ${actionId}`).to.exist;
		if (!action) return {};
		return typeof action.config === "string"
			? JSON.parse(action.config || "{}")
			: action.config || {};
	}

	function saveRuleAndWait(alias) {
		cy.intercept("POST", "**/api/method/frappe.client.save").as(alias);
		cy.contains("button", "Save Rule", { timeout: 20000 })
			.should("be.visible")
			.click({ force: true });
		cy.wait(`@${alias}`);
	}

	function addNodeFromEdgeMenu(type) {
		cy.get(".edge-add-button", { timeout: 20000 })
			.last()
			.should("be.visible")
			.click({ force: true });
		cy.get("body").then(($body) => {
			if ($body.find(".result-item.is-option").length === 0) {
				cy.get(".edge-add-button", { timeout: 20000 }).last().click({ force: true });
			}
		});
		cy.get(".result-item.is-option", { timeout: 20000 })
			.contains(type, { timeout: 15000 })
			.click({ force: true });
	}

	function persistedRule() {
		return cy.request("/api/resource/Rule/" + encodeURIComponent(ruleName)).its("body.data");
	}

	beforeEach(() => {
		ruleName = null;
		capturedConsoleMessages = [];

		cy.on("window:before:load", (win) => {
			["error", "warn"].forEach((level) => {
				const original = win.console[level];
				if (!original) return;
				win.console[level] = (...args) => {
					const message = args.map(String).join(" ");
					capturedConsoleMessages.push({
						level,
						message,
						url: win.location.href,
					});
					return original.apply(win.console, args);
				};
			});
		});

		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	afterEach(function () {
		const assertConsoleRegressions = () => {
			const regressions = capturedConsoleMessages.filter((item) =>
				isConsoleRegressionMessage(item.message)
			);
			if (regressions.length > 0) {
				const formatted = regressions
					.map((r) => `[${r.level}] ${r.url}: ${r.message}`)
					.join("\n");
				expect.fail(`Console regression guard detected error(s):\n${formatted}`);
			}
		};

		if (ruleName) {
			const name = ruleName;
			ruleName = null;
			cy.request({
				method: "DELETE",
				url: "/api/resource/Rule/" + encodeURIComponent(name),
				failOnStatusCode: false,
			}).then(assertConsoleRegressions);
		} else {
			assertConsoleRegressions();
		}
	});

	it("captures console warnings and errors emitted after listener installation", () => {
		cy.window().then((win) => {
			win.console.warn("Controlled sanity check warning message");
		});
		cy.then(() => {
			const captured = capturedConsoleMessages.some((msg) =>
				msg.message.includes("Controlled sanity check warning message")
			);
			expect(captured, "console.warn message was captured by the listener").to.eq(true);
		});
	});

	it("opens Assignment configuration and exposes the required assignment controls", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input")
			.should("be.visible")
			.clear()
			.type("Assignment configuration check");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", "Assignment configuration check")
			.should("be.visible")
			.dblclick({ force: true });

		cy.contains("Batch Assignments", { timeout: 15000 }).should("be.visible");
		cy.contains("button", "Add Assignment").should("be.visible").click();
		cy.contains("Target Field").should("be.visible");
		cy.contains("Operator").should("be.visible");
		cy.contains("Value Expression").should("be.visible");
	});

	it("opens Condition configuration and renders its condition editor", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Condition");
		cy.get(".labeling-container input")
			.should("be.visible")
			.clear()
			.type("Condition configuration check");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", "Condition configuration check")
			.should("be.visible")
			.dblclick({ force: true });

		cy.get(".config-modal-container", { timeout: 15000 }).should("be.visible");
		cy.get(".config-modal-container").contains("Condition").should("be.visible");
	});

	it("opens Query Records configuration and exposes the Fetch Records editor", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Query Records");
		cy.get(".result-item.is-option", { timeout: 15000 })
			.contains("Fetch Records", { timeout: 15000 })
			.click({ force: true });
		cy.get(".labeling-container input")
			.should("be.visible")
			.clear()
			.type("Query Records configuration check");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		openActionConfig("Query Records configuration check", true);
		cy.contains(".config-modal-container", "Query Mode", { timeout: 15000 }).should("be.visible");
		cy.contains(".config-modal-container", "Fetch Records").should("be.visible");
	});

	it("persists graph node data and edges through a hard reload", () => {
		createRuleAndOpenBuilder();
		const label = "Persisted graph " + Date.now();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").clear().type(label);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", label).should("be.visible").dblclick({ force: true });
		cy.contains("button", "Add Assignment", { timeout: 15000 }).should("be.visible").click();

		cy.intercept("POST", "**/api/method/frappe.client.save").as("saveRule");
		cy.contains("button", "Save Rule", { timeout: 15000 }).click({ force: true });
		cy.wait("@saveRule");

		persistedRule().then((doc) => {
			expect(doc.actions, "persisted action rows").to.be.an("array");
			expect(
				doc.actions.some(
					(action) =>
						action.action_type === "Assignment" &&
						(action.action_label === label || action.label === label)
				),
				"Assignment action row includes the configured label"
			).to.eq(true);

			const visual =
				typeof doc.visual_data === "string" ? JSON.parse(doc.visual_data) : doc.visual_data;
			expect(visual, "persisted visual graph").to.be.an("array");
			expect(
				visual.some((item) => item.position && item.id),
				"visual graph contains position metadata"
			).to.eq(true);
			expect(
				visual.some((item) => item.source && item.target),
				"visual graph contains persisted edges"
			).to.eq(true);
		});

		cy.reload();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.contains(".vue-flow__node", label).should("be.visible");
		persistedRule().then((doc) => {
			const visual =
				typeof doc.visual_data === "string" ? JSON.parse(doc.visual_data) : doc.visual_data;
			expect(visual.some((item) => item.position && item.id)).to.eq(true);
			expect(doc.actions.some((action) => action.action_type === "Assignment")).to.eq(true);
		});
	});

	it("coalesces overlapping layout requests and leaves the graph visible", () => {
		createRuleAndOpenBuilder();

		// Exercise the same overlap that can happen when initialization and node
		// insertion both request a layout. The last requested direction must win,
		// and every caller must settle only after its queued layout finishes.
		cy.window().then((win) => {
			const requestLayout = win.fxrRuleBuilder.layoutGraph;
			return Promise.all([requestLayout("LR"), requestLayout("TB"), requestLayout("LR")]);
		});

		cy.get(".vue-flow__node").should("have.length.at.least", 2);
		cy.get(".vue-flow__node").each(($node) => {
			cy.wrap($node).should("be.visible");
		});
	});

	it("keeps unsaved graph changes distinguishable from the persisted baseline", () => {
		createRuleAndOpenBuilder();
		const label = "Dirty state " + Date.now();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").clear().type(label);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		// The unsaved node is observable in the canvas, but the server copy must
		// remain unchanged until Save Rule is explicitly invoked.
		cy.contains(".vue-flow__node", label).should("be.visible");
		persistedRule().then((doc) => {
			expect(
				doc.actions.some(
					(action) =>
						action.action_type === "Assignment" &&
						(action.action_label === label || action.label === label)
				),
				"new node must not be persisted before Save Rule"
			).to.eq(false);
		});
	});

	it("supports undo and redo for a graph edit without persisting it implicitly", () => {
		createRuleAndOpenBuilder();
		const label = "Undo redo " + Date.now();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").clear().type(label);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();
		cy.contains(".vue-flow__node", label).should("be.visible");

		// Perform undo twice: selector node insertion + label upgrade
		cy.window().then((win) => {
			win.fxrRuleBuilder.ruleStore.undo();
			win.fxrRuleBuilder.ruleStore.undo();
		});
		cy.contains(".vue-flow__node", label).should("not.exist");

		// Perform redo twice: restore node + label
		cy.window().then((win) => {
			win.fxrRuleBuilder.ruleStore.redo();
			win.fxrRuleBuilder.ruleStore.redo();
		});
		cy.contains(".vue-flow__node", label).should("exist");

		persistedRule().then((doc) => {
			expect(
				doc.actions.some(
					(action) =>
						action.action_type === "Assignment" &&
						(action.action_label === label || action.label === label)
				),
				"undo/redo must not implicitly save the graph"
			).to.eq(false);
		});
	});

	it("keeps an incomplete Assignment out of persisted data when save validation rejects it", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input")
			.should("be.visible")
			.clear()
			.type("Incomplete assignment");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains("button", "Save Rule", { timeout: 15000 }).click({ force: true });
		persistedRule().then((doc) => {
			expect(
				doc.actions.some(
					(action) =>
						action.action_type === "Assignment" &&
						(action.action_label === "Incomplete assignment" ||
							action.label === "Incomplete assignment")
				),
				"an incomplete action should not be persisted"
			).to.eq(false);
		});
	});

	it("verifies console regression guard detects known grid and schema console errors", () => {
		createRuleAndOpenBuilder();
		cy.then(() => {
			const regressions = capturedConsoleMessages.filter((item) =>
				isConsoleRegressionMessage(item.message)
			);
			expect(regressions, regressions.map((r) => r.message).join("\n")).to.deep.equal([]);
		});
	});

	it("inserts a filter row in Fetch Records action configuration", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Query Records");
		cy.get(".result-item.is-option", { timeout: 15000 })
			.contains("Fetch Records", { timeout: 15000 })
			.click({ force: true });
		cy.get(".labeling-container input")
			.should("be.visible")
			.clear()
			.type("Filter insertion regression");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();
		openActionConfig("Filter insertion regression", true);
		cy.contains(".config-modal-container h6", "Filters").should("be.visible");
		cy.get(".config-modal-container .tree-builder__actions button").contains("Filter").click();
		cy.get(".config-modal-container .filter-row").should("have.length", 1).and("be.visible");
	});

	it("saves a changed Fetch Records configuration on the first modal click and persists it", () => {
		createRuleAndOpenBuilder(queryRecordsActions());
		openActionConfig("Fetch Records 1", true);
		setFetchRecordsLimit(35);

		// The action dialog itself must commit the isolated candidate on one click.
		cy.get(".config-modal-container .save-action").should("be.visible").click();
		cy.get(".config-modal-container").should("not.exist");
		cy.contains("button", "Save Rule", { timeout: 15000 }).should("be.visible");

		saveRuleAndWait("saveFirstFetchRecordsEdit");
		persistedRule().then((doc) => {
			const config = parsedActionConfig(doc, "query_1");
			expect(Number(config.limit), "saved Fetch Records limit").to.eq(35);
			const action = doc.actions.find((row) => row.action_id === "query_1");
			expect(action.permission_audit_reason).to.eq(DEFAULT_AUDIT_REASON);
		});

		cy.reload();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.contains(".vue-flow__node", "Fetch Records 1").should("be.visible");
		persistedRule().then((doc) => {
			expect(Number(parsedActionConfig(doc, "query_1").limit)).to.eq(35);
		});
	});

	it("rejects a Fetch Records modal save without an audit reason and leaves persisted data unchanged", () => {
		// Frappe 15 server validation requires an audited permission bypass when
		// initially inserting Fetch Records, so create a valid baseline first.
		createRuleAndOpenBuilder(queryRecordsActions());
		openActionConfig("Fetch Records 1", true);
		setFetchRecordsLimit(21);
		cy.get('.config-modal-container [data-fieldname="permission_audit_reason"]')
			.find("textarea, input")
			.first()
			.should("be.visible")
			.clear();

		cy.window().then((win) => {
			cy.stub(win.frappe, "msgprint").as("validationMessage");
		});
		cy.get(".config-modal-container .save-action").should("be.visible").click();
		cy.get("@validationMessage").should("have.been.called");
		cy.get("@validationMessage").should((stub) => {
			const messages = stub
				.getCalls()
				.map((call) => JSON.stringify(call.args[0]))
				.join("\n");
			expect(messages).to.contain(
				"Permission Audit Reason is required when bypassing permissions."
			);
		});
		cy.get(".config-modal-container").should("be.visible");

		// Modal validation must not write the candidate to the saved Rule.
		persistedRule().then((doc) => {
			expect(Number(parsedActionConfig(doc, "query_1").limit)).to.eq(20);
			const action = doc.actions.find((row) => row.action_id === "query_1");
			expect(action.permission_audit_reason).to.eq(DEFAULT_AUDIT_REASON);
		});
	});

	it("marks a real second Action edit dirty after the post-save fetch and persists the edit", () => {
		createRuleAndOpenBuilder(queryRecordsActions({ count: 2 }));

		openActionConfig("Fetch Records 1", true);
		setFetchRecordsLimit(30);
		cy.get(".config-modal-container .save-action").should("be.visible").click();
		cy.get(".config-modal-container").should("not.exist");
		saveRuleAndWait("saveFirstFetchRecordsAction");
		cy.contains("button", "Activate Rule", { timeout: 20000 }).should("be.visible");

		// This second edit occurs after the real save_changes() -> fetch() lifecycle.
		openActionConfig("Fetch Records 2", true);
		setFetchRecordsLimit(50);
		cy.get(".config-modal-container .save-action").should("be.visible").click();
		cy.get(".config-modal-container").should("not.exist");
		cy.contains("button", "Save Rule", { timeout: 15000 })
			.should("be.visible")
			.and("be.enabled")
			.and("have.class", "btn-primary");

		saveRuleAndWait("saveSecondFetchRecordsAction");
		cy.contains("button", "Activate Rule", { timeout: 20000 }).should("be.visible");
		cy.reload();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.contains(".vue-flow__node", "Fetch Records 2").should("be.visible");
		persistedRule().then((doc) => {
			expect(Number(parsedActionConfig(doc, "query_1").limit)).to.eq(30);
			expect(Number(parsedActionConfig(doc, "query_2").limit)).to.eq(50);
		});
	});
});
