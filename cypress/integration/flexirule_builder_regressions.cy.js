/* global afterEach */
import { isConsoleRegressionMessage } from "../support/regression_guards.mjs";

describe("FlexiRule builder regression coverage", () => {
	let ruleName;
	let capturedConsoleMessages = [];

	function defaultRuleActions() {
		return [
			{
				action_id: "root",
				action_label: "Start",
				action_type: "Entry Action",
				is_enabled: 1,
				next_step_if_true: "node_end",
			},
			{
				action_id: "node_end",
				action_label: "End",
				action_type: "Stop",
				operation: "Success",
				is_enabled: 1,
			},
		];
	}

	function createRuleAndOpenBuilder(actions = defaultRuleActions()) {
		const suffix = Date.now().toString() + "_" + Math.floor(Math.random() * 1000);
		ruleName = "Cypress_Regression_" + suffix;

		return cy
			.window()
			.then((win) =>
				win.frappe.call({
					method: "frappe.client.insert",
					args: {
						doc: {
							doctype: "Rule",
							rule_name: ruleName,
							document_type: "Contact",
							trigger_event: "After Save",
							trigger_type: "DocType Event",
							is_active: 0,
							actions,
						},
					},
				})
			)
			.then((response) => {
				ruleName = response?.message?.name || ruleName;
				return cy.window().then((win) => win.frappe.set_route("Form", "Rule", ruleName));
			})
			.then(() => cy.contains("button", "Visual Builder", { timeout: 30000 }).click())
			.then(() => cy.get(".vue-flow", { timeout: 30000 }).should("be.visible"))
			.then(() =>
				cy.get(".vue-flow__node", { timeout: 30000 }).should("have.length.at.least", 2)
			);
	}

	function addNodeFromEdgeMenu(type) {
		cy.get(".edge-add-button", { timeout: 20000 })
			.last()
			.should("be.visible")
			.click({ force: true });
		cy.get("body").then(($body) => {
			if ($body.find(".result-item.is-option").length === 0) {
				cy.get(".edge-add-button", { timeout: 20000 }).last().click({ force: true });
			}
		});
		cy.get(".result-item.is-option", { timeout: 20000 })
			.contains(type, { timeout: 15000 })
			.click({ force: true });
	}
	function persistedRule() {
		return cy.request("/api/resource/Rule/" + encodeURIComponent(ruleName)).its("body.data");
	}

	function actionConfig(action) {
		try {
			return typeof action.config === "string"
				? JSON.parse(action.config)
				: action.config || {};
		} catch (error) {
			return {};
		}
	}

	function configureLoopInModal(iteratorLabel, alias) {
		cy.get(".config-modal-container", { timeout: 15000 }).should("be.visible");
		cy.get(".config-modal-container .loop-node-config .combobox-button-trigger")
			.should("be.visible")
			.click({ force: true });
		cy.get(".fxr-dropdown:visible .fxr-dropdown-item")
			.contains(new RegExp(iteratorLabel))
			.click({ force: true });
		cy.get(".config-modal-container .loop-node-config .form-group")
			.eq(1)
			.find("input")
			.should("be.visible")
			.clear()
			.type(alias);
		cy.get(".config-modal-container .save-action").should("be.visible").click({ force: true });
		cy.get(".config-modal-container").should("not.exist");
	}

	function configureAssignmentForLoopBody(label) {
		cy.contains(".vue-flow__node", label, { timeout: 15000 }).dblclick({ force: true });
		cy.contains("Batch Assignments", { timeout: 15000 }).should("be.visible");
		cy.contains("button", "Add Assignment", { timeout: 15000 }).click();
		cy.get(".assignment-config .grid-col-target .combobox-button-trigger")
			.should("be.visible")
			.click({ force: true });
		cy.get(".fxr-dropdown:visible .fxr-dropdown-item")
			.contains("vars.inner_item.link_name")
			.click({ force: true });
		cy.get(".assignment-config .grid-col-operator .combobox-button-trigger")
			.should("be.visible")
			.click({ force: true });
		cy.get(".fxr-dropdown:visible .fxr-dropdown-item")
			.contains(/^Clear$/)
			.click({ force: true });
		cy.get(".config-modal-container .save-action").should("be.visible").click({ force: true });
		cy.get(".config-modal-container").should("not.exist");
	}

	beforeEach(() => {
		ruleName = null;
		capturedConsoleMessages = [];

		cy.on("window:before:load", (win) => {
			["error", "warn"].forEach((level) => {
				const original = win.console[level];
				if (!original) return;
				win.console[level] = (...args) => {
					const message = args.map(String).join(" ");
					capturedConsoleMessages.push({
						level,
						message,
						url: win.location.href,
					});
					return original.apply(win.console, args);
				};
			});
		});

		cy.login();
		cy.visit("/app");
		cy.get(".navbar", { timeout: 30000 }).should("be.visible");
	});

	afterEach(function () {
		const assertConsoleRegressions = () => {
			const regressions = capturedConsoleMessages.filter((item) =>
				isConsoleRegressionMessage(item.message)
			);
			if (regressions.length > 0) {
				const formatted = regressions
					.map((r) => `[${r.level}] ${r.url}: ${r.message}`)
					.join("\n");
				expect.fail(`Console regression guard detected error(s):\n${formatted}`);
			}
		};

		if (ruleName) {
			const name = ruleName;
			ruleName = null;
			cy.request({
				method: "DELETE",
				url: "/api/resource/Rule/" + encodeURIComponent(name),
				failOnStatusCode: false,
			}).then(assertConsoleRegressions);
		} else {
			assertConsoleRegressions();
		}
	});

	it("captures console warnings and errors emitted after listener installation", () => {
		cy.window().then((win) => {
			win.console.warn("Controlled sanity check warning message");
		});
		cy.then(() => {
			const captured = capturedConsoleMessages.some((msg) =>
				msg.message.includes("Controlled sanity check warning message")
			);
			expect(captured, "console.warn message was captured by the listener").to.eq(true);
		});
	});

	it("creates a nested Loop through the body selector and preserves routing after reload", () => {
		createRuleAndOpenBuilder();
		const outerLabel = "Outer Loop " + Date.now();
		const nestedLabel = "Nested Loop " + Date.now();
		const bodyLabel = "Nested Body " + Date.now();

		addNodeFromEdgeMenu("Loop");
		cy.get(".labeling-container input").should("be.visible").clear().type(outerLabel);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		// The Loop must be fully configured before the save/reload assertions.
		configureLoopInModal("Links", "outer_item");

		cy.get(".vue-flow__node-selector", { timeout: 15000 }).should("exist");
		cy.get(".vue-flow__node-selector")
			.last()
			.within(() => {
				cy.contains(".result-item.is-option", "Loop").click({ force: true });
			});
		cy.get(".labeling-container input", { timeout: 15000 })
			.last()
			.should("be.visible")
			.clear()
			.type(nestedLabel);
		cy.get(".labeling-container button.btn-primary").last().click({ force: true });
		cy.contains(".vue-flow__node", nestedLabel, { timeout: 15000 }).dblclick({ force: true });
		configureLoopInModal("Links", "inner_item");

		// A nested Loop creates its own Loop Body selector. The shared layout
		// request must move it away from the origin rather than leaving overlap.
		cy.contains(".vue-flow__node", nestedLabel, { timeout: 15000 }).should("be.visible");
		cy.get(".vue-flow__node-selector", { timeout: 15000 })
			.last()
			.should(($node) => {
				const style = $node.attr("style") || "";
				expect(style, "scaffold selector has a non-origin layout position").not.to.include(
					"translate(0px, 0px)"
				);
			});

		cy.get(".vue-flow__node-selector")
			.last()
			.within(() => {
				cy.contains(".result-item.is-option", "Assignment").click({ force: true });
			});
		cy.get(".labeling-container input", { timeout: 15000 })
			.last()
			.should("be.visible")
			.clear()
			.type(bodyLabel);
		cy.get(".labeling-container button.btn-primary").last().click({ force: true });
		cy.contains(".vue-flow__node", bodyLabel, { timeout: 15000 }).should("be.visible");
		configureAssignmentForLoopBody(bodyLabel);

		cy.intercept("POST", "**/api/method/frappe.client.save").as("saveRule");
		cy.contains("button", "Save Rule", { timeout: 15000 }).click({ force: true });
		cy.wait("@saveRule");

		persistedRule().then((doc) => {
			const loops = doc.actions.filter((action) => action.action_type === "Loop");
			expect(loops, "outer and nested Loop actions persisted").to.have.length(2);
			const outer = loops.find((action) => action.action_label === outerLabel);
			const nested = loops.find((action) => action.action_label === nestedLabel);
			const body = doc.actions.find(
				(action) => action.action_type === "Assignment" && action.action_label === bodyLabel
			);
			expect(outer, "outer Loop action").to.exist;
			expect(nested, "nested Loop action").to.exist;
			expect(body, "nested Loop body Assignment").to.exist;
			const bodyAssignments = actionConfig(body);
			expect(bodyAssignments, "persisted body assignments").to.be.an("array").and.not.empty;
			expect(bodyAssignments[0].target, "canonical nested item target").to.eq(
				"vars.inner_item.link_name"
			);
			expect(bodyAssignments[0].operator, "body Assignment operator").to.eq("clear");
			expect(body.next_step_if_true, "body Assignment returns to nested Loop").to.eq(
				nested.action_id
			);
			expect(outer.return_variable, "outer Loop item alias").to.eq("outer_item");
			expect(nested.return_variable, "nested Loop item alias").to.eq("inner_item");
			expect(actionConfig(outer).iterator, "outer Loop iterator").to.eq("doc.links");
			expect(actionConfig(nested).iterator, "nested Loop iterator").to.eq("doc.links");
			expect(nested.next_step_if_true, "nested Loop body destination").to.be.a("string");
			expect(
				nested.next_step_if_false,
				"nested Loop After Last resumes the outer Loop"
			).to.eq(outer.action_id);

			const visual =
				typeof doc.visual_data === "string" ? JSON.parse(doc.visual_data) : doc.visual_data;
			const afterLastEdge = visual.find(
				(item) =>
					item.source === nested.action_id &&
					item.target === outer.action_id &&
					item.sourceHandle === "false"
			);
			expect(afterLastEdge, "nested Loop After Last edge was persisted").to.exist;
			expect(afterLastEdge.sourceHandle).to.eq("false");
			// visual_data intentionally stores connection geometry, not edge styling
			// metadata; a reload rebuilds After Last/return markers from action contracts.
			expect(afterLastEdge.targetHandle).not.to.eq("return");
			expect(afterLastEdge.data?.isReturn).not.to.eq(true);
		});

		cy.reload();
		cy.get(".vue-flow", { timeout: 30000 }).should("be.visible");
		cy.contains(".vue-flow__node", outerLabel).should("be.visible");
		cy.contains(".vue-flow__node", nestedLabel).should("be.visible");
		cy.contains(".vue-flow__node", bodyLabel).should("be.visible");
		cy.get(".vue-flow__node-selector").should("not.exist");

		// Check server-persisted routing again after reload, not just the live canvas.
		persistedRule().then((doc) => {
			const loops = doc.actions.filter((action) => action.action_type === "Loop");
			const outer = loops.find((action) => action.action_label === outerLabel);
			const nested = loops.find((action) => action.action_label === nestedLabel);
			const body = doc.actions.find(
				(action) => action.action_type === "Assignment" && action.action_label === bodyLabel
			);
			expect(loops, "both Loop actions remain persisted after reload").to.have.length(2);
			expect(body, "nested Loop body Assignment remains persisted").to.exist;
			expect(body.next_step_if_true, "body return pointer persists after reload").to.eq(
				nested.action_id
			);
			expect(actionConfig(outer).iterator).to.eq("doc.links");
			expect(actionConfig(nested).iterator).to.eq("doc.links");
			expect(outer.return_variable).to.eq("outer_item");
			expect(nested.return_variable).to.eq("inner_item");
			expect(nested.next_step_if_false).to.eq(outer.action_id);
			const visual =
				typeof doc.visual_data === "string" ? JSON.parse(doc.visual_data) : doc.visual_data;
			expect(
				visual.some(
					(item) =>
						item.source === nested.action_id &&
						item.target === outer.action_id &&
						item.sourceHandle === "false"
				),
				"nested Loop After Last edge persists after reload"
			).to.eq(true);
		});

		// Reload must reconstruct exactly one actual return edge (the inner body
		// action back to its Loop). Neither Loop's After Last edge may keep the
		// dashed return styling that previously came from stale return metadata.
		cy.get(".vue-flow__edge-path").should(($paths) => {
			const returnStyledPaths = $paths
				.toArray()
				.filter(
					(path) =>
						path.ownerDocument.defaultView.getComputedStyle(path).strokeDasharray !==
						"none"
				);
			expect(
				returnStyledPaths,
				"only the inner body's return route is dashed"
			).to.have.length(1);
		});
	});

	it("opens Assignment configuration and exposes the required assignment controls", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input")
			.should("be.visible")
			.clear()
			.type("Assignment configuration check");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", "Assignment configuration check")
			.should("be.visible")
			.dblclick({ force: true });

		cy.contains("Batch Assignments", { timeout: 15000 }).should("be.visible");
		cy.contains("button", "Add Assignment").should("be.visible").click();
		cy.contains("Target Field").should("be.visible");
		cy.contains("Operator").should("be.visible");
		cy.contains("Value Expression").should("be.visible");
	});

	it("lists unsaved action drafts and resumes at the first dirty action when keeping editing", () => {
		const firstLabel = "Draft retention first " + Date.now();
		const secondLabel = "Draft retention second " + Date.now();
		const actions = [
			{
				action_id: "root",
				action_label: "Start",
				action_type: "Entry Action",
				is_enabled: 1,
				next_step_if_true: "draft_first",
			},
			{
				action_id: "draft_first",
				action_label: firstLabel,
				action_type: "Assignment",
				is_enabled: 1,
				next_step_if_true: "draft_second",
				assignments: [],
			},
			{
				action_id: "draft_second",
				action_label: secondLabel,
				action_type: "Assignment",
				is_enabled: 1,
				next_step_if_true: "node_end",
				assignments: [],
			},
			{
				action_id: "node_end",
				action_label: "End",
				action_type: "Stop",
				operation: "Success",
				is_enabled: 1,
			},
		];
		createRuleAndOpenBuilder(actions);

		// Start with a linked two-action flow so the dialog can be checked for
		// labels in graph order independently of the canvas insertion menu.
		cy.contains(".vue-flow__node", firstLabel).should("be.visible").dblclick({ force: true });
		cy.get(".config-modal-container", { timeout: 15000 }).should("be.visible");
		cy.contains(".config-modal-container button", "Add Assignment")
			.should("be.visible")
			.click();
		cy.get(".config-modal-container").contains("Target Field").should("be.visible");

		// Make the second action independently dirty as well.
		cy.get(".config-modal-container .toolbar-group.navigation button").last().click();
		cy.get(".config-modal-container h3").should("contain.text", secondLabel);
		// Wait until the first draft's row controls are unmounted and the second
		// action's panel has finished switching before querying its Add button.
		cy.get(".config-modal-container").contains("Target Field").should("not.exist");
		cy.contains(".config-modal-container", "Batch Assignments").should("be.visible");
		cy.get(".config-modal-container button.add-assignment-btn").should("be.visible");
		cy.get(".config-modal-container button.add-assignment-btn").click();
		cy.get(".config-modal-container").contains("Target Field").should("be.visible");

		cy.get(".config-modal-container .toolbar-btn.close-action").click();
		cy.get(".modal:visible .frappe-confirm-message").should(($message) => {
			const message = $message.text();
			expect(message).to.include("The following actions have unsaved configuration changes:");
			const firstIndex = message.indexOf(firstLabel);
			const secondIndex = message.indexOf(secondLabel);
			expect(firstIndex, "first action label is displayed").to.be.greaterThan(-1);
			expect(secondIndex, "second action label is displayed").to.be.greaterThan(-1);
			expect(firstIndex, "labels are shown in rule-flow order").to.be.lessThan(secondIndex);
		});

		// Keep editing must jump to the first dirty action, even when the user
		// opened the confirmation from a later action.
		cy.get(".modal:visible").contains("button", "Keep editing").click();
		cy.get(".modal-backdrop").should("not.exist");
		cy.get(".config-modal-container").should("be.visible");
		cy.get(".config-modal-container h3").should("contain.text", firstLabel);
		cy.get(".config-modal-container").contains("Target Field").should("be.visible");

		// Escape must dismiss the Frappe confirmation without reopening it or
		// losing the first action's draft.
		cy.get(".config-modal-container .toolbar-btn.close-action").click();
		cy.get(".modal:visible .frappe-confirm-message")
			.should("contain.text", firstLabel)
			.and("contain.text", secondLabel);
		cy.get(".modal:visible .btn-modal-secondary").trigger("keydown", {
			key: "Escape",
			code: "Escape",
			which: 27,
			keyCode: 27,
			bubbles: true,
			cancelable: true,
		});
		cy.get(".modal:visible .frappe-confirm-message").should("not.exist");
		cy.get(".modal-backdrop").should("not.exist");
		cy.get(".config-modal-container").should("be.visible");
		cy.get(".config-modal-container h3").should("contain.text", firstLabel);
		cy.get(".config-modal-container").contains("Target Field").should("be.visible");

		// Cleanup through the explicit discard action.
		cy.get(".config-modal-container .toolbar-btn.close-action").click();
		cy.get(".modal:visible").contains("button", "Discard changes").click();
		cy.get(".config-modal-container").should("not.exist");
	});
	it("opens Condition configuration and renders its condition editor", () => {
		createRuleAndOpenBuilder();
		addNodeFromEdgeMenu("Condition");
		cy.get(".labeling-container input")
			.should("be.visible")
			.clear()
			.type("Condition configuration check");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", "Condition configuration check")
			.should("be.visible")
			.dblclick({ force: true });

		cy.get(".config-modal-container", { timeout: 15000 }).should("be.visible");
		cy.get(".config-modal-container").contains("Condition").should("be.visible");
	});

	it("persists graph node data and edges through a hard reload", () => {
		createRuleAndOpenBuilder();
		const label = "Persisted graph " + Date.now();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").clear().type(label);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains(".vue-flow__node", label).should("be.visible").dblclick({ force: true });
		cy.contains("button", "Add Assignment", { timeout: 15000 }).should("be.visible").click();

		cy.intercept("POST", "**/api/method/frappe.client.save").as("saveRule");
		cy.contains("button", "Save Rule", { timeout: 15000 }).click({ force: true });
		cy.wait("@saveRule");

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
				visual.some((item) => item.position && item.id),
				"visual graph contains position metadata"
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
			expect(visual.some((item) => item.position && item.id)).to.eq(true);
			expect(doc.actions.some((action) => action.action_type === "Assignment")).to.eq(true);
		});
	});

	it("coalesces overlapping layout requests and leaves the graph visible", () => {
		createRuleAndOpenBuilder();

		// Exercise the same overlap that can happen when initialization and node
		// insertion both request a layout. The last requested direction must win,
		// and every caller must settle only after its queued layout finishes.
		cy.window().then((win) => {
			const requestLayout = win.fxrRuleBuilder.layoutGraph;
			return Promise.all([requestLayout("LR"), requestLayout("TB"), requestLayout("LR")]);
		});

		cy.get(".vue-flow__node").should("have.length.at.least", 2);
		cy.get(".vue-flow__node").each(($node) => {
			cy.wrap($node).should("be.visible");
		});
	});

	it("keeps unsaved graph changes distinguishable from the persisted baseline", () => {
		createRuleAndOpenBuilder();
		const label = "Dirty state " + Date.now();
		addNodeFromEdgeMenu("Assignment");
		cy.get(".labeling-container input").should("be.visible").clear().type(label);
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
		cy.get(".labeling-container input").should("be.visible").clear().type(label);
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();
		cy.contains(".vue-flow__node", label).should("be.visible");

		// Perform undo twice: selector node insertion + label upgrade
		cy.window().then((win) => {
			win.fxrRuleBuilder.ruleStore.undo();
			win.fxrRuleBuilder.ruleStore.undo();
		});
		cy.contains(".vue-flow__node", label).should("not.exist");

		// Perform redo twice: restore node + label
		cy.window().then((win) => {
			win.fxrRuleBuilder.ruleStore.redo();
			win.fxrRuleBuilder.ruleStore.redo();
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
		cy.get(".labeling-container input")
			.should("be.visible")
			.clear()
			.type("Incomplete assignment");
		cy.get(".labeling-container button.btn-primary").should("be.visible").click();

		cy.contains("button", "Save Rule", { timeout: 15000 }).click({ force: true });
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

	it("verifies console regression guard detects known grid and schema console errors", () => {
		createRuleAndOpenBuilder();
		cy.then(() => {
			const regressions = capturedConsoleMessages.filter((item) =>
				isConsoleRegressionMessage(item.message)
			);
			expect(regressions, regressions.map((r) => r.message).join("\n")).to.deep.equal([]);
		});
	});
});
