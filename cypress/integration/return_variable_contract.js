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
				expect((backendValidation.message?.errors || []).join("\\n")).to.match(
					/Missing Return Variable Process .*Return Variable Name/i
				);

				// Attempt a real Frappe save with the same invalid action payload.
				const savedRuleResponse = await win.frappe.call({
					method: "frappe.client.get",
					args: { doctype: "Rule", name: ruleDoc.name },
				});
				const invalidSaveDoc = {
					...savedRuleResponse.message,
					actions: invalidRulePayload.actions,
				};
				let serverSaveError = "";
				try {
					await win.frappe.call({
						method: "frappe.client.save",
						args: { doc: invalidSaveDoc },
						silent: true,
					});
				} catch (error) {
					serverSaveError = [
						error?.message,
						error?._server_messages,
						error?.exc,
						error?.responseText,
					]
						.map((value) =>
							typeof value === "string" ? value : JSON.stringify(value ?? "")
						)
						.join("\\n");
				}
				expect(
					serverSaveError,
					"backend Rule save rejects the same missing return variable"
				).to.match(/Return Variable Name/i);
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
