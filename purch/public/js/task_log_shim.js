// Task Log DocType removed — neutralize stale task_log.js (browser cache / old deploys).
(function () {
	const REMOVED = new Set(["Task Log", "Task Log Change", "Task Log Entry"]);
	const STUB_METHODS = new Set([
		"purch.purch.doctype.task_log.task_log.get_document_task_logs",
		"purch.purch.doctype.task_log.task_log.get_document_change_logs",
		"purch.purch.doctype.task_log.task_log.ensure_task_log_for_document",
		"purch.purch.doctype.task_log.task_log.mark_completed",
	]);

	function patch_frappe() {
		if (!frappe.model || !frappe.model.can_read) {
			return;
		}
		const _can_read = frappe.model.can_read.bind(frappe.model);
		frappe.model.can_read = function (doctype) {
			if (REMOVED.has(doctype)) {
				return false;
			}
			try {
				return _can_read(doctype);
			} catch (e) {
				if (REMOVED.has(doctype)) {
					return false;
				}
				throw e;
			}
		};

		if (frappe.xcall) {
			const _xcall = frappe.xcall.bind(frappe);
			frappe.xcall = function (method, args) {
				if (STUB_METHODS.has(method)) {
					if (method.endsWith("get_document_task_logs")) {
						return Promise.resolve([]);
					}
					if (method.endsWith("get_document_change_logs")) {
						return Promise.resolve([]);
					}
					if (method.endsWith("ensure_task_log_for_document")) {
						return Promise.resolve({ name: null, created: false });
					}
					if (method.endsWith("mark_completed")) {
						return Promise.resolve({});
					}
				}
				return _xcall(method, args);
			};
		}
	}

	if (typeof frappe !== "undefined") {
		patch_frappe();
	} else {
		document.addEventListener("DOMContentLoaded", () => {
			if (typeof frappe !== "undefined") {
				patch_frappe();
			}
		});
	}
})();
