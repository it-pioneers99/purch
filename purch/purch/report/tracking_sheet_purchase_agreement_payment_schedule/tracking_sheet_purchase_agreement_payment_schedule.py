# Copyright (c) 2026, Admin and contributors

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import flt, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Purchase Order"),
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 140,
		},
		{
			"label": _("Purchase Agreement"),
			"fieldname": "purchase_agreement",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 160,
		},
		{"label": _("PO Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": _("Approved Date"), "fieldname": "approved_date", "fieldtype": "Date", "width": 110},
		{"label": _("PO Status"), "fieldname": "po_status", "fieldtype": "Data", "width": 120},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120,
		},
		{
			"label": _("Payment Terms Template"),
			"fieldname": "payment_terms_template",
			"fieldtype": "Link",
			"options": "Payment Terms Template",
			"width": 160,
		},
		{
			"label": _("Payment Term"),
			"fieldname": "payment_term",
			"fieldtype": "Link",
			"options": "Payment Term",
			"width": 130,
		},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 200},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Invoice Portion"), "fieldname": "invoice_portion", "fieldtype": "Percent", "width": 110},
		{
			"label": _("Payment Amount"),
			"fieldname": "base_payment_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "base_paid_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Purchase Invoices"),
			"fieldname": "purchase_invoices",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Outstanding"),
			"fieldname": "base_outstanding",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{"label": _("Schedule Status"), "fieldname": "schedule_status", "fieldtype": "Data", "width": 110},
		{
			"label": _("PO Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "hidden": 1},
	]


def get_data(filters):
	company = filters.company or frappe.defaults.get_user_default("Company")
	if not company:
		frappe.throw(_("Please set Company."))

	from_date = filters.from_date or frappe.utils.add_months(today(), -3)
	to_date = filters.to_date or today()

	po = frappe.qb.DocType("Purchase Order")
	ps = frappe.qb.DocType("Payment Schedule")

	select_fields = [
		po.name.as_("purchase_order"),
		po.supplier,
		po.transaction_date,
		po.status.as_("po_status"),
		po.project,
		po.payment_terms_template,
		po.grand_total,
		po.currency,
		ps.payment_term,
		ps.description,
		ps.due_date,
		ps.invoice_portion,
		ps.base_payment_amount,
		ps.name.as_("payment_schedule_row"),
	]
	if frappe.db.has_column("Purchase Order", "purchase_agreement"):
		select_fields.insert(1, po.purchase_agreement)
	if frappe.db.has_column("Purchase Order", "approved_date"):
		select_fields.insert(4, po.approved_date)

	query = (
		frappe.qb.from_(po)
		.inner_join(ps)
		.on((ps.parent == po.name) & (ps.parenttype == "Purchase Order"))
		.select(*select_fields)
		.where((po.docstatus == 1) & (po.company == company) & (po.transaction_date[from_date:to_date]))
		.orderby(po.name, Order.asc)
		.orderby(ps.due_date, Order.asc)
		.orderby(ps.idx, Order.asc)
	)

	if filters.supplier:
		query = query.where(po.supplier == filters.supplier)
	if filters.project:
		query = query.where(po.project == filters.project)
	if filters.purchase_order:
		query = query.where(po.name == filters.purchase_order)
	if filters.from_due_date:
		query = query.where(ps.due_date >= filters.from_due_date)
	if filters.to_due_date:
		query = query.where(ps.due_date <= filters.to_due_date)
	if filters.po_status:
		query = query.where(po.status.isin(filters.po_status))

	rows = query.run(as_dict=True)
	if not frappe.db.has_column("Purchase Order", "purchase_agreement"):
		for row in rows:
			row.purchase_agreement = None
	if not frappe.db.has_column("Purchase Order", "approved_date"):
		for row in rows:
			row.approved_date = None

	po_names = list({row.purchase_order for row in rows})
	paid_by_term, invoice_pool = _get_purchase_invoice_paid_maps(po_names)
	_apply_invoice_paid_to_rows(rows, paid_by_term, invoice_pool)

	for row in rows:
		row.pop("payment_schedule_row", None)
		row.schedule_status = _schedule_status(row)

	if filters.schedule_status:
		statuses = (
			filters.schedule_status
			if isinstance(filters.schedule_status, list)
			else [filters.schedule_status]
		)
		rows = [r for r in rows if r.schedule_status in statuses]

	return rows


def _get_purchase_invoice_paid_maps(po_names):
	"""Paid amounts from submitted Purchase Invoices linked to each PO."""
	if not po_names:
		return {}, {}

	paid_by_term = {}
	invoices_by_term = {}

	schedule_rows = frappe.db.sql(
		"""
		SELECT
			pii.purchase_order,
			ps.payment_term,
			ps.due_date,
			SUM(ps.base_paid_amount) AS base_paid_amount,
			GROUP_CONCAT(DISTINCT pi.name ORDER BY pi.name SEPARATOR ', ') AS purchase_invoices
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
		INNER JOIN `tabPayment Schedule` ps
			ON ps.parent = pi.name AND ps.parenttype = 'Purchase Invoice'
		WHERE pi.docstatus = 1
			AND IFNULL(pii.purchase_order, '') != ''
			AND pii.purchase_order IN %(po_names)s
		GROUP BY pii.purchase_order, ps.payment_term, ps.due_date
		""",
		{"po_names": po_names},
		as_dict=True,
	)

	for row in schedule_rows:
		key = (row.purchase_order, row.payment_term, row.due_date)
		paid_by_term[key] = flt(row.base_paid_amount)
		invoices_by_term[key] = row.purchase_invoices or ""

	pi_rows = frappe.db.sql(
		"""
		SELECT DISTINCT
			pii.purchase_order,
			pi.name AS purchase_invoice,
			pi.base_paid_amount
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
		WHERE pi.docstatus = 1
			AND IFNULL(pii.purchase_order, '') != ''
			AND pii.purchase_order IN %(po_names)s
		""",
		{"po_names": po_names},
		as_dict=True,
	)

	invoice_paid_by_po = {}
	invoice_names_by_po = {}
	for row in pi_rows:
		po = row.purchase_order
		invoice_paid_by_po[po] = invoice_paid_by_po.get(po, 0) + flt(row.base_paid_amount)
		invoice_names_by_po.setdefault(po, set()).add(row.purchase_invoice)

	scheduled_paid_by_po = {}
	for (po, _term, _due), amount in paid_by_term.items():
		scheduled_paid_by_po[po] = scheduled_paid_by_po.get(po, 0) + flt(amount)

	# Remaining paid on PO invoices not tied to a PI payment schedule row (FIFO on PO terms)
	invoice_pool = {}
	for po, total_paid in invoice_paid_by_po.items():
		unallocated = max(total_paid - scheduled_paid_by_po.get(po, 0), 0)
		if unallocated:
			invoice_pool[po] = {
				"amount": unallocated,
				"invoices": ", ".join(sorted(invoice_names_by_po.get(po, []))),
			}

	paid_by_term["_invoices"] = invoices_by_term
	return paid_by_term, invoice_pool


def _apply_invoice_paid_to_rows(rows, paid_by_term, invoice_pool):
	invoices_by_term = paid_by_term.pop("_invoices", {})
	rows_by_po = {}
	for row in rows:
		rows_by_po.setdefault(row.purchase_order, []).append(row)

	for po, po_rows in rows_by_po.items():
		pool = invoice_pool.get(po, {"amount": 0, "invoices": ""})
		for row in po_rows:
			key_exact = (row.purchase_order, row.payment_term, row.due_date)
			key_term = (row.purchase_order, row.payment_term)

			paid = flt(paid_by_term.get(key_exact))
			invoices = invoices_by_term.get(key_exact, "")

			if not paid and key_term in paid_by_term:
				paid = flt(paid_by_term.get(key_term))
				invoices = invoices_by_term.get(key_term, invoices)

			# FIFO: leftover paid on PO invoices (no PI schedule match) oldest due date first
			if pool["amount"] > 0:
				need = max(flt(row.base_payment_amount) - paid, 0)
				if need > 0:
					take = min(need, pool["amount"])
					paid += take
					pool["amount"] -= take
					invoices = ", ".join(filter(None, [invoices, pool["invoices"]]))

			row.base_paid_amount = paid
			row.purchase_invoices = invoices
			row.base_outstanding = max(flt(row.base_payment_amount) - paid, 0)


def _schedule_status(row):
	payment_amount = flt(row.base_payment_amount)
	paid_amount = flt(row.base_paid_amount)
	outstanding = flt(row.base_outstanding)

	if payment_amount > 0 and outstanding <= 0.0001 and paid_amount >= payment_amount - 0.0001:
		return _("Completed")
	if paid_amount > 0 and outstanding > 0.0001:
		return _("Partly Paid")
	if row.due_date and getdate(row.due_date) < getdate(today()) and outstanding > 0.0001:
		return _("Overdue")
	return _("Unpaid")
