const { test, expect } = require('@playwright/test');

test('Verify Rule Builder actions and settings visibility', async ({ page }) => {
  // Login
  await page.goto('http://localhost:8000/login');
  await page.fill('#login_email', 'Administrator');
  await page.fill('#login_password', 'admin');
  await page.click('button:has-text("Login")');

  // Navigate to Rule Builder for the seeded rule
  await page.goto('http://localhost:8000/app/rule-builder/Block%20Duplicate%20Contact');

  // Wait for the canvas or a known element to load
  try {
    await page.waitForSelector('.vue-flow__pane', { timeout: 15000 });
  } catch (e) {
    console.log('Vue Flow pane not found, taking debug screenshot');
    await page.screenshot({ path: 'verification/screenshots/debug_load_fail.png' });
    // If we are at setup wizard, try to skip or just report
    if (await page.isVisible('text=Welcome')) {
        console.log('Setup Wizard detected');
    }
  }

  await page.screenshot({ path: 'verification/screenshots/rule_builder_init.png' });

  const unsavedBadge = page.locator('.indicator-pill:has-text("Unsaved")');
  const isUnsavedVisible = await unsavedBadge.isVisible();
  console.log('Is Unsaved visible on load?', isUnsavedVisible);

  // Attempt to open an action config if possible
  const node = page.locator('[data-id="ACT-W9J3"]');
  if (await node.isVisible()) {
      await node.click();
      await page.waitForSelector('.fxr-action-config-modal', { timeout: 5000 });
      const settingsBar = page.locator('.fxr-action-settings-bar');
      console.log('Settings bar visible?', await settingsBar.isVisible());
      await page.screenshot({ path: 'verification/screenshots/action_config_modal.png' });
  }
});
