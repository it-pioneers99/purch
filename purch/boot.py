# Copyright (c) 2026, Admin contributors

_REMOVED = frozenset({"Task Log", "Task Log Change", "Task Log Entry"})
_USER_PERM_KEYS = (
	"can_read",
	"can_write",
	"can_create",
	"can_delete",
	"can_submit",
	"can_cancel",
	"can_select",
	"can_get_report",
)


def strip_removed_doctypes_from_boot(bootinfo):
	user = bootinfo.get("user")
	if isinstance(user, dict):
		for key in _USER_PERM_KEYS:
			values = user.get(key)
			if isinstance(values, list):
				user[key] = [d for d in values if d not in _REMOVED]
