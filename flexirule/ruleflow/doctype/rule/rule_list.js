frappe.listview_settings["Rule"] = {
	add_fields: [
		"is_active",
		"status",
		"trigger_type",
		"document_type",
		"trigger_event",
		"version",
		"priority",
		"modified",
		"modified_by",
	],

	// Dedicated first column button for opening Rule Builder
	button: {
		show(doc) {
			return doc.name;
		},
		get_label() {
			return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="5" cy="20" r="1.5" fill="currentColor" stroke="none"/>
				<path d="M5 18 V 9 A 3.5 3.5 0 0 1 12 9 V 15 A 3.5 3.5 0 0 0 19 15 V 4" />
				<path d="M16 7 L 19 4 L 22 7" />
			</svg>`;
		},
		get_description(doc) {
			return __("Open Rule Builder for {0}", [doc.rule_name || doc.name]);
		},
		action(doc) {
			frappe.set_route("rule-builder", doc.name);
		},
	},

	// Contract-driven status indicators
	get_indicator: function (doc) {
		const is_active = Boolean(doc.is_active) || doc.status === "Active";
		if (is_active) {
			return [__(doc.status || "Active"), "green", "is_active,=,1"];
		}
		if (doc.status === "Disabled") {
			return [__("Disabled"), "gray", "status,=,Disabled"];
		}
		if (doc.status === "Archived") {
			return [__("Archived"), "red", "status,=,Archived"];
		}
		if (doc.status === "Invalid" || doc.status === "Error") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		}
		return [__(doc.status || "Draft"), "blue", "status,=,Draft"];
	},

	onload: function (listview) {
		// Ensure contracts are loaded for backend metadata resolution
		if (flexirule && flexirule.contracts && flexirule.contracts.loadContractsFromBackend) {
			flexirule.contracts.loadContractsFromBackend().catch((e) => {
				console.warn("FlexiRule contracts deferred load:", e);
			});
		}

		// Add "Create with Builder" inner action
		listview.page.add_inner_button(__("Create with Builder"), function () {
			frappe.prompt(
				[
					{
						fieldname: "rule_name",
						fieldtype: "Data",
						label: __("Rule Name"),
						reqd: 1,
					},
					{
						fieldname: "document_type",
						fieldtype: "Link",
						label: __("Document Type"),
						options: "DocType",
						reqd: 1,
						filters: { istable: 0 },
					},
					{
						fieldname: "trigger_event",
						fieldtype: "Select",
						label: __("Trigger Event"),
						options:
							"Before Insert\nBefore Save\nValidate\nAfter Insert\nAfter Save\nBefore Submit\nOn Submit\nBefore Cancel\nOn Cancel\nOn Trash",
						default: "Validate",
						reqd: 1,
					},
				],
				function (values) {
					frappe.call({
						method: "frappe.client.insert",
						args: {
							doc: {
								doctype: "Rule",
								rule_name: values.rule_name,
								document_type: values.document_type,
								trigger_event: values.trigger_event,
								is_active: 0,
							},
						},
						callback: function (r) {
							if (r.message) {
								frappe.set_route("rule-builder", r.message.name);
							}
						},
					});
				},
				__("Create New Rule"),
				__("Open Builder")
			);
		});
	},
};
