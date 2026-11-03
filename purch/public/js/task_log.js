// Task Log: auto-tracked change history on every document

(function () {
	const SKIP_DOCTYPES = new Set([
		"Task Log",
		"Task Log Change",
		"Task Log Entry",
		"DocType",
		"User",
		"File",
		"Version",
		"Activity Log",
		"Error Log",
		"Communication",
	]);

	function can_show_task_log(frm) {
		if (!frm || !frm.doc || frm.is_new()) {
			return false;
		}
		if (SKIP_DOCTYPES.has(frm.doctype)) {
			return false;
		}
		return frappe.model.can_read("Task Log");
	}

	function render_task_log_section(frm, task_log, entries) {
		const entry_links = (entries || [])
			.map((row) => {
				const when = row.changed_on ? frappe.datetime.str_to_user(row.changed_on) : "";
				const field = row.field_label ? frappe.utils.escape_html(row.field_label) : __("General");
				const old_val = row.old_value ? frappe.utils.escape_html(String(row.old_value)) : "—";
				const new_val = row.new_value ? frappe.utils.escape_html(String(row.new_value)) : "—";
				return `<div class="mb-1">
					<span class="text-muted">${when}</span>
					· <strong>${frappe.utils.escape_html(row.action)}</strong>
					· ${field}
					· ${old_val} → ${new_val}
					· ${frappe.utils.escape_html(row.changed_by || "")}
				</div>`;
			})
			.join("");

		frm.dashboard.add_section(
			`<div class="task-log-dashboard">
				<a href="/app/task-log/${encodeURIComponent(task_log.name)}">
					${frappe.utils.escape_html(task_log.subject)}
				</a>
				<span class="text-muted"> · ${__("{0} change(s)", [(entries || []).length])}</span>
				<div class="mt-2">${entry_links || `<span class="text-muted">${__("No changes yet")}</span>`}</div>
			</div>`,
			__("Task Log")
		);
		frm.dashboard.show();
	}

	function show_task_log_dashboard(frm) {
		if (!frm.dashboard) {
			return;
		}

		frappe
			.xcall("purch.purch.doctype.task_log.task_log.get_document_task_logs", {
				reference_doctype: frm.doctype,
				reference_name: frm.doc.name,
			})
			.then((task_logs) => {
				if (task_logs && task_logs.length) {
					const task_log = task_logs[0];
					return frappe
						.xcall("purch.purch.doctype.task_log.task_log.get_document_change_logs", {
							reference_doctype: frm.doctype,
							reference_name: frm.doc.name,
							limit: 6,
						})
						.then((entries) => render_task_log_section(frm, task_log, entries));
				}

				return frappe
					.xcall("purch.purch.doctype.task_log.task_log.ensure_task_log_for_document", {
						reference_doctype: frm.doctype,
						reference_name: frm.doc.name,
					})
					.then((result) => {
						if (!result || !result.name) {
							return;
						}
						return frappe
							.xcall("purch.purch.doctype.task_log.task_log.get_document_change_logs", {
								reference_doctype: frm.doctype,
								reference_name: frm.doc.name,
								limit: 6,
							})
							.then((entries) =>
								render_task_log_section(frm, { name: result.name, subject: frm.doc.name }, entries)
							);
					});
			});
	}

	frappe.ui.form.on("*", {
		refresh(frm) {
			if (can_show_task_log(frm)) {
				show_task_log_dashboard(frm);
			}
		},
	});
})();
