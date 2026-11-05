# Copyright (c) 2026, Admin and contributors
# Compatibility stubs — Task Log DocType was removed; old desk JS may still call these.

import frappe


@frappe.whitelist()
def get_document_task_logs(reference_doctype, reference_name):
	return []


@frappe.whitelist()
def get_document_change_logs(reference_doctype, reference_name, limit=20):
	return []


@frappe.whitelist()
def ensure_task_log_for_document(reference_doctype, reference_name):
	return {"name": None, "created": False}


@frappe.whitelist()
def mark_completed(name):
	return {}
