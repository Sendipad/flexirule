// action_type_list.js
// action_type_list.js

frappe.listview_settings["Action Type"] = {
	onload(listview) {
		listview.page.clear_primary_action();
	},
};
