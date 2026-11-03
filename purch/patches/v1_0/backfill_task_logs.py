# Copyright (c) 2026, Admin and contributors

import frappe
from frappe.utils import now_datetime

PURCH_DOCTYPES = (
	"Material Request",
	"Purchase Order",
	"Request for Proposal",
	"Custom Comparison",
)


def execute():
	created = 0

	for doctype in PURCH_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue

		meta = frappe.get_meta(doctype)
		names = frappe.get_all(doctype, pluck="name")

		for name in names:
			if frappe.db.exists(
				"Task Log",
				{"reference_doctype": doctype, "reference_name": name},
			):
				continue

			try:
				doc = frappe.get_doc(doctype, name)
			except Exception:
				continue

			task_log = frappe.get_doc(
				{
					"doctype": "Task Log",
					"subject": f"Track: {doctype} {name}",
					"reference_doctype": doctype,
					"reference_name": name,
					"status": "Open",
					"priority": "Medium",
					"assigned_to": doc.owner or "Administrator",
					"auto_created": 1,
					"company": doc.get("company") if meta.has_field("company") else None,
				}
			)
			task_log.append(
				"entries",
				{
					"action": "Created",
					"field_label": "Document Created (Historical)",
					"old_value": "",
					"new_value": str(name),
					"changed_by": doc.owner or "Administrator",
					"changed_on": doc.creation or now_datetime(),
				},
			)
			task_log.flags.ignore_validate = True
			task_log.insert(ignore_permissions=True)
			created += 1

	frappe.db.commit()
	frappe.logger().info(f"Task Log backfill: created {created} purch records")
