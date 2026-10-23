import os
import pathlib

import pytest
import requests  # type: ignore[import-untyped]
from playwright.sync_api import Browser, BrowserContext, Page


def get_base_url() -> str:
	return os.getenv("FRAPPE_SITE_URL", "http://127.0.0.1:8000").rstrip("/")


def get_credentials():
	user = os.getenv("FRAPPE_USER", "Administrator")
	password = os.getenv("FRAPPE_PASSWORD")
	if not password:
		pytest.fail(
			"FRAPPE_PASSWORD environment variable is not set. "
			"Please set FRAPPE_PASSWORD before running E2E tests."
		)
	return user, password


@pytest.fixture(scope="session")
def base_url() -> str:
	return get_base_url()


@pytest.fixture(scope="session")
def auth_storage_state(tmp_path_factory, browser_type) -> pathlib.Path:
	"""Authenticates once per worker and produces an isolated storage state JSON file."""
	site_url = get_base_url()
	user, password = get_credentials()

	auth_dir = pathlib.Path(".auth")
	auth_dir.mkdir(exist_ok=True)

	worker_id = os.getenv("PYTEST_XDIST_WORKER", "master")
	state_file = auth_dir / f"user_state_{worker_id}.json"

	browser = browser_type.launch(headless=True)
	context = browser.new_context()
	page = context.new_page()

	page.goto(f"{site_url}/login")
	page.fill("#login_email", user)
	page.fill("#login_password", password)
	page.click("button:has-text('Login')")
	page.wait_for_url("**/app**", timeout=15000)

	context.storage_state(path=str(state_file))
	browser.close()

	return state_file


@pytest.fixture(scope="function")
def authenticated_context(browser: Browser, auth_storage_state: pathlib.Path) -> BrowserContext:
	"""Creates a fresh browser context per test loaded with worker authentication state."""
	context = browser.new_context(storage_state=str(auth_storage_state))
	yield context
	context.close()


@pytest.fixture(scope="function")
def authenticated_page(authenticated_context: BrowserContext, request) -> Page:
	"""Provides a fresh authenticated page and captures failure diagnostics."""
	page = authenticated_context.new_page()

	console_logs = []
	network_errors = []

	def on_console(msg):
		console_logs.append(f"[{msg.type}] {msg.text}")

	def on_response(response):
		if response.status >= 400:
			network_errors.append(f"{response.status} {response.url}")

	page.on("console", on_console)
	page.on("response", on_response)

	yield page

	# Post-test failure diagnostic capture
	if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
		artifacts_dir = pathlib.Path("artifacts/failure_diagnostics")
		artifacts_dir.mkdir(parents=True, exist_ok=True)
		test_name = request.node.name

		try:
			screenshot_path = artifacts_dir / f"{test_name}.png"
			page.screenshot(path=str(screenshot_path), full_page=True)
		except Exception:
			pass

		log_path = artifacts_dir / f"{test_name}_diagnostics.txt"
		diagnostics_content = f"Test: {test_name}\n" f"URL: {page.url}\n\n" "--- CONSOLE LOGS ---\n" + (
			"\n".join(console_logs) if console_logs else "None\n"
		) + "\n\n--- NETWORK ERRORS ---\n" + ("\n".join(network_errors) if network_errors else "None\n")
		log_path.write_text(
			diagnostics_content, encoding="utf-8"
		)  # nosemgrep: frappe-security-file-traversal


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
	"""Exposes test call status on request.node for diagnostics capture."""
	outcome = yield
	rep = outcome.get_result()
	setattr(item, f"rep_{rep.when}", rep)


class FrappeAPIClient:
	"""Helper client for managing test records directly via Frappe REST API."""

	def __init__(self, base_url: str, user: str, password: str):
		self.base_url = base_url
		self.session = requests.Session()
		login_res = self.session.post(
			f"{self.base_url}/api/method/login",
			data={"usr": user, "pwd": password},
		)
		if login_res.status_code != 200:
			raise RuntimeError(f"API Login failed: {login_res.text}")

	def create_doc(self, doctype: str, data: dict) -> dict:
		import json

		res = self.session.post(
			f"{self.base_url}/api/resource/{doctype}",
			data={"data": json.dumps(data)},
		)
		if res.status_code not in (200, 201):
			raise RuntimeError(f"Failed to create {doctype}: {res.text}")
		return res.json().get("data")

	def delete_doc(self, doctype: str, name: str):
		res = self.session.delete(f"{self.base_url}/api/resource/{doctype}/{name}")
		return res.status_code == 200


@pytest.fixture(scope="session")
def frappe_api_client(base_url: str) -> FrappeAPIClient:
	user, password = get_credentials()
	return FrappeAPIClient(base_url=base_url, user=user, password=password)
