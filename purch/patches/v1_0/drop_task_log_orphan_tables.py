# Copyright (c) 2026, Admin and contributors

import frappe


def execute():
	"""Remove leftover DB tables after Task Log DocTypes were deleted."""
	for doctype in ("Task Log Entry", "Task Log", "Task Log Change"):
		tablename = f"tab{doctype}"
		if tablename in frappe.db.get_tables():
			frappe.db.sql(f"DROP TABLE `{tablename}`")
