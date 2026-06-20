# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Unified Backend/Frontend Contract for FlexiRule Action Types

This module defines the contract for action types that is shared between:
- Backend validation (Rule.validate)
- Frontend rendering (rule_builder/store.js)
"""

from __future__ import annotations

import json
from typing import Any

# Action Type Contract
# Each action type defines:
# - required_fields: Fields that must be set for this action type
# - has_next_true: Whether next_step_if_true is valid
# - has_next_false: Whether next_step_if_false is valid
# - terminal: Whether this action ends the flow
# - validation: Additional validation rules

ACTION_TYPE_CONTRACT: dict[str, dict[str, Any]] = {
	"Entry Action": {
		"required_fields": [],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-play", "color": "#22c55e"},
		"field_labels": {},
		"node_type": "start",
		"category": "Control Flow",
		"configurable": False,
	},
	"Condition": {
		"required_fields": ["config"],
		"has_next_true": True,
		"has_next_false": True,
		"terminal": False,
		"css": {"icon": "fa fa-code-fork", "color": "#3b82f6"},
		"validation": {"frontend": "validate_condition"},
		"field_labels": {
			"compiled_expression": "Compiled Expression (Python)",
			"config": "Condition Builder Config",
		},
		"node_type": "condition",
		"category": "Control Flow",
		"configurable": True,
		"config_component": "ConditionStep",
	},
	"Process": {
		"required_fields": ["process_name", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-cog", "color": "#8b5cf6"},
		"dynamic_fields": True,
		"field_labels": {
			"operation": "Process Operation",
			"mutation_mode": "Result Handling",
			"return_type": "Result Type",
		},
		"allowed_mutations": [
			"Set Context Variable",
			"Update Context Variable",
			"Append to Context Variable",
			"Set Doc Field",
			"Update Doc Field",
			"Batch Database Set",
		],
		"allowed_return_types": [
			"Yes / No",
			"Single Record",
			"List of Values",
			"List of Records",
			"Full Document",
		],
		"show_return_type": True,
		"require_return_type": False,
		"node_type": "process",
		"category": "Processes",
		"configurable": True,
		"config_component": "ProcessConfig",
	},
	"Loop": {
		"required_fields": ["config", "return_variable"],  # config must have iterator
		"has_next_true": True,  # Loop body
		"has_next_false": True,  # Loop exit
		"terminal": False,
		"css": {"icon": "fa fa-refresh", "color": "#f59e0b"},
		"field_labels": {
			"return_variable": "Item Alias",
		},
		"show_return_variable": True,
		"require_return_variable": True,
		"node_type": "loop",
		"category": "Control Flow",
		"configurable": True,
		"config_component": "LoopConfig",
	},
	"Stop": {
		"required_fields": ["operation"],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
		"css": {"icon": "fa fa-stop", "color": "#ef4444"},
		"operation_label": "Terminal Mode",
		"operation_options": ["Success", "Error"],
		"mandatory_fields": {
			"Error": ["value_template"],
		},
		"field_labels": {"operation": "Terminal Mode"},
		"node_type": "stop",
		"category": "Control Flow",
		"configurable": True,
		"config_component": "StopConfig",
	},
	"Switch": {
		"required_fields": ["config"],  # config must have cases
		"has_next_true": False,  # Uses cases instead
		"has_next_false": True,  # Default case
		"terminal": False,
		"css": {"icon": "fa fa-random", "color": "#06b6d4"},
		"node_type": "switch",
		"category": "Control Flow",
		"configurable": True,
		"config_component": "SwitchConfig",
	},
	"Wait": {
		"required_fields": [],  # config.duration optional
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-clock-o", "color": "#64748b"},
		"field_labels": {"operation": "Wait Mode"},
		"node_type": "wait",
		"category": "Control Flow",
		"configurable": True,
		"config_component": "WaitConfig",
	},
	"Sub-Rule": {
		"required_fields": ["rule"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-cube", "color": "#ec4899"},
		"field_labels": {
			"rule": "Sub-Rule Name",
			"skip_conditions": "Skip Compatibility Check",
			"return_type": "Sub-Rule Result Type",
		},
		"allowed_mutations": [
			"Set Context Variable",
			"Update Context Variable",
			"Append to Context Variable",
		],
		"allowed_return_types": [
			"Single Record",
			"List of Records",
		],
		"default_return_type": "Single Record",
		"show_return_type": True,
		"require_return_type": False,
		"node_type": "sub-rule",
		"category": "Control Flow",
		"configurable": True,
		"config_component": "SubRuleConfig",
	},
	"Assignment": {
		"required_fields": ["config"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-list-ol", "color": "#14b8a6"},
		"field_labels": {
			"config": "Assignments",
		},
		"node_type": "assignment",
		"category": "Data Actions",
		"configurable": True,
		"config_component": "AssignmentConfig",
	},
	"Notify": {
		"required_fields": ["value_template", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-bell", "color": "#0ea5e9"},
		"operation_label": "Notification Type",
		"operation_options": ["Toast", "System", "Email", "System Notification", "Provider"],
		"operation_policies": {
			"Email": {
				"required_config_keys": ["subject", "recipients"],
			},
			"System Notification": {
				"required_config_keys": ["subject"],
			},
			"Provider": {
				"required_config_keys": ["provider", "recipient"],
			},
		},
		"field_labels": {"operation": "Notification Type"},
		"node_type": "notify",
		"category": "Notifications",
		"configurable": True,
		"config_component": "NotifyConfig",
	},
	"Raise Error": {
		"required_fields": ["value_template"],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
		"css": {"icon": "fa fa-exclamation-triangle", "color": "#dc2626"},
		"field_labels": {
			"config": "Error Details (JSON)",
		},
		"node_type": "raise-error",
		"category": "Control Flow",
		"configurable": True,
		"config_component": "RaiseErrorConfig",
	},
	"Query Records": {
		"required_fields": ["reference_doctype", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-search", "color": "#0891b2"},
		"operation_label": "Query Mode",
		"operation_options": [
			"Query List",
			"Query Doc",
			"Exist Record",
			"Query Report",
			"Count",
			"Sum",
			"Average",
			"Min",
			"Max",
			"Group By",
		],
		"allowed_mutations": [
			"Set Context Variable",
			"Append to Context Variable",
			"Update Context Variable",
		],
		"allowed_return_types": [
			"Yes / No",
			"Single Record",
			"List of Values",
			"List of Records",
		],
		"default_return_type": "List of Records",
		"show_return_type": True,
		"require_return_type": False,
		"mandatory_fields": {
			"Exist Record": ["reference_doctype"],
		},
		"operation_policies": {
			"Query List": {
				"allowed_return_types": ["List of Records"],
				"default_return_type": "List of Records",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Rows Output Type"},
			},
			"Query Doc": {
				"allowed_return_types": ["Single Record", "Full Document"],
				"default_return_type": "Single Record",
				"show_return_type": True,
				"require_return_type": True,
				"field_labels": {"return_type": "Record Output Type"},
			},
			"Exist Record": {
				"allowed_return_types": ["Yes / No"],
				"default_return_type": "Yes / No",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Boolean Output Type"},
			},
			"Query Report": {
				"allowed_return_types": ["List of Records"],
				"default_return_type": "List of Records",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Report Output Type"},
			},
			"Count": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Sum": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Average": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Min": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Max": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Group By": {
				"allowed_return_types": ["List of Records"],
				"default_return_type": "List of Records",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Grouped Output Type"},
			},
		},
		"field_labels": {
			"operation": "Query Mode",
			"reference_doctype": "Target DocType",
			"reference_docname": "Target Record",
			"mutation_mode": "Result Handling",
			"return_type": "Result Type",
		},
		"node_type": "query",
		"category": "Data Actions",
		"configurable": True,
		"config_component": "QueryRecordsConfig",
	},
	"Document Action": {
		"required_fields": ["reference_doctype", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-file-text", "color": "#059669"},
		"operation_label": "Document Mode",
		"operation_options": ["Create New", "Update Existing", "Delete Record", "Create ToDo", "Add Comment"],
		"allowed_mutations": [
			"Set Doc Field",
			"Set Context Variable",
		],
		"allowed_return_types": [
			"Single Record",
			"Full Document",
			"Yes / No",
		],
		"default_return_type": "Single Record",
		"show_return_type": True,
		"require_return_type": False,
		"operation_policies": {
			"Create New": {
				"allowed_return_types": ["Single Record", "Full Document"],
				"default_return_type": "Single Record",
				"allowed_mutations": ["Set Context Variable", "Update Context Variable"],
				"show_return_type": True,
				"require_return_type": True,
				"field_labels": {"return_type": "Created Document Output"},
			},
			"Update Existing": {
				"allowed_return_types": ["Single Record", "Full Document"],
				"default_return_type": "Single Record",
				"allowed_mutations": ["Set Context Variable", "Update Context Variable", "Set Doc Field"],
				"show_return_type": True,
				"require_return_type": True,
				"field_labels": {"return_type": "Updated Document Output"},
			},
			"Delete Record": {
				"allowed_return_types": ["Yes / No"],
				"default_return_type": "Yes / No",
				"allowed_mutations": ["Set Context Variable"],
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Deletion Result Type"},
			},
			"Create ToDo": {
				"allowed_return_types": ["Single Record"],
				"default_return_type": "Single Record",
				"allowed_mutations": ["Set Context Variable", "Update Context Variable"],
				"show_return_type": False,
				"require_return_type": False,
				"required_config_keys": ["assigned_to", "description"],
				"field_labels": {"return_type": "ToDo Output Type"},
			},
			"Add Comment": {
				"allowed_return_types": ["Single Record"],
				"default_return_type": "Single Record",
				"allowed_mutations": ["Set Context Variable", "Update Context Variable"],
				"show_return_type": False,
				"require_return_type": False,
				"required_config_keys": ["comment_text"],
				"field_labels": {"return_type": "Comment Output Type"},
			},
		},
		"field_labels": {
			"operation": "Document Mode",
			"reference_doctype": "Target DocType",
			"reference_docname": "Target Record",
			"mutation_mode": "Result Handling",
			"return_type": "Result Type",
		},
		"node_type": "documentaction",
		"category": "Data Actions",
		"configurable": True,
		"config_component": "DocumentActionConfig",
	},
}

# Operation Contracts
# Each operation defines field overrides for Rule/Rule Action DocTypes and validation scripts
#
# Field Override Properties:
# - Standard Frappe properties: reqd, options, default, description, link_filters, etc.
# - Dynamic visibility: depends_on (already supported), hidden
# - Dynamic requirements: mandatory_depends_on
# - Dynamic editability: read_only_depends_on
#
# Expressions use eval: syntax and have access to:
# - doc: The current action document
# - parent: The parent rule document (e.g., parent.is_active, parent.execution_mode)
# - frappe: Frappe utilities (e.g., frappe.user.has_role())
#
# Examples:
# - "mandatory_depends_on": "eval:doc.parent.is_active===1"  # Required when rule is active
# - "hidden": "eval:doc.parent.execution_mode!=='Asynchronous'"  # Hide for sync rules
# - "read_only_depends_on": "eval:!frappe.user.has_role('System Manager')"  # Read-only for non-admins
#
OPERATION_CONTRACTS: dict[str, dict[str, Any]] = {
	# Entry Action operations
	"Entry Action": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Entry Action"},
			{"fieldname": "description", "description": "Entry point for rule execution flow"},
		],
		"Validation": {},
	},
	# Condition operations
	"Condition": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Condition"},
			{"fieldname": "config", "reqd": 1},
			{"fieldname": "next_step_if_false", "mandatory_depends_on": "eval:doc.parent.is_active===1"},
			{"fieldname": "description", "description": "Evaluates a condition to branch execution"},
		],
		"Validation": {"frontend": "validate_condition"},
	},
	# Stop operations
	"Success": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Stop"},
			{"fieldname": "operation", "default": "Success"},
			{"fieldname": "description", "description": "Terminates rule execution successfully"},
		],
		"Validation": {},
	},
	"Error": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Stop"},
			{"fieldname": "operation", "default": "Error"},
			{"fieldname": "value_template", "reqd": 1, "description": "⚠️ Error message that will be raised"},
			{"fieldname": "description", "description": "Terminates rule execution with an error"},
		],
		"Validation": {"backend": "validate_stop_error"},
	},
	# Raise Error operations
	"Raise Error": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Raise Error"},
			{"fieldname": "value_template", "reqd": 1, "description": "⚠️ Error message that will be raised"},
			{"fieldname": "description", "description": "Raises an exception to abort current operation"},
		],
		"Validation": {"backend": "validate_raise_error"},
	},
	# Wait operations
	"Wait": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Wait"},
			{"fieldname": "description", "description": "Pauses execution for a specified duration"},
		],
		"Validation": {},
	},
	# Sub-Rule operations
	"Sub-Rule": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Sub-Rule"},
			{
				"fieldname": "rule",
				"reqd": 1,
				"options": "Rule",
				"link_filters": "[['Rule','trigger_type','=','Callable Event'],['Rule','exposed_as_subrule','=',1],['Rule','is_active','=',1]]",
			},
			{
				"fieldname": "skip_conditions",
				"default": 1,
				"description": "⚠️ Bypasses sub-rule's trigger conditions",
			},
			{
				"fieldname": "skip_permissions",
				"read_only_depends_on": "eval:!frappe.user.has_role('System Manager')",
				"description": "⚠️ Requires audit reason when enabled",
			},
			{
				"fieldname": "permission_audit_reason",
				"mandatory_depends_on": "skip_permissions",
				"hidden": "eval:!doc.skip_permissions",
			},
			{"fieldname": "description", "description": "Executes another rule as a subroutine"},
		],
		"Validation": {"backend": "validate_sub_rule"},
	},
	"Assignment": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Assignment"},
			{"fieldname": "config", "reqd": 1, "description": "Array of assignments (JSON)"},
			{
				"fieldname": "description",
				"description": "Updates document fields or context variables in batch",
			},
		],
		"Validation": {"backend": "validate_assignment"},
	},
	# Notify operations
	"Toast": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Notify"},
			{"fieldname": "operation", "default": "Toast"},
			{"fieldname": "value_template", "reqd": 1},
			{"fieldname": "description", "description": "Shows a temporary notification to the user"},
		],
		"Validation": {},
	},
	"System": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Notify"},
			{"fieldname": "operation", "default": "System"},
			{"fieldname": "value_template", "reqd": 1},
			{"fieldname": "description", "description": "Sends a system notification"},
		],
		"Validation": {},
	},
	"Email": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Notify"},
			{"fieldname": "operation", "default": "Email"},
			{"fieldname": "value_template", "reqd": 1},
			{"fieldname": "description", "description": "Sends an email notification"},
		],
		"Validation": {"backend": "validate_email_notification"},
	},
	"System Notification": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Notify"},
			{"fieldname": "operation", "default": "System Notification"},
			{"fieldname": "value_template", "reqd": 1},
			{"fieldname": "description", "description": "Creates a system notification record"},
		],
		"Validation": {},
	},
	"Provider": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Notify"},
			{"fieldname": "operation", "default": "Provider"},
			{"fieldname": "value_template", "reqd": 1},
			{"fieldname": "description", "description": "Sends notification via external provider"},
		],
		"Validation": {"backend": "validate_provider_notification"},
	},
	# Query Records operations
	"Query List": {
		"Rule": [
			{
				"fieldname": "trigger_event",
				"options": [
					"Before Save",
					"After Insert",
					"After Save",
					"Validate",
					"On Submit",
					"On Change",
				],
			},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Query List"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{
				"fieldname": "config",
				"depends_on": "eval:doc.reference_doctype",
				"reqd": 1,
				"description": "Query configuration (filters, sorting)",
			},
			{
				"fieldname": "mutation_mode",
				"options": ["Set Context Variable", "Append to Context Variable", "Update Context Variable"],
				"reqd": 1,
			},
			{"fieldname": "return_type", "default": "List of Records", "read_only": 1},
			{
				"fieldname": "timeout",
				"hidden": "eval:doc.parent.execution_mode!=='Asynchronous'",
				"description": "Only available for async rules",
			},
			{"fieldname": "description", "description": "Queries multiple records from a DocType"},
		],
		"Validation": {"backend": "validate_query_list"},
	},
	"Query Doc": {
		"Rule": [
			{
				"fieldname": "trigger_event",
				"options": [
					"Before Save",
					"After Insert",
					"After Save",
					"Validate",
					"On Submit",
					"On Change",
				],
			},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Query Doc"},
			{
				"fieldname": "reference_doctype",
				"reqd": 0,
				"link_filters": "[['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{
				"fieldname": "mutation_mode",
				"options": ["Set Context Variable", "Update Context Variable"],
				"reqd": 1,
			},
			{"fieldname": "return_type", "options": ["Single Record", "Full Document"], "reqd": 1},
			{"fieldname": "description", "description": "Queries a single record using filters"},
		],
		"Validation": {"backend": "validate_query_doc"},
	},
	"Exist Record": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["Validate", "Before Save"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Exist Record"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "Yes / No", "read_only": 1},
			{"fieldname": "description", "description": "Checks if records exist matching criteria"},
		],
		"Validation": {"backend": "validate_exist_record"},
	},
	# Query Records operations (continued)
	"Query Report": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["After Save", "On Submit", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Query Report"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "List of Records", "read_only": 1},
			{
				"fieldname": "description",
				"description": "Queries records using a custom report configuration",
			},
		],
		"Validation": {"backend": "validate_query_report"},
	},
	"Count": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["Validate", "Before Save", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Count"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "List of Values", "read_only": 1},
			{"fieldname": "description", "description": "Counts records matching criteria"},
		],
		"Validation": {"backend": "validate_count_records"},
	},
	"Sum": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["Validate", "Before Save", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Sum"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "List of Values", "read_only": 1},
			{"fieldname": "description", "description": "Calculates sum of a numeric field"},
		],
		"Validation": {"backend": "validate_aggregate_query"},
	},
	"Average": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["Validate", "Before Save", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Average"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "List of Values", "read_only": 1},
			{"fieldname": "description", "description": "Calculates average of a numeric field"},
		],
		"Validation": {"backend": "validate_aggregate_query"},
	},
	"Min": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["Validate", "Before Save", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Min"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "List of Values", "read_only": 1},
			{"fieldname": "description", "description": "Finds minimum value of a field"},
		],
		"Validation": {"backend": "validate_aggregate_query"},
	},
	"Max": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["Validate", "Before Save", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Max"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "List of Values", "read_only": 1},
			{"fieldname": "description", "description": "Finds maximum value of a field"},
		],
		"Validation": {"backend": "validate_aggregate_query"},
	},
	"Group By": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["After Save", "On Submit", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": "Group By"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "config", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "List of Records", "read_only": 1},
			{"fieldname": "description", "description": "Groups records by specified fields"},
		],
		"Validation": {"backend": "validate_group_by_query"},
	},
	# Document Action operations
	"Create New": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["Before Insert", "Validate", "Before Save"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
			{
				"fieldname": "debug_mode",
				"mandatory_depends_on": "eval:doc.trigger_type==='DocType Event'",
				"description": "Enable detailed logging for document events",
			},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Document Action"},
			{"fieldname": "operation", "default": "Create New"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{
				"fieldname": "config",
				"depends_on": "eval:doc.reference_doctype",
				"reqd": 1,
				"description": "⚠️ Document data to create",
			},
			{
				"fieldname": "mutation_mode",
				"options": ["Set Context Variable", "Update Context Variable"],
				"reqd": 1,
			},
			{"fieldname": "return_type", "options": ["Single Record", "Full Document"], "reqd": 1},
			{
				"fieldname": "skip_permissions",
				"hidden": "eval:!frappe.user.has_role('System Manager')",
				"read_only_depends_on": "eval:!frappe.user.has_role('System Manager')",
			},
			{
				"fieldname": "permission_audit_reason",
				"mandatory_depends_on": "skip_permissions",
				"hidden": "eval:!doc.skip_permissions",
			},
			{"fieldname": "description", "description": "⚠️ Creates a new document record"},
		],
		"Validation": {"backend": "validate_create_document"},
	},
	"Update Existing": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Document Action"},
			{"fieldname": "operation", "default": "Update Existing"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "reference_docname", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{
				"fieldname": "config",
				"depends_on": "eval:doc.reference_doctype",
				"reqd": 1,
				"description": "⚠️ Fields to update",
			},
			{
				"fieldname": "mutation_mode",
				"options": ["Set Context Variable", "Update Context Variable", "Set Doc Field"],
				"reqd": 1,
			},
			{"fieldname": "return_type", "options": ["Single Record", "Full Document"], "reqd": 1},
			{"fieldname": "description", "description": "⚠️ Updates an existing document record"},
		],
		"Validation": {"backend": "validate_update_document"},
	},
	"Delete Record": {
		"Rule": [],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Document Action"},
			{"fieldname": "operation", "default": "Delete Record"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "reference_docname", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{"fieldname": "return_type", "default": "Yes / No", "read_only": 1},
			{"fieldname": "description", "description": "⚠️ Permanently deletes a document record"},
		],
		"Validation": {"backend": "validate_delete_document"},
	},
	"Create ToDo": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["After Save", "On Submit", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Document Action"},
			{"fieldname": "operation", "default": "Create ToDo"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{
				"fieldname": "config",
				"depends_on": "eval:doc.reference_doctype",
				"reqd": 1,
				"description": "⚠️ ToDo details (description, assigned_to, etc.)",
			},
			{
				"fieldname": "mutation_mode",
				"options": ["Set Context Variable", "Update Context Variable"],
				"reqd": 1,
			},
			{"fieldname": "return_type", "default": "Single Record", "read_only": 1},
			{"fieldname": "description", "description": "⚠️ Creates a ToDo task for users"},
		],
		"Validation": {"backend": "validate_create_todo"},
	},
	"Add Comment": {
		"Rule": [
			{"fieldname": "trigger_event", "options": ["After Save", "On Submit", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
		"Rule Action": [
			{"fieldname": "action_type", "default": "Document Action"},
			{"fieldname": "operation", "default": "Add Comment"},
			{
				"fieldname": "reference_doctype",
				"reqd": 1,
				"link_filters": "[['DocType','issingle','=',0],['DocType','istable','=',0]]",
			},
			{"fieldname": "reference_docname", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
			{
				"fieldname": "config",
				"depends_on": "eval:doc.reference_doctype",
				"reqd": 1,
				"description": "⚠️ Comment content and settings",
			},
			{
				"fieldname": "mutation_mode",
				"options": ["Set Context Variable", "Update Context Variable"],
				"reqd": 1,
			},
			{"fieldname": "return_type", "default": "Single Record", "read_only": 1},
			{"fieldname": "description", "description": "⚠️ Adds a comment to the document"},
		],
		"Validation": {"backend": "validate_add_comment"},
	},
}


def _parse_json_object(value: Any) -> dict[str, Any]:
	if isinstance(value, dict):
		return value
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
			return parsed if isinstance(parsed, dict) else {}
		except Exception:
			return {}
	return {}


def get_process_operation_overrides(process_operation: dict | None = None) -> dict[str, Any]:
	"""Parse optional operation-level action overrides from Process metadata."""
	if not isinstance(process_operation, dict):
		return {}
	overrides = _parse_json_object(process_operation.get("action_overrides"))
	if not overrides:
		return {}

	policy = overrides.get("policy")
	fields = overrides.get("fields")
	return {
		"policy": policy if isinstance(policy, dict) else {},
		"fields": fields if isinstance(fields, dict) else {},
	}


def get_operation_contract(operation: str, process_operation: dict | None = None) -> dict:
	"""Get contract for a known operation."""
	if operation in OPERATION_CONTRACTS:
		return OPERATION_CONTRACTS[operation].copy()

	# Fallback to action type based contract
	action_type = None
	for at, contract in ACTION_TYPE_CONTRACT.items():
		if operation in (contract.get("operation_options") or []):
			action_type = at
			break
	if not action_type and operation in ACTION_TYPE_CONTRACT:
		action_type = operation

	if action_type:
		# Generate basic contract from action type
		base_contract = get_contract(action_type)
		return {
			"Rule": [],
			"Rule Action": [
				{"fieldname": "action_type", "default": action_type},
				{"fieldname": "operation", "default": operation if operation != action_type else None},
				{
					"fieldname": "description",
					"description": base_contract.get("description", f"Executes {operation}"),
				},
			]
			+ [{"fieldname": f, "reqd": 1} for f in base_contract.get("required_fields", [])],
			"Validation": base_contract.get("validation", {}),
		}

	return {
		"Rule": [],
		"Rule Action": [{"fieldname": "description", "description": f"Unknown operation: {operation}"}],
		"Validation": {},
	}


def get_operation_field_overrides(
	operation: str, doctype: str, process_operation: dict | None = None
) -> list:
	"""Get field overrides for a specific operation and doctype."""
	contract = get_operation_contract(operation, process_operation)
	overrides = list(contract.get(doctype, []))

	# Process operations can contribute generic field-level overrides through metadata.
	if doctype == "Rule Action" and isinstance(process_operation, dict):
		process_overrides = get_process_operation_overrides(process_operation)
		for fieldname, field_config in (process_overrides.get("fields") or {}).items():
			if not fieldname or not isinstance(field_config, dict):
				continue
			overrides.append({"fieldname": fieldname, **field_config})

	return overrides


def apply_field_overrides(base_fields: list, overrides: list) -> list:
	"""Apply field overrides to base field definitions.

	Field overrides can include:
	- Standard Frappe field properties (reqd, options, default, etc.)
	- Dynamic properties: hidden, mandatory_depends_on, read_only_depends_on
	- Custom properties: description, link_filters, etc.

	These overrides are applied on top of base DocType field definitions
	to customize behavior per operation.
	"""
	field_map = {f["fieldname"]: f for f in base_fields}

	for override in overrides:
		fieldname = override["fieldname"]
		if fieldname in field_map:
			# Merge override into existing field, preserving base properties
			# but allowing overrides to take precedence
			existing = field_map[fieldname]
			merged = existing.copy()
			merged.update(override)
			field_map[fieldname] = merged
		else:
			# Add new field from override
			field_map[fieldname] = override.copy()

	return list(field_map.values())


ACTION_TYPES_WITH_REFERENCE_CONTEXT = {"Query Records", "Document Action", "Process", "Assignment"}
ACTION_TYPES_WITH_RETURN_SCHEMA = {"Process", "Query Records", "Document Action"}
CONFIG_MODAL_TYPES = {
	"Process",
	"Condition",
	"Assignment",
	"Stop",
	"Raise Error",
	"Notify",
	"Wait",
	"Sub-Rule",
	"Query Records",
	"Document Action",
	"Loop",
}

RELEASE_DISABLED_ACTION_TYPES: set[str] = set()
RETURN_TYPE_OPTIONS = [
	"Yes / No",
	"Single Record",
	"List of Values",
	"List of Records",
	"Full Document",
]
MUTATION_MODE_OPTIONS = [
	"Set Doc Field",
	"Update Doc Field",
	"Set Context Variable",
	"Update Context Variable",
	"Append to Context Variable",
	"Batch Database Set",
]

# Trigger Type Contract
# Defines which fields are required, optional, or hidden for each trigger_type.
TRIGGER_TYPE_CONTRACT = {
	"DocType Event": {
		"required_fields": ["document_type", "trigger_event"],
		"optional_fields": ["trigger_condition", "compiled_expression"],
		"hidden_fields": [],
	},
	"Scheduler Event": {
		"required_fields": [],
		"optional_fields": ["document_type"],
		"hidden_fields": ["trigger_event", "trigger_condition", "compiled_expression"],
	},
	"Callable Event": {
		"required_fields": [],
		"optional_fields": ["document_type", "trigger_condition", "compiled_expression"],
		"hidden_fields": ["trigger_event"],
	},
}


def get_contract(action_type: str) -> dict:
	"""Get contract for an action type, with defaults for unknown types"""
	action_type = normalize_action_type(action_type)
	return ACTION_TYPE_CONTRACT.get(
		action_type,
		{
			"required_fields": [],
			"has_next_true": True,
			"has_next_false": False,
			"terminal": False,
		},
	)


def is_terminal_action(action_type: str) -> bool:
	"""Check if action type terminates the flow"""
	return get_contract(action_type).get("terminal", False)


def get_required_fields(action_type: str) -> list:
	"""Get required fields for an action type"""
	return get_contract(action_type).get("required_fields", [])


def is_release_disabled_action(action_type: str) -> bool:
	"""Check if an action type is intentionally disabled for the current release."""
	action_type = normalize_action_type(action_type)
	return action_type in RELEASE_DISABLED_ACTION_TYPES


def normalize_action_type(action_type: str | None) -> str:
	"""Normalize machine/case variants to canonical action type keys."""
	if not action_type:
		return ""

	raw = str(action_type).strip()
	if raw in ACTION_TYPE_CONTRACT:
		return raw

	normalized = " ".join(raw.replace("_", " ").replace("-", " ").lower().split())
	for canonical in ACTION_TYPE_CONTRACT:
		if canonical.lower() == normalized:
			return canonical

	compact = normalized.replace(" ", "")
	for canonical in ACTION_TYPE_CONTRACT:
		if canonical.lower().replace(" ", "") == compact:
			return canonical

	return raw


def get_trigger_type_contract(trigger_type: str) -> dict:
	"""Get contract for a trigger type."""
	return TRIGGER_TYPE_CONTRACT.get(
		trigger_type,
		{
			"required_fields": [],
			"optional_fields": [],
			"hidden_fields": [],
		},
	)


def get_contract_dto() -> dict:
	"""Export a frontend-safe contract payload from backend single source of truth."""
	return {
		"action_type_contract": ACTION_TYPE_CONTRACT,
		"operation_contract": OPERATION_CONTRACTS,
		"trigger_type_contract": TRIGGER_TYPE_CONTRACT,
		"runtime_field_aliases": {
			"Sub-Rule": {
				"sub_rule_name": "rule",
			},
		},
		"release_disabled_action_types": sorted(RELEASE_DISABLED_ACTION_TYPES),
		"return_type_options": RETURN_TYPE_OPTIONS,
		"mutation_mode_options": MUTATION_MODE_OPTIONS,
		"action_types_with_reference_context": sorted(ACTION_TYPES_WITH_REFERENCE_CONTEXT),
		"action_types_with_return_schema": sorted(ACTION_TYPES_WITH_RETURN_SCHEMA),
		"config_modal_types": sorted(CONFIG_MODAL_TYPES),
	}


def infer_process_operation_policy(process_operation: dict | None) -> dict:
	"""Infer runtime/UI policy from Process Operation metadata."""
	policy: dict = {}
	if not isinstance(process_operation, dict):
		return policy

	process_overrides = get_process_operation_overrides(process_operation)

	writes_to = (process_operation.get("writes_to") or "None").strip()
	if writes_to == "Document":
		policy["allowed_mutations"] = [
			"Set Doc Field",
			"Update Doc Field",
			"Set Context Variable",
			"Update Context Variable",
		]
	elif writes_to == "Database":
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
			"Batch Database Set",
		]
	elif writes_to == "Context":
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
			"Append to Context Variable",
		]
	else:
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
		]

	output_schema = process_operation.get("output_schema")
	allowed_return_types = []
	default_return_type = None
	field_labels = {}
	show_return_type = True
	require_return_type = False
	require_return_variable = False

	if output_schema:
		try:
			schema = json.loads(output_schema) if isinstance(output_schema, str) else output_schema
			if isinstance(schema, dict):
				schema_type = schema.get("type")
				if schema_type == "array":
					allowed_return_types = ["List of Records", "List of Values"]
					default_return_type = "List of Records"
					field_labels["return_type"] = "Collection Output Type"
					show_return_type = True
					require_return_type = False
				elif schema_type == "boolean":
					allowed_return_types = ["Yes / No"]
					default_return_type = "Yes / No"
					field_labels["return_type"] = "Boolean Output Type"
					show_return_type = False
					require_return_type = False
				elif schema_type == "object":
					allowed_return_types = ["Single Record", "Full Document"]
					default_return_type = "Single Record"
					field_labels["return_type"] = "Record Output Type"
					show_return_type = True
					require_return_type = False
				elif schema_type in ("string", "number", "integer"):
					allowed_return_types = ["List of Values"]
					default_return_type = "List of Values"
					field_labels["return_type"] = "Value Output Type"
					show_return_type = False
					require_return_type = False
		except Exception:
			pass

	if writes_to == "Context":
		require_return_variable = True

	writes_vars = process_operation.get("writes_vars")
	try:
		parsed_writes_vars = json.loads(writes_vars) if isinstance(writes_vars, str) else writes_vars
		if isinstance(parsed_writes_vars, list) and parsed_writes_vars:
			require_return_variable = True
	except Exception:
		pass

	if output_schema:
		require_return_variable = True

	if not allowed_return_types:
		allowed_return_types = [
			"Yes / No",
			"Single Record",
			"List of Values",
			"List of Records",
			"Full Document",
		]
		default_return_type = "Single Record"
		field_labels["return_type"] = "Result Type"
		show_return_type = True
		require_return_type = False

	policy["allowed_return_types"] = allowed_return_types
	policy["default_return_type"] = default_return_type
	policy["show_return_type"] = show_return_type
	policy["require_return_type"] = require_return_type
	policy["require_return_variable"] = require_return_variable
	if field_labels:
		policy["field_labels"] = field_labels

	override_policy = process_overrides.get("policy") or {}
	if isinstance(override_policy, dict):
		if isinstance(override_policy.get("field_labels"), dict):
			policy["field_labels"] = {
				**policy.get("field_labels", {}),
				**override_policy.get("field_labels", {}),
			}
		for key, value in override_policy.items():
			if key == "field_labels":
				continue
			policy[key] = value

	return policy


def get_effective_action_policy(
	action_type: str | None,
	operation: str | None = None,
	process_operation: dict | None = None,
) -> dict:
	"""Resolve action policy including operation-level overrides."""
	contract = get_contract(action_type or "")

	# First, try to get operation-specific contract
	op_contract = {}
	if operation:
		op_contract = get_operation_contract(operation, process_operation)

	policy: dict = {
		"allowed_mutations": list(contract.get("allowed_mutations", []) or []),
		"allowed_return_types": list(contract.get("allowed_return_types", []) or []),
		"default_return_type": contract.get("default_return_type"),
		"field_labels": dict(contract.get("field_labels", {}) or {}),
		"show_return_type": contract.get("show_return_type"),
		"require_return_type": contract.get("require_return_type", False),
		"show_return_variable": contract.get("show_return_variable"),
		"require_return_variable": contract.get("require_return_variable", False),
	}

	# Override with operation-specific policies
	op_policy = {}
	if operation:
		# Check legacy operation_policies in action type contract
		op_policy = dict((contract.get("operation_policies", {}) or {}).get(operation, {}) or {})

		# Override with new operation contract policies if available
		if op_contract and op_contract.get("Rule Action"):
			# Extract policy-relevant fields from operation contract
			for field_def in op_contract["Rule Action"]:
				fieldname = field_def.get("fieldname")
				if fieldname == "mutation_mode" and field_def.get("options"):
					op_policy["allowed_mutations"] = field_def["options"]
				elif fieldname == "return_type":
					if field_def.get("options"):
						op_policy["allowed_return_types"] = field_def["options"]
					if field_def.get("default"):
						op_policy["default_return_type"] = field_def["default"]
					if "read_only" in field_def:
						op_policy["show_return_type"] = not field_def.get("read_only", False)
						op_policy["require_return_type"] = field_def.get("reqd", False)
	if action_type == "Process" and process_operation and operation:
		from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2

		process_name = process_operation.get("parent") if isinstance(process_operation, dict) else None
		if process_name:
			contract_v2 = resolve_process_operation_contract_v2(
				process_name,
				operation,
				process_operation,
				strict=True,
			)
			for key, value in (contract_v2.get("policy") or {}).items():
				if value is not None:
					op_policy[key] = value
	elif process_operation:
		dynamic_policy = infer_process_operation_policy(process_operation)
		for key, value in dynamic_policy.items():
			if value is not None:
				op_policy[key] = value

	for key in ("allowed_mutations", "allowed_return_types"):
		if op_policy.get(key):
			policy[key] = list(op_policy[key])
	if op_policy.get("default_return_type"):
		policy["default_return_type"] = op_policy["default_return_type"]
	if op_policy.get("show_return_type") is not None:
		policy["show_return_type"] = op_policy.get("show_return_type")
	if op_policy.get("require_return_type") is not None:
		policy["require_return_type"] = op_policy.get("require_return_type")
	if op_policy.get("show_return_variable") is not None:
		policy["show_return_variable"] = op_policy.get("show_return_variable")
	if op_policy.get("require_return_variable") is not None:
		policy["require_return_variable"] = op_policy.get("require_return_variable")
	if op_policy.get("field_labels"):
		policy["field_labels"].update(op_policy.get("field_labels", {}))

	return policy
