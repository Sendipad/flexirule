frappe.pages["rule-builder"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Rule Builder"),
		single_column: true,
	});

	// Hot reload in development
	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_rule_builder(wrapper));
	}
};

frappe.pages["rule-builder"].on_page_show = function (wrapper) {
	load_rule_builder(wrapper);
};

function load_rule_builder(wrapper) {
	let route = frappe.get_route();
	let $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();

	if (route.length > 1) {
		// Load the RuleBuilder bundle on demand
		frappe.require("rule_builder.bundle.js").then(() => {
			frappe.rule_builder = new frappe.ui.RuleBuilder({
				wrapper: $parent,
				page: wrapper.page,
				rule: route[1],
			});
		});
	} else {
		// No rule specified - show dialog to select
		let d = new frappe.ui.Dialog({
			title: __("Open Rule Builder"),
			fields: [
				{
					label: __("Select Rule"),
					fieldname: "rule",
					fieldtype: "Link",
					options: "Rule",
					reqd: 1,
				},
			],
			primary_action_label: __("Open"),
			primary_action({ rule }) {
				frappe.set_route("rule-builder", rule);
				d.hide();
			},
		});
		d.show();
	}
}
