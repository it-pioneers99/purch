app_name = "purch"
app_title = "Purch"
app_publisher = "Admin"
app_description = "Purchase Comparison"
app_email = "admin@test.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = ["erpnext"]
required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "purch",
# 		"logo": "/assets/purch/logo.png",
# 		"title": "Purch",
# 		"route": "/purch",
# 		"has_permission": "purch.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/pioneer/css/desk_theme.css"
app_include_js = "/assets/purch/js/task_log_shim.js"
boot_session = "purch.boot.strip_removed_doctypes_from_boot"

# include js, css files in header of web template
# web_include_css = "/assets/purch/css/purch.css"
# web_include_js = "/assets/purch/js/purch.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "purch/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Custom Comparison": "public/js/custom_comparison.js",
	"Material Request": "public/js/material_request.js",
	"Purchase Order": "public/js/purchase_order.js",
}

override_doctype_dashboards = {
	"Material Request": "purch.overrides.dashboard_overrides.get_dashboard_for_material_request",
	"Purchase Order": "purch.overrides.dashboard_overrides.get_dashboard_for_purchase_order",
	"Request for Proposal": "purch.overrides.dashboard_overrides.get_dashboard_for_request_for_proposal",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "purch/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "purch.utils.jinja_methods",
# 	"filters": "purch.utils.jinja_filters"
# }

# Installation
# ------------

# after_install = "purch.install.after_install"
after_install = "purch.install.after_install"
after_migrate = "purch.install.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "purch.uninstall.before_uninstall"
# after_uninstall = "purch.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "purch.utils.before_app_install"
# after_app_install = "purch.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "purch.utils.before_app_uninstall"
# after_app_uninstall = "purch.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "purch.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Order": {
		"before_insert": "purch.document_events.set_creation_date",
		"validate": "purch.document_events.set_creation_date",
		"on_submit": "purch.document_events.set_approved_date_on_submit",
		"on_cancel": "purch.document_events.clear_approved_date_on_cancel",
	},
	"Material Request": {
		"on_submit": "purch.document_events.set_approved_date_on_submit",
		"on_cancel": "purch.document_events.clear_approved_date_on_cancel",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"purch.tasks.all"
# 	],
# 	"daily": [
# 		"purch.tasks.daily"
# 	],
# 	"hourly": [
# 		"purch.tasks.hourly"
# 	],
# 	"weekly": [
# 		"purch.tasks.weekly"
# 	],
# 	"monthly": [
# 		"purch.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "purch.install.before_tests"

# Overriding Methods
# ------------------------------

override_whitelisted_methods = {
	"frappe.desk.notifications.get_open_count": "purch.overrides.linked_documents.get_open_count",
	"purch.purch.doctype.task_log.task_log.get_document_task_logs": (
		"purch.stubs.legacy_api.get_document_task_logs"
	),
	"purch.purch.doctype.task_log.task_log.get_document_change_logs": (
		"purch.stubs.legacy_api.get_document_change_logs"
	),
	"purch.purch.doctype.task_log.task_log.ensure_task_log_for_document": (
		"purch.stubs.legacy_api.ensure_task_log_for_document"
	),
	"purch.purch.doctype.task_log.task_log.mark_completed": "purch.stubs.legacy_api.mark_completed",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "purch.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Request Events
# ----------------
# before_request = ["purch.utils.before_request"]
# after_request = ["purch.utils.after_request"]

# Job Events
# ----------
# before_job = ["purch.utils.before_job"]
# after_job = ["purch.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"purch.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

