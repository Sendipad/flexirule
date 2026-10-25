class RuleBuilderPage {
	visitRule(ruleName) {
		cy.visit(`/app/rule/${encodeURIComponent(ruleName)}`);
		cy.get(".page-head", { timeout: 30000 }).should("exist");
	}

	openVisualBuilder() {
		cy.get('.primary-action:contains("Visual Builder")', { timeout: 15000 })
			.should("be.visible")
			.click();
		cy.url().should("include", "/app/rule-builder/");
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
	}

	addNodeFromEdge(nodeType, label, handle = null, optionLabel = null) {
		if (handle) {
			cy.get(`.vue-flow__edge-path[data-source-handle="${handle}"]`).trigger("mouseover", {
				force: true,
			});
			cy.get(`.edge-add-button[data-source-handle="${handle}"]`).click({ force: true });
		} else {
			cy.get(".edge-add-button").last().click({ force: true });
		}

		cy.get(`.result-item.is-option:contains("${nodeType}")`).click();

		// Some Frappe actions (for example Process) open a second chooser for
		// the record that will back the action node.
		if (optionLabel) {
			cy.get(".result-item.is-option", { timeout: 15000 })
				.contains(optionLabel, { timeout: 15000 })
				.click({ force: true });
		}

		// Selecting a concrete Process inserts the node directly; it does not
		// open the separate label-entry dialog used by other action types.
		if (label && !optionLabel) {
			cy.get(".labeling-container", { timeout: 10000 }).should("be.visible");
			cy.get(".labeling-container input").type(label);
			cy.get(".labeling-container button.btn-primary").click();
		}
	}

	selectNode(nodeClass) {
		cy.get(`.vue-flow__node .${nodeClass}`).last().click({ force: true });
		cy.get(".action-settings-container", { timeout: 10000 }).should("be.visible");
	}

	configureNodeLabel(newLabel) {
		cy.get('.action-settings-container [data-fieldname="action_label"] input')
			.clear()
			.type(newLabel);
	}

	closeSettingsPanel() {
		cy.get(".vue-flow").click(10, 10, { force: true });
		cy.get(".action-settings-container").should("not.exist");
	}

	saveRule() {
		cy.contains("button", "Save Rule").click();
		cy.get(".desk-alert.green", { timeout: 20000 }).should("contain", "Saved");
	}

	deleteSelectedNode() {
		cy.contains("button", "Delete Action").click();
		cy.get(".modal-footer button").contains("Yes").click();
	}
}

export const ruleBuilderPage = new RuleBuilderPage();
