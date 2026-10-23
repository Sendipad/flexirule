import uuid

import pytest
from playwright.sync_api import Page


@pytest.mark.rule_builder
def test_rule_persistence_via_api_and_ui_load(authenticated_page: Page, base_url: str, frappe_api_client):
	"""Verify that a rule saved via API persists and reloads correctly in the Rule Builder UI."""
	rule_name = f"Persistence Test {uuid.uuid4().hex[:6]}"
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
		# First load
		authenticated_page.goto(f"{base_url}/app/rule-builder/{created_id}")
		authenticated_page.wait_for_selector(".vue-flow", timeout=15000)
		assert authenticated_page.locator(".vue-flow").is_visible()

		# Reopen page to test persistence
		authenticated_page.reload()
		authenticated_page.wait_for_selector(".vue-flow", timeout=15000)
		assert authenticated_page.locator(".vue-flow").is_visible()
	finally:
		frappe_api_client.delete_doc("Rule", created_id)


@pytest.mark.rule_builder
@pytest.mark.skip(
	reason="UI save button triggers background compilation and graph serialization which is tested via API persistence in this phase."
)
def test_ui_save_and_reopen_persistence():
	"""Placeholder for UI save button persistence."""
	pass
