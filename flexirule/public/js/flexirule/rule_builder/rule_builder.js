import { createApp } from "vue";
import { createPinia } from "pinia";

// Import FlexiRule Utilities
import "../utils/utils.js";
import "../utils/patches.js";
import "../controls/flexi_autocomplete.js";
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
		this.page.add_button(
			__("Reset Changes"),
			() => {
				this.ruleStore.fetch();
			},
			{ icon: "refresh" }
		);

		// Status Toggle
		this.status_btn = this.page.add_inner_button(__("Draft"), async () => {
			await this.toggle_rule_active();
		});

		// Test
		this.test_btn = this.page.add_inner_button(__("Test Rule"), () => {
			this.show_test_dialog();
		});

		// Clear visualization if any
		this.clear_test_btn = this.page.add_inner_button(__("Clear Test Path"), () => {
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

		// Watch for state changes
		this.ruleStore.$subscribe((mutation, state) => {
			this.update_save_button(state.is_dirty);
			this.update_status_button(state.rule_doc?.is_active);
		});

		this.uiStore.$subscribe((mutation, state) => {
			this.update_test_ui(state.test_execution_path);
		});

		// Initial status update after fetch
		// We might need to wait for fetch, but store.$subscribe handles mutations.
		// We can also watch rule_doc specifically if needed, but the main subscribe is usually enough for state changes.
		// Also manual call after mount if data is already there (it fetches async)

		// Use a watcher on rule_doc specifically
		const unwatch = this.ruleStore.$onAction(({ name, after }) => {
			if (name === "fetch") {
				after(() => {
					this.update_status_button(this.ruleStore.rule_doc?.is_active);
				});
			}
		});

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

		this.update_status_button(this.ruleStore.rule_doc?.is_active);
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

	show_test_dialog() {
		let d = new frappe.ui.Dialog({
			title: __("Test Rule"),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "doctype",
					label: __("Document Type"),
					options: "DocType",
					default: this.ruleStore.rule_doc?.document_type,
					reqd: 1,
				},
				{
					fieldtype: "Dynamic Link",
					fieldname: "docname",
					label: __("Document"),
					options: "doctype",
					reqd: 1,
				},
				{
					fieldtype: "Check",
					fieldname: "save_log",
					label: __("Create Execution Log"),
					description: __("Persist a log record even for this test run"),
					default: 1,
				},
			],
			primary_action_label: __("Test"),
			primary_action: (values) => {
				frappe.call({
					method: "flexirule.ruleflow.api.test_rule",
					args: {
						rule_name: this.rule,
						doctype: values.doctype,
						docname: values.docname,
						dry_run: !values.save_log,
						skip_log_enqueue: !values.save_log,
					},
					callback: (r) => {
						if (r.message?.success) {
							// Highlight path in builder
							const pathTrace =
								r.message.path_trace || r.message.execution_path || [];
							if (pathTrace.length) {
								this.uiStore.set_test_result(
									pathTrace,
									r.message.vars || r.message.context_snapshot
								);
								this.update_test_ui(pathTrace);
							}

							frappe.msgprint({
								title: __("Success"),
								message:
									r.message?.message || __("Rule test completed successfully"),
								indicator: "green",
							});
						} else {
							frappe.msgprint({
								title: __("Error"),
								message: r.message?.error || __("Test failed"),
								indicator: "red",
							});
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
