/* global afterEach */
import { isConsoleRegressionMessage } from "../support/regression_guards.mjs";

describe("FlexiRule builder regression coverage", () => {
	let ruleName;
	let capturedConsoleMessages = [];

	function createRuleAndOpenBuilder() {
		const suffix = Date.now().toString() + "_" + Math.floor(Math.random() * 1000);
		ruleName = "Cypress_Regression_" + suffix;

		cy.window().then((win) => {
			return win.frappe.call({
				method: "frappe.client.insert",
				args: {
					doc: {
						doctype: "Rule",
						rule_name: ruleName,
						document_type: "Contact",
						trigger_event: "After Save",
						trigger_type: "DocType Event",
						actions: [
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
						],
					},
				},
			});
		});

		cy.window().then((win) => win.frappe.set_route("Form", "Rule", ruleName));
		cy.contains("button", "Visual Builder", { timeout: 30000 }).click();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.get(".vue-flow__node", { timeout: 30000 }).should("have.length.at.least", 2);
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

		const password = Cypress.env("frappePassword");
		if (!password)
			throw new Error("FRAPPE_PASSWORD is required for the Cypress regression suite.");

		cy.on("window:before:load", (win) => {
			["error", "warn"].forEach((level) => {
				const original = win.console[level];
				if (!original) return;
				win.console[level] = (...args) => {
					const msg = args.map(String).join(" ");
					capturedConsoleMessages.push({
						level,
						message: msg,
						url: win.location.href,
					});
					return original.apply(win.console, args);
				};
			});
		});

		cy.visit("/login");
		cy.get("#login_email")
			.should("be.visible")
			.clear()
			.type(Cypress.env("frappeUser") || "Administrator");
		cy.get("#login_password").should("be.visible").clear().type(password, { log: false });
		cy.get("button.btn-login").should("be.visible").click();
		cy.url().should("include", "/app");
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

		cy.contains(".vue-flow__node", "Query Records configuration check")
			.should("be.visible")
			.dblclick({ force: true });

		cy.contains("Query Mode", { timeout: 15000 }).should("exist");
		cy.contains("Fetch Records").should("exist");
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
});
