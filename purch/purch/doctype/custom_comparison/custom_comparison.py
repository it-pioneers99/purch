# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, fmt_money, getdate, nowdate

MAX_SUPPLIERS = 10
PRICE_FIELDS = [f"price_{i}" for i in range(1, MAX_SUPPLIERS + 1)]
AMOUNT_FIELDS = [f"amount_{i}" for i in range(1, MAX_SUPPLIERS + 1)]
TOTAL_AMOUNT_FIELDS = [f"total_amount_{i}" for i in range(1, MAX_SUPPLIERS + 1)]
COMPARISON_TYPE_MR = "Material Request"
COMPARISON_TYPE_RFP = "Request For Proposal"

MR_HEADER_FIELDS = ("budget_expense_type", "request_type")
MR_ITEM_COPY_FIELDS = (
	"budget_expense_item",
	"budget_expense_detail_description",
	"phc_budget_expense_item_split_json",
	"phc_budget_expense_item_split_summary",
)
SPLIT_COPY_FIELDS = (
	"phc_budget_expense_item_split_json",
	"phc_budget_expense_item_split_summary",
)
PO_REQUEST_TYPE_FIELD = "custom_request_type"


class CustomComparison(Document):
	def before_insert(self):
		self.set_created_date()

	def validate(self):
		self.set_created_date()
		self.validate_suppliers()
		if self.is_material_request_comparison():
			self.validate_material_requests()
		elif self.is_request_for_proposal_comparison():
			self.validate_request_for_proposals()
		self.update_item_prices()
		self.update_supplier_totals()
		self.update_cost_save()

	def set_created_date(self):
		if self.created_date:
			return
		if self.creation:
			self.created_date = getdate(self.creation)
		else:
			self.created_date = nowdate()

	def is_material_request_comparison(self):
		return (self.comparison_type or COMPARISON_TYPE_MR) == COMPARISON_TYPE_MR

	def is_request_for_proposal_comparison(self):
		return self.comparison_type == COMPARISON_TYPE_RFP

	def validate_material_requests(self):
		material_requests = []
		for row in self.material_requests:
			if not row.material_request:
				continue
			if row.material_request in material_requests:
				frappe.throw(_("Material Request {0} is duplicated").format(row.material_request))
			material_requests.append(row.material_request)

		sync_primary_material_request(self)

	def validate_request_for_proposals(self):
		request_for_proposals = []
		for row in self.request_for_proposals:
			if not row.request_for_proposal:
				continue
			if row.request_for_proposal in request_for_proposals:
				frappe.throw(
					_("Request for Proposal {0} is duplicated").format(row.request_for_proposal)
				)
			request_for_proposals.append(row.request_for_proposal)

		sync_primary_request_for_proposal(self)

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
		currency = frappe.db.get_value("Company", self.company, "default_currency") if self.company else None
		for idx, field in enumerate(AMOUNT_FIELDS):
			if idx < len(supplier_list):
				price_field = PRICE_FIELDS[idx]
				rate_precision = frappe.get_precision(item.doctype, price_field, currency=currency)
				amount_precision = frappe.get_precision(item.doctype, field, currency=currency)

				rate = flt(item.get(price_field), precision=rate_precision)
				amount = flt(rate * qty, precision=amount_precision)
				item.set(field, amount)
			else:
				item.set(field, 0)

	def update_supplier_totals(self):
		supplier_list = [row.supplier for row in self.suppliers if row.supplier]
		currency = frappe.db.get_value("Company", self.company, "default_currency") if self.company else None
		total_precision = frappe.get_precision("Custom Comparison Supplier", "total_amount", currency=currency)

		for idx, supplier_row in enumerate(self.suppliers):
			if idx < len(supplier_list):
				price_field = PRICE_FIELDS[idx]
				rate_precision = frappe.get_precision("Custom Comparison Item", price_field, currency=currency)
				total = sum(
					flt(item.get(price_field), precision=rate_precision) * flt(item.qty) for item in self.items
				)
				supplier_row.total_amount = flt(total, precision=total_precision)
			else:
				supplier_row.total_amount = 0

		self.sync_supplier_total_amount_fields()

	def sync_supplier_total_amount_fields(self):
		supplier_rows = [row for row in self.suppliers if row.supplier]
		currency = frappe.db.get_value("Company", self.company, "default_currency") if self.company else None

		for idx, fieldname in enumerate(TOTAL_AMOUNT_FIELDS):
			if idx < len(supplier_rows):
				self.set(fieldname, fmt_money(flt(supplier_rows[idx].total_amount), currency=currency))
			else:
				self.set(fieldname, None)

	def update_cost_save(self):
		totals = [flt(row.total_amount) for row in self.suppliers if flt(row.total_amount) > 0]
		currency = frappe.db.get_value("Company", self.company, "default_currency") if self.company else None
		precision = frappe.get_precision(self.doctype, "cost_save", currency=currency)

		if len(totals) < 2:
			self.cost_save = 0
			return

		self.cost_save = flt(max(totals) - min(totals), precision=precision)

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

		currency = frappe.db.get_value("Company", self.company, "default_currency") if self.company else None
		selected_rate_precision = frappe.get_precision(item.doctype, "selected_rate", currency=currency)
		item.selected_rate = flt(item.get(PRICE_FIELDS[supplier_idx]), precision=selected_rate_precision)

	def on_submit(self):
		self.status = "Submitted"
		if not self.approved_date:
			self.db_set("approved_date", nowdate(), update_modified=False)

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_set("approved_date", None, update_modified=False)


def get_supplier_list(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("Custom Comparison", doc)
	return [row.supplier for row in doc.suppliers if row.supplier]


def ensure_material_request_comparison(comparison):
	if comparison.comparison_type == COMPARISON_TYPE_RFP:
		frappe.throw(_("This action is only available for Material Request comparisons"))


def ensure_request_for_proposal_comparison(comparison):
	if comparison.comparison_type != COMPARISON_TYPE_RFP:
		frappe.throw(_("This action is only available for Request For Proposal comparisons"))


def ensure_po_allowed(comparison):
	if comparison.comparison_type == COMPARISON_TYPE_RFP:
		frappe.throw(_("Purchase Orders cannot be created from Request For Proposal comparisons"))


def get_item_rate(item, supplier, supplier_list):
	if supplier not in supplier_list:
		return 0

	idx = supplier_list.index(supplier)
	return flt(item.get(PRICE_FIELDS[idx]))


def meta_has_field(doctype, fieldname):
	return fieldname in frappe.get_meta(doctype).get_fieldnames_with_value()


def copy_document_fields(source_doc, target_doc, fieldnames):
	for fieldname in fieldnames:
		if not meta_has_field(source_doc.doctype, fieldname):
			continue
		if not meta_has_field(target_doc.doctype, fieldname):
			continue
		target_doc.set(fieldname, source_doc.get(fieldname))


def get_mr_item_copied_fields(mr_item):
	from phc_projects.phc_projects.budget_expense_item_split import compact_split_json_string

	values = {}
	for fieldname in MR_ITEM_COPY_FIELDS:
		if not meta_has_field("Material Request Item", fieldname):
			continue
		value = mr_item.get(fieldname)
		if value is None or value == "":
			continue
		if fieldname == "phc_budget_expense_item_split_json":
			value = compact_split_json_string(value)
		values[fieldname] = value
	return values


def sync_comparison_header_from_mr(comparison, mr):
	for fieldname in MR_HEADER_FIELDS:
		if not meta_has_field("Material Request", fieldname):
			continue
		if not meta_has_field(comparison.doctype, fieldname):
			continue

		mr_value = mr.get(fieldname)
		if not mr_value:
			continue

		current = comparison.get(fieldname)
		if not current:
			comparison.set(fieldname, mr_value)
		elif current != mr_value:
			frappe.throw(
				_(
					"Material Request {0} has {1} = {2}, which does not match the comparison value {3}."
				).format(mr.name, frappe.bold(fieldname), mr_value, current)
			)


def set_po_header_from_comparison(po, comparison):
	if meta_has_field("Purchase Order", "budget_expense_type"):
		po.budget_expense_type = comparison.get("budget_expense_type")

	request_type = comparison.get("request_type")
	if request_type:
		if meta_has_field("Purchase Order", PO_REQUEST_TYPE_FIELD):
			po.set(PO_REQUEST_TYPE_FIELD, request_type)
		elif meta_has_field("Purchase Order", "request_type"):
			po.request_type = request_type


def get_po_item_field_values(comparison_item):
	from phc_projects.phc_projects.budget_expense_item_split import compact_split_json_string

	values = {}
	for fieldname in MR_ITEM_COPY_FIELDS:
		if not meta_has_field("Purchase Order Item", fieldname):
			continue
		value = comparison_item.get(fieldname)
		if value is None or value == "":
			continue
		if fieldname == "phc_budget_expense_item_split_json":
			value = compact_split_json_string(value)
		values[fieldname] = value

	missing = [
		fieldname
		for fieldname in MR_ITEM_COPY_FIELDS
		if fieldname not in values and meta_has_field("Purchase Order Item", fieldname)
	]
	if missing and comparison_item.material_request_item:
		mr_values = frappe.db.get_value(
			"Material Request Item",
			comparison_item.material_request_item,
			missing,
			as_dict=True,
		)
		if mr_values:
			for fieldname, value in mr_values.items():
				if not value:
					continue
				if fieldname == "phc_budget_expense_item_split_json":
					value = compact_split_json_string(value)
				values[fieldname] = value

	return values


def get_po_item_dict(item, comparison, rate):
	mr_name = item.material_request or comparison.material_request
	row = {
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
	for fieldname, value in get_po_item_field_values(item).items():
		if meta_has_field("Purchase Order Item", fieldname):
			row[fieldname] = value
	return row


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
	row = {
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
	row.update(get_mr_item_copied_fields(mr_item))
	return row


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
	sync_comparison_header_from_mr(comparison, mr)

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


def validate_request_for_proposal_for_comparison(rfp, company=None):
	if rfp.docstatus != 1:
		frappe.throw(_("Request for Proposal {0} must be submitted").format(rfp.name))

	if company and rfp.company != company:
		frappe.throw(
			_("Request for Proposal {0} belongs to company {1}").format(rfp.name, rfp.company)
		)


def get_comparison_item_from_rfp_item(rfp_item, rfp_name):
	return {
		"item_code": rfp_item.item_code,
		"item_name": rfp_item.item_name,
		"description": rfp_item.description,
		"uom": rfp_item.uom,
		"qty": rfp_item.qty,
		"warehouse": rfp_item.warehouse,
		"project": rfp_item.project,
		"cost_center": rfp_item.cost_center,
		"request_for_proposal": rfp_name,
		"request_for_proposal_item": rfp_item.name,
		"selected_supplier": None,
		"selected_rate": 0,
		**{field: 0 for field in PRICE_FIELDS + AMOUNT_FIELDS},
	}


def get_existing_rfp_item_keys(comparison):
	return {
		(row.request_for_proposal, row.request_for_proposal_item)
		for row in comparison.items
		if row.request_for_proposal_item
	}


def get_linked_request_for_proposals(comparison):
	return {
		row.request_for_proposal
		for row in comparison.request_for_proposals
		if row.request_for_proposal
	}


def append_request_for_proposal_items(comparison, rfp_name, skip_existing=True):
	rfp = frappe.get_doc("Request for Proposal", rfp_name)
	validate_request_for_proposal_for_comparison(rfp, comparison.company)

	existing_items = get_existing_rfp_item_keys(comparison) if skip_existing else set()
	added_items = 0

	for rfp_item in rfp.items:
		key = (rfp_name, rfp_item.name)
		if skip_existing and key in existing_items:
			continue

		comparison.append("items", get_comparison_item_from_rfp_item(rfp_item, rfp_name))
		added_items += 1

	if rfp_name not in get_linked_request_for_proposals(comparison):
		comparison.append("request_for_proposals", {"request_for_proposal": rfp_name})

	sync_primary_request_for_proposal(comparison)
	return added_items


def sync_primary_request_for_proposal(comparison):
	if comparison.request_for_proposals:
		comparison.request_for_proposal = comparison.request_for_proposals[0].request_for_proposal
	else:
		comparison.request_for_proposal = None


@frappe.whitelist()
def get_items_from_request_for_proposals(request_for_proposals, company):
	if isinstance(request_for_proposals, str):
		request_for_proposals = json.loads(request_for_proposals)

	if not request_for_proposals:
		frappe.throw(_("Please select at least one Request for Proposal"))

	if not company:
		frappe.throw(_("Please select Company first"))

	items = []
	rfp_rows = []
	seen_items = set()

	for rfp_name in dict.fromkeys(request_for_proposals):
		rfp = frappe.get_doc("Request for Proposal", rfp_name)
		validate_request_for_proposal_for_comparison(rfp, company)
		rfp_rows.append({"request_for_proposal": rfp_name})

		for rfp_item in rfp.items:
			key = (rfp_name, rfp_item.name)
			if key in seen_items:
				continue
			seen_items.add(key)
			items.append(get_comparison_item_from_rfp_item(rfp_item, rfp_name))

	return {"items": items, "request_for_proposals": rfp_rows}


@frappe.whitelist()
def add_items_from_request_for_proposals(comparison_name, request_for_proposals):
	if isinstance(request_for_proposals, str):
		request_for_proposals = json.loads(request_for_proposals)

	comparison = frappe.get_doc("Custom Comparison", comparison_name)
	ensure_request_for_proposal_comparison(comparison)

	if comparison.docstatus != 0:
		frappe.throw(_("Cannot add items to a submitted Custom Comparison"))

	if not request_for_proposals:
		frappe.throw(_("Please select at least one Request for Proposal"))

	added_items = 0
	for rfp_name in dict.fromkeys(request_for_proposals):
		added_items += append_request_for_proposal_items(comparison, rfp_name)

	if not added_items:
		frappe.msgprint(_("Selected Request for Proposal items are already added"))

	comparison.save()
	return comparison


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
	ensure_material_request_comparison(comparison)

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
		target.comparison_type = COMPARISON_TYPE_MR
		target.material_request = source.name
		target.company = source.company
		target.transaction_date = source.transaction_date or nowdate()
		target.append("material_requests", {"material_request": source.name})
		copy_document_fields(source, target, MR_HEADER_FIELDS)

		mr_items_by_name = {row.name: row for row in source.items}
		for item in target.items:
			item.material_request = source.name
			item.selected_supplier = None
			item.selected_rate = 0
			for field in PRICE_FIELDS + AMOUNT_FIELDS:
				item.set(field, 0)

			mr_item = mr_items_by_name.get(item.material_request_item)
			if mr_item:
				for fieldname, value in get_mr_item_copied_fields(mr_item).items():
					if meta_has_field(item.doctype, fieldname):
						item.set(fieldname, value)

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
				"field_map": [
					["name", "material_request"],
					["budget_expense_type", "budget_expense_type"],
					["request_type", "request_type"],
				],
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
					["budget_expense_item", "budget_expense_item"],
					["budget_expense_detail_description", "budget_expense_detail_description"],
					[
						"phc_budget_expense_item_split_json",
						"phc_budget_expense_item_split_json",
					],
					[
						"phc_budget_expense_item_split_summary",
						"phc_budget_expense_item_split_summary",
					],
				],
			},
		},
		target_doc,
		postprocess,
	)


@frappe.whitelist()
def make_from_request_for_proposal(source_name, target_doc=None):
	def postprocess(source, target):
		target.comparison_type = COMPARISON_TYPE_RFP
		target.request_for_proposal = source.name
		target.company = source.company
		target.transaction_date = source.transaction_date or nowdate()
		target.append("request_for_proposals", {"request_for_proposal": source.name})

		for item in target.items:
			item.request_for_proposal = source.name
			item.selected_supplier = None
			item.selected_rate = 0
			for field in PRICE_FIELDS + AMOUNT_FIELDS:
				item.set(field, 0)

	return get_mapped_doc(
		"Request for Proposal",
		source_name,
		{
			"Request for Proposal": {
				"doctype": "Custom Comparison",
				"validation": {
					"docstatus": ["=", 1],
				},
				"field_map": [["name", "request_for_proposal"]],
			},
			"Request for Proposal Item": {
				"doctype": "Custom Comparison Item",
				"field_map": [
					["name", "request_for_proposal_item"],
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
	ensure_po_allowed(comparison)

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
	po.custom_comparison = comparison.name
	set_po_header_from_comparison(po, comparison)

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
	ensure_po_allowed(comparison)

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
		po.custom_comparison = comparison.name
		set_po_header_from_comparison(po, comparison)

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
	ensure_po_allowed(comparison)

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
		po.custom_comparison = comparison.name
		set_po_header_from_comparison(po, comparison)

		po.buying_price_list = get_buying_price_list(comparison, rows[0]["item"])

		for row in rows:
			item = row["item"]
			po.append("items", get_po_item_dict(item, comparison, row["rate"]))

		po.set_missing_values()
		po.calculate_taxes_and_totals()
		po.insert()
		created_pos.append(po.name)

	return created_pos
