# Copyright (c) 2026, Admin and contributors

import frappe

from purch.install import remove_task_log_desk_references, _sync_purch_workspace


def execute():
	remove_task_log_desk_references()
	_sync_purch_workspace()
	frappe.clear_cache()
