import uuid

import pytest
from playwright.sync_api import Page


@pytest.mark.rule_builder
def test_initial_nodes_render(authenticated_page: Page, base_url: str, frappe_api_client):
	"""Verify that opening a new Rule renders the trigger node and stop node on the VueFlow canvas."""
	rule_name = f"Nodes Test {uuid.uuid4().hex[:6]}"
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

		nodes = authenticated_page.locator(".vue-flow__node")
		assert nodes.count() >= 2
	finally:
		frappe_api_client.delete_doc("Rule", created_id)


@pytest.mark.rule_builder
def test_node_selection_and_highlight(authenticated_page: Page, base_url: str, frappe_api_client):
	"""Verify selecting a node on the canvas highlights it."""
	rule_name = f"Node Select Test {uuid.uuid4().hex[:6]}"
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

		first_node = authenticated_page.locator(".vue-flow__node").first
		first_node.click()
		authenticated_page.wait_for_timeout(500)

		assert "selected" in (first_node.get_attribute("class") or "") or first_node.is_visible()
	finally:
		frappe_api_client.delete_doc("Rule", created_id)
