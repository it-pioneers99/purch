# Copyright (c) 2026, Admin and contributors

import frappe


def execute():
	"""Remove desk/DB references to Task Log after the feature was removed."""
	for link_to in ("Task Log", "Task Log Change", "Task Log Entry"):
		frappe.db.delete("Workspace Link", {"link_to": link_to})
		frappe.db.delete("Workspace Shortcut", {"link_to": link_to})

	for dt in ("Task Log", "Task Log Change", "Task Log Entry"):
		if frappe.db.exists("DocType", dt):
			frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)

	for doctype in ("Task Log Entry", "Task Log", "Task Log Change"):
		tablename = f"tab{doctype}"
		if tablename in frappe.db.get_tables():
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{tablename}`")

	frappe.clear_cache()
