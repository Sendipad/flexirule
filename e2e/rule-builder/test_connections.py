import uuid

import pytest
from playwright.sync_api import Page


@pytest.mark.rule_builder
def test_canvas_edges_render(authenticated_page: Page, base_url: str, frappe_api_client):
	"""Verify that edges connecting default nodes render properly on the canvas."""
	rule_name = f"Connection Edge Test {uuid.uuid4().hex[:6]}"
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
		authenticated_page.wait_for_selector(".vue-flow__edge", timeout=15000)

		edges = authenticated_page.locator(".vue-flow__edge")
		assert edges.count() >= 1
	finally:
		frappe_api_client.delete_doc("Rule", created_id)


@pytest.mark.rule_builder
@pytest.mark.skip(
	reason="Interactive drag-and-drop node connection creation requires specific canvas edge-handle interaction helpers not yet exposed in initial E2E setup."
)
def test_interactive_node_connection():
	"""Placeholder for interactive node connection testing."""
	pass
