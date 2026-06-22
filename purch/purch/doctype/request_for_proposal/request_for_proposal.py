# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class RequestforProposal(Document):
	def validate(self):
		self.validate_schedule_date()
		self.set_title()
		if not self.status:
			self.status = "Draft"
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def validate_schedule_date(self):
		if not self.schedule_date:
			return

		for item in self.items:
			if not item.schedule_date:
				item.schedule_date = self.schedule_date
			elif getdate(item.schedule_date) < getdate(self.transaction_date):
				frappe.throw(
					_("Required By Date cannot be before Transaction Date for row {0}").format(item.idx)
				)

	def set_title(self):
		if not self.title:
			self.title = self.name or _("Request for Proposal")

	def on_submit(self):
		self.status = "Submitted"

	def on_cancel(self):
		self.status = "Cancelled"

	def reset_default_field_value(self, fieldname, child_table, child_fieldname):
		if self.get(fieldname):
			for row in self.get(child_table) or []:
				if not row.get(child_fieldname):
					row.set(child_fieldname, self.get(fieldname))
