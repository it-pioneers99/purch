from frappe import _


def get_data():
	return {
		"fieldname": "request_for_proposal",
		"transactions": [
			{"label": _("Reference"), "items": ["Custom Comparison"]},
		],
	}
