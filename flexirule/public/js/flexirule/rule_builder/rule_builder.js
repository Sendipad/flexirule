import { createApp, watch } from "vue";
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
	}

	setup_page() {
		// Set page title
		this.page.set_title(__(this.rule));

		// Clear existing actions
		this.page.clear_actions();
		this.page.clear_menu();
		this.page.clear_custom_actions();

		// Primary action - Save button
		const translatedSaveLabel = __("Save Rule");
		this.save_button_label =
			typeof translatedSaveLabel === "string" && translatedSaveLabel.trim()
				? translatedSaveLabel
				: "Save Rule";
		this.save_btn = this.page.set_primary_action(this.save_button_label, () =>
			this.ruleStore.save_changes()
		);

		// Secondary button - Reset
		this.reset_btn = this.page.add_button(
			__("Reset Changes"),
			() => {
				this.ruleStore.fetch();
			},
			{ icon: "refresh" }
		);
		this.reset_btn.hide();

		// Status Toggle
		this.status_btn = this.page.add_inner_button(__("Draft"), async () => {
			await this.toggle_rule_active();
		});

		// Debug
		this.test_btn = this.page.add_inner_button(__("Debug Rule"), () => {
			flexirule.debug.show_dialog();
		});

		// Clear visualization if any
		this.clear_test_btn = this.page.add_inner_button(__("Clear Debug Path"), () => {
			this.uiStore.clear_test_result();
			this.update_test_ui([]);
		});
		this.clear_test_btn.hide();

		// Custom status area beside title
		this.setup_custom_header();

		// Menu items
		this.page.add_menu_item(__("Go to Rule"), () => {
			frappe.set_route("Form", "Rule", this.rule);
		});

		this.page.add_menu_item(__("Keyboard Shortcuts"), () => {
			this.show_keyboard_shortcuts();
		});
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

		// Initial sync
		this.update_test_ui(this.uiStore.test_execution_path);

		// Watch for dirty state changes (computed)
		watch(
			() => this.ruleStore.is_dirty,
			(is_dirty) => {
				this.update_save_button(is_dirty);
				if (this.reset_btn) {
					is_dirty ? this.reset_btn.show() : this.reset_btn.hide();
				}
			}
		);

		// Watch for active status changes - Unified Source of Truth
		watch(
			() => [this.ruleStore.is_active, this.ruleStore.rule_doc?.is_active],
			([is_active]) => {
				this.update_status_button(is_active);
			},
			{ immediate: true }
		);

		this.uiStore.$subscribe((mutation, state) => {
			this.update_test_ui(state.test_execution_path);
		});

		this.setup_debug_api();

		// Mount app
		this.$rule_builder = app.mount(this.$wrapper.get(0));
	}

	async toggle_rule_active() {
		if (!this.ruleStore.rule_doc) return;

		// Do not allow silent state mutation. Use lifecycle API transitions.
		try {
			frappe.dom.freeze(__("Updating rule status..."));

			if (this.ruleStore.rule_doc.is_active) {
				await this.ruleStore.deactivate_rule();
			} else {
				// If there are semantic changes (logic, edges), persist first.
				// We allow purely visual changes (positions) to be saved during activation
				// if save_changes() is called, but is_semantically_dirty is the blocker.
				if (this.ruleStore.is_semantically_dirty) {
					const confirmed = await new Promise((resolve) => {
						frappe.confirm(
							__("You have unsaved semantic changes. Save and activate now?"),
							() => resolve(true),
							() => resolve(false)
						);
					});
					if (!confirmed) return;

					await this.ruleStore.save_changes();
					if (this.ruleStore.is_semantically_dirty) {
						// Save failed or was blocked; keep current status.
						return;
					}
				} else if (this.ruleStore.is_dirty) {
					// Purely visual changes - just save silently or continue
					await this.ruleStore.save_changes();
				}

				await this.ruleStore.activate_rule();
			}
		} finally {
			frappe.dom.unfreeze();
		}
	}

	update_status_button(is_active) {
		const status_text = is_active ? __("Active") : __("Draft");
		const indicator_color = is_active ? "green" : "orange";

		// 1. Update Title with Badges
		// We use a container to avoid overwriting the whole title if possible
		if (!this.page.$title_area.find(".flexirule-status-badges").length) {
			this.page.$title_area.find(".title-text, .page-title").first().append(`
				<span class="flexirule-status-badges ml-2" style="display: inline-flex; gap: 4px; vertical-align: middle;"></span>
			`);
		}
		const $badges = this.page.$title_area.find(".flexirule-status-badges");

		let badges_html = `<span class="indicator-pill ${indicator_color}" style="font-size: 10px; padding: 2px 10px; font-weight: 700;">
			${status_text}
		</span>`;

		if (
			this.ruleStore.rule_doc?.trigger_type === "Callable Event" &&
			this.ruleStore.rule_doc?.exposed_as_subrule
		) {
			badges_html += ` <span class="indicator-pill blue" style="font-size: 10px; padding: 2px 10px; font-weight: 700;">
				${__("Sub-Rule")}
			</span>`;
		}
		$badges.html(badges_html);

		// 2. Update Toggle Button (on the right)
		if (this.status_btn) {
			this.status_btn.show().removeClass("hide");
			if (is_active) {
				this.status_btn
					.text(__("Unlock for Editing"))
					.removeClass("btn-default btn-primary btn-success")
					.addClass("btn-warning");
			} else {
				this.status_btn
					.text(__("Set to Active"))
					.removeClass("btn-warning btn-success")
					.addClass("btn-default");
			}
		}
	}

	update_save_button(is_dirty) {
		if (this.save_btn?.text()?.trim() !== this.save_button_label) {
			this.save_btn.text(this.save_button_label);
		}
		if (is_dirty) {
			this.save_btn.removeClass("btn-primary-light").addClass("btn-primary");
			this.page.set_indicator(__("Not Saved"), "orange");
		} else {
			this.save_btn.removeClass("btn-primary").addClass("btn-primary-light");
			this.page.clear_indicator();
		}
	}

	update_test_ui(test_path) {
		const show = !!(test_path && test_path.length > 0);
		if (this.clear_test_btn) {
			if (show) {
				this.clear_test_btn.show().removeClass("hide");
			} else {
				this.clear_test_btn.hide().addClass("hide");
			}
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

				const args = {
					rule_name: this.rule,
					doctype: values.doctype,
					docnames: values.docnames,
					sim_user: values.sim_user,
					sim_role: values.sim_role,
					dry_run: !values.save_log,
					skip_log_enqueue: !values.save_log,
				};

				// If rule is dirty, send current draft for simulation
				if (this.ruleStore.is_dirty) {
					args.rule_doc_json = JSON.stringify(this.ruleStore.generateRuleDoc());
				}

				frappe.call({
					method: "flexirule.ruleflow.api.test_rule",
					args: args,
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
