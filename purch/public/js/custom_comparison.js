// Copyright (c) 2026, Admin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Custom Comparison", {
	setup(frm) {
		frm.set_query("selected_supplier", "items", () => {
			const suppliers = (frm.doc.suppliers || []).map((row) => row.supplier).filter(Boolean);
			return { filters: { name: ["in", suppliers.length ? suppliers : [" "]] } };
		});
	},

	refresh(frm) {
		setup_custom_buttons(frm);
		if (frm.fields_dict.items?.grid) {
			update_supplier_price_columns(frm);
			(frm.doc.items || []).forEach((row) => {
				set_row_amounts(row.doctype, row.name, row);
			});
			update_supplier_totals(frm);
		}
	},

	suppliers_add(frm) {
		update_supplier_price_columns(frm, true);
		update_supplier_totals(frm);
	},

	suppliers_remove(frm) {
		clear_removed_supplier_prices(frm);
		update_supplier_price_columns(frm, true);
		update_supplier_totals(frm);
	},

	items_remove(frm) {
		update_supplier_totals(frm);
	},
});

frappe.ui.form.on("Custom Comparison Supplier", {
	supplier(frm) {
		update_supplier_price_columns(frm, true);
		update_supplier_totals(frm);
	},
});

frappe.ui.form.on("Custom Comparison Item", {
	selected_supplier(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const supplier_list = get_supplier_list(frm);
		const idx = supplier_list.indexOf(row.selected_supplier);
		if (idx >= 0) {
			frappe.model.set_value(cdt, cdn, "selected_rate", flt(row[PRICE_FIELDS[idx]]));
		}
	},

	price_1(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_2(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_3(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_4(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_5(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_6(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_7(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_8(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_9(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
	price_10(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},

	qty(frm, cdt, cdn) {
		update_row_price_summary(frm, cdt, cdn);
	},
});

const MAX_SUPPLIERS = 10;
const PRICE_FIELDS = Array.from({ length: MAX_SUPPLIERS }, (_, i) => `price_${i + 1}`);
const AMOUNT_FIELDS = Array.from({ length: MAX_SUPPLIERS }, (_, i) => `amount_${i + 1}`);

function get_supplier_list(frm) {
	return (frm.doc.suppliers || []).map((row) => row.supplier).filter(Boolean);
}

function get_supplier_name(frm, supplier) {
	return (
		(frm.doc.suppliers || []).find((row) => row.supplier === supplier)?.supplier_name || supplier
	);
}

function update_supplier_price_columns(frm, refresh_grid) {
	const items_grid = frm.fields_dict.items?.grid;
	if (!items_grid) return;

	const supplier_list = get_supplier_list(frm);
	const visible_count = Math.max(supplier_list.length, 1);

	PRICE_FIELDS.forEach((field, idx) => {
		const supplier = supplier_list[idx];
		const should_show = idx < visible_count;
		let label = __("Price Supplier {0}", [idx + 1]);

		if (supplier) {
			label = __("Price {0}", [get_supplier_name(frm, supplier)]);
		}

		items_grid.update_docfield_property(field, "label", label);
		items_grid.update_docfield_property(field, "hidden", should_show ? 0 : 1);
	});

	AMOUNT_FIELDS.forEach((field, idx) => {
		const supplier = supplier_list[idx];
		const should_show = idx < visible_count;
		let label = __("Total Supplier {0}", [idx + 1]);

		if (supplier) {
			label = __("Total {0}", [get_supplier_name(frm, supplier)]);
		}

		items_grid.update_docfield_property(field, "label", label);
		items_grid.update_docfield_property(field, "hidden", should_show ? 0 : 1);
	});

	if (refresh_grid) {
		items_grid.refresh();
	}

	setTimeout(() => highlight_lowest_prices(frm), 300);
}

function highlight_lowest_prices(frm) {
	const supplier_list = get_supplier_list(frm);
	const grid = frm.fields_dict.items?.grid;
	if (!grid?.grid_rows?.length) return;

	grid.grid_rows.forEach((grid_row) => {
		const row = grid_row.doc;
		if (!row) return;

		let lowest_rate = null;
		let lowest_idx = null;

		supplier_list.forEach((supplier, idx) => {
			const rate = flt(row[PRICE_FIELDS[idx]]);
			if (rate <= 0) return;
			if (lowest_rate === null || rate < lowest_rate) {
				lowest_rate = rate;
				lowest_idx = idx;
			}
		});

		PRICE_FIELDS.forEach((field, idx) => {
			const column = grid_row.columns?.[field];
			const $cell = column?.$wrapper || column;
			if (!$cell || !$cell.css) return;
			$cell.css("background-color", idx === lowest_idx && lowest_rate ? "#d4edda" : "");
		});
	});
}

function clear_removed_supplier_prices(frm) {
	const supplier_list = get_supplier_list(frm);
	(frm.doc.items || []).forEach((row) => {
		PRICE_FIELDS.forEach((field, idx) => {
			if (!supplier_list[idx]) {
				frappe.model.set_value(row.doctype, row.name, field, 0);
			}
		});
		AMOUNT_FIELDS.forEach((field, idx) => {
			if (!supplier_list[idx]) {
				frappe.model.set_value(row.doctype, row.name, field, 0);
			}
		});
		update_row_price_summary(frm, row.doctype, row.name);
	});
}

function set_row_amounts(cdt, cdn, row) {
	const qty = flt(row.qty);
	AMOUNT_FIELDS.forEach((field, idx) => {
		const amount = flt(row[PRICE_FIELDS[idx]]) * qty;
		frappe.model.set_value(cdt, cdn, field, amount);
	});
}

function update_supplier_totals(frm) {
	const supplier_list = get_supplier_list(frm);
	(frm.doc.suppliers || []).forEach((supplier_row, idx) => {
		if (!supplier_list[idx]) {
			frappe.model.set_value(
				supplier_row.doctype,
				supplier_row.name,
				"total_amount",
				0
			);
			return;
		}

		let total = 0;
		(frm.doc.items || []).forEach((item) => {
			total += flt(item[AMOUNT_FIELDS[idx]]);
		});

		frappe.model.set_value(
			supplier_row.doctype,
			supplier_row.name,
			"total_amount",
			total
		);
	});

	frm.refresh_field("suppliers");
}

function update_row_price_summary(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const supplier_list = get_supplier_list(frm);

	set_row_amounts(cdt, cdn, row);

	let lowest_rate = null;
	let lowest_supplier = null;

	supplier_list.forEach((supplier, idx) => {
		const rate = flt(row[PRICE_FIELDS[idx]]);
		if (rate <= 0) return;
		if (lowest_rate === null || rate < lowest_rate) {
			lowest_rate = rate;
			lowest_supplier = supplier;
		}
	});

	frappe.model.set_value(cdt, cdn, "lowest_rate", lowest_rate || 0);
	frappe.model.set_value(cdt, cdn, "lowest_supplier", lowest_supplier);

	if (row.selected_supplier) {
		const idx = supplier_list.indexOf(row.selected_supplier);
		if (idx >= 0) {
			frappe.model.set_value(cdt, cdn, "selected_rate", flt(row[PRICE_FIELDS[idx]]));
		}
	}

	update_supplier_totals(frm);
	highlight_lowest_prices(frm);
}

function setup_custom_buttons(frm) {
	if (frm.doc.docstatus !== 1) {
		if (frm.doc.items?.length && get_supplier_list(frm).length) {
			frm.add_custom_button(__("Select Lowest Price (All Items)"), () => {
				const supplier_list = get_supplier_list(frm);
				(frm.doc.items || []).forEach((row) => {
					let lowest_rate = null;
					let lowest_supplier = null;
					supplier_list.forEach((supplier, idx) => {
						const rate = flt(row[PRICE_FIELDS[idx]]);
						if (rate <= 0) return;
						if (lowest_rate === null || rate < lowest_rate) {
							lowest_rate = rate;
							lowest_supplier = supplier;
						}
					});
					if (lowest_supplier) {
						frappe.model.set_value(
							row.doctype,
							row.name,
							"selected_supplier",
							lowest_supplier
						);
						frappe.model.set_value(row.doctype, row.name, "selected_rate", lowest_rate);
					}
				});
				frm.refresh_field("items");
			});
		}
		return;
	}

	frm.add_custom_button(__("Create PO (All Items)"), () => {
		frappe.call({
			method: "purch.purch.doctype.custom_comparison.custom_comparison.make_purchase_orders_for_all",
			args: { source_name: frm.doc.name },
			freeze: true,
			callback(r) {
				if (!r.exc && r.message?.length) {
					if (r.message.length === 1) {
						frappe.set_route("Form", "Purchase Order", r.message[0]);
					} else {
						frappe.msgprint(
							__("Created {0} Purchase Orders: {1}", [
								r.message.length,
								r.message.join(", "),
							])
						);
					}
				}
			},
		});
	}, __("Create"));

	const items_grid = frm.fields_dict.items?.grid;
	if (items_grid) {
		items_grid.add_custom_button(__("Create PO (Selected Items)"), () => {
			const selected = items_grid.get_selected_children();
			if (!selected.length) {
				frappe.msgprint(__("Please select at least one item row"));
				return;
			}
			create_purchase_order(frm, null, selected.map((row) => row.name));
		});
	}
}

function create_purchase_order(frm, supplier, item_rows) {
	frappe.call({
		method: "purch.purch.doctype.custom_comparison.custom_comparison.make_purchase_order",
		args: {
			source_name: frm.doc.name,
			supplier,
			item_rows,
		},
		freeze: true,
		callback(r) {
			if (!r.exc && r.message) {
				frappe.model.sync(r.message);
				frappe.set_route("Form", r.message.doctype, r.message.name);
			}
		},
	});
}
