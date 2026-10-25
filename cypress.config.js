const path = require("node:path");
const { defineConfig } = require("cypress");

const artifactRoot = path.join(__dirname, "artifacts", "cypress");

module.exports = defineConfig({
	defaultCommandTimeout: 30000,
	requestTimeout: 30000,
	responseTimeout: 60000,
	pageLoadTimeout: 60000,
	video: true,
	screenshotOnRunFailure: true,
	trashAssetsBeforeRuns: true,
	screenshotsFolder: path.join(artifactRoot, "screenshots"),
	videosFolder: path.join(artifactRoot, "videos"),
	viewportHeight: 960,
	viewportWidth: 1400,
	retries: {
		runMode: 0,
		openMode: 0,
	},
	testUser: process.env.CYPRESS_testUser || process.env.FRAPPE_USER || "Administrator",
	env: {
		adminPassword: process.env.CYPRESS_adminPassword || process.env.FRAPPE_PASSWORD || "admin",
		artifactRoot,
	},
	e2e: {
		setupNodeEvents(on, config) {
			return require("./cypress/plugins/index.js")(on, config);
		},
		testIsolation: true,
		baseUrl:
			process.env.CYPRESS_baseUrl || process.env.FRAPPE_SITE_URL || "http://localhost:8000",
		specPattern: "cypress/integration/*.js",
		supportFile: "cypress/support/e2e.js",
	},
});
