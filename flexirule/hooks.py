app_name = "flexirule"
app_title = "FlexiRule"
app_publisher = "Abdo Ruzaqi"
app_description = "a true Advanced Rule and Orchestration Engine for the Frappe Framework"
app_email = "ruzaqi@gmail.com"
app_license = "agpl-3.0"

# Apps
# ------------------

# required_apps = []
# JS/CSS includes
app_include_js = ["flexirule.bundle.js"]
# Document Events - ALL paths must be to MODULE-LEVEL functions
# NEVER use class method paths like "module.ClassName.method"
doc_events = {
	"*": {
		"before_naming": "flexirule.ruleflow.hooks.execute_rules",
		"before_insert": "flexirule.ruleflow.hooks.execute_rules",
		"before_save": "flexirule.ruleflow.hooks.execute_rules",
		"validate": "flexirule.ruleflow.hooks.execute_rules",
		"after_insert": "flexirule.ruleflow.hooks.execute_rules",
		"on_update": "flexirule.ruleflow.hooks.execute_rules",
		"before_submit": "flexirule.ruleflow.hooks.execute_rules",
		"on_submit": "flexirule.ruleflow.hooks.execute_rules",
		"on_update_after_submit": "flexirule.ruleflow.hooks.execute_rules",
		"on_change": "flexirule.ruleflow.hooks.execute_rules",
		"before_cancel": "flexirule.ruleflow.hooks.execute_rules",
		"on_cancel": "flexirule.ruleflow.hooks.execute_rules",
		"before_print": "flexirule.ruleflow.hooks.execute_rules",
		"before_rename": "flexirule.ruleflow.hooks.execute_rules",
		"after_rename": "flexirule.ruleflow.hooks.execute_rules",
		"on_trash": "flexirule.ruleflow.hooks.execute_rules",
	},
	"Rule": {
		"after_insert": "flexirule.ruleflow.hooks.clear_rule_cache",
		"on_update": "flexirule.ruleflow.hooks.clear_rule_cache",
		"on_trash": "flexirule.ruleflow.hooks.clear_rule_cache",
	},
}

doctype_js = {"Rule": "ruleflow/doctype/rule/rule.js"}

fixtures: list = [
	{"dt": "Rule", "filters": {"module": ["is", "set"]}},
	{"dt": "Rule Scheduler", "filters": {"module": ["is", "set"]}},
]

flexirule_excluded_doctypes = [
	"Error Log",
	"Activity Log",
	"Access Log",
	"Email Queue",
	"Scheduled Job Log",
	"Version",
	"Comment",
	"Communication",
	"File",
]

export_python_type_annotations = True
# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "flexirule",
# 		"logo": "/assets/flexirule/logo.png",
# 		"title": "FlexiRule",
# 		"route": "/flexirule",
# 		"has_permission": "flexirule.api.permission.has_app_permission"
# 	}
# ]

# FlexiRule Settings
# ------------------
# Allow List for Process Methods (Security)
# Only modules starting with these prefixes can be used in Process Methods

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
	"/assets/flexirule/css/design-tokens.css",
	"/assets/flexirule/css/controls.css",
	"/assets/flexirule/css/rule_builder.css"
]
# app_include_js = "/assets/flexirule/js/flexirule.js"

# include js, css files in header of web template
# web_include_css = "/assets/flexirule/css/flexirule.css"
# web_include_js = "/assets/flexirule/js/flexirule.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "flexirule/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "flexirule/public/icons.svg"

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
# 	"methods": "flexirule.utils.jinja_methods",
# 	"filters": "flexirule.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "flexirule.install.before_install"
after_install = "flexirule.install.after_install"
after_migrate = [
	"flexirule.ruleflow.core.process_sync.sync_all_processes",
]

# Uninstallation
# ------------

# before_uninstall = "flexirule.uninstall.before_uninstall"
# after_uninstall = "flexirule.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "flexirule.utils.before_app_install"
# after_app_install = "flexirule.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "flexirule.utils.before_app_uninstall"
# after_app_uninstall = "flexirule.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "flexirule.notifications.get_notification_config"

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

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": ["flexirule.ruleflow.scheduler.check_scheduled_rules"],
	"daily": ["flexirule.tasks.clear_old_logs"],
}

# Testing
# -------

before_tests = "flexirule.ruleflow.core.process_sync.sync_all_processes"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "flexirule.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "flexirule.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["flexirule.utils.before_request"]
# after_request = ["flexirule.utils.after_request"]

# Job Events
# ----------
# before_job = ["flexirule.utils.before_job"]
# after_job = ["flexirule.utils.after_job"]

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
# 	"flexirule.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
