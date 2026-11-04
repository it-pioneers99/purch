// Copyright (c) 2026, Admin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		setup_custom_comparison_connection(frm);
	},
});

function setup_custom_comparison_connection(frm) {
	if (frm.dashboard && !frm.is_new()) {
		frm.dashboard.add_transactions({
			label: __("Reference"),
			items: ["Custom Comparison", "Material Request"],
		});
	}

	if (!frm.doc.custom_comparison) {
		return;
	}

	frm.add_custom_button(__("Custom Comparison"), () => {
		frappe.set_route("Form", "Custom Comparison", frm.doc.custom_comparison);
	}, __("View"));
}
