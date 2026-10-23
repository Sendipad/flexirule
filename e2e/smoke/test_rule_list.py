import pytest
from playwright.sync_api import Page


@pytest.mark.smoke
def test_rule_list_loads(authenticated_page: Page, base_url: str):
	"""Verify that the Rule list view loads and displays core list elements."""
	authenticated_page.goto(f"{base_url}/app/rule")
	authenticated_page.wait_for_load_state("networkidle")

	assert "/app/rule" in authenticated_page.url
	authenticated_page.wait_for_selector(".page-head, .frappe-list", timeout=10000)
	assert authenticated_page.locator(".page-head").is_visible()
