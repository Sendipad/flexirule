from frappe import _


def get_data():
	return {
		"fieldname": "rule",
		"non_standard_fieldnames": {
			"Rule": "rule",
		},
		"internal_and_external_links": {
			"Rule": ["actions", "rule"],
		},
		"transactions": [
			{
				"label": _("Logs & Schedulers"),
				"items": ["Rule Execution Log", "Rule Scheduler"],
			},
			{
				"label": _("Tasks"),
				"items": ["Data Review Task"],
			},
			{
				"label": _("Related Rules"),
				"items": ["Rule"],
			},
		],
	}
