const { defineConfig } = require("cypress");

module.exports = defineConfig({
	defaultCommandTimeout: 30000,
	pageLoadTimeout: 60000,
	video: true,
	viewportHeight: 960,
	viewportWidth: 1400,
	retries: {
		runMode: 1,
		openMode: 1,
	},
	env: {
		adminPassword: "admin",
		testUser: "Administrator",
	},
	e2e: {
		setupNodeEvents(on, config) {
			return require("./cypress/plugins/index.js")(on, config);
		},
		testIsolation: false,
		baseUrl: "http://localhost:8000",
		specPattern: "cypress/integration/*.js",
		supportFile: "cypress/support/e2e.js",
	},
});
