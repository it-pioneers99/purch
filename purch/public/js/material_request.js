// Copyright (c) 2026, Admin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Material Request", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.set_df_property("request_status", "read_only", 0);
		}

		setup_purch_connections_dashboard(frm);

		if (frm.doc.docstatus !== 1 || frm.doc.status === "Stopped") {
			return;
		}

		if (frm.doc.material_request_type !== "Purchase") {
			return;
		}

		frm.add_custom_button(__("Create Comparison"), () => {
			frappe.model.open_mapped_doc({
				method:
					"purch.purch.doctype.custom_comparison.custom_comparison.make_from_material_request",
				frm,
				run_link_triggers: true,
			});
		}, __("Create"));
	},
});

function setup_purch_connections_dashboard(frm) {
	if (frm.is_new() || !frm.dashboard) {
		return;
	}

	frm.dashboard.add_transactions({
		label: __("Reference"),
		items: ["Custom Comparison", "Purchase Order"],
	});
}
