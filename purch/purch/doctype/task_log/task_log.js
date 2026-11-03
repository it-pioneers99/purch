// Copyright (c) 2026, Admin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Task Log", {
	refresh(frm) {
		frm.set_df_property("entries", "cannot_add_rows", true);
		frm.set_df_property("entries", "cannot_delete_rows", true);

		if (frm.doc.reference_doctype && frm.doc.reference_name) {
			frm.add_custom_button(__("Open Document"), () => {
				frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name);
			});
		}

		if (!frm.doc.auto_created && frm.doc.status !== "Completed" && frm.doc.status !== "Cancelled") {
			frm.add_custom_button(__("Mark Completed"), () => {
				frappe.call({
					method: "purch.purch.doctype.task_log.task_log.mark_completed",
					args: { name: frm.doc.name },
					freeze: true,
					callback(r) {
						if (!r.exc) {
							frm.reload_doc();
						}
					},
				});
			}).addClass("btn-primary");
		}
	},

	status(frm) {
		if (frm.doc.status === "Completed") {
			frm.set_value("completed_on", frappe.datetime.now_datetime());
			frm.set_value("completed_by", frappe.session.user);
		}
	},
});
