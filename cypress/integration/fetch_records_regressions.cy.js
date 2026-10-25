/* global afterEach */
import { isConsoleRegressionMessage } from "../support/regression_guards.mjs";
import { ruleBuilderPage } from "../support/pages/RuleBuilderPage";

describe("Fetch Records builder regressions", () => {
	let ruleName = null;
	let capturedConsoleMessages = [];

	const DEFAULT_AUDIT_REASON = "Cypress regression test: audited Fetch Records access";

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

	function queryRecordsActions({
		count = 1,
		auditReason = DEFAULT_AUDIT_REASON,
		mutationMode,
		returnType,
	} = {}) {
		expect(mutationMode, "backend-provided Fetch Records result handling").to.be.a("string").and
			.not.be.empty;
		expect(returnType, "backend-provided Fetch Records result type").to.be.a("string").and.not
			.be.empty;

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
				mutation_mode: mutationMode,
				return_type: returnType,
				return_variable: `fetch_records_${index}`,
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
		ruleName = "Cypress_Fetch_Records_" + suffix;

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

	function createFetchRecordsRuleAndOpenBuilder({
		count = 1,
		auditReason = DEFAULT_AUDIT_REASON,
	} = {}) {
		// Read the same backend contract DTO that hydrates the builder UI. Do not
		// duplicate the result-handling/result-type policy in test fixtures.
		return cy
			.window()
			.then((win) =>
				win.frappe.call({
					method: "flexirule.ruleflow.api.get_contract_dto",
				})
			)
			.then((response) => {
				const dto = response?.message;
				const queryContract = dto?.action_type_contract?.["Query Records"];
				const fetchPolicy = queryContract?.operation_policies?.["Fetch Records"];
				// The backend DTO indexes operation contracts by operation name.
				const fetchOperationContract = dto?.operation_contract?.["Fetch Records"];
				const actionOverrides = fetchOperationContract?.["Rule Action"] || [];
				const mutationModeOverride = actionOverrides.find(
					(field) => field.fieldname === "mutation_mode"
				);
				const mutationMode =
					mutationModeOverride?.options?.[0] || queryContract?.allowed_mutations?.[0];
				const returnType =
					fetchPolicy?.default_return_type || queryContract?.default_return_type;

				expect(dto?.contract_version_hash, "backend contract DTO version hash").to.be.a(
					"string"
				).and.not.be.empty;
				expect(
					mutationModeOverride?.reqd,
					"backend requires Fetch Records result handling"
				).to.equal(1);

				return createRuleAndOpenBuilder(
					queryRecordsActions({ count, auditReason, mutationMode, returnType })
				);
			});
	}

	function suppressSchemaRefreshConfirmation() {
		cy.window().then((win) => {
			const frappe = win.frappe;
			const originalKey = "__flexiruleCypressOriginalConfirm";
			if (frappe[originalKey]) return;

			// The prompt is orthogonal to these configuration tests. Override it
			// idempotently instead of Sinon-stubbing the shared Frappe function;
			// direct restoration in afterEach avoids leaving wrapped callbacks behind.
			const originalConfirm = frappe.confirm;
			frappe[originalKey] = originalConfirm;
			frappe.confirm = function (message, onConfirm, onReject, primaryLabel, secondaryLabel) {
				if (/refresh the output schema/i.test(String(message))) {
					onReject?.();
					return;
				}
				return originalConfirm.call(
					this,
					message,
					onConfirm,
					onReject,
					primaryLabel,
					secondaryLabel
				);
			};
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
		ruleBuilderPage.setConfigField("Custom Limit", String(value));
	}

	function clearPermissionAuditReason() {
		cy.get(
			'.config-modal-container [data-fxr-fieldname="permission_audit_reason"] textarea, .config-modal-container [data-fxr-fieldname="permission_audit_reason"] input',
			{ timeout: 15000 }
		)
			.first()
			.should("be.visible")
			.clear();
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
		return cy.then(() => {
			expect(
				ruleName,
				"created Rule name is available before reading persisted state"
			).to.be.a("string").and.not.be.empty;
			return cy
				.request("/api/resource/Rule/" + encodeURIComponent(ruleName))
				.its("body.data");
		});
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
					capturedConsoleMessages.push({ level, message, url: win.location.href });
					return original.apply(win.console, args);
				};
			});
		});

		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	afterEach(function () {
		const name = ruleName;
		ruleName = null;

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

		cy.window({ log: false }).then((win) => {
			const frappe = win.frappe;
			const originalKey = "__flexiruleCypressOriginalConfirm";
			if (frappe?.[originalKey]) {
				frappe.confirm = frappe[originalKey];
				delete frappe[originalKey];
			}
		});

		if (name) {
			cy.request({
				method: "DELETE",
				url: "/api/resource/Rule/" + encodeURIComponent(name),
				failOnStatusCode: false,
			}).then(assertConsoleRegressions);
		} else {
			cy.then(assertConsoleRegressions);
		}
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
		cy.contains(".config-modal-container", "Query Mode", { timeout: 15000 }).should(
			"be.visible"
		);
		cy.contains(".config-modal-container", "Fetch Records").should("be.visible");
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
		createFetchRecordsRuleAndOpenBuilder();
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
		createFetchRecordsRuleAndOpenBuilder();
		openActionConfig("Fetch Records 1", true);
		setFetchRecordsLimit(21);
		clearPermissionAuditReason();

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
		createFetchRecordsRuleAndOpenBuilder({ count: 2 });

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
