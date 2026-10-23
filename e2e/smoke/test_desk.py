import pytest
from playwright.sync_api import Page


@pytest.mark.smoke
def test_desk_loads(authenticated_page: Page, base_url: str):
	"""Verify that the Frappe Desk loads successfully upon navigation."""
	authenticated_page.goto(f"{base_url}/app")
	authenticated_page.wait_for_url("**/app**")
	authenticated_page.wait_for_load_state("networkidle")

	assert (
		"Workspace" in authenticated_page.title()
		or "Desk" in authenticated_page.title()
		or "/app" in authenticated_page.url
	)
	assert authenticated_page.locator(".navbar-brand, .navbar-home").is_visible()
