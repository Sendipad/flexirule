# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import ast
import json
import re

import frappe
from frappe import _
from frappe.model.document import Document

from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity


class Rule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		from flexirule.ruleflow.doctype.rule_action.rule_action import RuleAction
		from flexirule.ruleflow.doctype.rule_permission.rule_permission import RulePermission

		actions: DF.Table[RuleAction]
		compiled_expression: DF.Code | None

		debug_mode: DF.Check
		description: DF.Text | None
		document_type: DF.Link | None
		execution_mode: DF.Literal["Synchronous", "Asynchronous"]
		exposed_as_subrule: DF.Check
		is_active: DF.Check
		last_error: DF.Text | None
		max_execution_time: DF.Int
		module: DF.Link | None
		permissions: DF.Table[RulePermission]
		priority: DF.Literal[
			"0",
			"1",
			"2",
			"3",
			"4",
			"5",
			"6",
			"7",
			"8",
			"9",
			"10",
			"11",
			"12",
			"13",
			"14",
			"15",
			"16",
			"17",
			"18",
			"19",
			"20",
		]
		rule_name: DF.Data
		skip_for_roles: DF.TableMultiSelect[HasRole]
		status: DF.Literal["Draft", "Active", "Disabled", "Invalid", "Error", "Archived"]
		trigger_condition: DF.Code | None
		trigger_event: DF.Literal[
			"",
			"Before Naming",
			"Before Insert",
			"Before Save",
			"Validate",
			"Before Submit",
			"After Insert",
			"After Save",
			"On Submit",
			"Before Cancel",
			"On Cancel",
			"On Trash",
			"On Update After Submit",
			"On Change",
			"Before Rename",
			"After Rename",
			"Before Print",
		]
		trigger_type: DF.Literal["DocType Event", "Scheduler Event", "Callable Event"]
		version: DF.Int
		visual_data: DF.Code | None
		watched_fields: DF.SmallText | None

	# end: auto-generated types
	def _ensure_version_lineage_fields(self):
		"""Keep version lineage fields populated before validation and naming."""
		if not self.version:
			self.version = 1
		if not self.get("base_rule_name") and self.rule_name:
			self.set("base_rule_name", re.sub(r"_[vV]\d+$", "", self.rule_name))

	def _sync_status(self):
		"""Keep status and is_active compatible."""
		active_flag = self.get("is_active")
		status = self.get("status")

		if active_flag:
			if status not in ("Error", "Invalid", "Active"):
				self.status = "Active"
		else:
			if status == "Active":
				self.status = "Disabled"
			elif status not in ("Error", "Invalid", "Disabled", "Archived"):
				self.status = "Draft"

	def validate(self):
		"""
		Validate Rule Configuration
		"""
		self._ensure_version_lineage_fields()
		self._sync_status()

		if not self.visual_data:
			self._initialize_default_graph()

		self.ensure_start_node()
		self.validate_entry_action_invariants()
		self.reorder_actions()
		self.compile_conditions()
		self.compile_action_templates()
		self.compile_action_mappings()
		self.normalize_trigger_type_fields()
		self.validate_with_service()
		self.validate_active_rule_lock()
		self.validate_priority_callable()
		self.set_callable_permissions()
		self.validate_deactivation_safety()
		self.validate_activation_safety()
		self.validate_single_active_version()

	# Removed status computation for lifecycle_state

	def validate_with_service(self):
		"""Shared structured validation layer used by form save and builder precheck."""
		from flexirule.ruleflow.core.validation_service import validate_rule_definition

		# Use 'full' mode for active rules, 'draft' mode for drafts
		mode = "full" if self.is_active else "draft"
		result = validate_rule_definition(self, mode=mode)
		if result.get("warnings"):
			for warning in result.get("warnings", []):
				frappe.msgprint(warning, alert=True)
		if result.get("valid"):
			return

		message = "<br>".join(result.get("errors", []))
		frappe.throw(_("Rule validation failed:<br>{0}").format(message))

	def before_save(self):
		"""Initialize version for new rules."""
		self._ensure_version_lineage_fields()
		self._sync_status()
		if not self.visual_data:
			self._initialize_default_graph()

	def is_exposed_as_subrule(self):
		"""Return whether the rule is allowed to be targeted by Sub-Rule actions."""
		return bool(self.get("exposed_as_subrule"))

	def validate_priority_callable(self):
		"""If trigger_type is Callable Event, priority must be 0."""
		if self.trigger_type == "Callable Event" and str(self.priority) != "0":
			self.priority = "0"
			frappe.msgprint(_("Priority reset to 0 for Callable Event rule."), alert=True)

	def set_callable_permissions(self):
		"""
		Automatically add 'All' role permission for callable sub-rules.
		Req: when a rule is callable and exposed as sub rule it must set permission to role: 'all'
		"""
		if self.trigger_type == "Callable Event" and self.exposed_as_subrule:
			has_all = any(p.role == "All" for p in self.permissions)
			if not has_all:
				self.append("permissions", {"role": "All", "can_execute": 1})

	def normalize_trigger_type_fields(self):
		"""Clear fields hidden by the selected trigger type."""
		from flexirule.ruleflow.core.contracts import get_trigger_type_contract

		contract = get_trigger_type_contract(self.trigger_type)
		for fieldname in contract.get("hidden_fields", []):
			if self.get(fieldname):
				self.set(fieldname, None)

		pass

	def validate_trigger_alignment(
		self, rule_doc=None, visited_rules=None, is_after_event_context=None, target_rule_override=None
	):
		"""
		Ensure document-editing actions are only present in 'Before' triggers.
		Recursively checks sub-rules.

		Manual triggers are allowed to define doc-editing actions (for use as sub-rules),
		but their usage is restricted based on the calling rule's trigger.
		"""
		if visited_rules is None:
			visited_rules = set()

		doc_to_check = rule_doc or self

		if doc_to_check.name in visited_rules:
			return
		visited_rules.add(doc_to_check.name)

		# Define 'Before' events that allow document modification
		before_events = [
			"Before Naming",
			"Before Insert",
			"Before Save",
			"Validate",
			"Before Submit",
		]

		# Callable/Scheduler rules are not considered 'after events' when defined.
		# They only become 'after events' if called from an after-event parent.
		is_non_doc_event = doc_to_check.trigger_type in ("Callable Event", "Scheduler Event")
		local_is_after_event = doc_to_check.trigger_event not in before_events and not is_non_doc_event

		# Effective context: inherited from parent or determined locally for root rule
		effective_after_event = (
			is_after_event_context if is_after_event_context is not None else local_is_after_event
		)

		for action in doc_to_check.actions:
			# Check Assignment (doc.* mutations are blocked in after-events)
			if action.action_type == "Assignment" and effective_after_event:
				# Only block if any assignment targets a doc.* path
				config_str = getattr(action, "config", "[]") or "[]"
				try:
					assignments = json.loads(config_str) if isinstance(config_str, str) else config_str
				except Exception:
					assignments = []
				has_doc_mutation = any(
					(a.get("target") or "").startswith("doc.") for a in assignments if isinstance(a, dict)
				)
				if has_doc_mutation:
					frappe.throw(
						_(
							"Action '{0}' (Assignment) in Rule '{1}' contains doc.* mutations that are not "
							"allowed in current execution context. "
							"Document modification is restricted after the document is saved. "
							"Parent/Trigger: {2}"
						).format(action.action_label, doc_to_check.name, self.trigger_event)
					)

			# Check Process operations that write to Document
			if action.action_type == "Process" and effective_after_event:
				if action.process_name and action.operation:
					try:
						process = frappe.get_cached_doc("Process", action.process_name)
						op = process.get_operation(action.operation)
						if op and op.writes_to == "Document":
							frappe.throw(
								_(
									"Action '{0}' in Rule '{1}' uses operation '{2}' which modifies the document. "
									"This is restricted in current execution context (Parent/Trigger: {3})."
								).format(
									action.action_label,
									doc_to_check.name,
									action.operation,
									self.trigger_event,
								)
							)
					except Exception:
						pass  # Handled by other validations

				# Recursive check for Sub-Rules
				if action.action_type == "Sub-Rule" and action.rule:
					if target_rule_override and (
						target_rule_override.base_rule_name == action.rule
						or target_rule_override.name == action.rule
					):
						sub_rule = target_rule_override
					else:
						from flexirule.ruleflow.core.rule_service import resolve_rule_reference

						target_rule_name = resolve_rule_reference(
							action.rule,
							active_only=bool(doc_to_check.is_active),
							callable_only=True,
							exposed_only=True,
						)
						if not target_rule_name:
							target_rule_name = action.rule
						sub_rule = frappe.get_doc("Rule", target_rule_name)
					self.validate_trigger_alignment(
						sub_rule,
						visited_rules,
						effective_after_event,
						target_rule_override=target_rule_override,
					)

	def validate_active_rule_lock(self):
		"""
		Governance: Prevent editing of Active rules.
		User must deactivate (Draft) to edit.
		"""
		if self.is_new():
			return

		# Note: We intentionally do NOT skip for ignore_validate flag
		# to prevent accidental bypass of governance rules

		# Check prior state
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return

		# If rule was active and is still active
		if old_doc.is_active and self.is_active:
			# Allow saving ONLY if it's a programmatic update (like stats or error log)
			# but usually those use ignore_validate=True.
			# If we are here, it's likely a user edit.
			frappe.throw(
				_("Cannot edit an Active Rule. Please set to 'Disabled' (Draft) before making changes.")
			)

		def before_insert(self):
			self._ensure_version_lineage_fields()
			self._initialize_default_graph()
			self.ensure_start_node()

	def _initialize_default_graph(self):
		"""
		Initialize default visual_data with Trigger -> End nodes
		if it is empty or missing valid nodes.
		"""
		# Respect explicitly provided actions (tests and API payloads).
		# Default root/end graph is only for truly empty rules.
		if self.actions:
			return

		if self.visual_data:
			try:
				data = json.loads(self.visual_data)
				if data and data.get("nodes"):
					return
			except ValueError:
				pass

		root_id = "root"
		end_id = "node_end"

		has_root = any(a.action_id == root_id or a.action_type == "Entry Action" for a in self.actions)
		has_end = any(a.action_id == end_id for a in self.actions)

		if not has_root:
			self.append(
				"actions",
				{
					"action_type": "Entry Action",
					"action_label": _(self.trigger_event or "Start"),
					"action_id": root_id,
					"is_enabled": 1,
					"next_step_if_true": end_id,
				},
			)
		else:
			for a in self.actions:
				if (a.action_id == root_id or a.action_type == "Entry Action") and not a.next_step_if_true:
					a.next_step_if_true = end_id

		if not has_end:
			self.append(
				"actions",
				{
					"action_type": "Stop",
					"action_label": _("End"),
					"action_id": end_id,
					"is_enabled": 1,
				},
			)

		default_visual = {
			"nodes": [
				{
					"id": root_id,
					"type": "TriggerNode",
					"position": {"x": 250, "y": 50},
					"data": {"action_id": root_id, "label": _(self.trigger_event or "Start")},
				},
				{
					"id": end_id,
					"type": "EndNode",
					"position": {"x": 250, "y": 200},
					"data": {"action_id": end_id, "label": "End"},
				},
			],
			"edges": [
				{
					"id": f"edge_{root_id}_{end_id}",
					"source": root_id,
					"target": end_id,
					"sourceHandle": "true",
				}
			],
		}
		self.visual_data = json.dumps(default_visual)

	def validate_entry_action_invariants(self):
		"""Enforce that exactly one Entry Action exists."""
		entry_actions = [
			a
			for a in self.actions
			if (a.get("action_type") == "Entry Action" or a.get("action_id") == "root")
		]
		if not entry_actions:
			frappe.throw(_("Rule must have exactly one Entry Action (Start Node)."))
		if len(entry_actions) > 1:
			frappe.throw(_("Rule cannot have multiple Entry Actions. Found {0}.").format(len(entry_actions)))

	def ensure_start_node(self):
		"""Ensure a Start Node (Entry Action) exists"""
		# Check if an Entry Action already exists (by type or by the standard 'root' ID)
		root_action = self.get_entry_action()

		if not root_action:
			# Determine next step if there are existing actions
			# We pick the first action that is NOT 'root'
			first_action_id = None
			existing_actions = [a for a in self.actions if a.get("action_id") != "root"]
			if existing_actions:
				first_action_id = existing_actions[0].get("action_id") or existing_actions[0].name

			self.append(
				"actions",
				{
					"action_type": "Entry Action",
					"action_label": _(self.trigger_event or "Start"),
					"action_id": "root",
					"is_enabled": 1,
					"next_step_if_true": first_action_id,  # Link to first existing action
					"config": self.trigger_condition,
				},
			)

	def reorder_actions(self):
		"""Ensure Entry Action is the first action (idx=1)"""
		if not self.actions:
			return

		# Find entry action index
		# Priority: action_id='root' OR action_type='Entry Action'
		entry_index = -1
		for i, action in enumerate(self.actions):
			if action.action_id == "root" or action.action_type == "Entry Action":
				entry_index = i
				break

		if entry_index > 0:
			# Move to top
			entry_action = self.actions.pop(entry_index)
			self.actions.insert(0, entry_action)

		# Re-assign idx
		for i, action in enumerate(self.actions):
			action.idx = i + 1

	def get_entry_action(self):
		"""
		Returns the Entry Action (Start Node) for this rule.
		An Entry Action is identified by action_id='root' or action_type='Entry Action'.
		"""
		for action in self.actions:
			if action.get("action_id") == "root" or action.get("action_type") == "Entry Action":
				return action
		return None

	def get_entry_condition(self):
		"""
		Public API to get the trigger condition JSON.
		Encapsulates the dual-read logic during the migration period.
		"""
		return self.resolve_entry_condition()

	def resolve_entry_condition(self):
		"""
		Internal helper for Release N dual-read logic.
		Priority: EntryAction.config > Rule.trigger_condition.
		"""
		entry_action = self.get_entry_action()
		config = {}
		if entry_action and entry_action.config:
			try:
				config = (
					json.loads(entry_action.config)
					if isinstance(entry_action.config, str)
					else entry_action.config
				)
			except (ValueError, TypeError):
				config = {}

		# If Entry Action has a non-empty configuration, use it.
		if config and (
			isinstance(config, list)
			or (isinstance(config, dict) and (config.get("conditions") or config.get("collection")))
		):
			return config

		# Fallback to legacy Rule-level field during Release N transition.
		if self.trigger_condition:
			try:
				legacy_config = (
					json.loads(self.trigger_condition)
					if isinstance(self.trigger_condition, str)
					else self.trigger_condition
				)
				return legacy_config
			except (ValueError, TypeError):
				return None

		return config

	def _parse_action_config(self, action):
		"""Parse action config to mutable dict."""
		raw = action.get("config")
		if not raw:
			return {}
		if isinstance(raw, dict | list):
			return raw
		try:
			parsed = json.loads(raw)
			return parsed if isinstance(parsed, dict | list) else {}
		except Exception:
			return {}

	def _extract_expression_roots(self, expression: str) -> set[str]:
		"""Extract top-level variable roots from a Python expression."""
		if not expression or not isinstance(expression, str):
			return set()

		tree = ast.parse(expression, mode="eval")
		roots = set()

		class RootVisitor(ast.NodeVisitor):
			def visit_Name(self, node):
				roots.add(node.id)

			def visit_Attribute(self, node):
				root = node
				while isinstance(root, ast.Attribute):
					root = root.value
				if isinstance(root, ast.Name):
					roots.add(root.id)
				self.generic_visit(node)

			def visit_Subscript(self, node):
				root = node.value
				while isinstance(root, ast.Attribute):
					root = root.value
				if isinstance(root, ast.Name):
					roots.add(root.id)
				self.generic_visit(node)

		RootVisitor().visit(tree)
		return roots

	@staticmethod
	def _collect_known_return_variables(actions) -> set[str]:
		known = set()
		for action in actions or []:
			name = (getattr(action, "return_variable", None) or "").strip()
			if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
				known.add(name)
		return known

	def _normalize_context_ref(
		self, ref: str, known_var_roots: set[str] | None = None, extra_allowed_roots: set[str] | None = None
	) -> str:
		"""Normalize shorthand refs to canonical roots used by runtime.

		Examples:
		- is_pos -> doc.is_pos
		- result.total (where result is return_variable) -> vars.result.total
		"""
		if not ref or not isinstance(ref, str):
			return ref

		value = ref.strip()
		if not value:
			return value

		# Only normalize simple dotted paths; keep full expressions untouched.
		if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$", value):
			return value

		known_var_roots = known_var_roots or set()
		extra_allowed_roots = extra_allowed_roots or set()
		allowed_roots = {"doc", "old_doc", "vars", "item", "loop", "caller", "rule", "doctype"}.union(
			extra_allowed_roots
		)
		root = value.split(".", 1)[0]

		if root in allowed_roots:
			return value

		if root in known_var_roots:
			return f"vars.{value}"

		return f"doc.{value}"

	@staticmethod
	def _normalize_inline_jinja_refs(
		content: str, known_var_roots: set[str] | None = None, extra_allowed_roots: set[str] | None = None
	) -> str:
		"""Normalize inline {{ field }} / {{ result.x }} refs inside free text segments."""
		if not content or not isinstance(content, str):
			return content

		known_var_roots = known_var_roots or set()
		extra_allowed_roots = extra_allowed_roots or set()
		allowed_roots = {"doc", "old_doc", "vars", "item", "loop", "caller", "rule", "doctype"}.union(
			extra_allowed_roots
		)
		path_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")

		def _repl(match):
			expr = (match.group(1) or "").strip()
			if not expr or not path_pattern.match(expr):
				return match.group(0)
			root = expr.split(".", 1)[0]
			if root in allowed_roots:
				return "{{ " + expr + " }}"
			if root in known_var_roots:
				return "{{ vars." + expr + " }}"
			return "{{ doc." + expr + " }}"

		return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", _repl, content)

	@staticmethod
	def _collect_condition_aliases(node) -> set[str]:
		aliases: set[str] = set()
		if not isinstance(node, dict):
			return aliases

		if "collection" in node:
			alias = (node.get("alias") or "item").strip()
			if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", alias):
				aliases.add(alias)
			aliases.update(Rule._collect_condition_aliases(node.get("where")))

		for child in node.get("conditions") or []:
			aliases.update(Rule._collect_condition_aliases(child))

		return aliases

	def _validate_allowed_roots(
		self, expression: str, label: str = "expression", extra_roots: set[str] | None = None
	):
		"""Validate expression only references allowed context roots."""
		if not expression:
			return

		allowed = {"doc", "old_doc", "vars", "item", "loop", "True", "False", "None"}
		if extra_roots:
			allowed = allowed.union(set(extra_roots))
		try:
			roots = self._extract_expression_roots(expression)
		except Exception as exc:
			frappe.throw(_("Invalid {0}: {1}").format(label, str(exc)))

		disallowed = sorted(root for root in roots if root not in allowed)
		if disallowed:
			frappe.throw(_("{0} uses unsupported context roots: {1}").format(label, ", ".join(disallowed)))

	def compile_action_templates(self):
		"""Compile config.text_generator_ui (v2) into action.value_template.

		Supports:
		- text segments with inline {{ var }} markers
		- variable segments
		- conditional segments with condition tree objects (from ConditionBuilder)
		  including elif branches and else blocks
		"""
		for action in self.actions or []:
			config = self._parse_action_config(action)

			if action.action_type == "Assignment" and isinstance(config, list):
				# Handle batch assignment compilation
				changed = False
				known_var_roots = self._collect_known_return_variables(self.actions)
				from flexirule.ruleflow.core.compiler import ConditionCompiler

				condition_compiler = ConditionCompiler()

				for assignment in config:
					if not isinstance(assignment, dict):
						continue

					# Generate or preserve name key
					if not assignment.get("name"):
						assignment["name"] = frappe.generate_hash(length=9)
						changed = True

					text_ui = assignment.get("text_generator_ui")
					if isinstance(text_ui, dict):
						segments = text_ui.get("segments") or []
						compiled = self._compile_segments_v2(
							segments, action.action_label or action.action_id, known_var_roots
						)
						if not (isinstance(assignment.get("value"), dict) and "mode" in assignment["value"]):
							assignment["value"] = compiled
							assignment["value_template"] = compiled
							changed = True

					compiled_when = self._compile_assignment_when_expression(
						assignment,
						condition_compiler,
						action_label=action.action_label or action.action_id or _("Assignment"),
					)
					if assignment.get("pythonExpression") != compiled_when:
						assignment["pythonExpression"] = compiled_when
						changed = True

					compiled_operand = self._compile_assignment_operand_metadata(assignment, known_var_roots)
					for key, value in compiled_operand.items():
						if assignment.get(key) != value:
							assignment[key] = value
							changed = True

				if changed:
					action.config = json.dumps(config)
				continue

			if not isinstance(config, dict):
				continue

			text_ui = config.get("text_generator_ui")
			if not isinstance(text_ui, dict):
				continue

			segments = text_ui.get("segments") or []
			known_var_roots = self._collect_known_return_variables(self.actions)
			compiled = self._compile_segments_v2(
				segments, action.action_label or action.action_id, known_var_roots
			)

			action.value_template = compiled
			action.config = json.dumps(config)

	def _compile_assignment_operand_metadata(self, assignment: dict, known_var_roots: set[str]) -> dict:
		operator_key = assignment.get("operator", "set")
		try:
			from flexirule.ruleflow.core.operators import AssignmentOperatorRegistry

			operator = AssignmentOperatorRegistry.get(operator_key)
			if not operator.metadata.get("requires_value"):
				return {
					"value_source": "none",
					"value_literal": None,
					"value_path": None,
					"value_template": None,
				}
		except Exception:
			pass

		# Check if the new unified 'value' key holds a structured object
		val_obj = assignment.get("value")
		if isinstance(val_obj, dict) and "mode" in val_obj:
			mode = val_obj.get("mode")
			if mode in {"static", "link", "dynamic_link"}:
				return {
					"value_source": "literal",
					"value_literal": val_obj.get("value"),
					"value_path": None,
					"value_template": None,
				}
			if mode == "variable":
				normalized_path = self._normalize_context_ref(
					val_obj.get("path") or val_obj.get("value") or "",
					known_var_roots,
					extra_allowed_roots=None,
				)
				return {
					"value_source": "context_path",
					"value_literal": None,
					"value_path": self._normalize_assignment_context_path(normalized_path),
					"value_template": None,
				}
			# Formula/Resolver/Formatter/etc compile to Jinja
			from flexirule.ruleflow.core.action_handlers.assignment import AssignmentHandler

			compiled_jinja = AssignmentHandler._compile_structured_value_to_jinja(val_obj)
			return {
				"value_source": "jinja",
				"value_literal": None,
				"value_path": None,
				"value_template": compiled_jinja,
			}

		value_ui = assignment.get("value_template_ui")
		if not isinstance(value_ui, dict):
			value_ui = {}
		mode = value_ui.get("mode")

		value_template = assignment.get("value_template")
		if value_template is None:
			value_template = assignment.get("value")

		if mode in {"static", "link", "dynamic_link"}:
			return {
				"value_source": "literal",
				"value_literal": value_ui.get("value"),
				"value_path": None,
				"value_template": None,
			}

		if mode == "variable":
			normalized_path = self._normalize_context_ref(
				value_ui.get("path") or "", known_var_roots, extra_allowed_roots=None
			)
			return {
				"value_source": "context_path",
				"value_literal": None,
				"value_path": self._normalize_assignment_context_path(normalized_path),
				"value_template": None,
			}

		if isinstance(value_template, str):
			contains_jinja = "{{" in value_template or "{%" in value_template
			if mode in {"formula", "resolver"} or contains_jinja:
				return {
					"value_source": "jinja",
					"value_literal": None,
					"value_path": None,
					"value_template": value_template,
				}

			return {
				"value_source": "literal",
				"value_literal": value_template,
				"value_path": None,
				"value_template": None,
			}

		return {
			"value_source": "literal",
			"value_literal": value_template,
			"value_path": None,
			"value_template": None,
		}

	def _compile_assignment_when_expression(
		self,
		assignment: dict,
		condition_compiler,
		action_label: str,
	) -> str:
		when_condition = assignment.get("when_condition")
		if isinstance(when_condition, dict | list):
			compiled_when = condition_compiler.compile(when_condition)
			is_valid, error = condition_compiler.validate(compiled_when)
			if not is_valid:
				frappe.throw(
					_("Action '{0}' assignment condition is invalid: {1}").format(action_label, error)
				)
			return compiled_when or ""

		when_expression = (assignment.get("when_expression") or assignment.get("when") or "").strip()
		if when_expression:
			self._validate_allowed_roots(
				when_expression,
				_("Action '{0}' assignment expression").format(action_label),
			)
		return when_expression

	@staticmethod
	def _normalize_assignment_context_path(path: str | None) -> str | None:
		if not path:
			return None
		path = str(path).strip()
		if not path:
			return None
		if path.startswith("doc.") or path.startswith("vars."):
			return path
		return f"vars.{path}"

	def _compile_segments_v2(self, segments, action_label, known_var_roots=None, extra_allowed_roots=None):
		"""Compile v2 segment list to Jinja template string."""
		if not isinstance(segments, list):
			return ""

		known_var_roots = known_var_roots or set()
		out = []
		for segment in segments:
			if not isinstance(segment, dict):
				continue

			seg_type = (segment.get("type") or "text").strip().lower()

			if seg_type == "text":
				# Content may contain inline {{ var }} markers from TipTap
				content = segment.get("content") or segment.get("text") or ""
				out.append(self._normalize_inline_jinja_refs(content, known_var_roots, extra_allowed_roots))
				continue

			if seg_type == "translation":
				content = segment.get("content", "")
				out.append(f'{{{{ _("{content}") }}}}')
				continue

			if seg_type == "variable":
				path = self._normalize_context_ref(
					segment.get("path") or "", known_var_roots, extra_allowed_roots
				)
				if not path:
					continue
				self._validate_allowed_roots(
					path,
					_("Action '{0}' variable path").format(action_label),
					extra_roots=extra_allowed_roots,
				)
				out.append("{{ " + path + " }}")
				continue

			if seg_type == "conditional":
				condition = segment.get("condition")
				if isinstance(condition, dict):
					# ConditionBuilder tree — compile to expression
					cond_expr = self._compile_condition_tree(condition, known_var_roots, extra_allowed_roots)
					extra_roots = self._collect_condition_aliases(condition)
					if extra_allowed_roots:
						extra_roots.update(extra_allowed_roots)
				elif isinstance(condition, str):
					cond_expr = condition.strip()
					extra_roots = None
				else:
					cond_expr = "True"
					extra_roots = None

				if cond_expr:
					self._validate_allowed_roots(
						cond_expr,
						_("Action '{0}' conditional expression").format(action_label),
						extra_roots=extra_roots,
					)

				then_block = self._compile_segments_v2(
					segment.get("then_segments") or [], action_label, known_var_roots, extra_allowed_roots
				)
				block = "{% if " + (cond_expr or "True") + " %}" + then_block

				for elif_b in segment.get("elif_branches") or []:
					elif_cond = elif_b.get("condition")
					if isinstance(elif_cond, dict):
						elif_expr = self._compile_condition_tree(
							elif_cond, known_var_roots, extra_allowed_roots
						)
						elif_extra_roots = self._collect_condition_aliases(elif_cond)
						if extra_allowed_roots:
							elif_extra_roots.update(extra_allowed_roots)
					elif isinstance(elif_cond, str):
						elif_expr = elif_cond.strip()
						elif_extra_roots = None
					else:
						elif_expr = "True"
						elif_extra_roots = None

					if elif_expr:
						self._validate_allowed_roots(
							elif_expr,
							_("Action '{0}' elif expression").format(action_label),
							extra_roots=elif_extra_roots,
						)
					elif_content = self._compile_segments_v2(
						elif_b.get("segments") or [], action_label, known_var_roots, extra_allowed_roots
					)
					block += "{% elif " + (elif_expr or "True") + " %}" + elif_content

				# else
				else_block = self._compile_segments_v2(
					segment.get("else_segments") or [], action_label, known_var_roots, extra_allowed_roots
				)
				if else_block:
					block += "{% else %}" + else_block

				block += "{% endif %}"
				out.append(block)
				continue

			if seg_type == "loop":
				iterator = (segment.get("iterator") or "item").strip()
				iterable = self._normalize_context_ref(
					segment.get("iterable") or "[]", known_var_roots, extra_allowed_roots
				)

				loop_allowed = set(extra_allowed_roots) if extra_allowed_roots else set()
				loop_allowed.add(iterator)

				loop_block = self._compile_segments_v2(
					segment.get("segments") or [], action_label, known_var_roots, loop_allowed
				)

				out.append(f"{{% for {iterator} in {iterable} %}}{loop_block}{{% endfor %}}")
				continue

		return "".join(out)

	def _compile_condition_tree(self, node, known_var_roots=None, extra_allowed_roots=None):
		"""Compile a ConditionBuilder JSON tree to a Python boolean expression."""
		if not node or not isinstance(node, dict):
			return "True"
		known_var_roots = known_var_roots or set()

		if "conditions" in node:
			conditions = node.get("conditions") or []
			if not conditions:
				return "True"

			parts = []
			for child in conditions:
				compiled = self._compile_condition_tree(child, known_var_roots, extra_allowed_roots)
				if compiled:
					parts.append(compiled)

			if not parts:
				return "True"
			if len(parts) == 1:
				return parts[0]

			joiner = " or " if node.get("op") == "or" else " and "
			return "(" + joiner.join(parts) + ")"

		# Collection node (any/all)
		if "collection" in node:
			alias = node.get("alias") or "item"
			collection = self._normalize_context_ref(
				node.get("collection") or "[]", known_var_roots, extra_allowed_roots
			)

			child_allowed = set(extra_allowed_roots) if extra_allowed_roots else set()
			child_allowed.add(alias)

			where_expr = self._compile_condition_tree(node.get("where") or {}, known_var_roots, child_allowed)
			quantifier = "all" if node.get("op") == "all" else "any"
			return f"{quantifier}({where_expr} for {alias} in {collection})"

		# Simple condition (left op right)
		if "left" in node:
			left = self._normalize_context_ref(
				(node.get("left") or {}).get("ref", ""), known_var_roots, extra_allowed_roots
			)
			if not left:
				return ""

			op = node.get("op") or "=="

			if op == "is_set":
				return f"({left} is not None and {left} != '')"
			if op == "is_not_set":
				return f"({left} is None or {left} == '')"

			right_obj = node.get("right") or {}
			if right_obj.get("ref"):
				right = self._normalize_context_ref(right_obj["ref"], known_var_roots, extra_allowed_roots)
			else:
				right = self._format_condition_value(right_obj.get("value"))

			op_map = {
				"==": "==",
				"!=": "!=",
				">": ">",
				"<": "<",
				">=": ">=",
				"<=": "<=",
				"in": "in",
				"not in": "not in",
				"like": "like",
				"not like": "not like",
				"contains": "in",
				"not_contains": "not in",
			}
			py_op = op_map.get(op, op)

			if op in ("contains", "not_contains"):
				return f"{right} {py_op} {left}"

			return f"{left} {py_op} {right}"

		return "True"

	@staticmethod
	def _format_condition_value(val):
		"""Format a condition value for Python expression output."""
		if val is None:
			return "None"
		if isinstance(val, bool):
			return "True" if val else "False"
		if isinstance(val, int | float):
			return str(val)
		if isinstance(val, list):
			if len(val) == 2 and isinstance(val[0], str):
				return Rule._format_condition_value(val[1])
			return "[" + ", ".join(Rule._format_condition_value(v) for v in val) + "]"
		escaped = str(val).replace("'", "\\'")
		return f"'{escaped}'"

	def compile_action_mappings(self):
		"""Compile config.resource_mapper_ui into backend mapping keys."""
		for action in self.actions or []:
			config = self._parse_action_config(action)
			if not isinstance(config, dict):
				continue
			mapper_ui = config.get("resource_mapper_ui")
			if not isinstance(mapper_ui, dict):
				continue

			target_doctype = action.reference_doctype or self.document_type
			if not target_doctype:
				frappe.throw(
					_("Action '{0}' requires target DocType for Resource Mapper.").format(
						action.action_label or action.action_id
					)
				)

			meta = frappe.get_meta(target_doctype)
			table_meta = {
				df.fieldname: frappe.get_meta(df.options)
				for df in meta.fields
				if df.fieldtype in ("Table", "Table MultiSelect") and df.options
			}
			allowed_scalar_fields = {
				df.fieldname for df in meta.fields if df.fieldtype not in ("Table", "Table MultiSelect")
			}

			static_values = {}
			field_mappings = []
			input_mapping = {}
			table_mappings = []
			mode = (mapper_ui.get("mode") or "field_mappings").strip().lower()
			mapper_source_path = (mapper_ui.get("source_path") or "doc").strip() or "doc"
			copy_same_fields = bool(mapper_ui.get("copy_same_fields"))
			field_no_map = [
				(f or "").strip()
				for f in (mapper_ui.get("field_no_map") or [])
				if isinstance(f, str) and (f or "").strip()
			]
			field_no_map = [f for f in field_no_map if f in allowed_scalar_fields]
			scalars = mapper_ui.get("scalars") or []

			self._validate_allowed_roots(
				mapper_source_path,
				_("Action '{0}' mapper source base").format(action.action_label or action.action_id),
			)

			for row in scalars:
				if not isinstance(row, dict):
					continue
				target = (row.get("target") or "").strip()
				if not target:
					continue
				if target not in allowed_scalar_fields:
					frappe.throw(
						_("Action '{0}': invalid mapper target field '{1}' for {2}.").format(
							action.action_label or action.action_id,
							target,
							target_doctype,
						)
					)

				source_type = (row.get("source_type") or "path").strip().lower()
				if source_type == "literal":
					static_values[target] = row.get("literal")
					continue

				if source_type == "path":
					source_expr = (row.get("path") or "").strip()
				else:
					source_expr = (row.get("expr") or "").strip()

				if not source_expr:
					continue

				self._validate_allowed_roots(
					source_expr,
					_("Action '{0}' mapper source").format(action.action_label or action.action_id),
				)

				if mode == "input_mapping" and source_type == "path":
					input_mapping[target] = source_expr
				else:
					field_mappings.append({"source": source_expr, "target": target})

			for table in mapper_ui.get("tables") or []:
				if not isinstance(table, dict):
					continue

				target_table = (table.get("target_table") or "").strip()
				table_source_path = (table.get("source_path") or "").strip()
				if not target_table or not table_source_path:
					continue
				if target_table not in table_meta:
					frappe.throw(
						_("Action '{0}': invalid table mapping target '{1}'.").format(
							action.action_label or action.action_id, target_table
						)
					)

				self._validate_allowed_roots(
					table_source_path,
					_("Action '{0}' table mapping source").format(action.action_label or action.action_id),
				)

				child_meta = table_meta[target_table]
				child_fields = {df.fieldname for df in child_meta.fields}
				item_alias = (table.get("item_alias") or "item").strip() or "item"
				condition_expr = (table.get("condition") or "").strip()
				filter_expr = (table.get("filter") or "").strip()
				if condition_expr:
					self._validate_allowed_roots(
						condition_expr,
						_("Action '{0}' table mapping condition").format(
							action.action_label or action.action_id
						),
						extra_roots={item_alias},
					)
				if filter_expr:
					self._validate_allowed_roots(
						filter_expr,
						_("Action '{0}' table mapping filter").format(
							action.action_label or action.action_id
						),
						extra_roots={item_alias},
					)

				assignments = []
				for mapping in table.get("mappings") or []:
					if not isinstance(mapping, dict):
						continue
					child_target = (mapping.get("target") or "").strip()
					if not child_target:
						continue
					if child_target not in child_fields:
						frappe.throw(
							_("Action '{0}': invalid child field '{1}' for table '{2}'.").format(
								action.action_label or action.action_id,
								child_target,
								target_table,
							)
						)

					source_type = (mapping.get("source_type") or "path").strip().lower()
					if source_type == "literal":
						assignments.append(
							{
								"target": child_target,
								"source_type": "literal",
								"literal": mapping.get("literal"),
							}
						)
						continue

					if source_type == "path":
						source_expr = (mapping.get("path") or "").strip()
					else:
						source_expr = (mapping.get("expr") or "").strip()
					if not source_expr:
						continue

					self._validate_allowed_roots(
						source_expr,
						_("Action '{0}' child table mapper source").format(
							action.action_label or action.action_id
						),
						extra_roots={item_alias},
					)
					assignments.append(
						{
							"target": child_target,
							"source_type": "expr",
							"source": source_expr,
						}
					)

				if assignments:
					table_mappings.append(
						{
							"target_table": target_table,
							"source": table_source_path,
							"item_alias": item_alias,
							"reset_value": bool(table.get("reset_value", True)),
							"add_if_empty": bool(table.get("add_if_empty", False)),
							"condition": condition_expr,
							"filter": filter_expr,
							"assignments": assignments,
						}
					)

			# Optimization: Compile scalars into a single dictionary AST string
			compiled_scalars_parts = []
			for fm in field_mappings:
				compiled_scalars_parts.append(f"{fm['target']!r}: ({fm['source']})")
			config["compiled_scalars"] = "{" + ", ".join(compiled_scalars_parts) + "}"

			compiled_input_mapping_parts = []
			for target, source in input_mapping.items():
				compiled_input_mapping_parts.append(f"{target!r}: ({source})")
			config["compiled_input_mapping"] = "{" + ", ".join(compiled_input_mapping_parts) + "}"

			if not isinstance(table_mappings, list):
				table_mappings = []

			for tmap in table_mappings:
				if not isinstance(tmap, dict):
					continue
				row_dict_parts = []
				for mapping in tmap.get("assignments", []):
					target = mapping["target"]
					if mapping.get("source_type") == "literal":
						row_dict_parts.append(f"{target!r}: {mapping.get('literal')!r}")
					else:
						row_dict_parts.append(f"{target!r}: ({mapping['source']})")
				tmap["compiled_row_eval"] = "{" + ", ".join(row_dict_parts) + "}"

			config["mapper_options"] = {
				"source_path": mapper_source_path,
				"copy_same_fields": copy_same_fields,
				"field_no_map": field_no_map,
			}
			config["static_values"] = static_values
			config["field_mappings"] = field_mappings
			config["input_mapping"] = input_mapping
			config["table_mappings"] = table_mappings
			action.config = json.dumps(config)

	def compile_conditions(self):
		from flexirule.ruleflow.core.compiler import ConditionCompiler
		from flexirule.ruleflow.core.condition_payload import (
			get_condition_payload,
			parse_condition_payload,
			set_condition_payload_on_action,
		)
		from flexirule.ruleflow.core.contracts import normalize_action_type

		compiler = ConditionCompiler()

		# Compile Trigger using encapsulated API
		trigger_condition = self.get_entry_condition()
		if trigger_condition:
			try:
				compiled_expression = compiler.compile(trigger_condition)
				self.compiled_expression = compiled_expression
				is_valid, error = compiler.validate(compiled_expression)
				if not is_valid:
					frappe.throw(_("Invalid Trigger Condition: {0}").format(error))
			except ValueError as e:
				frappe.throw(_("Error compiling Trigger Condition: {0}").format(str(e)))
			except Exception as e:
				frappe.throw(_("Error compiling Trigger Condition: {0}").format(str(e)))
		else:
			self.compiled_expression = None

		# Compile Action Conditions
		for action in self.actions:
			if normalize_action_type(action.action_type) != "Condition":
				continue

			condition_payload = get_condition_payload(action)
			if condition_payload is None:
				# Keep strict behavior for malformed/non-empty JSON strings
				raw_config = action.get("config")
				raw_legacy = action.get("condition_json")
				if raw_config not in (None, ""):
					condition_payload = raw_config
				elif raw_legacy not in (None, ""):
					condition_payload = raw_legacy

			if condition_payload in (None, ""):
				action.compiled_expression = None
				continue

			try:
				action.compiled_expression = compiler.compile(condition_payload)

				# Persist canonical payload in config for deprecated-condition_json migration.
				parsed_payload = parse_condition_payload(condition_payload)
				if parsed_payload is not None:
					set_condition_payload_on_action(action, parsed_payload)

				# Validate compiled expression
				is_valid, error = compiler.validate(action.compiled_expression)
				if not is_valid:
					frappe.throw(_("Invalid Condition in Action {0}: {1}").format(action.action_label, error))
			except ValueError as e:
				frappe.throw(
					_("Error compiling Action {0} Condition: {1}").format(action.action_label, str(e))
				)
			except Exception as e:
				frappe.throw(
					_("Error compiling Action {0} Condition: {1}").format(action.action_label, str(e))
				)

	def _validate_action_config(self, action):
		if not frappe.db.exists("Process", action.process_name):
			frappe.throw(_("Process not found: {0}").format(action.process_name))

		process = frappe.get_cached_doc("Process", action.process_name)

		# If operation is set, validate existence and contracts
		if action.operation:
			try:
				op = process.get_operation(action.operation)
				from flexirule.ruleflow.core.process_contract_v2 import (
					resolve_process_operation_contract_v2,
				)

				op_dict = op.as_dict() if hasattr(op, "as_dict") else dict(op)
				resolve_process_operation_contract_v2(
					action.process_name,
					action.operation,
					op_dict,
					strict=True,
				)

				# Validate return_variable mandatory for context-writing operations
				self._validate_return_variable_requirement(action, op)

			except Exception as e:
				frappe.throw(str(e))

	def _validate_return_variable_requirement(self, action, operation):
		"""
		Enforce return_variable is set when operation writes to context.
		"""
		if not operation:
			return

		from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2

		op_dict = operation.as_dict() if hasattr(operation, "as_dict") else operation
		process_name = getattr(action, "process_name", None)
		operation_name = getattr(action, "operation", None)
		if not process_name or not operation_name:
			return
		contract_v2 = resolve_process_operation_contract_v2(
			process_name,
			operation_name,
			op_dict,
			strict=True,
		)
		policy = contract_v2.get("policy") or {}
		requires_return_var = bool(policy.get("require_return_variable"))

		if requires_return_var and not action.return_variable:
			frappe.throw(
				_(
					"Action '{0}' uses operation '{1}' which writes to context. "
					"Please specify a Return Variable Name."
				).format(action.action_label, action.operation)
			)

	def _validate_assignment(self, action):
		"""Validate Assignment action configuration."""
		config_str = action.get("config") if hasattr(action, "get") else getattr(action, "config", "[]")
		if not config_str:
			return

		try:
			assignments = json.loads(config_str)
			if not isinstance(assignments, list):
				frappe.throw(
					_("Action '{0}': Assignment config must be a JSON array").format(action.action_label)
				)
		except Exception:
			frappe.throw(_("Action '{0}': Invalid JSON in Assignment config").format(action.action_label))

		# Validate fields
		for row in assignments:
			target = row.get("target")
			if not target:
				continue

			forbidden_prefixes = ("meta.", "frappe.", "rule.", "caller.")
			if target.startswith(forbidden_prefixes):
				frappe.throw(
					_("Action '{0}': Cannot assign to protected system path '{1}'").format(
						action.action_label, target
					)
				)

			if not (target.startswith("doc.") or target.startswith("vars.")):
				frappe.throw(
					_("Action '{0}': Assignment target '{1}' must start with 'doc.' or 'vars.'").format(
						action.action_label, target
					)
				)

			if target.startswith("doc.") and self.document_type:
				# Validate doc fields similar to Set Value
				field_path = target[4:]  # remove "doc."
				base_field = field_path.split(".")[0]

				meta = frappe.get_meta(self.document_type)
				df = meta.get_field(base_field)
				if not df:
					frappe.throw(
						_("Action '{0}': Field '{1}' does not exist on DocType '{2}'").format(
							action.action_label, base_field, self.document_type
						)
					)

				after_submit_events = ["On Submit", "On Update After Submit"]
				if self.trigger_event in after_submit_events and df:
					if not df.allow_on_submit:
						frappe.throw(
							_(
								"Action '{0}': Cannot set field '{1}' after submit. Field does not have 'Allow on Submit' enabled."
							).format(action.action_label, target)
						)

	def _validate_set_value_editable(self, action):
		"""Check if Set Value target field is valid and editable for current trigger event"""
		target_field = (
			action.get("target_field") if hasattr(action, "get") else getattr(action, "target_field", None)
		)
		if not target_field:
			return

		if not self.document_type:
			return

		# Skip DocType field validation if we are setting a context variable or using a variable path
		mutation_mode = (
			action.get("mutation_mode") if hasattr(action, "get") else getattr(action, "mutation_mode", None)
		)
		if mutation_mode in ["Set Context Variable", "Update Context Variable"] or (
			target_field and str(target_field).startswith("vars.")
		):
			return

		meta = frappe.get_meta(self.document_type)
		df = meta.get_field(target_field)

		if not df:
			frappe.throw(
				_("Action '{0}': Field '{1}' does not exist on DocType '{2}'").format(
					action.action_label, target_field, self.document_type
				)
			)

		# Only check for after-submit events
		after_submit_events = ["On Submit", "On Update After Submit"]
		if self.trigger_event in after_submit_events:
			if not df.allow_on_submit:
				frappe.throw(
					_(
						"Action '{0}': Cannot set field '{1}' after submit. Field does not have 'Allow on Submit' enabled."
					).format(action.action_label, target_field)
				)

	def validate_sub_rule_target(self, action, target_rule_override=None):
		"""Validate that a Sub-Rule action targets a compatible callable rule."""
		if not action.rule:
			return

		if action.rule == self.name or action.rule == getattr(self, "base_rule_name", None):
			frappe.throw(
				_("Action '{0}' cannot reference its own Rule as Sub-Rule.").format(action.action_label)
			)

		if target_rule_override and (
			target_rule_override.base_rule_name == action.rule or target_rule_override.name == action.rule
		):
			target_rule = target_rule_override
		else:
			from flexirule.ruleflow.core.rule_service import resolve_rule_reference

			target_rule_name = resolve_rule_reference(
				action.rule,
				active_only=bool(self.is_active),
				callable_only=True,
				exposed_only=True,
			)
			if not target_rule_name and self.is_active:
				target_rule_name = resolve_rule_reference(
					action.rule,
					active_only=False,
					callable_only=True,
					exposed_only=True,
				)
			if not target_rule_name or not frappe.db.exists("Rule", target_rule_name):
				frappe.throw(_("Action '{0}' references a missing Rule.").format(action.action_label))
			target_rule = frappe.get_cached_doc("Rule", target_rule_name)

		if hasattr(target_rule, "normalize_sub_rule_exposure_flag"):
			target_rule.normalize_sub_rule_exposure_flag()

		if target_rule.trigger_type != "Callable Event":
			frappe.throw(
				_("Action '{0}' must target a Callable Event rule. Selected rule '{1}' uses '{2}'.").format(
					action.action_label, target_rule.name, target_rule.trigger_type
				)
			)

		if not target_rule.is_exposed_as_subrule():
			frappe.throw(
				_(
					"Action '{0}' must target a rule exposed as a sub-rule. Enable 'Exposed As Sub-Rule' on '{1}'."
				).format(action.action_label, target_rule.name)
			)

		is_target_active = target_rule.is_active or (
			target_rule_override and target_rule.name == target_rule_override.name
		)
		if self.is_active and not is_target_active:
			frappe.throw(
				_("Action '{0}' must target an active rule. Activate '{1}' first.").format(
					action.action_label, target_rule.name
				)
			)

		# Callable sub-rules are selected by trigger_type + exposure.
		# Compatibility is evaluated at runtime via target trigger_condition/compiled_expression
		# using caller and document metadata.

	def validate_no_sub_rule_cycles(self):
		"""
		Detect direct or indirect cycles in sub-rule references.

		Uses a single bulk query to build the full sub-rule adjacency graph,
		then runs DFS entirely in-memory. This eliminates the N+1 query pattern
		that previously caused timeouts on large rule graphs (~50+ sub-rules).
		"""
		# Collect sub-rule names referenced by this rule
		sub_rules = set()
		for action in self.actions or []:
			if action.action_type == "Sub-Rule" and action.rule:
				sub_rules.add(action.rule)

		if not sub_rules:
			return  # No sub-rules, no cycles possible

		# Single bulk query: fetch the ENTIRE sub-rule adjacency graph
		all_edges = frappe.db.get_all(
			"Rule Action",
			filters={
				"action_type": "Sub-Rule",
				"rule": ["is", "set"],
			},
			fields=["parent", "rule"],
		)

		# Build in-memory adjacency map: parent_rule → {child_rule, ...}
		# Normalize all parents and children to logical base names for cycle detection
		adjacency: dict[str, set[str]] = {}
		for edge in all_edges:
			if edge.parent and edge.rule:
				logical_parent = re.sub(r"_[vV]\d+$", "", edge.parent)
				logical_child = re.sub(r"_[vV]\d+$", "", edge.rule)
				adjacency.setdefault(logical_parent, set()).add(logical_child)

		# Include this rule's own (possibly unsaved) sub-rule edges
		current_rule_logical = re.sub(r"_[vV]\d+$", "", self.name or self.rule_name or "")
		if current_rule_logical:
			logical_sub_rules = {re.sub(r"_[vV]\d+$", "", r) for r in sub_rules if r}
			adjacency[current_rule_logical] = logical_sub_rules

		# DFS with path tracking — zero additional DB queries
		max_depth = 200  # Depth guard against Python RecursionError

		def dfs_detect_cycle(current_rule, path, globally_visited, depth=0):
			"""DFS with path tracking to detect any cycle."""
			if depth > max_depth:
				return None  # Depth guard: stop exploring unreasonably deep graphs

			if current_rule in path:
				# Cycle detected — build readable cycle path
				cycle_start = path.index(current_rule)
				cycle_path = [*path[cycle_start:], current_rule]
				return " → ".join([str(part) for part in cycle_path if part])

			if current_rule in globally_visited:
				return None  # Already fully explored, no cycle from here

			path.append(current_rule)

			for child in adjacency.get(current_rule, set()):
				if child:
					result = dfs_detect_cycle(child, path.copy(), globally_visited, depth + 1)
					if result:
						return result

			globally_visited.add(current_rule)
			return None

		# Start DFS from this rule
		globally_visited: set[str] = set()
		initial_path = [current_rule_logical]

		for sub_rule in sub_rules:
			if sub_rule:
				logical_sub_rule = re.sub(r"_[vV]\d+$", "", sub_rule)
				cycle = dfs_detect_cycle(logical_sub_rule, initial_path.copy(), globally_visited)
				if cycle:
					frappe.throw(_("Cycle detected in sub-rule graph: {0}").format(cycle))

	def validate_variable_availability(self):
		"""
		Check if variables used in templates are defined before use.
		User requested: throw on undefined variables.
		"""
		if not self.actions:
			return

		action_map = {a.action_id: a for a in self.actions if a.action_id}

		# Find root node
		start_action = None
		for action in self.actions:
			if action.action_id == "root" or action.action_type == "Entry Action":
				start_action = action
				break

		if not start_action:
			return  # No root node, skip validation

		self._validate_variable_paths(
			start_action,
			{"doc", "old_doc", "frappe", "utils", "vars"},
			action_map,
			set(),
		)

	def _validate_variable_paths(self, action, available_vars, action_map, path, depth=0):
		"""Validate template variable usage for every reachable execution path."""
		# Depth guard: prevent Python RecursionError on deeply nested graphs
		if depth > 200:
			return

		action_id = action.action_id or action.name
		if action_id in path:
			return

		self._check_template_variables(action, available_vars)

		next_available = set(available_vars)
		if action.return_variable:
			next_available.add(action.return_variable)

		if action.action_type == "Loop":
			config = self._parse_action_config(action)
			# Use return_variable as alias, fallback to config.alias, then 'item'
			alias = action.return_variable or config.get("alias") or "item"
			next_available.add(alias)
			next_available.add("loop")

		next_path = set(path)
		next_path.add(action_id)

		for next_id in [action.next_step_if_true, action.next_step_if_false]:
			if not next_id:
				continue
			next_action = action_map.get(next_id)
			if next_action:
				self._validate_variable_paths(next_action, next_available, action_map, next_path, depth + 1)

	def _check_template_variables(self, action, available_vars):
		"""Check Jinja template for undefined variable references.

		Uses multiple patterns to catch all variable reference styles:
		  - {{ vars.foo }}         (Jinja dot notation)
		  - {{ vars['foo'] }}      (Jinja bracket notation)
		  - {{ vars.get('foo') }}  (Jinja method call)
		  - vars.foo               (bare expression in compiled conditions)
		"""
		import re

		# Templates to check based on action type
		templates_to_check = []
		if action.action_type == "Assignment":
			# Scan value_template from each assignment row in config JSON
			config_str = getattr(action, "config", "[]") or "[]"
			try:
				assignments = json.loads(config_str) if isinstance(config_str, str) else config_str
			except Exception:
				assignments = []
			for i, a in enumerate(assignments or []):
				tpl = (a.get("value_template") or a.get("value")) if isinstance(a, dict) else None
				if isinstance(tpl, str) and tpl:
					templates_to_check.append((f"assignment[{i}].value_template", tpl))
		elif action.action_type == "Stop" and getattr(action, "operation", None) == "Error":
			templates_to_check.append(("value_template", getattr(action, "value_template", "")))
		elif action.action_type == "Notify":
			templates_to_check.append(("value_template", getattr(action, "value_template", "")))

		# Multiple patterns to catch all variable reference styles
		var_patterns = [
			re.compile(r"\{\{\s*vars\.(\w+)"),  # {{ vars.foo }}
			re.compile(r"\{\{\s*vars\[['\"]?(\w+)"),  # {{ vars['foo'] }} or {{ vars["foo"] }}
			re.compile(r"\bvars\.get\(['\"]?(\w+)"),  # vars.get('foo')
			re.compile(r"(?<!\.)\bvars\.(\w+)"),  # bare vars.foo in expressions
		]

		for _field_name, template in templates_to_check:
			if not template or not isinstance(template, str):
				continue

			# Collect all unique variable names across all patterns
			all_matches = set()
			for pattern in var_patterns:
				all_matches.update(pattern.findall(template))

			for var_name in all_matches:
				if var_name not in available_vars:
					frappe.throw(
						_(
							"Action '{0}' uses undefined variable 'vars.{1}'. "
							"Ensure a previous action sets return_variable='{1}'."
						).format(action.action_label, var_name)
					)

	def on_update(self):
		"""
		Perform heavier checks on update, especially if Active
		"""
		if self.is_active:
			validate_graph_integrity(self)

	def validate_deactivation_safety(self):
		"""
		Ensure that we don't deactivate a sub-rule that active rules depend on,
		unless another version of it is active.
		"""
		if self.is_new():
			return

		if frappe.flags.in_test and not self.flags.run_deactivation_safety_in_test:
			return

		old_doc = self.get_doc_before_save()
		if not old_doc:
			return

		# If transitioning from Active to Inactive
		if old_doc.is_active and not self.is_active:
			# Check if there are other active versions
			other_active_versions = frappe.get_all(
				"Rule",
				filters={"base_rule_name": self.base_rule_name, "is_active": 1, "name": ["!=", self.name]},
				limit=1,
			)
			if not other_active_versions:
				# This is the last active version of this sub-rule. Check active parents.
				refs = frappe.get_all(
					"Rule Action",
					filters={"action_type": "Sub-Rule", "rule": self.base_rule_name},
					fields=["parent"],
				)
				if refs:
					active_parents = []
					for r in refs:
						# If the parent is active and not this rule itself
						if r.parent != self.name and frappe.db.get_value("Rule", r.parent, "is_active"):
							active_parents.append(r.parent)
					if active_parents:
						names = ", ".join(active_parents[:5])
						frappe.throw(
							_(
								"Cannot deactivate Rule '{0}': it is referenced by active parent rules: {1}"
							).format(self.name, names)
						)

	def validate_activation_safety(self):
		"""
		When activating a Callable Event rule (sub-rule), ensure all active parent rules
		remain valid under the new version's schema/interface.
		"""
		if not self.is_active:
			return

		if frappe.flags.in_test and not self.flags.run_activation_safety_in_test:
			return

		# Only validate sub-rules
		if self.trigger_type != "Callable Event" or not self.exposed_as_subrule:
			return

		old_doc = self.get_doc_before_save()
		# Only check if transitioning to active
		if old_doc and old_doc.is_active:
			return

		# Find all active parent rules that call this sub-rule logical name
		parent_actions = frappe.get_all(
			"Rule Action", filters={"action_type": "Sub-Rule", "rule": self.base_rule_name}, fields=["parent"]
		)

		if not parent_actions:
			return

		parent_names = sorted(list({pa.parent for pa in parent_actions if pa.parent}))

		from flexirule.ruleflow.core.validation_service import validate_rule_definition

		for parent_name in parent_names:
			if parent_name == self.name:
				continue

			try:
				parent_doc = frappe.get_doc("Rule", parent_name)
			except Exception:
				continue

			# Only check if parent is active
			if not parent_doc.is_active:
				continue

			# Run validation on the active parent with the current rule as target_rule_override
			result = validate_rule_definition(parent_doc, mode="full", target_rule_override=self)
			if not result.get("valid"):
				errors = "<br>".join(result.get("errors", []))
				frappe.throw(
					_(
						"Cannot activate Sub-Rule '{0}': active parent rule '{1}' would become invalid:<br>{2}"
					).format(self.name, parent_name, errors)
				)

	def validate_single_active_version(self):
		"""Enforce one active version per logical rule lineage."""
		if not self.is_active or not self.base_rule_name:
			return

		if self.flags.skip_single_active_version_validation:
			return

		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.is_active:
			return

		existing_active = frappe.get_all(
			"Rule",
			filters={
				"base_rule_name": self.base_rule_name,
				"is_active": 1,
				"name": ["!=", self.name],
			},
			pluck="name",
			limit=1,
		)
		if existing_active:
			frappe.throw(
				_(
					"Cannot activate Rule '{0}' while '{1}' is already active for logical rule '{2}'. "
					"Use the rule transition action to promote a version safely."
				).format(self.name, existing_active[0], self.base_rule_name)
			)

	def on_trash(self):
		"""
		Cleanup when a rule is deleted:
		1. Block if referenced as sub-rule by another active parent rule (unless other active version exists)
		2. Delete linked Rule Scheduler records
		3. Clear rule cache
		"""
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		# 1. Block if referenced as sub-rule and this is the only active version, or if deleting the whole lineage
		other_active_versions = frappe.get_all(
			"Rule",
			filters={"base_rule_name": self.base_rule_name, "is_active": 1, "name": ["!=", self.name]},
			limit=1,
		)
		if not other_active_versions:
			refs = frappe.get_all(
				"Rule Action",
				filters={"action_type": "Sub-Rule", "rule": self.base_rule_name},
				fields=["parent"],
				limit=5,
			)
			if refs:
				active_parents = []
				for r in refs:
					if frappe.db.get_value("Rule", r.parent, "is_active"):
						active_parents.append(r.parent)
				if active_parents:
					names = ", ".join(active_parents[:5])
					frappe.throw(
						_("Cannot delete Rule '{0}': referenced as sub-rule by active rules: {1}").format(
							self.name, names
						)
					)

		# 2. Delete linked schedulers
		for s in frappe.get_all("Rule Scheduler", filters={"rule": self.name}, pluck="name"):
			frappe.delete_doc("Rule Scheduler", s, force=True)

		# 3. Clear cache
		RuleCoordinator.clear_cache()
