# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe


def setup_custom_fields():
	custom_field = {
		"doctype": "Custom Field",
		"dt": "Purchase Order",
		"fieldname": "custom_comparison",
		"label": "Custom Comparison",
		"fieldtype": "Link",
		"options": "Custom Comparison",
		"insert_after": "supplier",
		"read_only": 1,
		"no_copy": 1,
		"print_hide": 1,
		"allow_on_submit": 1,
	}

	existing = frappe.db.get_value(
		"Custom Field",
		{"dt": "Purchase Order", "fieldname": "custom_comparison"},
		"name",
	)
	if existing:
		doc = frappe.get_doc("Custom Field", existing)
		doc.insert_after = "supplier"
		doc.save(ignore_permissions=True)
	elif not frappe.db.exists("Custom Field", {"dt": "Purchase Order", "fieldname": "custom_comparison"}):
		frappe.get_doc(custom_field).insert(ignore_permissions=True)


def remove_custom_fields():
	if frappe.db.exists("Custom Field", {"dt": "Purchase Order", "fieldname": "custom_comparison"}):
		frappe.delete_doc(
			"Custom Field",
			frappe.db.get_value(
				"Custom Field",
				{"dt": "Purchase Order", "fieldname": "custom_comparison"},
			),
			ignore_permissions=True,
		)
