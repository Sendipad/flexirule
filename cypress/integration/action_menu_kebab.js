/* global afterEach */
import { isConsoleRegressionMessage } from "../support/regression_guards.mjs";

describe("GenericGrid & TreeBuilder ActionMenu Kebab Coverage", () => {
	let ruleName = null;
	let capturedConsoleMessages = [];

	function defaultRuleActions() {
		return [
			{
				action_id: "root",
				action_label: "Start",
				action_type: "Entry Action",
				is_enabled: 1,
				next_step_if_true: "fetch_1",
			},
			{
				action_id: "fetch_1",
				action_label: "Fetch Records 1",
				action_type: "Query Records",
				operation: "Fetch Records",
				reference_doctype: "Contact",
				is_enabled: 1,
				ignore_permissions: 1,
				permission_audit_reason: "Action menu test audit reason",
				writes_to: "Context",
				return_variable: "fetched_contacts",
				mutation_mode: "Set New Variable",
				return_type: "List of Records",
				filters: [
					["Contact", "first_name", "=", { mode: "static", value: "Alice" }],
					["Contact", "last_name", "=", { mode: "static", value: "Smith" }],
				],
				fields: [
					{ fieldname: "first_name", label: "First Name" },
					{ fieldname: "last_name", label: "Last Name" },
				],
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

	function createRuleAndOpenBuilder(actions = defaultRuleActions()) {
		const suffix = Date.now().toString() + "_" + Math.floor(Math.random() * 1000);
		ruleName = "Cypress_ActionMenu_" + suffix;

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

	beforeEach(() => {
		capturedConsoleMessages = [];
		cy.on("window:before:load", (win) => {
			["error", "warn"].forEach((level) => {
				const original = win.console[level].bind(win.console);
				win.console[level] = (...args) => {
					const message = args
						.map((arg) => (typeof arg === "string" ? arg : JSON.stringify(arg)))
						.join(" ");
					capturedConsoleMessages.push({ level, message });
					return original(...args);
				};
			});
		});

		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	afterEach(() => {
		const failures = capturedConsoleMessages.filter(({ message }) =>
			isConsoleRegressionMessage(message)
		);
		expect(failures, "console regressions occurred during test execution").to.deep.equal([]);

		if (!ruleName) return;
		const name = ruleName;
		ruleName = null;
		cy.window().then((win) => {
			if (win.frappe?.call) {
				win.frappe.call({
					method: "frappe.client.delete",
					args: { doctype: "Rule", name },
				});
			}
		});
	});

	it("renders ActionMenu in TreeBuilder and GenericGrid and supports menu actions", () => {
		createRuleAndOpenBuilder();

		// Open configuration modal for the Fetch Records action node
		cy.contains(".vue-flow__node", "Fetch Records 1").dblclick();
		cy.get(".config-modal-container", { timeout: 20000 }).should("be.visible");

		// --- GenericGrid action menu checks ---
		// Find rows in OutputFieldsEditor GenericGrid
		cy.get(".fxr-generic-grid-data").should("exist");
		cy.get(".fxr-generic-grid-row").should("have.length.at.least", 1);

		// The row action should contain our kebab ActionMenu trigger
		cy.get(".fxr-generic-grid-row .fxr-action-menu__trigger")
			.first()
			.should("be.visible")
			.click();

		// Menu items dropdown should be visible in Teleport
		cy.get(".fxr-action-menu__items").should("be.visible");
		cy.get(".fxr-action-menu__item").should("have.length.at.least", 5);

		// Check menu item labels
		cy.contains(".fxr-action-menu__item", "Duplicate").should("exist");
		cy.contains(".fxr-action-menu__item", "Copy").should("exist");
		cy.contains(".fxr-action-menu__item", "Delete").should("exist");

		// Test Duplicate row action
		cy.contains(".fxr-action-menu__item", "Duplicate").click();
		cy.get(".fxr-action-menu__items").should("not.exist");

		// --- TreeBuilder action menu checks ---
		// Check TreeBuilder leaf kebab menu
		cy.get(".tree-leaf .fxr-action-menu__trigger").first().should("be.visible").click();

		cy.get(".fxr-action-menu__items").should("be.visible");
		cy.contains(".fxr-action-menu__item", "Edit").should("exist");
		cy.contains(".fxr-action-menu__item", "Move Up").should("exist");
		cy.contains(".fxr-action-menu__item", "Move Down").should("exist");
		cy.contains(".fxr-action-menu__item", "Duplicate").should("exist");
		cy.contains(".fxr-action-menu__item", "Copy").should("exist");
		cy.contains(".fxr-action-menu__item", "Delete").should("exist");

		// Close modal
		cy.get(".config-modal-container").type("{esc}");
	});
});
