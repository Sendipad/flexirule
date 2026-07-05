describe("Rule Builder E2E Tests", () => {
	beforeEach(() => {
		cy.login();
		cy.visit("/app");
		// Wait for the desk to be fully loaded
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	it("Creates a new rule, adds actions in the builder, and verifies persistence", () => {
		const ruleName = `Test Rule ${Date.now()}`;

		// 1. Create a new Rule
		cy.new_form("Rule");
		cy.fill_field("rule_name", ruleName);
		cy.fill_field("document_type", "Contact", "Link");
		cy.get('select[data-fieldname="trigger_event"]').select("After Save");
		cy.save();

		// 2. Open Visual Builder
		cy.get('.primary-action:contains("Visual Builder")').click();
		cy.url().should("include", "/rule-builder/");
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");

		// 3. Add an Assignment action
		cy.get(".edge-add-button").last().click();
		cy.get('.result-item.is-option:contains("Assignment")').click();

		// Set label in labeling container
		cy.get(".labeling-container", { timeout: 10000 }).should("be.visible");
		cy.get(".labeling-container input").type("Set Initial Score");
		cy.get(".labeling-container button.btn-primary").click();

		// Verify node added
		cy.get(".vue-flow__node .assignment", { timeout: 10000 }).should("be.visible");
		cy.get(".vue-flow__node .assignment .node-title").should("contain", "Set Initial Score");

		// 4. Configure the node
		cy.get(".vue-flow__node .assignment").last().click();
		cy.get(".action-settings-container", { timeout: 10000 }).should("be.visible");
		cy.get('.action-settings-container [data-fieldname="action_label"] input')
			.clear()
			.type("Calculate Global Score");
		cy.get(".vue-flow__node .assignment .node-title").should(
			"contain",
			"Calculate Global Score"
		);

		// Click outside to close settings
		cy.get(".vue-flow").click(10, 10);
		cy.get(".action-settings-container").should("not.exist");

		// 5. Add a Notify action
		cy.get(".edge-add-button").last().click();
		cy.get('.result-item.is-option:contains("Notify")').click();
		cy.get(".labeling-container input").type("Alert Manager");
		cy.get(".labeling-container button.btn-primary").click();

		// Configure Notify action
		cy.get(".vue-flow__node .notify").last().click();
		cy.get('.action-settings-container [data-fieldname="is_async"] input').check();
		cy.get('.action-settings-container [data-fieldname="on_error"] select').select("Ignore");
		cy.get(".vue-flow").click(10, 10);

		// 6. Save Rule
		cy.get('button:contains("Save Rule")').click();
		cy.get(".desk-alert.green", { timeout: 20000 }).should("contain", "Saved");

		// 7. Reload and verify persistence
		cy.reload();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.get(".vue-flow__node .assignment").should("be.visible");
		cy.get(".vue-flow__node .assignment .node-title").should(
			"contain",
			"Calculate Global Score"
		);
		cy.get(".vue-flow__node .notify").should("be.visible");
		cy.get(".vue-flow__node .notify .node-title").should("contain", "Alert Manager");

		// 8. Delete an action
		cy.get(".vue-flow__node .notify").last().click();
		cy.get(".action-settings-container").should("be.visible");
		cy.get('button:contains("Delete Action")').click();
		// Assuming there is a confirmation dialog
		cy.get('.modal-footer button:contains("Yes")').click();
		cy.get(".vue-flow__node .notify").should("not.exist");

		// Save again
		cy.get('button:contains("Save Rule")').click();
		cy.get(".desk-alert.green").should("contain", "Saved");
	});

	it("Handles nested groups and branching (Condition)", () => {
		const ruleName = `Branching Rule ${Date.now()}`;

		cy.new_form("Rule");
		cy.fill_field("rule_name", ruleName);
		cy.fill_field("document_type", "Contact", "Link");
		cy.get('select[data-fieldname="trigger_event"]').select("After Save");
		cy.save();

		cy.get('.primary-action:contains("Visual Builder")').click();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");

		// Add Condition node
		cy.get(".edge-add-button").last().click();
		cy.get('.result-item.is-option:contains("Condition")').click();
		cy.get(".labeling-container input").type("Check Score");
		cy.get(".labeling-container button.btn-primary").click();

		cy.get(".vue-flow__node .condition", { timeout: 10000 }).should("be.visible");

		// Add action to TRUE branch
		cy.get('.vue-flow__node .condition [data-handleid="true"]').should("exist");
		// Trigger hover on the edge path coming from true handle
		cy.get('.vue-flow__edge-path[data-source-handle="true"]').trigger("mouseover", {
			force: true,
		});
		cy.get('.edge-add-button[data-source-handle="true"]').click({ force: true });
		cy.get('.result-item.is-option:contains("Assignment")').click();
		cy.get(".labeling-container input").type("High Score Action");
		cy.get(".labeling-container button.btn-primary").click();

		// Add action to FALSE branch
		cy.get('.vue-flow__edge-path[data-source-handle="false"]').trigger("mouseover", {
			force: true,
		});
		cy.get('.edge-add-button[data-source-handle="false"]').click({ force: true });
		cy.get('.result-item.is-option:contains("Notify")').click();
		cy.get(".labeling-container input").type("Low Score Alert");
		cy.get(".labeling-container button.btn-primary").click();

		cy.get('button:contains("Save Rule")').click();
		cy.get(".desk-alert.green").should("contain", "Saved");

		// Verify both branches saved
		cy.reload();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.get(".vue-flow__node .assignment .node-title").should("contain", "High Score Action");
		cy.get(".vue-flow__node .notify .node-title").should("contain", "Low Score Alert");
	});
});
