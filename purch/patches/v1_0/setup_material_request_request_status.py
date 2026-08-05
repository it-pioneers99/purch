import frappe

from purch.custom_fields import setup_material_request_request_status


def execute():
	setup_material_request_request_status()
