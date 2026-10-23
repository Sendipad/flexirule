import uuid

import pytest
from playwright.sync_api import Page


@pytest.mark.smoke
def test_rule_builder_loads_with_rule(authenticated_page: Page, base_url: str, frappe_api_client):
	"""Verify that opening Rule Builder with a valid Rule loads the asset bundle and renders the canvas."""
	rule_name = f"Smoke Test Rule {uuid.uuid4().hex[:6]}"
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
		authenticated_page.wait_for_selector(".vue-flow, #rule-builder-app, .rule-builder", timeout=15000)

		assert authenticated_page.locator(".vue-flow, #rule-builder-app, .rule-builder").is_visible()
	finally:
		frappe_api_client.delete_doc("Rule", created_id)
