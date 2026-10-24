const fs = require("node:fs");
const path = require("node:path");
const { defineConfig } = require("cypress");

module.exports = defineConfig({
	defaultCommandTimeout: 20000,
	requestTimeout: 30000,
	responseTimeout: 60000,
	pageLoadTimeout: 90000,
	video: true,
	screenshotOnRunFailure: true,
	trashAssetsBeforeRuns: true,
	screenshotsFolder: "artifacts/cypress/screenshots",
	videosFolder: "artifacts/cypress/videos",
	viewportWidth: 1400,
	viewportHeight: 900,
	retries: {
		runMode: 0,
		openMode: 0,
	},
	env: {
		frappeUser: process.env.FRAPPE_USER || "Administrator",
		frappePassword: process.env.FRAPPE_PASSWORD || "",
	},
	e2e: {
		baseUrl: process.env.FRAPPE_SITE_URL || "http://localhost:8000",
		specPattern: "cypress/reboot/e2e/**/*.cy.js",
		// This runner intentionally does not load the legacy Cypress support file,
		// commands, or page objects. It is an isolated smoke path.
		supportFile: false,
		testIsolation: true,
		setupNodeEvents(on, config) {
			const diagnosticsRoot = path.join(config.projectRoot, "artifacts", "cypress");
			fs.mkdirSync(diagnosticsRoot, { recursive: true });
			return config;
		},
	},
});
