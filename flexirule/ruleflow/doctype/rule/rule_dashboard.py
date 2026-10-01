from frappe import _


def get_data():
	return {
		"fieldname": "rule",
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
