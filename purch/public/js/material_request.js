// Copyright (c) 2026, Admin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Material Request", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status === "Stopped") {
			return;
		}

		if (frm.doc.material_request_type !== "Purchase") {
			return;
		}

		frm.add_custom_button(__("Custom Comparison"), () => {
			frappe.model.open_mapped_doc({
				method:
					"purch.purch.doctype.custom_comparison.custom_comparison.make_from_material_request",
				frm,
				run_link_triggers: true,
			});
		}, __("Create"));
	},
});
