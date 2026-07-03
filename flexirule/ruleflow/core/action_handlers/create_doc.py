# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Document Action Handler

Modes:
- Create New: Creates a new document with field mappings
- Update Existing: Updates an existing document with field mappings
"""

import json

import frappe
from frappe import _
from frappe.model import child_table_fields, default_fields, table_fields

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import (
	ActionContract,
	OperationContract,
	reference_doctype_override,
)
from flexirule.ruleflow.core.action_plan_cache import get_action_plan
from flexirule.ruleflow.core.permissions import can_skip_permissions
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class DocumentActionHandler(ActionHandler):
	"""Handler for creating, updating, or deleting documents."""

	action_type = "Document Action"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Document Action",
			required_fields=["reference_doctype", "operation"],
			has_next_true=True,
			has_next_false=False,
			terminal=False,
			css={"icon": "fa fa-file-text", "color": "#059669"},
			operation_label="Document Mode",
			operation_options=["Create New", "Update Existing", "Delete Record", "Create ToDo", "Add Comment"],
			allowed_mutations=[
				"Set Doc Field",
				"Set Context Variable",
			],
			allowed_return_types=[
				"Single Record",
				"Full Document",
				"Yes / No",
			],
			default_return_type="Single Record",
			show_return_type=True,
			operation_policies={
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
			field_labels={
				"operation": "Document Mode",
				"reference_doctype": "Target DocType",
				"reference_docname": "Target Record",
				"mutation_mode": "Result Handling",
				"return_type": "Result Type",
			},
			node_type="documentaction",
			category="Data Actions",
			configurable=True,
			config_component="DocumentActionConfig",
		)

	@classmethod
	def get_operation_contracts(cls):
		return {
			"Create New": OperationContract(
				operation="Create New",
				rule_overrides=[
					{"fieldname": "trigger_event", "options": ["Before Insert", "Validate", "Before Save"]},
					{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
					{
						"fieldname": "debug_mode",
						"mandatory_depends_on": "eval:doc.trigger_type==='DocType Event'",
						"description": "Enable detailed logging for document events",
					},
				],
				action_overrides=[
					{"fieldname": "action_type", "default": "Document Action"},
					{"fieldname": "operation", "default": "Create New"},
					reference_doctype_override(),
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
				validation={"backend": "validate_create_document"},
			),
			"Update Existing": OperationContract(
				operation="Update Existing",
				action_overrides=[
					{"fieldname": "action_type", "default": "Document Action"},
					{"fieldname": "operation", "default": "Update Existing"},
					reference_doctype_override(),
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
				validation={"backend": "validate_update_document"},
			),
			"Delete Record": OperationContract(
				operation="Delete Record",
				action_overrides=[
					{"fieldname": "action_type", "default": "Document Action"},
					{"fieldname": "operation", "default": "Delete Record"},
					reference_doctype_override(),
					{"fieldname": "reference_docname", "depends_on": "eval:doc.reference_doctype", "reqd": 1},
					{"fieldname": "return_type", "default": "Yes / No", "read_only": 1},
					{"fieldname": "description", "description": "⚠️ Permanently deletes a document record"},
				],
				validation={"backend": "validate_delete_document"},
			),
			"Create ToDo": OperationContract(
				operation="Create ToDo",
				rule_overrides=[
					{"fieldname": "trigger_event", "options": ["After Save", "On Submit", "On Change"]},
					{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
				],
				action_overrides=[
					{"fieldname": "action_type", "default": "Document Action"},
					{"fieldname": "operation", "default": "Create ToDo"},
					reference_doctype_override(),
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
				validation={"backend": "validate_create_todo"},
			),
			"Add Comment": OperationContract(
				operation="Add Comment",
				rule_overrides=[
					{"fieldname": "trigger_event", "options": ["After Save", "On Submit", "On Change"]},
					{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
				],
				action_overrides=[
					{"fieldname": "action_type", "default": "Document Action"},
					{"fieldname": "operation", "default": "Add Comment"},
					reference_doctype_override(),
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
				validation={"backend": "validate_add_comment"},
			),
		}

	def execute(self, action, context, engine):
		"""Execute document creation/update based on mode."""
		plan = get_action_plan(engine.rule, action)
		mode = plan.get("mode") or action.operation
		reference_doctype = plan.get("reference_doctype") or action.reference_doctype
		config = (
			plan.get("config") if isinstance(plan.get("config"), dict) else self._parse_config(action.config)
		)
		ignore_permissions = can_skip_permissions(action, context, throw=True)
		is_async = bool(plan.get("is_async") if "is_async" in plan else action.is_async)

		if not mode:
			frappe.throw(_("Operation/Mode is required for Document Action"))

		if not reference_doctype:
			frappe.throw(_("Reference DocType is required for Document Action"))

		# Apply input mapping (Context -> Config)
		if plan.get("has_input_mapping"):
			config = apply_input_mapping(context, plan.get("input_mapping"), config)
		else:
			action_config = frappe.parse_json(getattr(action, "config", "{}") or "{}")
			if action_config.get("input_mapping"):
				config = apply_input_mapping(context, action_config.get("input_mapping"), config)

		# Dispatch to mode handler
		if mode == "Create New":
			result = self._create_new(
				reference_doctype, config, context, action, ignore_permissions, is_async
			)
		elif mode == "Update Existing":
			result = self._update_existing(reference_doctype, config, context, action, ignore_permissions)
		elif mode == "Delete Record":
			result = self._delete_record(reference_doctype, config, context, action, ignore_permissions)
		elif mode == "Create ToDo":
			result = self._create_todo(reference_doctype, config, context, ignore_permissions)
		elif mode == "Add Comment":
			result = self._add_comment(reference_doctype, config, context, ignore_permissions)
		else:
			frappe.throw(_("Unknown Document Action mode: {0}").format(mode))

		next_action = action.next_step_if_true
		return result, next_action

	def validate(self, action, context):
		"""Validate Document Action configuration."""
		errors = []
		if not action.operation:
			errors.append(_("Operation/Mode is required"))
		if not action.reference_doctype:
			errors.append(_("Reference DocType is required"))

		mode = action.operation
		if mode in ("Update Existing", "Delete Record") and not action.reference_docname:
			config = self._parse_config(action.config)
			if not config.get("docname") and not config.get("docname_expression"):
				errors.append(
					_(
						"{0} mode requires either a Reference Document "
						"or a docname/docname_expression in config"
					).format(mode)
				)
		elif mode == "Create ToDo":
			if action.reference_doctype and action.reference_doctype != "ToDo":
				errors.append(_("Create ToDo mode requires Reference DocType = ToDo"))
			config = self._parse_config(action.config)
			if not config.get("assigned_to"):
				errors.append(_("Create ToDo mode requires assigned_to in config"))
			if not config.get("description"):
				errors.append(_("Create ToDo mode requires description in config"))
		elif mode == "Add Comment":
			if action.reference_doctype and action.reference_doctype != "Comment":
				errors.append(_("Add Comment mode requires Reference DocType = Comment"))
			config = self._parse_config(action.config)
			if not config.get("comment_text"):
				errors.append(_("Add Comment mode requires comment_text in config"))
		return errors

	def _parse_config(self, config_str):
		"""Safely parse config JSON."""
		if not config_str:
			return {}
		if isinstance(config_str, dict):
			return config_str
		try:
			return json.loads(config_str)
		except (json.JSONDecodeError, TypeError):
			return {}

	def _resolve_field_mappings(self, mappings, context):
		"""
		Resolve field mappings from context to target values.

		Mapping format:
		[
		    {"source": "doc.customer", "target": "customer"},
		    {"source": "vars.calculated_total", "target": "grand_total"},
		    {"source": "'Fixed Value'", "target": "status"},
		]
		"""
		resolved = {}
		eval_cache: dict = {}
		for mapping in mappings:
			source = mapping.get("source", "")
			target = mapping.get("target", "")
			if not target:
				continue

			try:
				if source in eval_cache:
					value = eval_cache[source]
				else:
					# Resolve source expression
					value = self._safe_eval(source, context)
					eval_cache[source] = value
				resolved[target] = value
			except Exception as e:
				frappe.logger().warning(f"Failed to resolve field mapping '{source}' -> '{target}': {e}")

		return resolved

	def _create_new(self, reference_doctype, config, context, action, ignore_permissions, is_async):
		"""Create a new document with field mappings."""
		field_mappings = config.get("field_mappings", [])
		static_values = config.get("static_values", {})
		table_mappings = config.get("table_mappings", [])
		mapper_options = config.get("mapper_options") or {}

		# Build document data
		doc_data = {"doctype": reference_doctype}

		# 1) Optional same-field copy (Frappe mapper style)
		doc_data.update(self._get_same_field_mappings(reference_doctype, mapper_options, context))

		# 2) Apply dynamic field mappings
		compiled_scalars = config.get("compiled_scalars")
		if compiled_scalars:
			try:
				resolved = self._safe_eval(compiled_scalars, context)
				if isinstance(resolved, dict):
					doc_data.update(resolved)
			except Exception as e:
				frappe.logger().warning(f"Failed to resolve compiled field mappings: {e}")
		elif field_mappings:
			resolved = self._resolve_field_mappings(field_mappings, context)
			doc_data.update(resolved)

		# 3) Apply static values last (explicit user constants should win)
		doc_data.update(static_values)

		if is_async:
			# Enqueue document creation
			frappe.enqueue(
				"flexirule.ruleflow.core.action_handlers.create_doc._async_create_doc",
				queue="default",
				doc_data=doc_data,
				ignore_permissions=ignore_permissions,
			)
			return {"enqueued": True, "doctype": reference_doctype}

		# Synchronous creation
		new_doc = frappe.get_doc(doc_data)
		self._apply_table_mappings(new_doc, table_mappings, context)
		new_doc.insert(ignore_permissions=ignore_permissions)

		return new_doc.as_dict()

	def _update_existing(self, reference_doctype, config, context, action, ignore_permissions):
		"""Update an existing document with field mappings."""
		docname = action.reference_docname or config.get("docname")

		# Support dynamic docname from expression
		if not docname and config.get("docname_expression"):
			docname = self._safe_eval(config["docname_expression"], context)

		if not docname:
			frappe.throw(_("No document name specified for Update Existing"))

		doc = frappe.get_doc(reference_doctype, docname)
		if not ignore_permissions:
			doc.check_permission("write")

		# Apply field mappings
		field_mappings = config.get("field_mappings", [])
		static_values = config.get("static_values", {})
		table_mappings = config.get("table_mappings", [])
		mapper_options = config.get("mapper_options") or {}

		# Optional same-field copy (Frappe mapper style)
		for field, value in self._get_same_field_mappings(reference_doctype, mapper_options, context).items():
			doc.set(field, value)

		# Apply static values
		for field, value in static_values.items():
			doc.set(field, value)

		# Apply dynamic field mappings
		compiled_scalars = config.get("compiled_scalars")
		if compiled_scalars:
			try:
				resolved = self._safe_eval(compiled_scalars, context)
				if isinstance(resolved, dict):
					for field, value in resolved.items():
						doc.set(field, value)
			except Exception as e:
				frappe.logger().warning(f"Failed to resolve compiled field mappings: {e}")
		elif field_mappings:
			resolved = self._resolve_field_mappings(field_mappings, context)
			for field, value in resolved.items():
				doc.set(field, value)

		self._apply_table_mappings(doc, table_mappings, context)

		doc.save(ignore_permissions=ignore_permissions)

		return doc.as_dict()

	def _safe_eval(self, expression, context):
		"""Evaluate expressions using SafeFrappeAPI from context."""
		safe_frappe = context.get("frappe") or frappe
		eval_locals = {
			"doc": context.get("doc"),
			"old_doc": context.get("old_doc"),
			"vars": context.get("vars", {}),
			"item": context.get("item"),
			"loop": context.get("loop"),
		}
		return frappe.safe_eval(
			expression,
			eval_globals={"frappe": safe_frappe},
			eval_locals=eval_locals,
		)

	def _apply_table_mappings(self, doc, table_mappings, context):
		"""Apply compiled child table mappings using Frappe-native row append."""
		if not table_mappings or not isinstance(table_mappings, list):
			return

		for table_cfg in table_mappings:
			table_field = table_cfg.get("target_table")
			source_expr = table_cfg.get("source")
			assignments = table_cfg.get("assignments", [])
			item_alias = table_cfg.get("item_alias") or "item"
			reset_value = table_cfg.get("reset_value", True)
			add_if_empty = bool(table_cfg.get("add_if_empty"))
			condition_expr = (table_cfg.get("condition") or "").strip()
			filter_expr = (table_cfg.get("filter") or "").strip()

			if not table_field or not source_expr or not assignments:
				continue

			try:
				rows = self._safe_eval(source_expr, context)
			except Exception as exc:
				frappe.logger().warning(
					f"Document Action: table mapping source eval failed ({table_field}): {exc}"
				)
				continue

			if not isinstance(rows, list | tuple):
				continue

			existing_rows = doc.get(table_field) or []
			if add_if_empty and existing_rows:
				continue

			if reset_value:
				# Preserve existing behavior unless explicitly disabled.
				doc.set(table_field, [])

			total_rows = len(rows)
			for idx, row_item in enumerate(rows):
				item_value = row_item.as_dict() if hasattr(row_item, "as_dict") else row_item
				item_proxy = frappe._dict(item_value) if isinstance(item_value, dict) else item_value

				row_context = dict(context)
				row_context[item_alias] = item_proxy
				row_context["item"] = item_proxy
				row_context["loop"] = {
					"index": idx,
					"first": idx == 0,
					"last": idx == total_rows - 1,
					"length": total_rows,
				}

				if condition_expr:
					try:
						if not bool(self._safe_eval(condition_expr, row_context)):
							continue
					except Exception as exc:
						frappe.logger().warning(
							f"Document Action: table condition eval failed ({table_field}): {exc}"
						)
						continue

				if filter_expr:
					try:
						if bool(self._safe_eval(filter_expr, row_context)):
							continue
					except Exception as exc:
						frappe.logger().warning(
							f"Document Action: table filter eval failed ({table_field}): {exc}"
						)
						continue

				row_payload = {}
				compiled_row_eval = table_cfg.get("compiled_row_eval")
				if compiled_row_eval:
					try:
						row_payload = self._safe_eval(compiled_row_eval, row_context)
					except Exception as exc:
						frappe.logger().warning(
							f"Document Action: compiled table field eval failed ({table_field}): {exc}"
						)
				else:
					for assignment in assignments:
						target = assignment.get("target")
						if not target:
							continue

						source_type = assignment.get("source_type") or "expr"
						if source_type == "literal":
							row_payload[target] = assignment.get("literal")
							continue

						source = assignment.get("source")
						if not source:
							continue

						try:
							row_payload[target] = self._safe_eval(source, row_context)
						except Exception as exc:
							frappe.logger().warning(
								f"Document Action: table field eval failed ({table_field}.{target}): {exc}"
							)

				if row_payload:
					doc.append(table_field, row_payload)

	def _get_same_field_mappings(self, target_doctype, mapper_options, context):
		"""Map same field names from source object to target doctype (Frappe mapper style)."""
		if not mapper_options or not mapper_options.get("copy_same_fields"):
			return {}

		source_path = (mapper_options.get("source_path") or "doc").strip() or "doc"
		source_obj = self._resolve_source_object(source_path, context)
		if source_obj is None:
			return {}

		field_no_map = [
			f.strip() for f in (mapper_options.get("field_no_map") or []) if isinstance(f, str) and f.strip()
		]
		return self._map_same_fields(source_obj, target_doctype, field_no_map)

	def _resolve_source_object(self, source_path, context):
		"""Resolve mapper source object from context expression/path."""
		if source_path in ("", "doc"):
			return context.get("doc")
		try:
			return self._safe_eval(source_path, context)
		except Exception:
			return None

	def _map_same_fields(self, source_obj, target_doctype, field_no_map=None):
		"""Equivalent of frappe.model.mapper.map_fields for same-name scalar fields."""
		target_meta = frappe.get_meta(target_doctype)
		source_meta = getattr(source_obj, "meta", None)

		no_copy_fields = set(default_fields).union(set(child_table_fields))
		no_copy_fields.update(field_no_map or [])

		# Exclude table and no_copy fields from source/target definitions.
		if source_meta:
			no_copy_fields.update(
				{
					d.fieldname
					for d in source_meta.get("fields")
					if (d.no_copy == 1 or d.fieldtype in table_fields)
				}
			)
		no_copy_fields.update(
			{
				d.fieldname
				for d in target_meta.get("fields")
				if (d.no_copy == 1 or d.fieldtype in table_fields)
			}
		)

		mapped = {}
		for df in target_meta.get("fields"):
			if df.fieldname in no_copy_fields:
				continue

			val = self._get_source_value(source_obj, df.fieldname)
			if val not in (None, ""):
				mapped[df.fieldname] = val
				continue

			# Map link-to-source fallback as frappe mapper does.
			if df.fieldtype == "Link" and df.options == getattr(source_obj, "doctype", None):
				source_name = getattr(source_obj, "name", None)
				if source_name:
					mapped[df.fieldname] = source_name

		return mapped

	def _get_source_value(self, source_obj, fieldname):
		"""Read field value from frappe document, dict, or generic object."""
		if source_obj is None:
			return None
		if isinstance(source_obj, dict):
			return source_obj.get(fieldname)
		if hasattr(source_obj, "get"):
			try:
				return source_obj.get(fieldname)
			except Exception:
				pass
		return getattr(source_obj, fieldname, None)

	def _template_context(self, context):
		return {
			"doc": context.get("doc"),
			"vars": context.get("vars", {}),
			"context": context,
			"frappe": context.get("frappe") or frappe,
			"utils": frappe.utils,
		}

	def _render_scalar(self, value, context):
		if value is None or not isinstance(value, str):
			return value
		return frappe.render_template(value, self._template_context(context))  # nosemgrep: frappe-ssti

	def _create_todo(self, reference_doctype, config, context, ignore_permissions):
		"""Create a linked ToDo using the current context document."""
		if reference_doctype != "ToDo":
			frappe.throw(_("Create ToDo mode requires Reference DocType = ToDo"))

		doc = context.get("doc")
		if not doc:
			frappe.throw(_("Create ToDo mode requires a context document"))

		raw_assigned = config.get("assigned_to")
		# Support dynamic resolution: {variable} syntax first, then Jinja {{ }} templates
		assigned_to = self._resolve_value_expression(raw_assigned, context) if raw_assigned else None
		if (
			assigned_to
			and isinstance(assigned_to, str)
			and ("{{" in str(raw_assigned) or "{%" in str(raw_assigned))
		):
			assigned_to = self._render_scalar(raw_assigned, context)
		description = self._render_scalar(config.get("description"), context)
		priority = self._render_scalar(config.get("priority") or "Medium", context)

		if not assigned_to:
			frappe.throw(_("Create ToDo mode requires assigned_to in config"))
		if not description:
			frappe.throw(_("Create ToDo mode requires description in config"))

		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": assigned_to,
				"description": description,
				"priority": priority,
				"reference_type": doc.doctype,
				"reference_name": doc.name,
			}
		)
		todo.insert(ignore_permissions=ignore_permissions)
		return todo.as_dict()

	def _add_comment(self, reference_doctype, config, context, ignore_permissions):
		"""Add a timeline comment to the current context document."""
		if reference_doctype != "Comment":
			frappe.throw(_("Add Comment mode requires Reference DocType = Comment"))

		doc = context.get("doc")
		if not doc:
			frappe.throw(_("Add Comment mode requires a context document"))

		comment_text = self._resolve_value_expression(config.get("comment_text", ""), context)
		comment_type = self._resolve_value_expression(config.get("comment_type") or "Comment", context)

		if not comment_text:
			frappe.throw(_("Add Comment mode requires comment_text in config"))

		comment = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": comment_type,
				"reference_doctype": doc.doctype,
				"reference_name": doc.name,
				"content": comment_text,
			}
		)
		comment.insert(ignore_permissions=ignore_permissions)
		return comment.as_dict()

	def _delete_record(self, reference_doctype, config, context, action, ignore_permissions):
		"""Deletes an existing document."""
		docname = action.reference_docname

		if not docname:
			# Fallback to config explicitly mapping docname
			if config.get("docname_expression"):
				docname = self._safe_eval(config.get("docname_expression"), context)
			else:
				docname = self._resolve_value_expression(config.get("docname"), context)

		if not docname:
			frappe.throw(_("Record name is required for Delete Record mode"))

		if not frappe.db.exists(reference_doctype, docname):
			frappe.throw(
				_("DocType {0} with name {1} does not exist").format(reference_doctype, docname),
				frappe.DoesNotExistError,
			)

		if not ignore_permissions and not frappe.has_permission(reference_doctype, "delete", docname):
			frappe.throw(
				_("You don't have delete permission for {0}").format(reference_doctype),
				frappe.PermissionError,
			)

		frappe.delete_doc(reference_doctype, docname, ignore_permissions=ignore_permissions)

		return {"deleted": True, "doctype": reference_doctype, "name": docname}


# Register handler
HandlerRegistry.register(DocumentActionHandler())
