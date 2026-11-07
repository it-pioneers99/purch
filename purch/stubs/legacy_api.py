# Copyright (c) 2026, Admin contributors
# Empty responses for removed desk JS / cached bundles (no Task Log DocType).

import frappe


@frappe.whitelist()
def get_document_task_logs(reference_doctype=None, reference_name=None):
	return []


@frappe.whitelist()
def get_document_change_logs(reference_doctype=None, reference_name=None, limit=20):
	return []


@frappe.whitelist()
def ensure_task_log_for_document(reference_doctype=None, reference_name=None):
	return {"name": None, "created": False}


@frappe.whitelist()
def mark_completed(name=None):
	return {}
