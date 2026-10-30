const KNOWN_REGRESSION =
	/could not find grid field|grid field.*not found|cannot set property hasResolvedOutputSchema|uncaught typeerror/i;

describe("FlexiRule Cypress smoke flow", () => {
	let createdRuleName = null;
	let browserMessages = [];
	let assetFailures = [];
	let lastVisitedUrl = "";

	beforeEach(() => {
		createdRuleName = null;
		browserMessages = [];
		assetFailures = [];
		lastVisitedUrl = "";

		// Record log/warn/error messages before application code starts. Do not
		// suppress console output or globally ignore uncaught exceptions.
		cy.on("window:before:load", (win) => {
			lastVisitedUrl = win.location.href;

			["log", "warn", "error"].forEach((level) => {
				const original = win.console[level].bind(win.console);
				win.console[level] = (...args) => {
					const rendered = args
						.map((value) => {
							if (typeof value === "string") return value;
							try {
								return JSON.stringify(value);
							} catch {
								return String(value);
							}
						})
						.join(" ");
					browserMessages.push("[" + level + "] " + rendered);
					return original(...args);
				};
			});
		});

		// Missing JS/CSS assets can leave the builder partially rendered. Track
		// these specifically instead of treating every optional HTTP 404 as fatal.
		cy.intercept("GET", "**/assets/**", (request) => {
			request.continue((response) => {
				const isScriptOrStyle = /\.(js|css)(?:[?#]|$)/i.test(request.url);
				if (response.statusCode >= 400 && isScriptOrStyle) {
					assetFailures.push(response.statusCode + " " + request.url);
				}
			});
		});

		// Use Frappe's supported UI-test login command from cypress/support.
		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
		cy.screenshot("01-login-and-desk");
	});

	afterEach(function () {
		const failed = this.currentTest && this.currentTest.state === "failed";

		const cleanupRule = () => {
			if (!createdRuleName) return;

			const ruleName = createdRuleName;
			createdRuleName = null;
			cy.request({
				method: "DELETE",
				url: "/api/resource/Rule/" + encodeURIComponent(ruleName),
				failOnStatusCode: false,
			});
		};

		if (failed) {
			const diagnostic = {
				test: this.currentTest.fullTitle(),
				url: lastVisitedUrl,
				browserMessages,
				assetFailures,
			};
			cy.writeFile(`${Cypress.env("artifactRoot")}/diagnostics.json`, diagnostic, {
				log: false,
			}).then(cleanupRule);
		} else {
			cleanupRule();
		}
	});

	it("creates a Rule, opens Visual Builder, adds an Assignment, saves and reloads", () => {
		const suffix = Date.now().toString();
		const ruleName = "Cypress_Smoke_" + suffix;
		const assignmentLabel = "Cypress Assignment " + suffix;
		createdRuleName = ruleName;

		// Use Frappe's Rule List and quick-entry UI, not a backend-only fixture.
		cy.window().then((win) => {
			win.frappe.set_route("List", "Rule");
		});
		cy.url().should("include", "/app/rule");
		cy.contains("button", "Add Rule", { timeout: 30000 }).should("be.visible").click();
		cy.get('input[data-fieldname="rule_name"][data-doctype="Rule"]', {
			timeout: 20000,
		}).should("be.visible");

		// Quick Entry field APIs are used only to populate the actual dialog.
		// Saving still goes through the visible Quick Entry Save button.
		cy.window().then((win) => {
			const dialog =
				win.cur_dialog ||
				(win.frappe && win.frappe.quick_entry && win.frappe.quick_entry.dialog);
			expect(dialog, "Rule Quick Entry dialog controller").to.exist;

			return Cypress.Promise.resolve(dialog.set_value("rule_name", ruleName))
				.then(() => dialog.set_value("document_type", "Contact"))
				.then(() => dialog.set_value("trigger_event", "After Save"));
		});
		cy.get('input[data-fieldname="rule_name"][data-doctype="Rule"]').should(
			"have.value",
			ruleName
		);
		cy.screenshot("02-rule-quick-entry-filled");

		cy.get(".modal.show")
			.last()
			.within(() => {
				cy.get("button.btn-modal-primary")
					.filter(':contains("Save")')
					.first()
					.should("be.visible")
					.click({ force: true });
			});
		cy.get(".modal.show").should("not.exist");

		// Verify the save reached Frappe before attempting to open the builder.
		cy.request("/api/resource/Rule/" + encodeURIComponent(ruleName)).then((response) => {
			expect(response.status).to.eq(200);
			expect(response.body.data.rule_name).to.eq(ruleName);
		});
		cy.screenshot("03-rule-saved");

		cy.window().then((win) => {
			win.frappe.set_route("Form", "Rule", ruleName);
		});
		cy.contains("button", "Visual Builder", { timeout: 30000 }).should("be.visible").click();
		cy.url().should("include", "/app/rule-builder/" + ruleName);
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.get(".vue-flow__node").should(($nodes) => {
			expect($nodes.length, "initial Rule Builder nodes").to.be.at.least(2);
		});
		cy.screenshot("04-visual-builder-loaded");

		// Add a real graph node through the edge menu.
		cy.get(".edge-add-button").last().click({ force: true });
		cy.get(".result-item.is-option")
			.contains("Assignment")
			.should("be.visible")
			.click({ force: true });
		cy.get(".labeling-container", { timeout: 10000 }).should("be.visible");
		cy.get(".labeling-container input").clear().type(assignmentLabel);
		cy.get(".labeling-container button.btn-primary").click();
		cy.get(".vue-flow__node .assignment").should("be.visible");
		cy.get(".vue-flow__node .assignment .node-title").should("contain", assignmentLabel);
		cy.screenshot("05-assignment-added");

		// Save through the builder's UI, then verify the node survives a hard reload.
		cy.contains("button", "Save Rule", { timeout: 15000 }).should("be.visible").click();
		// The builder uses Frappe alert rendering that differs across versions;
		// do not couple the smoke test to a toast CSS class. The hard-reload
		// assertion below verifies the actual outcome: the node was persisted.
		cy.get(".vue-flow__node .assignment .node-title", { timeout: 30000 }).should(
			"contain",
			assignmentLabel
		);
		cy.reload();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.get(".vue-flow__node .assignment .node-title", { timeout: 30000 }).should(
			"contain",
			assignmentLabel
		);
		cy.screenshot("06-assignment-persisted-after-reload");

		// Fail explicitly on the earlier reported grid-field diagnostic, known
		// schema getter regression, or JS/CSS asset failures. Uncaught exceptions
		// remain Cypress failures by default.
		cy.then(() => {
			const regressions = browserMessages.filter((message) => KNOWN_REGRESSION.test(message));
			expect(
				regressions,
				"known Rule Builder console regressions:\n" + regressions.join("\n")
			).to.deep.equal([]);
			expect(
				assetFailures,
				"failed JavaScript/CSS asset responses:\n" + assetFailures.join("\n")
			).to.deep.equal([]);
		});
	});
});
