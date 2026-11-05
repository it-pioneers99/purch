# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.core.doctype.version.version import get_diff
from frappe.utils import cstr, now_datetime

SKIP_DOCTYPES = {
	"Task Log Change",
	"Task Log",
	"Task Log Entry",
	"Version",
	"Activity Log",
	"Error Log",
	"Communication",
	"Comment",
	"View Log",
	"Access Log",
	"Email Queue",
	"Notification Log",
	"Scheduled Job Log",
	"Route History",
	"Energy Point Log",
	"DocType",
	"Patch Log",
	"Transaction Log",
	"Prepared Report",
	"Singles",
}


def apply_delete_link_check_patch():
	"""Ensure Task Log never blocks delete/cancel even if hooks cache is stale."""
	import frappe.model.delete_doc as delete_doc

	if getattr(delete_doc, "_purch_task_log_patch_applied", False):
		return

	_original = delete_doc.check_if_doc_is_dynamically_linked

	def check_if_doc_is_dynamically_linked(doc, method="Delete"):
		detach_task_logs_from_document(doc, method)
		return _original(doc, method)

	delete_doc.check_if_doc_is_dynamically_linked = check_if_doc_is_dynamically_linked
	delete_doc._purch_task_log_patch_applied = True


def _track_subject(doc):
	return _("Track: {0} {1}").format(doc.doctype, doc.name)


def _find_task_log_name(doc):
	name = frappe.db.get_value(
		"Task Log",
		{"reference_doctype": doc.doctype, "reference_name": doc.name},
		"name",
	)
	if name:
		return name
	return frappe.db.get_value("Task Log", {"subject": _track_subject(doc)}, "name")


def detach_task_logs_from_document(doc, method=None):
	"""Unlink Task Logs so delete/cancel of the source document is never blocked."""
	if frappe.flags.in_migrate or frappe.flags.in_install:
		return

	if not doc or not getattr(doc, "doctype", None):
		return

	if doc.doctype in SKIP_DOCTYPES or frappe.get_meta(doc.doctype).istable:
		return

	allow_delete_despite_task_logs(doc)

	label = cstr(doc.name)
	for task_log in frappe.get_all(
		"Task Log",
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
		fields=["name", "description"],
	):
		note = _("\nReference detached ({0}): {1} {2}").format(
			method or "unlink", doc.doctype, label
		)
		description = (task_log.description or "") + note
		frappe.db.set_value(
			"Task Log",
			task_log.name,
			{
				"reference_doctype": None,
				"reference_name": None,
				"description": description.strip(),
			},
			update_modified=False,
		)

	for row in frappe.get_all(
		"Task Log Change",
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
		pluck="name",
	):
		frappe.db.set_value(
			"Task Log Change",
			row,
			{"reference_doctype": None, "reference_name": None},
			update_modified=False,
		)


def allow_delete_despite_task_logs(doc):
	"""Frappe link checks during cancel/delete."""
	existing = list(doc.get("ignore_linked_doctypes") or [])
	for doctype in ("Task Log", "Task Log Change"):
		if doctype not in existing:
			existing.append(doctype)
	doc.ignore_linked_doctypes = existing


def log_document_change(doc, method=None):
	if frappe.flags.in_task_log_change:
		return

	if frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_import:
		return

	if not doc or not getattr(doc, "doctype", None):
		return

	if doc.doctype in SKIP_DOCTYPES or frappe.get_meta(doc.doctype).istable:
		return

	if method == "on_trash":
		return

	action = _get_action(doc, method)
	if not action:
		return

	changed_by = frappe.session.user or "Administrator"
	changed_on = now_datetime()
	field_changes = _get_field_changes(doc, action)

	try:
		frappe.flags.in_task_log_change = True
		task_log, is_new = _get_or_create_task_log(doc)
		if is_new and action != "Created":
			_append_backfill_entry(task_log, doc)
		_append_change_entries(task_log, action, field_changes, changed_by, changed_on)
	except Exception:
		frappe.log_error(title=_("Task Log tracking failed for {0} {1}").format(doc.doctype, doc.name))
	finally:
		frappe.flags.in_task_log_change = False

	# on_cancel runs after before_cancel detach; logging must not leave a dynamic link
	if method == "on_cancel":
		detach_task_logs_from_document(doc, method)


def _get_or_create_task_log(doc):
	name = _find_task_log_name(doc)
	if name:
		return frappe.get_doc("Task Log", name), False

	company = doc.get("company") if doc.meta.has_field("company") else None
	payload = {
		"doctype": "Task Log",
		"subject": _track_subject(doc),
		"status": "Open",
		"priority": "Medium",
		"assigned_to": doc.owner or frappe.session.user,
		"auto_created": 1,
		"company": company,
	}
	# Cancelled/deleted docs must not get a new dynamic link (blocks check_no_back_links_exist)
	if doc.docstatus != 2 and not getattr(doc.flags, "in_delete", False):
		payload["reference_doctype"] = doc.doctype
		payload["reference_name"] = doc.name

	task_log = frappe.get_doc(payload)
	task_log.insert(ignore_permissions=True)
	return task_log, True


def _append_backfill_entry(task_log, doc):
	"""Add historical creation row for documents that existed before auto-tracking."""
	task_log.append(
		"entries",
		{
			"action": "Created",
			"field_label": _("Document Created (Historical)"),
			"old_value": "",
			"new_value": cstr(doc.name),
			"changed_by": doc.owner or frappe.session.user or "Administrator",
			"changed_on": doc.creation or now_datetime(),
		},
	)
	task_log.flags.ignore_validate = True
	task_log.save(ignore_permissions=True)


def _append_change_entries(task_log, action, field_changes, changed_by, changed_on):
	task_log.reload()

	for change in field_changes:
		label, old_value, new_value = _normalize_change(change)
		if not label and not old_value and not new_value:
			continue

		task_log.append(
			"entries",
			{
				"action": action,
				"field_label": label,
				"old_value": old_value,
				"new_value": new_value,
				"changed_by": changed_by,
				"changed_on": changed_on,
			},
		)

	if not task_log.entries:
		return

	task_log.flags.ignore_validate = True
	task_log.save(ignore_permissions=True)


def _normalize_change(change):
	label = cstr(change.get("label") or change.get("fieldname") or "").strip()
	if not label:
		label = _("General")

	old_value = cstr(change.get("old") or "")
	new_value = cstr(change.get("new") or "")
	return label, old_value, new_value


def _get_action(doc, method):
	if method == "after_insert":
		return "Created"

	if method == "on_submit":
		return "Submitted"

	if method == "on_cancel":
		return "Cancelled"

	if method == "on_trash":
		return "Deleted"

	if method in {"on_update", "on_update_after_submit"}:
		if getattr(doc.flags, "in_insert", False):
			return None

		previous = doc.get_doc_before_save()
		if previous and previous.docstatus != doc.docstatus:
			return None

		return "Updated"

	return None


def _get_field_changes(doc, action):
	if action == "Created":
		return [{"label": _("Document Created"), "old": "", "new": doc.name}]

	if action in {"Submitted", "Cancelled", "Deleted"}:
		return [{"label": _("Document {0}").format(action), "old": "", "new": action}]

	previous = doc.get_doc_before_save()
	if not previous:
		return [{"label": _("Updated"), "old": "", "new": _("No previous version")}]

	diff = get_diff(previous, doc) or {}
	changes = []

	for fieldname, old, new in diff.get("changed", []):
		label = doc.meta.get_label(fieldname) or fieldname or _("General")
		changes.append({"label": label, "old": old, "new": new})

	for table_field, _row_name, row_idx, row_diff in diff.get("row_changed", []):
		table_label = doc.meta.get_label(table_field) or table_field or _("Table")
		table_options = doc.meta.get_field(table_field).options
		child_meta = frappe.get_meta(table_options) if table_options else None

		for child_field, old, new in row_diff:
			child_label = (child_meta.get_label(child_field) if child_meta else None) or child_field or _("Field")
			changes.append(
				{
					"label": f"{table_label} #{row_idx} · {child_label}",
					"old": old,
					"new": new,
				}
			)

	for table_field, _row in diff.get("added", []):
		table_label = doc.meta.get_label(table_field) or table_field or _("Table")
		changes.append({"label": table_label, "old": "", "new": _("Row added")})

	for table_field, _row in diff.get("removed", []):
		table_label = doc.meta.get_label(table_field) or table_field or _("Table")
		changes.append({"label": table_label, "old": _("Row removed"), "new": ""})

	if not changes:
		return [{"label": _("Updated"), "old": "", "new": _("Saved with no tracked field changes")}]

	return changes[:50]
