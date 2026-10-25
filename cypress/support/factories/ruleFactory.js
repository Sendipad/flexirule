Cypress.Commands.add("create_test_rule_backend", (ruleData = {}) => {
	const defaultRule = {
		doctype: "Rule",
		rule_name: ruleData.rule_name || `Test_Rule_${Date.now()}`,
		document_type: ruleData.document_type || "Contact",
		trigger_event: ruleData.trigger_event || "After Save",
		is_active: ruleData.is_active ?? 0,
		is_draft: ruleData.is_draft ?? 0,
	};

	return cy.insert_doc("Rule", { ...defaultRule, ...ruleData });
});

Cypress.Commands.add("cleanup_test_rule", (ruleName) => {
	if (!ruleName) return;
	return cy.request({
		method: "DELETE",
		url: `/api/resource/Rule/${encodeURIComponent(ruleName)}`,
		failOnStatusCode: false,
	});
});
