# Copyright (c) 2026, Admin and contributors

import frappe

from purch.install import _purge_legacy_doctypes_from_site


def execute():
	_purge_legacy_doctypes_from_site()
	frappe.clear_cache()
