# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate

MAX_SUPPLIERS = 10
PRICE_FIELDS = [f"price_{i}" for i in range(1, MAX_SUPPLIERS + 1)]


class CustomComparison(Document):
	def validate(self):
		self.validate_suppliers()
		self.update_item_prices()

	def validate_suppliers(self):
		if len(self.suppliers) > MAX_SUPPLIERS:
			frappe.throw(_("Maximum {0} suppliers allowed").format(MAX_SUPPLIERS))

		suppliers = []
		for row in self.suppliers:
			if row.supplier in suppliers:
				frappe.throw(_("Supplier {0} is duplicated").format(row.supplier))
			suppliers.append(row.supplier)

	def update_item_prices(self):
		supplier_list = [row.supplier for row in self.suppliers if row.supplier]

		for item in self.items:
			self.set_lowest_price(item, supplier_list)
			self.set_selected_rate(item, supplier_list)

	def set_lowest_price(self, item, supplier_list):
		lowest_rate = None
		lowest_supplier = None

		for idx, supplier in enumerate(supplier_list):
			rate = flt(item.get(PRICE_FIELDS[idx]))
			if rate <= 0:
				continue
			if lowest_rate is None or rate < lowest_rate:
				lowest_rate = rate
				lowest_supplier = supplier

		item.lowest_rate = lowest_rate
		item.lowest_supplier = lowest_supplier

	def set_selected_rate(self, item, supplier_list):
		if not item.selected_supplier:
			return

		try:
			supplier_idx = supplier_list.index(item.selected_supplier)
		except ValueError:
			item.selected_rate = 0
			return

		item.selected_rate = flt(item.get(PRICE_FIELDS[supplier_idx]))

	def on_submit(self):
		self.status = "Submitted"

	def on_cancel(self):
		self.status = "Cancelled"


def get_supplier_list(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("Custom Comparison", doc)
	return [row.supplier for row in doc.suppliers if row.supplier]


def get_item_rate(item, supplier, supplier_list):
	if supplier not in supplier_list:
		return 0

	idx = supplier_list.index(supplier)
	return flt(item.get(PRICE_FIELDS[idx]))


def get_po_item_dict(item, comparison, rate):
	return {
		"item_code": item.item_code,
		"item_name": item.item_name,
		"description": item.description,
		"uom": item.uom,
		"stock_uom": item.uom,
		"qty": item.qty,
		"rate": rate,
		"warehouse": item.warehouse,
		"project": item.project,
		"cost_center": item.cost_center,
		"material_request": comparison.material_request,
		"material_request_item": item.material_request_item,
		"schedule_date": nowdate(),
	}


@frappe.whitelist()
def make_from_material_request(source_name, target_doc=None):
	def postprocess(source, target):
		target.material_request = source.name
		target.company = source.company
		target.transaction_date = source.transaction_date or nowdate()

		for item in target.items:
			item.selected_supplier = None
			item.selected_rate = 0
			for field in PRICE_FIELDS:
				item.set(field, 0)

	return get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Custom Comparison",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["=", "Purchase"],
				},
				"field_map": [["name", "material_request"]],
			},
			"Material Request Item": {
				"doctype": "Custom Comparison Item",
				"field_map": [
					["name", "material_request_item"],
					["item_code", "item_code"],
					["item_name", "item_name"],
					["description", "description"],
					["uom", "uom"],
					["qty", "qty"],
					["warehouse", "warehouse"],
					["project", "project"],
					["cost_center", "cost_center"],
				],
			},
		},
		target_doc,
		postprocess,
	)


@frappe.whitelist()
def make_purchase_order(source_name, supplier=None, item_rows=None):
	comparison = frappe.get_doc("Custom Comparison", source_name)

	if comparison.docstatus != 1:
		frappe.throw(_("Custom Comparison must be submitted before creating Purchase Order"))

	supplier_list = get_supplier_list(comparison)
	if not supplier_list:
		frappe.throw(_("Please add at least one supplier"))

	if item_rows and isinstance(item_rows, str):
		item_rows = json.loads(item_rows)

	selected_items = []
	for item in comparison.items:
		if item_rows and item.name not in item_rows:
			continue

		chosen_supplier = supplier or item.selected_supplier or item.lowest_supplier
		if not chosen_supplier:
			frappe.throw(
				_("Please select a supplier for item {0}").format(item.item_code)
			)

		rate = get_item_rate(item, chosen_supplier, supplier_list)
		if rate <= 0:
			frappe.throw(
				_("Please enter a price for supplier {0} on item {1}").format(
					chosen_supplier, item.item_code
				)
			)

		selected_items.append(
			{
				"item": item,
				"supplier": chosen_supplier,
				"rate": rate,
			}
		)

	if not selected_items:
		frappe.throw(_("No items selected for Purchase Order"))

	if not supplier:
		suppliers_in_selection = {row["supplier"] for row in selected_items}
		if len(suppliers_in_selection) > 1:
			frappe.throw(
				_("Selected items belong to multiple suppliers. Use 'Create PO (All Items)' or select one supplier.")
			)
		supplier = selected_items[0]["supplier"]

	po_items = [row for row in selected_items if row["supplier"] == supplier]
	if not po_items:
		frappe.throw(_("No items found for supplier {0}").format(supplier))

	po = frappe.new_doc("Purchase Order")
	po.supplier = supplier
	po.company = comparison.company
	po.transaction_date = comparison.transaction_date
	po.schedule_date = nowdate()

	if comparison.material_request:
		mr = frappe.get_doc("Material Request", comparison.material_request)
		po.buying_price_list = mr.buying_price_list

	for row in po_items:
		item = row["item"]
		po.append("items", get_po_item_dict(item, comparison, row["rate"]))

	po.set_missing_values()
	po.calculate_taxes_and_totals()
	return po


@frappe.whitelist()
def make_purchase_orders_for_all(source_name):
	comparison = frappe.get_doc("Custom Comparison", source_name)

	if comparison.docstatus != 1:
		frappe.throw(_("Custom Comparison must be submitted before creating Purchase Order"))

	supplier_list = get_supplier_list(comparison)
	items_by_supplier = {}

	for item in comparison.items:
		supplier = item.selected_supplier or item.lowest_supplier
		if not supplier:
			frappe.throw(_("Please select a supplier for item {0}").format(item.item_code))

		rate = get_item_rate(item, supplier, supplier_list)
		if rate <= 0:
			frappe.throw(
				_("Please enter a price for supplier {0} on item {1}").format(
					supplier, item.item_code
				)
			)

		items_by_supplier.setdefault(supplier, []).append({"item": item, "rate": rate})

	created_pos = []
	for supplier, rows in items_by_supplier.items():
		po = frappe.new_doc("Purchase Order")
		po.supplier = supplier
		po.company = comparison.company
		po.transaction_date = comparison.transaction_date
		po.schedule_date = nowdate()

		if comparison.material_request:
			mr = frappe.get_doc("Material Request", comparison.material_request)
			po.buying_price_list = mr.buying_price_list

		for row in rows:
			item = row["item"]
			po.append("items", get_po_item_dict(item, comparison, row["rate"]))

		po.set_missing_values()
		po.calculate_taxes_and_totals()
		po.insert()
		created_pos.append(po.name)

	return created_pos
