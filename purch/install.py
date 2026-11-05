import frappe

from purch.custom_fields import setup_custom_fields

_TASK_LOG_DOCTYPES = ("Task Log", "Task Log Change", "Task Log Entry")


def after_install():
	setup_custom_fields()
	remove_task_log_desk_references()
	frappe.clear_cache()


def after_migrate():
	remove_task_log_desk_references()
	_sync_purch_workspace()
	frappe.clear_cache()


def remove_task_log_desk_references():
	for link_to in _TASK_LOG_DOCTYPES:
		frappe.db.delete("Workspace Link", {"link_to": link_to})
		frappe.db.delete("Workspace Shortcut", {"link_to": link_to})


def _sync_purch_workspace():
	if not frappe.db.exists("Workspace", "Purch"):
		return
	try:
		frappe.reload_doc("Purch", "Workspace", "Purch", force=True)
	except Exception:
		frappe.log_error(title="Purch workspace sync failed")
