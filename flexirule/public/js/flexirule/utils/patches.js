/**
 * FlexiRule Patches for Frappe Core Controls
 * Targeted at fixing issues in standard controls without modifying Frappe core files.
 */

(function () {
	// 1. Fix ControlMultiCheck
	if (frappe.ui.form.ControlMultiCheck) {
		// Add validate method to prevent TypeError in BaseControl.validate_and_set_in_model
		if (!frappe.ui.form.ControlMultiCheck.prototype.validate) {
			frappe.ui.form.ControlMultiCheck.prototype.validate = function (v) {
				return v;
			};
		}

		/**
		 * Add set_input to handle reactivity correctly.
		 * When set_value is called, BaseControl calls set_input.
		 * Standard MultiCheck was missing this, causing UI to stay out of sync.
		 */
		frappe.ui.form.ControlMultiCheck.prototype.set_input = function (value) {
			this.selected_options = Array.isArray(value) ? value : [];
			this.value = this.selected_options; // Ensure this.value is kept in sync
			if (this.$checkbox_area) {
				this.select_options(this.selected_options);
			}
		};

		/**
		 * Override set_checked_options to be more robust.
		 * It should prioritize the value already in the control or model.
		 * Fixes the "fast uncheck" bug where refresh() wipes UI state in Dialogs.
		 */
		const standard_set_checked_options =
			frappe.ui.form.ControlMultiCheck.prototype.set_checked_options;
		frappe.ui.form.ControlMultiCheck.prototype.set_checked_options = function () {
			// Priority: Model Value > Control Value > Internal Selected Options
			let val = this.get_model_value() || this.value || this.selected_options;

			if (val && Array.isArray(val) && val.length > 0) {
				this.selected_options = val;
				this.select_options(this.selected_options);
			} else {
				// Only fallback to standard (filtered options) if we have no existing value
				standard_set_checked_options.apply(this, arguments);
			}
		};

		/**
		 * Fix bind_checkboxes:
		 * 1. Remove previous listeners (fix multiple triggers bug in core).
		 * 2. Call set_value to sync UI changes back to the model (fix state loss on refresh).
		 */
		frappe.ui.form.ControlMultiCheck.prototype.bind_checkboxes = function () {
			// Remove any existing listeners on the wrapper to prevent double execution
			// Standard Frappe was leaking listeners on every refresh()
			$(this.wrapper).off("change", ":checkbox");

			$(this.wrapper).on("change", ":checkbox", (e) => {
				const $checkbox = $(e.target);
				const option_name = $checkbox.attr("data-unit");

				if (!this.selected_options) {
					this.selected_options = [];
				}

				if ($checkbox.is(":checked")) {
					if (!this.selected_options.includes(option_name)) {
						this.selected_options.push(option_name);
					}
				} else {
					let index = this.selected_options.indexOf(option_name);
					if (index > -1) {
						this.selected_options.splice(index, 1);
					}
				}

				// CRITICAL: Sync back to model/control.
				// Using set_value(v, true) to force internal consistency without triggering another refresh loop if possible
				this.set_value(this.selected_options);

				// Handle both underscore and no-underscore variations of on_change
				if (this.df.on_change) {
					this.df.on_change.apply(this, [e]);
				} else if (this.df.onchange) {
					this.df.onchange.apply(this, [e]);
				}
			});
		};

		/**
		 * Add set_read_only support.
		 * Standard MultiCheck ignores read_only state changes during refresh.
		 */
		frappe.ui.form.ControlMultiCheck.prototype.set_read_only = function () {
			const is_read_only = !!this.df.read_only;
			if (this.$checkbox_area) {
				this.$checkbox_area.find(":checkbox").prop("disabled", is_read_only);
			}
			if (this.$select_buttons) {
				this.$select_buttons.find("button").prop("disabled", is_read_only);
			}
		};

		/**
		 * Ensure refresh_input respects read_only
		 */
		const standard_refresh_input = frappe.ui.form.ControlMultiCheck.prototype.refresh_input;
		frappe.ui.form.ControlMultiCheck.prototype.refresh_input = function () {
			standard_refresh_input.apply(this, arguments);
			this.set_read_only();
		};
	}

	// 2. Patch Workspace.prototype.show_page to handle non-workspace routes gracefully
	if (frappe.views && frappe.views.Workspace) {
		const original_show_page = frappe.views.Workspace.prototype.show_page;
		frappe.views.Workspace.prototype.show_page = async function (page) {
			if (!page || !page.name) {
				return;
			}
			const pages = page.public && this.public_pages?.length ? this.public_pages : this.private_pages;
			const current_page = pages?.filter((p) => p.title == page.name)[0];
			if (!current_page) {
				return;
			}
			return original_show_page.apply(this, arguments);
		};
	}
})();
