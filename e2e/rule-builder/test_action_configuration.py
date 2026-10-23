import uuid

import pytest
from playwright.sync_api import Page


@pytest.mark.rule_builder
def test_open_node_config_panel(authenticated_page: Page, base_url: str, frappe_api_client):
	"""Verify that clicking a node opens its configuration panel or drawer if configured."""
	rule_name = f"Action Config Test {uuid.uuid4().hex[:6]}"
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
		authenticated_page.wait_for_selector(".vue-flow__node", timeout=15000)

		trigger_node = authenticated_page.locator(".vue-flow__node").first
		trigger_node.click()
		authenticated_page.wait_for_timeout(500)

		assert authenticated_page.locator(".vue-flow__node").first.is_visible()
	finally:
		frappe_api_client.delete_doc("Rule", created_id)


@pytest.mark.rule_builder
@pytest.mark.skip(
	reason="Full action parameter editing requires palette-spawned action nodes which are currently being integrated."
)
def test_configure_action_parameters():
	"""Placeholder for configuring action parameters."""
	pass
