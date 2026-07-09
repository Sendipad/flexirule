import { createApp, watchEffect } from "vue";
import { createPinia } from "pinia";

// Import FlexiRule Utilities
import "../utils/utils.js";
import "../utils/patches.js";
import "../core/ProcessConfigurator.js";
import { useRuleStore } from "./stores/useRuleStore";
import { useUIStore } from "./stores/useUIStore";
import RuleBuilderComponent from "./App.vue";
import { registerGlobalComponents } from "./globals.js";

class RuleBuilder {
	constructor({ wrapper, page, rule }) {
		this.$wrapper = $(wrapper);
		this.page = page;
		this.rule = rule;
		window.fxrRuleBuilder = this;

		this.init();
	}

	init() {
		this.setup_app();
		this.setup_page();
		this.watch_changes();
	}

	setup_page() {
		// Clear existing actions
		this.page.clear_actions();
		this.page.clear_menu();
		this.page.clear_custom_actions();

		// Static menu items
		this.page.add_menu_item(__("Go to Rule"), () => {
			frappe.set_route("Form", "Rule", this.rule);
		});

		this.page.add_menu_item(__("Keyboard Shortcuts"), () => {
			this.show_keyboard_shortcuts();
		});
	}

	setup_breadcrumbs() {
		if (frappe.breadcrumbs && frappe.breadcrumbs.$breadcrumbs) {
			let breadcrumbs = `
				<li><a href="/app/rule">${__("Rule")}</a></li>
				<li><a href="/app/rule/${this.rule}">${__(this.ruleStore.rule_doc?.rule_name || this.rule)}</a></li>
				<li class="disabled"><a href="#">${__("Builder")}</a></li>
			`;
			frappe.breadcrumbs.clear();
			frappe.breadcrumbs.$breadcrumbs.append(breadcrumbs);
		} else if (frappe.breadcrumbs && frappe.breadcrumbs.add) {
			// Modern Frappe 15 fallback
			frappe.breadcrumbs.add({
				type: "Custom",
				module: "Rule",
				workspace: "RuleFlow",
			});
		}
	}

	show_keyboard_shortcuts() {
		if (this.uiStore) {
			this.uiStore.show_shortcuts_help = true;
			return;
		}

		window.dispatchEvent(new CustomEvent("flexirule:show-shortcuts-help"));
	}

	setup_custom_header() {
		// No custom left actions needed per user request
	}

	setup_app() {
		// Create Pinia instance
		let pinia = createPinia();

		// Create Vue app
		let app = createApp(RuleBuilderComponent, { rule: this.rule });
		app.use(pinia);
		registerGlobalComponents(app);

		// Get store references
		this.ruleStore = useRuleStore(pinia);
		this.uiStore = useUIStore(pinia);
		this.ruleStore.rule_name = this.rule;

		this.setup_debug_api();

		// Mount app
		this.$rule_builder = app.mount(this.$wrapper.get(0));
	}

	watch_changes() {
		watchEffect(() => {
			const is_dirty = this.ruleStore.is_dirty;
			const is_active = this.ruleStore.is_active;
			const has_test_path = this.uiStore.has_test_path;

			// 1. Update Title & Breadcrumbs
			this.page.set_title(__(this.ruleStore.rule_doc?.rule_name || this.rule));
			this.setup_breadcrumbs();

			// 2. Indicators
			this.page.clear_indicator();
			if (is_dirty) {
				this.page.set_indicator(__("Not Saved"), "orange");
			} else if (is_active) {
				this.page.set_indicator(__("Active"), "green");
			} else {
				this.page.set_indicator(__("Draft"), "orange");
			}

			// 3. Toolbar Actions
			this.refresh_toolbar(is_dirty, is_active, has_test_path);
		});
	}

	refresh_toolbar(is_dirty, is_active, has_test_path) {
		this.page.clear_actions();
		this.page.clear_custom_actions();

		// Primary Action: Save or Activate
		if (is_dirty) {
			this.page.set_primary_action(__("Save Rule"), () => this.ruleStore.save_changes());
		} else if (!is_active) {
			this.page.set_primary_action(__("Activate Rule"), () => this.toggle_rule_active());
		} else {
			// If active and not dirty, primary action is to Unlock
			this.page.set_primary_action(__("Edit Rule"), () => this.toggle_rule_active());
		}

		// Secondary Actions
		if (is_dirty) {
			this.page.add_button(__("Reset Changes"), () => this.ruleStore.fetch(), {
				icon: "refresh",
			});
		}

		// Inner Buttons
		this.page.add_inner_button(__("Debug Rule"), () => {
			flexirule.debug.show_dialog();
		});

		if (has_test_path) {
			this.page.add_inner_button(__("Clear Debug Path"), () => {
				this.uiStore.clear_test_result();
			});
		}
	}

	async toggle_rule_active() {
		if (!this.ruleStore.rule_doc) return;

		// Do not allow silent state mutation. Use lifecycle API transitions.
		try {
			frappe.dom.freeze(__("Updating rule status..."));

			if (this.ruleStore.rule_doc.is_active) {
				await this.ruleStore.deactivate_rule();
			} else {
				// If there are unsaved edits, persist first, then activate.
				if (this.ruleStore.is_dirty) {
					await this.ruleStore.save_changes();
					if (this.ruleStore.is_dirty) {
						// Save failed or was blocked; keep current status.
						return;
					}
				}
				await this.ruleStore.activate_rule();
			}
		} finally {
			frappe.dom.unfreeze();
		}
	}

	setup_debug_api() {
		frappe.provide("flexirule.debug");
		flexirule.debug.show_dialog = () => this.show_debug_dialog();
	}

	show_debug_dialog() {
		let last_docname = localStorage.getItem(`flexirule-debug-last-doc-${this.rule}`);
		try {
			last_docname = last_docname ? JSON.parse(last_docname) : [];
			if (!Array.isArray(last_docname)) {
				last_docname = last_docname ? last_docname.split(",") : [];
			}
		} catch (e) {
			last_docname = last_docname ? last_docname.split(",") : [];
		}

		const last_sim_user = localStorage.getItem(`flexirule_debug_user_${this.rule}`);
		const last_sim_role = localStorage.getItem(`flexirule_debug_role_${this.rule}`);

		let d = new frappe.ui.Dialog({
			title: __("Debug Rule"),
			fields: [
				{
					fieldtype: "HTML",
					options: `
						<div class="alert alert-info small" style="margin-bottom: 15px;">
							${__(
								"Debug a rule against an existing record to inspect execution flow, conditions, variables, and action results. This is a simulation and does not modify data."
							)}
						</div>
					`,
				},
				{
					fieldtype: "Link",
					fieldname: "doctype",
					label: __("Document Type"),
					options: "DocType",
					default: this.ruleStore.rule_doc?.document_type,
					reqd: 1,
				},
				{
					fieldtype: "MultiSelectList",
					fieldname: "docnames",
					label: __("Documents"),
					reqd: 1,
					default: last_docname,
					get_data: async (txt) => {
						const doctype = d.get_value("doctype");

						if (!doctype) {
							return [];
						}

						const r = await frappe.db.get_link_options(doctype, txt);

						return r || [];
					},
				},
				{
					fieldtype: "Section Break",
					fieldname: "simulator",
				},
				{
					fieldtype: "Link",
					fieldname: "sim_user",
					label: __("Simulate User"),
					options: "User",
					default: last_sim_user ?? frappe.session.user,
					description: __("Execute the rule as if initiated by this user"),
				},
				{
					fieldtype: "HTML",
					fieldname: "current_context",
					options: `
					<div class="small text-muted">
						<strong>${__("Current User")}:</strong> ${frappe.session.user}
					</div>
					`,
				},
				{
					fieldtype: "Column Break",
					fieldname: "column_role",
				},
				{
					fieldtype: "Link",
					fieldname: "sim_role",
					label: __("Simulate Role"),
					options: "Role",
					default: last_sim_role,
					description: __("Use only this role during execution"),
				},
				{
					fieldtype: "Section Break",
					fieldname: "debug_log",
				},
				{
					fieldtype: "Check",
					fieldname: "save_log",
					label: __("Create Execution Log"),
					description: __("Persist a log record even for this debug run"),
					default: 1,
				},
			],
			primary_action_label: __("Debug"),
			primary_action: (values) => {
				if (values.docnames && values.docnames.length) {
					localStorage.setItem(
						`flexirule-debug-last-doc-${this.rule}`,
						JSON.stringify(values.docnames)
					);
				}
				localStorage.setItem(`flexirule_debug_user_${this.rule}`, values.sim_user || "");
				localStorage.setItem(`flexirule_debug_role_${this.rule}`, values.sim_role || "");

				this.uiStore.clear_test_result();

				frappe.call({
					method: "flexirule.ruleflow.api.test_rule",
					args: {
						rule_name: this.rule,
						doctype: values.doctype,
						docnames: values.docnames,
						sim_user: values.sim_user,
						sim_role: values.sim_role,
						dry_run: !values.save_log,
						skip_log_enqueue: !values.save_log,
					},
					callback: (r) => {
						if (r.message?.multi) {
							// For multi-run, we might already have results from realtime.
							// But we should ensure the UI store is populated with what the API returned.
							// We clear first to avoid duplicates if realtime did work.
							this.uiStore.clear_test_result();
							if (r.message.results && r.message.results.length > 0) {
								r.message.results.forEach((res) => {
									this.uiStore.add_test_progress_result(res);
								});
							}

							if (r.message.success_count > 0) {
								frappe.show_alert(
									{
										message: __(
											"Debug completed: {0} succeeded, {1} failed out of {2}",
											[
												r.message.success_count,
												r.message.failure_count,
												r.message.total,
											]
										),
										indicator: r.message.failure_count > 0 ? "orange" : "green",
									},
									5
								);
							} else {
								frappe.show_alert(
									{
										message: __("Debug completed: All {0} failed", [
											r.message.total,
										]),
										indicator: "red",
									},
									7
								);
							}
						} else {
							this.uiStore.set_test_execution_visuals(r.message || {});
							if (r.message?.success) {
								const pathTrace =
									r.message.path_trace || r.message.execution_path || [];
								this.update_test_ui(pathTrace);

								frappe.show_alert(
									{
										message:
											r.message?.message ||
											__("Rule debug completed successfully"),
										indicator: "green",
									},
									5
								);
							} else {
								this.update_test_ui(r.message?.path_trace || []);
								frappe.show_alert(
									{
										message:
											r.message?.message ||
											r.message?.error ||
											(r.message?.execution?.errors || []).join("\n") ||
											__("Debug failed"),
										indicator: "red",
									},
									7
								);
							}
						}
						d.hide();
					},
				});
			},
		});
		d.show();
	}
}

/**
 * Entry point for Rule Builder
 */
frappe.ui.RuleBuilder = RuleBuilder;
export default RuleBuilder;
