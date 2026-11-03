# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe
from frappe.desk import notifications


@frappe.whitelist()
@frappe.read_only()
def get_open_count(doctype: str, name: str, items=None):
	"""Extend default connection counts for purch MR / Custom Comparison / PO flow."""
	result = notifications.get_open_count(doctype, name, items)
	count = result.get("count")
	if not isinstance(count, dict):
		return result

	if doctype == "Material Request":
		_enrich_material_request_connections(count, name)
	elif doctype == "Custom Comparison":
		_enrich_custom_comparison_connections(count, name)
	elif doctype == "Purchase Order":
		_enrich_purchase_order_connections(count, name)

	return result


def _enrich_material_request_connections(count, material_request):
	po_names = _get_purchase_orders_for_material_request(material_request)
	cc_names = _get_custom_comparisons_for_material_request(material_request)

	_set_named_internal_link(count, "Purchase Order", po_names)
	_set_named_internal_link(count, "Custom Comparison", cc_names)


def _enrich_custom_comparison_connections(count, comparison_name):
	mr_names = _get_material_requests_for_custom_comparison(comparison_name)
	_set_named_internal_link(count, "Material Request", mr_names)


def _enrich_purchase_order_connections(count, purchase_order):
	doc = frappe.get_doc("Purchase Order", purchase_order)
	cc_name = doc.get("custom_comparison")
	if cc_name:
		_set_named_internal_link(count, "Custom Comparison", [cc_name])

	mr_names = sorted({row.material_request for row in doc.items if row.material_request})
	if mr_names:
		_set_named_internal_link(count, "Material Request", mr_names)


def _set_named_internal_link(count, link_doctype, names):
	names = [name for name in dict.fromkeys(names or []) if name]
	if not names:
		return

	existing = None
	for row in count.get("internal_links_found") or []:
		if row.get("doctype") == link_doctype:
			existing = row
			break

	if not existing:
		existing = {"doctype": link_doctype, "open_count": 0, "count": 0, "names": []}
		count.setdefault("internal_links_found", []).append(existing)

	existing["names"] = names
	existing["count"] = len(names)
	existing["open_count"] = _open_count_for_doctype(link_doctype, names)


def _open_count_for_doctype(doctype, names):
	open_filters = notifications.get_filters_for(doctype) or {}
	if not open_filters:
		return len(names)

	return frappe.db.count(
		doctype,
		filters={"name": ["in", names], **open_filters},
	)


def _get_purchase_orders_for_material_request(material_request):
	return frappe.db.sql(
		"""
		select distinct parent
		from `tabPurchase Order Item`
		where material_request = %s
		""",
		material_request,
		pluck=True,
	)


def _get_custom_comparisons_for_material_request(material_request):
	return frappe.db.sql(
		"""
		select distinct name from `tabCustom Comparison` where material_request = %s
		union
		select distinct parent from `tabCustom Comparison Material Request` where material_request = %s
		union
		select distinct parent from `tabCustom Comparison Item` where material_request = %s
		""",
		(material_request, material_request, material_request),
		pluck=True,
	)


def _get_material_requests_for_custom_comparison(comparison_name):
	return frappe.db.sql(
		"""
		select distinct material_request from `tabCustom Comparison Material Request`
		where parent = %s and ifnull(material_request, '') != ''
		union
		select distinct material_request from `tabCustom Comparison Item`
		where parent = %s and ifnull(material_request, '') != ''
		union
		select distinct material_request from `tabCustom Comparison`
		where name = %s and ifnull(material_request, '') != ''
		""",
		(comparison_name, comparison_name, comparison_name),
		pluck=True,
	)
