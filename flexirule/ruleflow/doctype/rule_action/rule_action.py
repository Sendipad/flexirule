# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe.model.document import Document


class RuleAction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action_id: DF.Data
		action_label: DF.Data
		action_type: DF.Literal[
			"Entry Action",
			"Condition",
			"Process",
			"Stop",
			"Raise Error",
			"Wait",
			"Sub-Rule",
			"Assignment",
			"Notify",
			"Query Records",
			"Document Action",
			"Loop",
		]
		compiled_expression: DF.Code | None
		condition_json: DF.Code | None
		config: DF.Code | None
		description: DF.SmallText | None
		input_source: DF.Literal["", "Context Doc", "Context Variable", "Both"]
		is_async: DF.Check
		is_enabled: DF.Check
		mutation_mode: DF.Literal[
			"",
			"Set Doc Field",
			"Update Doc Field",
			"Set Context Variable",
			"Update Context Variable",
			"Append to Context Variable",
			"Batch Database Set",
		]
		next_step_if_false: DF.Data | None
		next_step_if_true: DF.Autocomplete | None
		on_error: DF.Literal["Stop", "Continue", "Retry", "Rollback", "Escalate"]
		operation: DF.Autocomplete | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		permission_audit_reason: DF.SmallText | None
		process_name: DF.Link | None
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		resolved_output_schema: DF.Code | None
		retry_count: DF.Int
		return_type: DF.Literal[
			"", "Yes / No", "Single Record", "List of Values", "List of Records", "Full Document"
		]
		return_variable: DF.Data | None
		rule: DF.Link | None
		skip_conditions: DF.Check
		skip_permissions: DF.Check
		target_field: DF.Data | None
		timeout: DF.Int
		value_template: DF.Code | None
	# end: auto-generated types
	"""
	Rule Action child table - individual action nodes in a rule flow
	"""
