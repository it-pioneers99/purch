# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_dashboard_for_material_request(data):
	data = frappe._dict(data)

	for group in data.get("transactions", []):
		if _(group.get("label")) == _("Reference"):
			items = group.get("items", [])
			if "Custom Comparison" not in items:
				items.append("Custom Comparison")

	return data


def get_dashboard_for_purchase_order(data):
	data = frappe._dict(data)

	internal_links = data.get("internal_links") or {}
	internal_links["Custom Comparison"] = "custom_comparison"
	data.internal_links = internal_links

	for group in data.get("transactions", []):
		if _(group.get("label")) == _("Reference"):
			items = group.get("items", [])
			if "Custom Comparison" not in items:
				items.append("Custom Comparison")

	return data


def get_dashboard_for_request_for_proposal(data):
	data = frappe._dict(data)

	for group in data.get("transactions", []):
		if _(group.get("label")) == _("Reference"):
			items = group.get("items", [])
			if "Custom Comparison" not in items:
				items.append("Custom Comparison")

	return data
