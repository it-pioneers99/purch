// Removed purch Task Log — neutralize cached task_log.js and stray boot permissions.
(function () {
	const REMOVED = new Set(["Task Log", "Task Log Change", "Task Log Entry"]);
	const STUB = "purch.purch.doctype.task_log.task_log.";

	function scrub_boot() {
		const user = frappe.boot && frappe.boot.user;
		if (!user) {
			return;
		}
		[
			"can_read",
			"can_write",
			"can_create",
			"can_delete",
			"can_submit",
			"can_cancel",
			"can_select",
			"can_get_report",
		].forEach((key) => {
			if (Array.isArray(user[key])) {
				user[key] = user[key].filter((d) => !REMOVED.has(d));
			}
		});
	}

	function patch_model() {
		const wrap = (fn) =>
			function (doctype) {
				if (REMOVED.has(doctype)) {
					return false;
				}
				return fn.apply(this, arguments);
			};

		if (frappe.model) {
			["can_read", "can_write", "can_create", "can_delete", "can_submit"].forEach((m) => {
				if (typeof frappe.model[m] === "function") {
					frappe.model[m] = wrap(frappe.model[m]);
				}
			});
		}

		if (frappe.get_meta) {
			const _get_meta = frappe.get_meta.bind(frappe);
			frappe.get_meta = function (doctype) {
				if (REMOVED.has(doctype)) {
					return { name: doctype, istable: 0, fields: [] };
				}
				return _get_meta(doctype);
			};
		}
	}

	function patch_calls() {
		const stub = (method) => {
			if (method.includes("get_document_task_logs") || method.includes("get_document_change_logs")) {
				return Promise.resolve([]);
			}
			if (method.includes("ensure_task_log_for_document")) {
				return Promise.resolve({ name: null, created: false });
			}
			if (method.includes("mark_completed")) {
				return Promise.resolve({});
			}
			return null;
		};

		if (frappe.xcall) {
			const _xcall = frappe.xcall.bind(frappe);
			frappe.xcall = function (method, args) {
				if (typeof method === "string" && method.indexOf(STUB) === 0) {
					const hit = stub(method);
					if (hit) {
						return hit;
					}
				}
				return _xcall(method, args);
			};
		}

	}

	function apply() {
		if (typeof frappe === "undefined") {
			return;
		}
		scrub_boot();
		patch_model();
		patch_calls();
	}

	if (typeof frappe !== "undefined") {
		apply();
	} else {
		document.addEventListener("app_ready", apply);
		document.addEventListener("DOMContentLoaded", () => setTimeout(apply, 0));
	}
})();
