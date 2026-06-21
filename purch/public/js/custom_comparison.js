// Copyright (c) 2026, Admin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Custom Comparison", {
	setup(frm) {
		frm.set_query("selected_supplier", "items", () => {
			const suppliers = (frm.doc.suppliers || []).map((row) => row.supplier).filter(Boolean);
			return { filters: { name: ["in", suppliers.length ? suppliers : [" "]] } };
		});

		frm.set_query("material_request", "material_requests", () => ({
			filters: {
				docstatus: 1,
				material_request_type: "Purchase",
				company: frm.doc.company || "",
			},
		}));
	},

	refresh(frm) {
		setup_custom_buttons(frm);
		if (frm.fields_dict.items?.grid) {
			update_supplier_price_columns(frm);
			setup_items_grid_selection(frm);
			(frm.doc.items || []).forEach((row) => {
				set_row_amounts(frm, row.doctype, row.name, row);
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

	items_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		set_row_amounts(frm, cdt, cdn, row);
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

frappe.ui.form.on("Custom Comparison Material Request", {
	material_request(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.material_request || frm.doc.docstatus !== 0) {
			return;
		}
		fetch_material_request_items(frm, [row.material_request]);
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

function get_item_amount(row, supplier_idx) {
	return flt(row[PRICE_FIELDS[supplier_idx]]) * flt(row.qty);
}

function get_supplier_total(frm, supplier_idx) {
	return (frm.doc.items || []).reduce(
		(sum, item) => sum + get_item_amount(item, supplier_idx),
		0
	);
}

function set_row_amounts(frm, cdt, cdn, row) {
	const supplier_count = get_supplier_list(frm).length;
	AMOUNT_FIELDS.forEach((field, idx) => {
		const amount = idx < supplier_count ? get_item_amount(row, idx) : 0;
		frappe.model.set_value(cdt, cdn, field, amount);
	});
}

function update_supplier_totals(frm) {
	const supplier_list = get_supplier_list(frm);
	(frm.doc.suppliers || []).forEach((supplier_row, idx) => {
		const total = supplier_list[idx] ? get_supplier_total(frm, idx) : 0;
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

	set_row_amounts(frm, cdt, cdn, row);

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

function setup_items_grid_selection(frm) {
	const grid = frm.fields_dict.items?.grid;
	if (!grid) return;

	if (frm.doc.docstatus !== 1) {
		return;
	}

	grid.only_sortable();
	grid.df.cannot_add_rows = true;
	grid.wrapper.find(".grid-footer").toggle(true);

	grid.wrapper
		.off("change.custom_comparison_selection")
		.on("change.custom_comparison_selection", () => {
			enable_items_grid_bulk_select(grid);
		});

	enable_items_grid_bulk_select(grid);
}

function enable_items_grid_bulk_select(grid) {
	grid.toggle_checkboxes(true);
}

function get_selected_items(frm) {
	const grid = frm.fields_dict.items?.grid;
	if (frm.doc.docstatus === 1 && grid) {
		return grid.get_selected_children() || [];
	}

	return (frm.doc.items || []).filter((row) => cint(row.select));
}

function clear_item_selection(frm) {
	const grid = frm.fields_dict.items?.grid;
	if (grid?.grid_rows?.length) {
		grid.grid_rows.forEach((grid_row) => {
			if (grid_row.doc?.__checked) {
				grid_row.select(false);
				grid_row.refresh_check();
			}
		});
		return;
	}

	(frm.doc.items || []).forEach((row) => {
		if (cint(row.select)) {
			frappe.model.set_value(row.doctype, row.name, "select", 0);
		}
	});
}

function setup_custom_buttons(frm) {
	if (frm.doc.docstatus !== 1) {
		if (frm.doc.company) {
			frm.add_custom_button(__("Material Requests"), () => {
				open_material_request_selector(frm);
			}, __("Get Items From"));
		}

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

	const items_grid = frm.fields_dict.items?.grid;

	frm.add_custom_button(__("Create PO (All Items)"), () => {
		frappe.call({
			method: "purch.purch.doctype.custom_comparison.custom_comparison.make_purchase_orders_for_all",
			args: { source_name: frm.doc.name },
			freeze: true,
			callback(r) {
				handle_po_creation_response(r);
			},
		});
	}, __("Create"));

	frm.add_custom_button(__("Create PO (Selected Items)"), () => {
		const selected = get_selected_items(frm);
		if (!selected.length) {
			frappe.msgprint(
				__("Please select at least one item row using the checkboxes in the Items table")
			);
			return;
		}

		frappe.call({
			method:
				"purch.purch.doctype.custom_comparison.custom_comparison.make_purchase_orders_for_selected",
			args: {
				source_name: frm.doc.name,
				item_rows: selected.map((row) => row.name),
			
			},
			freeze: true,
			callback(r) {
				if (!r.exc && r.message?.length) {
					clear_item_selection(frm);
				}
				handle_po_creation_response(r);
			},
		});
	}, __("Create"));
}

function handle_po_creation_response(r) {
	if (r.exc || !r.message?.length) return;

	if (r.message.length === 1) {
		frappe.set_route("Form", "Purchase Order", r.message[0]);
		return;
	}

	frappe.msgprint(
		__("Created {0} Purchase Orders: {1}", [r.message.length, r.message.join(", ")])
	);
}

function open_material_request_selector(frm) {
	if (!frm.doc.company) {
		frappe.msgprint(__("Please select Company first"));
		return;
	}

	new frappe.ui.form.MultiSelectDialog({
		doctype: "Material Request",
		target: frm,
		setters: {
			company: frm.doc.company,
		},
		read_only_setters: ["company"],
		get_query() {
			return {
				filters: {
					docstatus: 1,
					material_request_type: "Purchase",
					company: frm.doc.company,
				},
			};
		},
		action(selections) {
			if (!selections?.length) {
				frappe.msgprint(__("Please select at least one Material Request"));
				return;
			}
			fetch_material_request_items(frm, selections);
		},
	});
}

function fetch_material_request_items(frm, material_requests) {
	if (frm.doc.name && !frm.is_new()) {
		frappe.call({
			method:
				"purch.purch.doctype.custom_comparison.custom_comparison.add_items_from_material_requests",
			args: {
				comparison_name: frm.doc.name,
				material_requests,
			},
			freeze: true,
			callback(r) {
				if (!r.exc && r.message) {
					frappe.model.sync(r.message);
					frm.refresh();
					frappe.show_alert({
						message: __("Material Request items added"),
						indicator: "green",
					});
				}
			},
		});
		return;
	}

	frappe.call({
		method:
			"purch.purch.doctype.custom_comparison.custom_comparison.get_items_from_material_requests",
		args: {
			material_requests,
			company: frm.doc.company,
		},
		freeze: true,
		callback(r) {
			if (r.exc || !r.message) return;
			merge_material_request_data(frm, r.message);
			frm.refresh_field("material_requests");
			frm.refresh_field("items");
			frappe.show_alert({
				message: __("Material Request items added"),
				indicator: "green",
			});
		},
	});
}

function merge_material_request_data(frm, data) {
	const existing_items = new Set(
		(frm.doc.items || [])
			.filter((row) => row.material_request_item)
			.map((row) => `${row.material_request}::${row.material_request_item}`)
	);
	const existing_mrs = new Set(
		(frm.doc.material_requests || []).map((row) => row.material_request).filter(Boolean)
	);

	(data.material_requests || []).forEach((row) => {
		if (existing_mrs.has(row.material_request)) {
			return;
		}
		const child = frappe.model.add_child(
			frm.doc,
			"Custom Comparison Material Request",
			"material_requests"
		);
		child.material_request = row.material_request;
		existing_mrs.add(row.material_request);
	});

	if (!frm.doc.material_request && frm.doc.material_requests?.length) {
		frm.doc.material_request = frm.doc.material_requests[0].material_request;
	}

	(data.items || []).forEach((row) => {
		const key = `${row.material_request}::${row.material_request_item}`;
		if (existing_items.has(key)) {
			return;
		}
		const child = frappe.model.add_child(frm.doc, "Custom Comparison Item", "items");
		Object.assign(child, row);
		existing_items.add(key);
	});
}

