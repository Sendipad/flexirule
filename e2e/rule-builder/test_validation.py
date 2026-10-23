import uuid

import pytest
from playwright.sync_api import Page


@pytest.mark.rule_builder
def test_valid_rule_graph_loads_without_validation_errors(
	authenticated_page: Page, base_url: str, frappe_api_client
):
	"""Verify that a newly created valid rule loads without displaying immediate modal validation errors."""
	rule_name = f"Validation Test {uuid.uuid4().hex[:6]}"
	doc = frappe_api_client.create_doc(
		"Rule",
		{
			"rule_name": rule_name,
			"trigger_type": "DocType Event",
			"reference_doctype": "User",
			"trigger_event": "After Insert",
			"is_active": 0,
		},
	)
	created_id = doc["name"]

	try:
		authenticated_page.goto(f"{base_url}/app/rule-builder/{created_id}")
		authenticated_page.wait_for_selector(".vue-flow", timeout=15000)

		# Ensure no crash dialog or unhandled error overlay appears
		assert not authenticated_page.locator(
			".modal-dialog.modal-danger, .msgprint-dialog.error"
		).is_visible()
	finally:
		frappe_api_client.delete_doc("Rule", created_id)


@pytest.mark.rule_builder
@pytest.mark.skip(
	reason="Client-side validation error badges and modal alerts for invalid action configurations are triggered upon activation/save flows."
)
def test_invalid_graph_validation_display():
	"""Placeholder for invalid graph validation display."""
	pass
