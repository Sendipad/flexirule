const { chromium } = require("playwright");

(async () => {
	const browser = await chromium.launch();
	const page = await browser.newPage();
	try {
		console.log("Navigating to login...");
		await page.goto("http://localhost:8000/login");
		await page.fill("#login_email", "Administrator");
		await page.fill("#login_password", "admin");
		await page.click('button:has-text("Login")');
		await page.waitForNavigation();

		console.log("Navigating to Rule Builder...");
		await page.goto("http://localhost:8000/app/rule-builder/Block%20Duplicate%20Contact");

		// Give it some time to load
		await page.waitForTimeout(5000);
		await page.screenshot({ path: "verification/screenshots/final_rule_builder.png" });

		const isUnsaved = await page.isVisible('.indicator-pill:has-text("Unsaved")');
		console.log("Unsaved indicator present:", isUnsaved);

		const node = page.locator('[data-id="ACT-W9J3"]');
		if (await node.isVisible()) {
			console.log("Node ACT-W9J3 found, clicking...");
			await node.click();
			await page.waitForTimeout(2000);
			await page.screenshot({ path: "verification/screenshots/final_action_modal.png" });

			const isSettingsVisible = await page.isVisible(".fxr-action-settings-bar");
			console.log("Settings bar visible:", isSettingsVisible);
		} else {
			console.log("Node ACT-W9J3 NOT found");
		}
	} catch (err) {
		console.error("Error during verification:", err);
		await page.screenshot({ path: "verification/screenshots/verification_error.png" });
	} finally {
		await browser.close();
	}
})();
