import { ruleBuilderPage } from "../support/pages/RuleBuilderPage";

describe("Process return-variable contract parity", () => {
	beforeEach(() => {
		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	it("rejects a selected mutation mode when the allowlist is explicitly empty", () => {
		cy.create_test_rule_backend({
			rule_name: `Rule_Empty_Mutation_Allowlist_${Date.now()}`,
		}).then((doc) => {
			ruleBuilderPage.visitRule(doc.name);
			ruleBuilderPage.openVisualBuilder();

			cy.window().then((win) => {
				const contracts = win.flexirule?.contracts;
				expect(contracts, "shared contracts API").to.exist;
				expect(contracts.isMutationModeAllowed).to.be.a("function");

				const processName = "Validation";
				const operationName = "on_field_change";
				const operationContract =
					contracts.PROCESS_OPERATION_REGISTRY_V2?.[processName]?.[operationName];
				expect(operationContract, "backend-provided Process operation contract").to.exist;
				expect(operationContract.policy).to.exist;
				const originalAllowedMutations = operationContract.policy.allowed_mutations;
				operationContract.policy.allowed_mutations = [];
				try {
					const invalidAction = {
						action_type: "Process",
						process_name: processName,
						operation: operationName,
						mutation_mode: "Set Context Variable",
						return_variable: "result",
					};
					const result = contracts.validateAgainstContract(invalidAction);
					expect(result.valid).to.equal(false);
					expect(result.errors.join("\\n")).to.match(
						/Mutation mode .* is not allowed for Process/i
					);

					contracts.applyOutputPolicyDefaults(invalidAction, {
						preserveUserChoices: true,
					});
					expect(invalidAction.mutation_mode).to.equal(null);
				} finally {
					operationContract.policy.allowed_mutations = originalAllowedMutations;
				}
			});
		});
	});

	it("rejects a missing Process return variable in frontend and backend Rule saves", () => {
		const ruleName = `Rule_Process_Return_Required_${Date.now()}`;
		const processName = "Validation";
		const operationName = "on_field_change";
		const processConfig = {
			watched_fields: ["email_id", "phone", "mobile_no"],
			match_mode: "Any",
			store_result: "changed_fields",
		};

		cy.create_test_rule_backend({ rule_name: ruleName }).then((ruleDoc) => {
			ruleBuilderPage.visitRule(ruleDoc.name);
			ruleBuilderPage.openVisualBuilder();
			ruleBuilderPage.addNodeFromEdge("Process", "Missing Return Variable Process", null, processName, operationName);

			cy.window().then(async (win) => {
				const store = win.fxrRuleBuilder?.ruleStore;
				const contracts = win.flexirule?.contracts;
				expect(store, "whole-Rule builder store").to.exist;
				expect(contracts, "shared contracts API").to.exist;

				const process = store.processes.find((item) => item.name === processName);
				expect(process, "installed Process used by this regression").to.exist;
				expect(
					(process.operations || []).some((item) => item.func_name === operationName),
					"the selected operation exists on the Process"
				).to.equal(true);

				const node = store.nodes.find(
					(item) =>
						item.data?.action_type === "Process" &&
						item.data?.process_name === processName
				);
				expect(node, "Process node on the Rule graph").to.exist;
				// Native Process selection creates its node without the generic label
				// dialog. Give this test node a deterministic label before validation.
				node.data.action_label = "Missing Return Variable Process";
				node.label = "Missing Return Variable Process";
				Object.assign(node.data, {
					action_type: "Process",
					process_name: processName,
					operation: operationName,
					config: processConfig,
					return_type: "Yes / No",
					return_variable: null,
					mutation_mode: null,
					is_enabled: 1,
				});

				const frontendContractResult = contracts.validateAgainstContract(node.data);
				expect(
					contracts.requiresReturnVariable(node.data, {
						processName,
						operation: operationName,
					})
				).to.equal(true);
				expect(frontendContractResult.valid).to.equal(false);
				expect(frontendContractResult.errors.join("\\n")).to.match(/Return Variable Name/i);

				const processActionId = node.data.action_id || node.id;
				const processAction = {
					action_id: processActionId,
					action_type: "Process",
					action_label: "Missing Return Variable Process",
					process_name: processName,
					operation: operationName,
					config: JSON.stringify(processConfig),
					return_type: "Yes / No",
					return_variable: null,
					mutation_mode: null,
					is_enabled: 1,
				};
				const invalidRulePayload = {
					doctype: "Rule",
					name: ruleDoc.name,
					is_active: 0,
					trigger_type: "DocType Event",
					document_type: "Contact",
					trigger_event: "After Save",
					actions: [
						{
							action_id: "root",
							action_type: "Entry Action",
							action_label: "Start",
							is_enabled: 1,
							next_step_if_true: processActionId,
						},
						processAction,
					],
				};

				const backendValidation = await win.frappe.call({
					method: "flexirule.ruleflow.api.validate_rule_document",
					args: { mode: "draft", doc: invalidRulePayload },
				});
				expect(backendValidation.message?.valid).to.equal(false);
				const backendErrors = (backendValidation.message?.errors || []).join("\n");
				expect(backendErrors).to.include("Missing Return Variable Process");
				expect(backendErrors).to.include("Return Variable Name");

				// Exercise the actual whitelisted save endpoint without Frappe's
				// client-call error dialog covering the builder under test.
				const savedRuleResponse = await win.fetch(
					`/api/resource/Rule/${encodeURIComponent(ruleDoc.name)}`,
						{ credentials: "same-origin" }
					);
				expect(savedRuleResponse.ok, "baseline Rule can be fetched").to.equal(true);
				const savedRulePayload = await savedRuleResponse.json();
				const invalidSaveDoc = {
					...savedRulePayload.data,
					actions: invalidRulePayload.actions,
				};
				const serverSaveResponse = await win.fetch("/api/method/frappe.client.save", {
					method: "POST",
					credentials: "same-origin",
					headers: {
						Accept: "application/json",
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token": win.frappe.csrf_token,
					},
					body: JSON.stringify({ doc: invalidSaveDoc }),
				});
				const serverSaveBody = await serverSaveResponse.text();
				expect(
					serverSaveResponse.status,
					"backend Rule save rejects the invalid document"
				).to.be.greaterThan(299);
				expect(serverSaveBody).to.include("Return Variable Name");
			});

			cy.window().then((win) => {
				cy.stub(win.frappe, "msgprint").as("saveValidationMessage");
			});
			cy.get('button:contains("Save Rule")').click();
			cy.get("@saveValidationMessage").should("have.been.called");
			cy.get("@saveValidationMessage").should((stub) => {
				const messages = stub
					.getCalls()
					.map((call) => JSON.stringify(call.args[0]))
					.join("\\n");
				expect(messages).to.match(/Validation Error/i);
				expect(messages).to.match(/Return Variable Name/i);
			});
		});
	});
});
