frappe.listview_settings["Rule"] = {
	add_fields: ["is_active", "document_type", "trigger_event", "rule_type"],

	get_indicator: function (doc) {
		// Active + Manual
		if (doc.is_active && doc.trigger_type === "Callable Event") {
			return [__("Active (Manual)"), "green", "is_active,=,1"];
		}

		// Active + Non-manual → BLUE
		if (doc.is_active && doc.trigger_type !== "Callable Event") {
			return [__(doc.trigger_event), "blue", "is_active,=,1"];
		}

		// Inactive
		return [__("Inactive"), "gray", "is_active,=,0"];
	},

	formatters: {
		rule_name: function (value, field, doc) {
			// Add builder icon before rule name
			return `
                <span class="rule-name-cell">
                    <a class="builder-icon"
                       href="/app/rule-builder/${doc.name}"
                       title="${__("Open in Rule Builder")}"
                       onclick="event.stopPropagation();">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="5" cy="20" r="1.5" fill="currentColor" stroke="none"/>
                            <path d="M5 18 V 9 A 3.5 3.5 0 0 1 12 9 V 15 A 3.5 3.5 0 0 0 19 15 V 4" />
                            <path d="M16 7 L 19 4 L 22 7" />
                        </svg>
                    </a>
                    ${value}
                </span>
            `;
		},
	},

	onload: function (listview) {
		// Add "New with Builder" button
		listview.page.add_inner_button(__("Create with Builder"), function () {
			// Create new rule and open builder
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

		// Add custom CSS
		if (!document.getElementById("rule-list-styles")) {
			const style = document.createElement("style");
			style.id = "rule-list-styles";
			style.textContent = `
                .rule-name-cell {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                .builder-icon {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 24px;
                    height: 24px;
                    border-radius: 4px;
                    background: var(--bg-light-gray);
                    color: var(--text-muted);
                    transition: all 0.2s;
                }
                .builder-icon:hover {
                    background: var(--primary);
                    color: white;
                }
            `;
			document.head.appendChild(style);
		}
	},
};
