// Copyright (c) 2026, Admin and contributors

frappe.query_reports["Tracking Sheet Purchase Agreement Payment Schedule"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("PO From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("PO To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{ fieldname: "from_due_date", label: __("Due Date From"), fieldtype: "Date" },
		{ fieldname: "to_due_date", label: __("Due Date To"), fieldtype: "Date" },
		{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier" },
		{ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project" },
		{
			fieldname: "purchase_order",
			label: __("Purchase Order"),
			fieldtype: "Link",
			options: "Purchase Order",
		},
		{
			fieldname: "po_status",
			label: __("PO Status"),
			fieldtype: "MultiSelectList",
			get_data: () =>
				[
					"To Receive and Bill",
					"To Bill",
					"To Receive",
					"Completed",
					"Closed",
					"On Hold",
				].map((value) => ({ value, label: __(value) })),
		},
		{
			fieldname: "schedule_status",
			label: __("Schedule Status"),
			fieldtype: "MultiSelectList",
			get_data: () =>
				["Unpaid", "Partly Paid", "Overdue", "Completed"].map((value) => ({
					value,
					label: __(value),
				})),
		},
	],
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "schedule_status") {
			const formatted = default_formatter(value, row, column, data);
			if (value === "Completed") {
				return `<span style="color:green;">${formatted}</span>`;
			}
			if (value === "Overdue") {
				return `<span style="color:red;">${formatted}</span>`;
			}
		}
		return default_formatter(value, row, column, data);
	},
};
