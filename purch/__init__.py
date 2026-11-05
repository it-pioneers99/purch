__version__ = "0.0.1"


def _patch_frappe_link_checks():
	from purch.task_log_tracker import apply_delete_link_check_patch

	apply_delete_link_check_patch()


_patch_frappe_link_checks()
