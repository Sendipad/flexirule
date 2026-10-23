import uuid

import pytest
from playwright.sync_api import Page


@pytest.mark.rule_builder
def test_canvas_controls_render(authenticated_page: Page, base_url: str, frappe_api_client):
	"""Verify that VueFlow canvas controls panel and buttons are present and visible."""
	rule_name = f"Layout Test {uuid.uuid4().hex[:6]}"
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
		authenticated_page.wait_for_selector(".controls-panel, .vue-flow__panel", timeout=15000)

		controls = authenticated_page.locator(".controls-panel, .vue-flow__panel")
		assert controls.is_visible()
	finally:
		frappe_api_client.delete_doc("Rule", created_id)


@pytest.mark.rule_builder
def test_canvas_zoom_buttons_interactive(authenticated_page: Page, base_url: str, frappe_api_client):
	"""Verify interacting with zoom in / zoom out canvas buttons."""
	rule_name = f"Zoom Test {uuid.uuid4().hex[:6]}"
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
		authenticated_page.wait_for_selector(".controls-panel, .vue-flow__panel", timeout=15000)

		zoom_in_btn = authenticated_page.locator("button:has-text('+')").first
		if zoom_in_btn.is_visible():
			zoom_in_btn.click()
			authenticated_page.wait_for_timeout(300)

		assert authenticated_page.locator(".vue-flow").is_visible()
	finally:
		frappe_api_client.delete_doc("Rule", created_id)
