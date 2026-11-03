# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def _append_transaction_item(data, doctype, anchor_items=None):
	"""Add a doctype to the same dashboard group as known anchor items (language-safe)."""
	anchor_items = anchor_items or ("Purchase Order", "Request for Quotation", "Supplier Quotation")

	for group in data.get("transactions", []):
		items = group.get("items", [])
		if any(item in items for item in anchor_items):
			if doctype not in items:
				items.append(doctype)
			return

	for group in data.get("transactions", []):
		items = group.get("items", [])
		if doctype not in items:
			items.append(doctype)
			return


def get_dashboard_for_material_request(data):
	data = frappe._dict(data)
	_append_transaction_item(data, "Custom Comparison")
	return data


def get_dashboard_for_purchase_order(data):
	data = frappe._dict(data)

	internal_links = data.get("internal_links") or {}
	internal_links["Custom Comparison"] = "custom_comparison"
	data.internal_links = internal_links

	_append_transaction_item(
		data,
		"Custom Comparison",
		anchor_items=("Purchase Receipt", "Purchase Invoice", "Sales Order", "Supplier Quotation"),
	)

	return data


def get_dashboard_for_request_for_proposal(data):
	data = frappe._dict(data)

	for group in data.get("transactions", []):
		if _(group.get("label")) == _("Reference"):
			items = group.get("items", [])
			if "Custom Comparison" not in items:
				items.append("Custom Comparison")

	return data
