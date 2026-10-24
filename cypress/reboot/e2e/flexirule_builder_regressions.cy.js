/* global afterEach */
const REGRESSION_CONSOLE =
	/could not find grid field|grid field.*not found|cannot set property hasResolvedOutputSchema/i;

describe("FlexiRule builder regression coverage", () => {
	let ruleName;

	function createRuleAndOpenBuilder() {
		const suffix = Date.now().toString();
		ruleName = "Cypress_Regression_" + suffix;

		cy.window().then((win) => win.frappe.set_route("List", "Rule"));
		cy.url().should("include", "/app/rule");
		cy.contains("button", "Add Rule", { timeout: 30000 }).click();
		cy.get('input[data-fieldname="rule_name"][data-doctype="Rule"]', { timeout: 20000 }).should(
			"be.visible"
		);

		cy.window().then((win) => {
			const dialog =
				win.cur_dialog ||
				(win.frappe && win.frappe.quick_entry && win.frappe.quick_entry.dialog);
			expect(dialog, "Rule Quick Entry controller").to.exist;

			return Cypress.Promise.resolve(dialog.set_value("rule_name", ruleName))
				.then(() => dialog.set_value("document_type", "Contact"))
				.then(() => dialog.set_value("trigger_event", "After Save"));
		});

		cy.get('input[data-fieldname="rule_name"][data-doctype="Rule"]', { timeout: 10000 }).should(
			"have.value",
			ruleName
		);
		cy.get('input[data-fieldname="document_type"][data-doctype="Rule"]', {
			timeout: 10000,
		}).should("have.value", "Contact");

		cy.get(".modal.show button.btn-modal-primary")
			.filter(':contains("Save")')
			.should("be.visible")
			.click({ force: true });

		cy.get(".modal.show", { timeout: 20000 }).should("not.exist");
		cy.request("/api/resource/Rule/" + encodeURIComponent(ruleName))
			.its("status")
			.should("eq", 200);

		cy.window().then((win) => win.frappe.set_route("Form", "Rule", ruleName));
		cy.contains("button", "Visual Builder", { timeout: 30000 }).click();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
	}

	function addNodeFromEdgeMenu(type) {
		cy.get(".edge-add-button").last().click({ force: true });
		cy.get(".action-popover", { timeout: 15000 }).should("be.visible");
		cy.get(".action-popover .result-item.is-option").contains(type).click({ force: true });
	}

	function persistedRule() {
		return cy.request("/api/resource/Rule/" + encodeURIComponent(ruleName)).its("body.data");
	}

	beforeEach(() => {
		ruleName = null;
		const password = Cypress.env("frappePassword");
		if (!password)
			throw new Error("FRAPPE_PASSWORD is required for the Cypress regression suite.");

		cy.visit("/login");
		cy.get("#login_email")
			.should("be.visible")
			.clear()
			.type(Cypress.env("frappeUser") || "Administrator");
		cy.get("#login_password").should("be.visible").clear().type(password, { log: false });
		cy.get("button.btn-login").should("be.visible").click();
		cy.url().should("include", "/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	afterEach(() => {
		if (ruleName) {
			const name = ruleName;
			ruleName = null;
			cy.request({
				method: "DELETE",
				url: "/api/resource/Rule/" + encodeURIComponent(name),
				failOnStatusCode: false,
			});
		}
	});

	it("opens Assignment configuration and exposes the required assignment controls", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input")
			.should("be.visible")
			.type("Assignment configuration check");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", "Assignment configuration check")
			.should("be.visible")
			.dblclick({ force: true });

		cy.get(".config-modal-container", { timeout: 15000 })
			.should("be.visible")
			.within(() => {
				cy.contains("Batch Assignments").should("be.visible");
				cy.get('[data-fxr-fieldname="assignments.target"]').should("exist");
				cy.get('[data-fxr-fieldname="assignments.operator"]').should("exist");
				cy.get('[data-fxr-fieldname="assignments.value"]').should("exist");
			});
	});

	it("opens Condition configuration and renders its condition editor", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Condition");
		cy.get(".labeling-container input")
			.should("be.visible")
			.type("Condition configuration check");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", "Condition configuration check")
			.should("be.visible")
			.dblclick({ force: true });

		cy.get(".config-modal-container", { timeout: 15000 })
			.should("be.visible")
			.within(() => {
				cy.contains("Condition").should("be.visible");
			});
	});

	it("opens Query Records configuration and exposes the Fetch Records editor", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Query Records");
		cy.get(".action-popover", { timeout: 10000 }).then(($popover) => {
			if ($popover.find(".result-item.is-option").length > 0) {
				cy.wrap($popover).contains("Fetch Records").click({ force: true });
			}
		});
		cy.get(".labeling-container input")
			.should("be.visible")
			.type("Query Records configuration check");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", "Query Records configuration check")
			.should("be.visible")
			.dblclick({ force: true });

		cy.get(".config-modal-container", { timeout: 15000 })
			.should("be.visible")
			.within(() => {
				cy.contains("Query Mode").should("be.visible");
				cy.contains("Fetch Records").should("be.visible");
			});
	});

	it("persists graph node data and edges through a hard reload", () => {
		createRuleAndOpenBuilder();
		const label = "Persisted graph " + Date.now();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").type(label);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		// Populate valid assignment target so validation passes
		cy.contains(".vue-flow__node", label).dblclick({ force: true });
		cy.get(".config-modal-container", { timeout: 15000 }).should("be.visible");
		cy.get('[data-fxr-fieldname="assignments.target"]').type("first_name");
		cy.get(".config-modal-container").contains("button", "Save").click({ force: true });
		cy.get(".config-modal-container").should("not.exist");

		cy.contains("button", "Save Rule", { timeout: 15000 }).should("be.visible").click();
		cy.contains("button", "Save Rule", { timeout: 20000 }).should("not.exist");

		persistedRule().then((doc) => {
			expect(doc.actions, "persisted action rows").to.be.an("array");
			expect(
				doc.actions.some(
					(action) =>
						action.action_type === "Assignment" &&
						(action.action_label === label || action.label === label)
				),
				"Assignment action row includes the configured label"
			).to.eq(true);

			const visual =
				typeof doc.visual_data === "string" ? JSON.parse(doc.visual_data) : doc.visual_data;
			expect(visual, "persisted visual graph").to.be.an("array");
			expect(
				visual.some(
					(item) =>
						item.type === "assignment" &&
						item.data &&
						(item.data.action_label === label || item.label === label)
				),
				"visual graph contains the Assignment node"
			).to.eq(true);
			expect(
				visual.some((item) => item.source && item.target),
				"visual graph contains persisted edges"
			).to.eq(true);
		});

		cy.reload();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.contains(".vue-flow__node", label).should("be.visible");
		persistedRule().then((doc) => {
			const visual =
				typeof doc.visual_data === "string" ? JSON.parse(doc.visual_data) : doc.visual_data;
			expect(
				visual.some(
					(item) =>
						item.type === "assignment" &&
						item.data &&
						(item.data.action_label === label || item.label === label)
				)
			).to.eq(true);
			expect(doc.actions.some((action) => action.action_type === "Assignment")).to.eq(true);
		});
	});

	it("keeps unsaved graph changes distinguishable from the persisted baseline", () => {
		createRuleAndOpenBuilder();
		const label = "Dirty state " + Date.now();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").type(label);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		// The unsaved node is observable in the canvas, but the server copy must
		// remain unchanged until Save Rule is explicitly invoked.
		cy.contains(".vue-flow__node", label).should("be.visible");
		persistedRule().then((doc) => {
			expect(
				doc.actions.some(
					(action) =>
						action.action_type === "Assignment" &&
						(action.action_label === label || action.label === label)
				),
				"new node must not be persisted before Save Rule"
			).to.eq(false);
		});
	});

	it("supports undo and redo for a graph edit without persisting it implicitly", () => {
		createRuleAndOpenBuilder();
		const label = "Undo redo " + Date.now();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").type(label);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();
		cy.contains(".vue-flow__node", label).should("be.visible");

		cy.window().then((win) => {
			if (win.fxrRuleBuilder?.ruleStore) {
				win.fxrRuleBuilder.ruleStore.undo();
			}
		});
		cy.contains(".vue-flow__node", label).should("not.exist");

		cy.window().then((win) => {
			if (win.fxrRuleBuilder?.ruleStore) {
				win.fxrRuleBuilder.ruleStore.redo();
			}
		});
		cy.contains(".vue-flow__node", label).should("exist");

		persistedRule().then((doc) => {
			expect(
				doc.actions.some(
					(action) =>
						action.action_type === "Assignment" &&
						(action.action_label === label || action.label === label)
				),
				"undo/redo must not implicitly save the graph"
			).to.eq(false);
		});
	});

	it("keeps an incomplete Assignment out of persisted data when save validation rejects it", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").type("Incomplete assignment");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains("button", "Save Rule", { timeout: 15000 }).should("be.visible").click();
		persistedRule().then((doc) => {
			expect(
				doc.actions.some(
					(action) =>
						action.action_type === "Assignment" &&
						(action.action_label === "Incomplete assignment" ||
							action.label === "Incomplete assignment")
				),
				"an incomplete action should not be persisted"
			).to.eq(false);
		});
	});

	it("does not treat known schema/grid console regressions as successful UI behavior", () => {
		const messages = [];
		cy.on("window:before:load", (win) => {
			["error", "warn"].forEach((level) => {
				const original = win.console[level].bind(win.console);
				win.console[level] = (...args) => {
					messages.push(args.map(String).join(" "));
					return original(...args);
				};
			});
		});
		createRuleAndOpenBuilder();
		cy.then(() => {
			const regressions = messages.filter((message) => REGRESSION_CONSOLE.test(message));
			expect(regressions, regressions.join("\n")).to.deep.equal([]);
		});
	});
});
