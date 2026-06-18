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
AMOUNT_FIELDS = [f"amount_{i}" for i in range(1, MAX_SUPPLIERS + 1)]


class CustomComparison(Document):
	def validate(self):
		self.validate_suppliers()
		self.validate_material_requests()
		self.update_item_prices()
		self.update_supplier_totals()

	def validate_material_requests(self):
		material_requests = []
		for row in self.material_requests:
			if not row.material_request:
				continue
			if row.material_request in material_requests:
				frappe.throw(_("Material Request {0} is duplicated").format(row.material_request))
			material_requests.append(row.material_request)

		sync_primary_material_request(self)

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
			self.set_item_amounts(item, supplier_list)
			self.set_lowest_price(item, supplier_list)
			self.set_selected_rate(item, supplier_list)

	def set_item_amounts(self, item, supplier_list):
		qty = flt(item.qty)
		for idx, field in enumerate(AMOUNT_FIELDS):
			if idx < len(supplier_list):
				rate = flt(item.get(PRICE_FIELDS[idx]))
				item.set(field, rate * qty)
			else:
				item.set(field, 0)

	def update_supplier_totals(self):
		supplier_list = [row.supplier for row in self.suppliers if row.supplier]

		for idx, supplier_row in enumerate(self.suppliers):
			if idx < len(supplier_list):
				total = sum(
					flt(item.get(PRICE_FIELDS[idx])) * flt(item.qty) for item in self.items
				)
				supplier_row.total_amount = total
			else:
				supplier_row.total_amount = 0

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
	mr_name = item.material_request or comparison.material_request
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
		"material_request": mr_name,
		"material_request_item": item.material_request_item,
		"schedule_date": nowdate(),
	}


def get_buying_price_list(comparison, item=None):
	mr_name = None
	if item and item.material_request:
		mr_name = item.material_request
	elif comparison.material_requests:
		mr_name = comparison.material_requests[0].material_request
	elif comparison.material_request:
		mr_name = comparison.material_request

	if not mr_name:
		return None

	return frappe.db.get_value("Material Request", mr_name, "buying_price_list")


def validate_material_request_for_comparison(mr, company=None):
	if mr.docstatus != 1:
		frappe.throw(_("Material Request {0} must be submitted").format(mr.name))

	if mr.material_request_type != "Purchase":
		frappe.throw(_("Material Request {0} must be of type Purchase").format(mr.name))

	if company and mr.company != company:
		frappe.throw(
			_("Material Request {0} belongs to company {1}").format(mr.name, mr.company)
		)


def get_comparison_item_from_mr_item(mr_item, mr_name):
	return {
		"item_code": mr_item.item_code,
		"item_name": mr_item.item_name,
		"description": mr_item.description,
		"uom": mr_item.uom,
		"qty": mr_item.qty,
		"warehouse": mr_item.warehouse,
		"project": mr_item.project,
		"cost_center": mr_item.cost_center,
		"material_request": mr_name,
		"material_request_item": mr_item.name,
		"selected_supplier": None,
		"selected_rate": 0,
		**{field: 0 for field in PRICE_FIELDS + AMOUNT_FIELDS},
	}


def get_existing_mr_item_keys(comparison):
	return {
		(row.material_request, row.material_request_item)
		for row in comparison.items
		if row.material_request_item
	}


def get_linked_material_requests(comparison):
	return {
		row.material_request
		for row in comparison.material_requests
		if row.material_request
	}


def append_material_request_items(comparison, mr_name, skip_existing=True):
	mr = frappe.get_doc("Material Request", mr_name)
	validate_material_request_for_comparison(mr, comparison.company)

	existing_items = get_existing_mr_item_keys(comparison) if skip_existing else set()
	added_items = 0

	for mr_item in mr.items:
		key = (mr_name, mr_item.name)
		if skip_existing and key in existing_items:
			continue

		comparison.append("items", get_comparison_item_from_mr_item(mr_item, mr_name))
		added_items += 1

	if mr_name not in get_linked_material_requests(comparison):
		comparison.append("material_requests", {"material_request": mr_name})

	sync_primary_material_request(comparison)
	return added_items


def sync_primary_material_request(comparison):
	if comparison.material_requests:
		comparison.material_request = comparison.material_requests[0].material_request
	else:
		comparison.material_request = None


@frappe.whitelist()
def get_items_from_material_requests(material_requests, company):
	if isinstance(material_requests, str):
		material_requests = json.loads(material_requests)

	if not material_requests:
		frappe.throw(_("Please select at least one Material Request"))

	if not company:
		frappe.throw(_("Please select Company first"))

	items = []
	mr_rows = []
	seen_items = set()

	for mr_name in dict.fromkeys(material_requests):
		mr = frappe.get_doc("Material Request", mr_name)
		validate_material_request_for_comparison(mr, company)
		mr_rows.append({"material_request": mr_name})

		for mr_item in mr.items:
			key = (mr_name, mr_item.name)
			if key in seen_items:
				continue
			seen_items.add(key)
			items.append(get_comparison_item_from_mr_item(mr_item, mr_name))

	return {"items": items, "material_requests": mr_rows}


@frappe.whitelist()
def add_items_from_material_requests(comparison_name, material_requests):
	if isinstance(material_requests, str):
		material_requests = json.loads(material_requests)

	comparison = frappe.get_doc("Custom Comparison", comparison_name)

	if comparison.docstatus != 0:
		frappe.throw(_("Cannot add items to a submitted Custom Comparison"))

	if not material_requests:
		frappe.throw(_("Please select at least one Material Request"))

	added_items = 0
	for mr_name in dict.fromkeys(material_requests):
		added_items += append_material_request_items(comparison, mr_name)

	if not added_items:
		frappe.msgprint(_("Selected Material Request items are already added"))

	comparison.save()
	return comparison


@frappe.whitelist()
def make_from_material_request(source_name, target_doc=None):
	def postprocess(source, target):
		target.material_request = source.name
		target.company = source.company
		target.transaction_date = source.transaction_date or nowdate()
		target.append("material_requests", {"material_request": source.name})

		for item in target.items:
			item.material_request = source.name
			item.selected_supplier = None
			item.selected_rate = 0
			for field in PRICE_FIELDS + AMOUNT_FIELDS:
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

	po.buying_price_list = get_buying_price_list(comparison, po_items[0]["item"])

	for row in po_items:
		item = row["item"]
		po.append("items", get_po_item_dict(item, comparison, row["rate"]))

	po.set_missing_values()
	po.calculate_taxes_and_totals()
	return po


@frappe.whitelist()
def make_purchase_orders_for_selected(source_name, item_rows=None):
	comparison = frappe.get_doc("Custom Comparison", source_name)

	if comparison.docstatus != 1:
		frappe.throw(_("Custom Comparison must be submitted before creating Purchase Order"))

	if item_rows and isinstance(item_rows, str):
		item_rows = json.loads(item_rows)

	if not item_rows:
		frappe.throw(_("Please select at least one item"))

	supplier_list = get_supplier_list(comparison)
	items_by_supplier = {}

	for item in comparison.items:
		if item.name not in item_rows:
			continue

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

	if not items_by_supplier:
		frappe.throw(_("No items selected for Purchase Order"))

	created_pos = []
	for supplier, rows in items_by_supplier.items():
		po = frappe.new_doc("Purchase Order")
		po.supplier = supplier
		po.company = comparison.company
		po.transaction_date = comparison.transaction_date
		po.schedule_date = nowdate()

		po.buying_price_list = get_buying_price_list(comparison, rows[0]["item"])

		for row in rows:
			item = row["item"]
			po.append("items", get_po_item_dict(item, comparison, row["rate"]))

		po.set_missing_values()
		po.calculate_taxes_and_totals()
		po.insert()
		created_pos.append(po.name)

	return created_pos


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

		po.buying_price_list = get_buying_price_list(comparison, rows[0]["item"])

		for row in rows:
			item = row["item"]
			po.append("items", get_po_item_dict(item, comparison, row["rate"]))

		po.set_missing_values()
		po.calculate_taxes_and_totals()
		po.insert()
		created_pos.append(po.name)

	return created_pos
