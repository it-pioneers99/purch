# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return {
		"fieldname": "custom_comparison",
		"internal_links": {
			"Material Request": ["material_requests", "material_request"],
			"Request for Proposal": ["request_for_proposals", "request_for_proposal"],
		},
		"non_standard_fieldnames": {
			"Purchase Order": "custom_comparison",
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Material Request", "Request for Proposal", "Purchase Order"]},
		],
	}
