# Copyright (c) 2026, Admin and contributors

import frappe


def execute():
	"""Drop Task Log feature: data and DocTypes (no longer shipped in purch)."""
	for doctype in ("Task Log Entry", "Task Log", "Task Log Change"):
		if frappe.db.table_exists(doctype):
			frappe.db.sql(f"DELETE FROM `tab{doctype}`")

	for dt in ("Task Log", "Task Log Change", "Task Log Entry"):
		if frappe.db.exists("DocType", dt):
			frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)

	frappe.clear_cache()
