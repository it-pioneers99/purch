# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class TaskLog(Document):
	def validate(self):
		self.validate_reference()
		self.set_completion_fields()

	def validate_reference(self):
		if not self.reference_doctype or not self.reference_name:
			return

		if frappe.flags.in_task_log_change:
			return

		if not frappe.db.exists(self.reference_doctype, self.reference_name):
			frappe.throw(
				_("{0} {1} does not exist").format(self.reference_doctype, self.reference_name)
			)

		if not self.company and frappe.get_meta(self.reference_doctype).has_field("company"):
			self.company = frappe.db.get_value(
				self.reference_doctype, self.reference_name, "company"
			)

	def set_completion_fields(self):
		if self.status == "Completed":
			if not self.completed_on:
				self.completed_on = now_datetime()
			if not self.completed_by:
				self.completed_by = frappe.session.user
		else:
			self.completed_on = None
			self.completed_by = None


def get_task_log_for_document(reference_doctype, reference_name):
	return frappe.db.get_value(
		"Task Log",
		{"reference_doctype": reference_doctype, "reference_name": reference_name},
		"name",
	)


@frappe.whitelist()
def get_document_task_logs(reference_doctype, reference_name):
	if not reference_doctype or not reference_name:
		return []

	return frappe.get_all(
		"Task Log",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		},
		fields=[
			"name",
			"subject",
			"status",
			"priority",
			"due_date",
			"assigned_to",
			"auto_created",
			"modified",
		],
		order_by="modified desc",
	)


@frappe.whitelist()
def get_document_change_logs(reference_doctype, reference_name, limit=20):
	if not reference_doctype or not reference_name:
		return []

	task_log = get_task_log_for_document(reference_doctype, reference_name)
	if not task_log:
		return []

	return frappe.get_all(
		"Task Log Entry",
		filters={"parent": task_log},
		fields=[
			"name",
			"action",
			"field_label",
			"old_value",
			"new_value",
			"changed_by",
			"changed_on",
		],
		order_by="changed_on desc, idx desc",
		limit_page_length=limit,
	)


@frappe.whitelist()
def ensure_task_log_for_document(reference_doctype, reference_name):
	if not reference_doctype or not reference_name:
		frappe.throw(_("Document Type and Document are required"))

	frappe.has_permission(reference_doctype, "read", reference_name, throw=True)
	doc = frappe.get_doc(reference_doctype, reference_name)

	from purch.task_log_tracker import _append_backfill_entry, _get_or_create_task_log

	task_log, is_new = _get_or_create_task_log(doc)
	if is_new:
		_append_backfill_entry(task_log, doc)

	return {"name": task_log.name, "created": is_new}


@frappe.whitelist()
def mark_completed(name):
	doc = frappe.get_doc("Task Log", name)
	doc.check_permission("write")
	doc.status = "Completed"
	doc.save()
	return doc.as_dict()
