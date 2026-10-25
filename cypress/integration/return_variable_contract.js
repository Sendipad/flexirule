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
		const processActionId = "process_return";
		const validProcessAction = {
			action_id: processActionId,
			action_type: "Process",
			action_label: "Missing Return Variable Process",
			process_name: processName,
			operation: operationName,
			config: JSON.stringify(processConfig),
			return_type: "Yes / No",
			return_variable: "changed_fields",
			mutation_mode: null,
			is_enabled: 1,
			next_step_if_true: "node_end",
		};
		const baselineActions = [
			{
				action_id: "root",
				action_type: "Entry Action",
				action_label: "Start",
				is_enabled: 1,
				next_step_if_true: processActionId,
			},
			validProcessAction,
			{
				action_id: "node_end",
				action_type: "Stop",
				action_label: "End",
				operation: "Success",
				is_enabled: 1,
			},
		];

		cy.window()
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
							actions: baselineActions,
						},
					},
				})
			)
			.then((response) => {
				const ruleDoc = response?.message;
				expect(ruleDoc?.name, "created Rule with the backend-seeded Process action")
					.to.be.a("string")
					.and.not.be.empty;
				expect(
					(ruleDoc?.actions || []).some((action) => action.action_id === processActionId),
					"insert response contains the seeded Process action"
				).to.equal(true);
				ruleBuilderPage.visitRule(ruleDoc.name);
			ruleBuilderPage.openVisualBuilder();

			// The canvas shell can render before Rule actions have finished hydrating.
			// Wait for the seeded action itself, then inspect the shared graph store.
			cy.contains(".vue-flow__node", "Missing Return Variable Process", {
				timeout: 30000,
			})
				.should("be.visible");

			cy.window().then(async (win) => {
				const store = win.fxrRuleBuilder?.ruleStore;
				const contracts = win.flexirule?.contracts;
				expect(store, "whole-Rule builder store").to.exist;
				expect(contracts, "shared contracts API").to.exist;

				const processOperation =
					contracts.PROCESS_OPERATION_REGISTRY_V2?.[processName]?.[operationName];
				expect(processOperation, "backend-provided Process operation contract").to.exist;
				expect(processOperation.policy, "resolved operation policy").to.exist;

				const nodeIndex = store.nodes.findIndex(
					(item) =>
						item.data?.action_type === "Process" &&
						item.data?.process_name === processName
				);
				expect(nodeIndex, "seeded Process node on the Rule graph").to.be.at.least(0);
				const node = store.nodes[nodeIndex];
				const invalidData = {
					...node.data,
					action_label: "Missing Return Variable Process",
					action_type: "Process",
					process_name: processName,
					operation: operationName,
					config: processConfig,
					return_type: "Yes / No",
					return_variable: null,
					mutation_mode: null,
					is_enabled: 1,
				};
				store.nodes.splice(nodeIndex, 1, {
					...node,
					label: invalidData.action_label,
					data: invalidData,
				});
				store.touch_node?.(node.id);
				store.mark_dirty?.();

				const frontendContractResult = contracts.validateAgainstContract(invalidData);
				expect(
					contracts.requiresReturnVariable(invalidData, {
						processName,
						operation: operationName,
					})
				).to.equal(true);
				expect(frontendContractResult.valid).to.equal(false);
				expect(frontendContractResult.errors.join("\n")).to.match(/Return Variable Name/i);

				const invalidProcessAction = {
					...validProcessAction,
					return_variable: null,
				};
				const invalidActions = [
					{
						action_id: "root",
						action_type: "Entry Action",
						action_label: "Start",
						is_enabled: 1,
						next_step_if_true: processActionId,
					},
					invalidProcessAction,
					{
						action_id: "node_end",
						action_type: "Stop",
						action_label: "End",
						operation: "Success",
						is_enabled: 1,
					},
				];
				const invalidRulePayload = {
					doctype: "Rule",
					name: ruleDoc.name,
					is_active: 0,
					trigger_type: "DocType Event",
					document_type: "Contact",
					trigger_event: "After Save",
					actions: invalidActions,
				};

				const backendValidation = await win.frappe.call({
					method: "flexirule.ruleflow.api.validate_rule_document",
					args: { mode: "draft", doc: invalidRulePayload },
				});
				expect(backendValidation.message?.valid).to.equal(false);
				const backendErrors = (backendValidation.message?.errors || []).join("\n");
				expect(backendErrors).to.include("Missing Return Variable Process");
				expect(backendErrors).to.include("Return Variable Name");

				// Exercise the same backend save endpoint without showing a Frappe
				// error dialog; the UI save assertion below covers the visible behavior.
				const savedRuleResponse = await win.fetch(
					`/api/resource/Rule/${encodeURIComponent(ruleDoc.name)}`,
					{ credentials: "same-origin" }
				);
				expect(savedRuleResponse.ok, "baseline Rule can be fetched").to.equal(true);
				const savedRulePayload = await savedRuleResponse.json();
				const invalidSaveDoc = { ...savedRulePayload.data, actions: invalidActions };
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
			cy.get('button:contains("Save Rule")')
				.should("be.visible")
				.and("be.enabled")
				.click();
			cy.get("@saveValidationMessage").should("have.been.called");
			cy.get("@saveValidationMessage").should((stub) => {
				const messages = stub
					.getCalls()
					.map((call) => JSON.stringify(call.args[0]))
					.join("\n");
				expect(messages).to.match(/Validation Error/i);
				expect(messages).to.match(/Return Variable Name/i);
			});
		});
	});
});
