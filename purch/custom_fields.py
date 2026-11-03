# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe


CUSTOM_FIELDS = [
	{
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
	},
	{
		"dt": "Purchase Order",
		"fieldname": "purchase_agreement",
		"label": "Purchase Agreement",
		"fieldtype": "Data",
		"insert_after": "custom_comparison",
		"allow_on_submit": 1,
		"in_standard_filter": 1,
	},
	{
		"dt": "Purchase Order",
		"fieldname": "creation_date",
		"label": "Creation Date",
		"fieldtype": "Date",
		"insert_after": "transaction_date",
		"read_only": 1,
		"no_copy": 1,
	},
	{
		"dt": "Purchase Order",
		"fieldname": "approved_date",
		"label": "Approved Date",
		"fieldtype": "Date",
		"insert_after": "creation_date",
		"read_only": 1,
		"no_copy": 1,
		"allow_on_submit": 1,
	},
	{
		"dt": "Material Request",
		"fieldname": "approved_date",
		"label": "Approved Date",
		"fieldtype": "Date",
		"insert_after": "transaction_date",
		"read_only": 1,
		"no_copy": 1,
		"allow_on_submit": 1,
	},
]

MATERIAL_REQUEST_PROPERTY_SETTERS = [
	{
		"doctype": "Material Request",
		"fieldname": "request_status",
		"property": "allow_on_submit",
		"value": "1",
		"property_type": "Check",
	},
	{
		"doctype": "Material Request",
		"fieldname": "request_status",
		"property": "hidden",
		"value": "0",
		"property_type": "Check",
	},
]


def ensure_custom_field(field):
	filters = {"dt": field["dt"], "fieldname": field["fieldname"]}
	existing = frappe.db.get_value("Custom Field", filters, "name")
	if existing:
		doc = frappe.get_doc("Custom Field", existing)
		changed = False
		for key, value in field.items():
			if key in ("dt", "fieldname"):
				continue
			if doc.get(key) != value:
				doc.set(key, value)
				changed = True
		if changed:
			doc.save(ignore_permissions=True)
		return

	frappe.get_doc({"doctype": "Custom Field", **field}).insert(ignore_permissions=True)


def ensure_property_setter(property_setter):
	filters = {
		"doc_type": property_setter["doctype"],
		"field_name": property_setter["fieldname"],
		"property": property_setter["property"],
	}
	existing = frappe.db.get_value("Property Setter", filters, "name")
	if existing:
		if frappe.db.get_value("Property Setter", existing, "value") != property_setter["value"]:
			frappe.db.set_value("Property Setter", existing, "value", property_setter["value"])
		return

	frappe.make_property_setter(
		{
			"doctype": property_setter["doctype"],
			"doctype_or_field": "DocField",
			"fieldname": property_setter["fieldname"],
			"property": property_setter["property"],
			"value": property_setter["value"],
			"property_type": property_setter["property_type"],
		},
		validate_fields_for_doctype=False,
		is_system_generated=False,
	)


def setup_material_request_request_status():
	for property_setter in MATERIAL_REQUEST_PROPERTY_SETTERS:
		ensure_property_setter(property_setter)

	frappe.clear_cache(doctype="Material Request")


def setup_custom_fields():
	for field in CUSTOM_FIELDS:
		ensure_custom_field(field)
	setup_material_request_request_status()


def remove_custom_fields():
	for field in CUSTOM_FIELDS:
		name = frappe.db.get_value(
			"Custom Field",
			{"dt": field["dt"], "fieldname": field["fieldname"]},
			"name",
		)
		if name:
			frappe.delete_doc("Custom Field", name, ignore_permissions=True)
