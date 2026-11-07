import frappe

from purch.custom_fields import setup_custom_fields

# Legacy purch doctypes removed from the app — scrub on every migrate (idempotent).
_PURGE_DOCTYPES = ("Task Log", "Task Log Change", "Task Log Entry")


def after_install():
	setup_custom_fields()
	_purge_legacy_doctypes_from_site()
	frappe.clear_cache()


def after_migrate():
	_purge_legacy_doctypes_from_site()
	_sync_purch_workspace()
	frappe.clear_cache()


def _purge_legacy_doctypes_from_site():
	for link_to in _PURGE_DOCTYPES:
		frappe.db.delete("Workspace Link", {"link_to": link_to})
		frappe.db.delete("Workspace Shortcut", {"link_to": link_to})

	for dt in _PURGE_DOCTYPES:
		frappe.db.delete("Custom Field", {"options": dt})
		frappe.db.delete("Client Script", {"dt": dt})

	if frappe.db.table_exists("Client Script"):
		frappe.db.delete("Client Script", {"script": ["like", "%task_log%"]})
		frappe.db.delete("Client Script", {"script": ["like", "%Task Log%"]})
		frappe.db.delete("Report", {"ref_doctype": dt})
		if frappe.db.table_exists("Custom DocPerm"):
			frappe.db.delete("Custom DocPerm", {"parent": dt})

	for dt in _PURGE_DOCTYPES:
		if frappe.db.exists("DocType", dt):
			frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)

	for doctype in reversed(_PURGE_DOCTYPES):
		if frappe.db.table_exists(doctype):
			frappe.db.sql(f"DELETE FROM `tab{doctype}`")

	for doctype in reversed(_PURGE_DOCTYPES):
		tablename = f"tab{doctype}"
		if tablename in frappe.db.get_tables():
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{tablename}`")

	if frappe.db.table_exists("User Permission"):
		for dt in _PURGE_DOCTYPES:
			frappe.db.delete("User Permission", {"allow": dt})


def _sync_purch_workspace():
	if not frappe.db.exists("Workspace", "Purch"):
		return
	try:
		frappe.reload_doc("Purch", "Workspace", "Purch", force=True)
	except Exception:
		frappe.log_error(title="Purch workspace sync failed")
