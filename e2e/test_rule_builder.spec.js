const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

test.describe("Flexirule Visual Builder - Comprehensive Flow", () => {
	const SCREENSHOTS_DIR = "e2e/screenshots";

	test.beforeAll(async () => {
		if (!fs.existsSync(SCREENSHOTS_DIR)) {
			fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
		}
	});

	test.beforeEach(async ({ page }) => {
		test.setTimeout(120000);
		console.log("Logging in to Frappe Desk...");
		await page.goto("http://localhost:8000/login", { waitUntil: "load" });

		await page.waitForSelector("#login_email");
		await page.fill("#login_email", "Administrator");
		await page.fill("#login_password", "admin");

		console.log("Submitting login form");
		await page.click("button.btn-login");

		// Stable wait for transition
		await page.waitForTimeout(5000);

		// Bypass setup wizard if environment forces it
		if (page.url().includes("setup-wizard")) {
			console.log("Setup wizard detected, navigating to rule builder entry point");
			await page.goto("http://localhost:8000/app", { waitUntil: "networkidle" });
		}

		await expect(page.locator(".navbar, .standard-sidebar, #body")).toBeVisible({
			timeout: 60000,
		});
	});

	test("Should construct and verify a multi-action rule flow", async ({ page }) => {
		test.setTimeout(300000);

		// 1. Create New Rule
		console.log("Initiating New Rule...");
		await page.goto("http://localhost:8000/app/rule/new-rule-1", { waitUntil: "networkidle" });

		const ruleNameInput = page.locator('input[data-fieldname="rule_name"]');
		await expect(ruleNameInput).toBeVisible({ timeout: 45000 });

		const ruleName = `Flow_Harden_${Date.now()}`;
		await ruleNameInput.fill(ruleName);

		// Set Document Type
		console.log("Configuring Rule Metadata...");
		const docTypeInput = page.locator('[data-fieldname="document_type"] input');
		await docTypeInput.fill("Contact");
		await page.keyboard.press("Enter");
		await expect(docTypeInput).toHaveValue("Contact", { timeout: 15000 });

		// Set Trigger Event
		await page.selectOption('[data-fieldname="trigger_event"] select', "After Save");

		// Save Rule Form
		const savePromise = page
			.waitForResponse(
				(res) =>
					res.url().includes("method=frappe.desk.form.save.savedocs") &&
					res.status() === 200,
				{ timeout: 30000 }
			)
			.catch(() => {});

		await page.click('button.primary-action:has-text("Save")');
		await savePromise;

		// 2. Open Visual Builder
		console.log("Entering Visual Builder...");
		const visualBuilderBtn = page.locator('button:has-text("Visual Builder")');
		await expect(visualBuilderBtn).toBeVisible({ timeout: 30000 });
		await visualBuilderBtn.click();

		await page.waitForURL("**/rule-builder/**", { timeout: 30000 });
		const canvas = page.locator(".vue-flow");
		await expect(canvas).toBeVisible({ timeout: 60000 });

		// --- Helper: Add Action ---
		const addActionToFlow = async (typeLabel, internalClass) => {
			console.log(`Adding node: ${typeLabel}`);
			const addBtn = page.locator(".edge-add-button").last();
			await addBtn.scrollIntoViewIfNeeded();
			await addBtn.click();

			const option = page.locator(`.result-item.is-option:has-text("${typeLabel}")`);
			await expect(option).toBeVisible({ timeout: 15000 });
			await option.click();

			const labeling = page.locator(".labeling-container");
			if (await labeling.isVisible({ timeout: 3000 })) {
				await labeling.locator("input").fill(`E2E ${typeLabel}`);
				await labeling.locator("button.btn-primary").click();
			}

			await expect(canvas.locator(`.vue-flow__node .${internalClass}`)).toBeVisible({
				timeout: 15000,
			});
		};

		// --- Helper: Configure Node ---
		const configureNodeDetails = async (internalClass, configCallback) => {
			console.log(`Configuring node: ${internalClass}`);
			const node = canvas.locator(`.vue-flow__node .${internalClass}`).last();
			await node.click();

			const settingsPanel = page.locator(".action-settings-container");
			await expect(settingsPanel).toBeVisible({ timeout: 15000 });

			if (configCallback) await configCallback(settingsPanel);

			await page.mouse.click(10, 10);
			await expect(settingsPanel).toBeHidden({ timeout: 15000 });
		};

		// 3. Construct Flow
		await addActionToFlow("Assignment", "assignment");
		await configureNodeDetails("assignment", async (panel) => {
			const labelInput = panel.locator('[data-fieldname="action_label"] input');
			await labelInput.fill("Calculate Score");
			await expect(canvas.locator(".vue-flow__node .assignment .node-title")).toContainText(
				"Calculate Score"
			);
		});

		await addActionToFlow("Notify", "notify");
		await configureNodeDetails("notify", async (panel) => {
			const asyncField = panel.locator('[data-fieldname="is_async"] input');
			await expect(asyncField).toBeVisible();
			await asyncField.check();
			await expect(asyncField).toBeChecked();

			const onError = panel.locator('[data-fieldname="on_error"] select');
			await onError.selectOption("Ignore");
		});

		// 4. Final Verification
		console.log("Finalizing flow...");
		const flowSaveBtn = page.locator('button:has-text("Save Rule")');
		await flowSaveBtn.click();

		await expect(page.locator(".alert.desk-alert.green")).toContainText("Saved", {
			timeout: 25000,
		});

		await page.screenshot({
			path: path.join(SCREENSHOTS_DIR, "hardened_e2e_final.png"),
			fullPage: true,
		});
		console.log("E2E Test Cycle Successful!");
	});
});
