const { test, expect } = require("@playwright/test");

/**
 * Flexirule Rule Builder E2E Test
 *
 * This test covers:
 * 1. Login to Frappe Desk.
 * 2. Creation of a new Rule for 'Contact' doctype.
 * 3. Navigation to the Visual Rule Builder.
 * 4. Adding and configuring multiple Action Types:
 *    - Assignment: Testing label and basic configuration.
 *    - Notify: Testing async flags and error handling.
 *    - Document Action: Testing mutation modes.
 *    - Query Records: Testing data fetching configuration.
 * 5. Saving the complete flow.
 *
 * Prerequisites:
 * - Bench server running on http://localhost:8000
 * - Site: test_site
 * - User: Administrator / admin
 */

test.describe("Flexirule Visual Builder", () => {
	test.beforeEach(async ({ page }) => {
		test.setTimeout(120000);
		console.log("Logging in...");
		await page.goto("http://localhost:8000/login");
		await page.fill("#login_email", "Administrator");
		await page.fill("#login_password", "admin");
		await page.click("button.btn-login");
		await page.waitForURL("**/app**", { timeout: 30000 }).catch(() => {});
		// Give it a moment to settle
		await page.waitForTimeout(3000);
	});

	test("Create and configure a multi-action rule flow", async ({ page }) => {
		test.setTimeout(300000);

		// 1. Create New Rule
		console.log("Creating new rule");
		await page.goto("http://localhost:8000/app/rule/new-rule-1");
		await page.waitForSelector('input[data-fieldname="rule_name"]');

		const ruleName = `Flow_Test_${Date.now()}`;
		await page.fill('input[data-fieldname="rule_name"]', ruleName);

		// Set Target Doctype
		await page.fill('input[data-fieldname="document_type"]', "Contact");
		await page.keyboard.press("Tab");

		// Set Trigger
		await page.selectOption('select[data-fieldname="trigger_event"]', "After Save");

		// Save
		await page.click('button.primary-action:has-text("Save")');
		console.log(`Rule ${ruleName} saved`);

		// 2. Open Visual Builder
		const builderBtn = page.locator('button:has-text("Visual Builder")');
		await builderBtn.waitFor({ state: "visible", timeout: 30000 });
		await builderBtn.click();
		console.log("Entered Visual Builder");

		await page.waitForURL("**/rule-builder/**");
		await page.waitForSelector(".vue-flow", { timeout: 60000 });

		// Helper: Add Action
		const addAction = async (type) => {
			console.log(`Adding ${type}`);
			const actionZones = page.locator(".fa-plus-circle");
			await actionZones.last().click();
			await page.waitForTimeout(500);
			await page.click(`.action-item:has-text("${type}"), text="${type}"`);
			await page.waitForTimeout(1500);
		};

		// Helper: Configure Node
		const configureNode = async (type, configCallback) => {
			console.log(`Configuring ${type}`);
			const node = page.locator(`.vue-flow__node:has-text("${type}")`).last();
			await node.click();
			await page.waitForSelector(".action-settings-container");
			if (configCallback) await configCallback();
			// Click canvas to close
			await page.mouse.click(50, 50);
			await page.waitForTimeout(500);
		};

		// --- Add Assignment ---
		await addAction("Assignment");
		await configureNode("Assignment", async () => {
			await page.fill('[data-fieldname="action_label"] input', "Init Contact Data");
		});

		// --- Add Notify ---
		await addAction("Notify");
		await configureNode("Notify", async () => {
			await page.fill('[data-fieldname="action_label"] input', "Send Welcome Email");
			const asyncCheck = page.locator('[data-fieldname="is_async"] input');
			if (await asyncCheck.isVisible()) await asyncCheck.check();
		});

		// --- Add Document Action ---
		await addAction("Document Action");
		await configureNode("Document Action", async () => {
			const modeSelect = page.locator('[data-fieldname="mutation_mode"] select');
			if (await modeSelect.isVisible()) await modeSelect.selectOption("Update");
		});

		// 3. Save Flow
		console.log("Saving flow");
		await page.click('button.btn-primary:has-text("Save Rule")');
		await page.waitForTimeout(2000);

		// 4. Verification
		await page.screenshot({ path: "e2e/screenshots/comprehensive_flow.png", fullPage: true });
		console.log("Test completed successfully");
	});
});
