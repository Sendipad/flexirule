describe("FlexiRule Rule List & Workspace E2E Suite", () => {
	beforeEach(() => {
		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	it("1. Rule List Dedicated Builder Action & Column Verification", () => {
		const ruleName = `Rule_List_Test_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			cy.visit("/app/rule");
			cy.get(".list-row-container", { timeout: 30000 }).should("be.visible");

			// Verify dedicated first-column button exists in row
			cy.get('.list-row-container .list-row').first().within(() => {
				cy.get('button[title*="Open Rule Builder"]').should("exist");
			});

			// Click Builder action button and verify navigation to Rule Builder route
			cy.get('.list-row-container .list-row').first().find('button[title*="Open Rule Builder"]').first().click({ force: true });
			cy.url({ timeout: 15000 }).should("include", "/app/rule-builder/");
		});
	});

	it("2. Native RuleFlow Workspace Loading & Component Verification", () => {
		cy.visit("/app/workspace/ruleflow");
		cy.get(".workspace-header", { timeout: 30000 }).should("be.visible");

		// Verify Shortcuts
		cy.contains(".shortcut-widget", "New Rule").should("be.visible");
		cy.contains(".shortcut-widget", "Rule List").should("be.visible");
		cy.contains(".shortcut-widget", "Rule Builder").should("be.visible");
		cy.contains(".shortcut-widget", "Execution Logs").should("be.visible");

		// Verify Number Cards
		cy.contains(".number-card-widget", "Total Rules").should("be.visible");
		cy.contains(".number-card-widget", "Active Rules").should("be.visible");
	});
});
