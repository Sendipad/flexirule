describe("FlexiRule Rule List & Workspace E2E Suite", () => {
	let createdRuleName = null;

	beforeEach(() => {
		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	afterEach(() => {
		if (!createdRuleName) return;
		const ruleName = createdRuleName;
		createdRuleName = null;
		cy.request({
			method: "DELETE",
			url: `/api/resource/Rule/${encodeURIComponent(ruleName)}`,
			failOnStatusCode: false,
		});
	});

	it("1. Rule List Dedicated Builder Action & Column Verification", () => {
		const ruleName = `Rule_List_Test_${Date.now()}`;

		cy.create_test_rule_backend({ rule_name: ruleName }).then((doc) => {
			createdRuleName = doc.name;
			cy.visit("/app/rule");
			cy.get(".list-row-container", { timeout: 30000 }).should("be.visible");

			// Verify dedicated first-column button exists in row
			cy.contains(".list-row-container .list-row", ruleName)
				.should("be.visible")
				.within(() => {
					cy.get('button[title*="Open Rule Builder"]').should("exist");
				});

			// Click the action on the row created by this test.
			cy.contains(".list-row-container .list-row", ruleName)
				.find('button[title*="Open Rule Builder"]')
				.first()
				.click({ force: true });
			cy.url({ timeout: 15000 }).should("include", "/app/rule-builder/");
		});
	});

	it("2. Native RuleFlow Workspace Loading & Component Verification", () => {
		// Frappe routes workspaces by their slug (the Workspace name is RuleFlow),
		// not through the generic Workspace DocType form route.
		cy.visit("/app/ruleflow");
		cy.get("#editorjs", { timeout: 30000 }).should("be.visible");
		cy.get(".ce-block", { timeout: 30000 }).should("have.length.at.least", 1);

		// Assert the native Frappe Workspace block types rendered from the fixture.
		cy.contains(".shortcut-widget-box", "New Rule").should("be.visible");
		cy.contains(".shortcut-widget-box", "Rule List").should("be.visible");
		cy.contains(".shortcut-widget-box", "Rule Builder").should("be.visible");
		cy.contains(".shortcut-widget-box", "Execution Logs").should("be.visible");

		cy.contains(".number-widget-box", "Total Rules").should("be.visible");
		cy.contains(".number-widget-box", "Active Rules").should("be.visible");
	});
});
