// Copyright (c) 2026, Admin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Request for Proposal", {
	setup(frm) {
		frm.set_query("set_warehouse", () => ({
			filters: { company: frm.doc.company || "" },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status === "Stopped") {
			return;
		}

		frm.add_custom_button(__("Custom Comparison"), () => {
			frappe.model.open_mapped_doc({
				method:
					"purch.purch.doctype.custom_comparison.custom_comparison.make_from_request_for_proposal",
				frm,
				run_link_triggers: true,
			});
		}, __("Create"));
	},

	company(frm) {
		frm.trigger("set_warehouse");
	},

	set_warehouse(frm) {
		if (frm.doc.set_warehouse) {
			(frm.doc.items || []).forEach((row) => {
				if (!row.warehouse) {
					frappe.model.set_value(row.doctype, row.name, "warehouse", frm.doc.set_warehouse);
				}
			});
		}
	},

	schedule_date(frm) {
		if (frm.doc.schedule_date) {
			(frm.doc.items || []).forEach((row) => {
				if (!row.schedule_date) {
					frappe.model.set_value(row.doctype, row.name, "schedule_date", frm.doc.schedule_date);
				}
			});
		}
	},
});

frappe.ui.form.on("Request for Proposal Item", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) {
			return;
		}

		frappe.db.get_value("Item", row.item_code, ["item_name", "stock_uom", "description"]).then((r) => {
			if (!r.message) {
				return;
			}
			frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
			frappe.model.set_value(cdt, cdn, "stock_uom", r.message.stock_uom);
			frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
			frappe.model.set_value(cdt, cdn, "description", r.message.description);
		});
	},

	qty(frm, cdt, cdn) {
		calculate_amount(cdt, cdn);
	},

	rate(frm, cdt, cdn) {
		calculate_amount(cdt, cdn);
	},
});

function calculate_amount(cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
}
