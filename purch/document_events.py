# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate


def set_creation_date(doc, method=None):
	if doc.get("creation_date"):
		return

	if doc.creation:
		doc.creation_date = getdate(doc.creation)
	else:
		doc.creation_date = nowdate()


def set_approved_date_on_submit(doc, method=None):
	if doc.get("approved_date"):
		return
	doc.db_set("approved_date", nowdate(), update_modified=False)


def clear_approved_date_on_cancel(doc, method=None):
	if doc.meta.has_field("approved_date"):
		doc.db_set("approved_date", None, update_modified=False)
