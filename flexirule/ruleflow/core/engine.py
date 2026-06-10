# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Enhanced Rule Engine with:
- Process DocType integration
- Permission-based security
- Retry logic and error handling
- Timeout protection
- Cycle detection
- Comprehensive logging
"""

import json
import time
import traceback
import uuid
from concurrent.futures import TimeoutError as FuturesTimeoutError
from contextlib import contextmanager

import frappe
import jsonschema
from frappe import _
from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate

from flexirule.ruleflow.core.context_manager import ContextManager
from flexirule.ruleflow.core.contracts import (
	get_contract,
	get_effective_action_policy,
	is_release_disabled_action,
	normalize_action_type,
)
from flexirule.ruleflow.core.evaluator import check_link_match
from flexirule.ruleflow.core.exceptions import (
	CycleDetectedError,
	EmptyRuleError,
	MethodExecutionError,
	RuleDisabledError,
)
from flexirule.ruleflow.core.exceptions import TimeoutError as FlexiRuleTimeoutError
from flexirule.ruleflow.core.runtime_eval import eval_condition_bool, eval_value
from flexirule.ruleflow.utils.field_resolver import FieldResolver
from flexirule.ruleflow.utils.mapping import apply_output_mapping
from flexirule.ruleflow.utils.schema_validator import (
	frappe_fields_to_json_schema,
	get_custom_validator,
)

# Configuration constants
MAX_SUB_RULE_DEPTH = 2  # Maximum nesting depth for sub-rule calls


class TimeoutException(Exception):
	"""Internal timeout exception"""

	pass


class ReadOnlyDocument:
	"""Proxy for Document that prevents mutation"""

	def __init__(self, doc):
		object.__setattr__(self, "_doc", doc)

	def __getattr__(self, name):
		return getattr(self._doc, name)

	def __getitem__(self, key):
		return self._doc[key]

	def get(self, key, default=None):
		return self._doc.get(key, default)

	def __setattr__(self, name, value):
		raise frappe.ValidationError("Cannot mutate document in Pure method")

	def __setitem__(self, key, value):
		raise frappe.ValidationError("Cannot mutate document in Pure method")

	def save(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot save document in Pure method")

	def insert(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot insert document in Pure method")

	def delete(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot delete document in Pure method")

	def db_set(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot db_set document in Pure method")

	def run_method(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot run_method on document in Pure method")

	def add_comment(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot add_comment on document in Pure method")

	def queue_action(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot queue_action on document in Pure method")

	@property
	def flags(self):
		import copy

		return copy.deepcopy(self._doc.flags)


@contextmanager
def time_limit(seconds):
	"""
	Context manager for timeout protection.
	Cross-platform compatible (works on Windows/Linux/Mac).
	Sets a flag that can be checked periodically by long-running operations.
	"""
	if seconds <= 0:
		yield
		return

	import threading

	timeout_event = threading.Event()
	timer = threading.Timer(seconds, timeout_event.set)
	timer.start()
	try:
		yield timeout_event
	finally:
		timer.cancel()


# TODO : Explore frappe source code to find if they have a similar implementation and use it instead Introduced for SafeFrappeAPI
class SafeFrappeAPI:
	"""
	Restricted Frappe API proxy for rule condition evaluation.
	Exposes only safe, read-only operations to prevent security issues.
	"""

	def __init__(self):
		# Safe utilities
		self.utils = frappe.utils
		self._dict = frappe._dict

	@property
	def session(self):
		"""Read-only access to frappe.session (current user, roles, etc.)"""
		return frappe.session

	@staticmethod
	def get_roles(user=None):
		"""Read-only: return roles for the given user (or current session user)."""
		return frappe.get_roles(user)

	# Safe read operations
	@staticmethod
	def get_value(doctype, filters, fieldname=None, **kwargs):
		"""Read-only get_value"""
		return frappe.get_value(doctype, filters, fieldname, **kwargs)

	@staticmethod
	def get_all(doctype, filters=None, fields=None, limit_page_length=500, **kwargs):
		"""Read-only get_all with default limit"""
		if "limit" in kwargs:
			limit_page_length = kwargs.pop("limit")
		return frappe.get_all(
			doctype, filters=filters, fields=fields, limit_page_length=limit_page_length, **kwargs
		)

	@staticmethod
	def db_exists(doctype, name):
		"""Check if document exists"""
		return frappe.db.exists(doctype, name)

	@staticmethod
	def get_meta(doctype):
		"""Get doctype metadata"""
		return frappe.get_meta(doctype)

	@staticmethod
	def format_value(value, df=None, doc=None, currency=None):
		"""Format value for display"""
		return frappe.format_value(value, df, doc, currency)

	# Logging (safe)
	@staticmethod
	def log(message):
		"""Log a message"""
		frappe.logger().info(message)

	# Explicitly denied operations (will raise)
	def get_doc(self, *args, **kwargs):
		raise PermissionError("get_doc is not allowed in rule conditions. Use frappe.get_value instead.")

	def new_doc(self, *args, **kwargs):
		raise PermissionError("new_doc is not allowed in rule conditions.")

	def delete_doc(self, *args, **kwargs):
		raise PermissionError("delete_doc is not allowed in rule conditions.")

	def db_set_value(self, *args, **kwargs):
		raise PermissionError("db.set_value is not allowed in rule conditions.")

	@property
	def db(self):
		"""Return restricted db proxy"""
		return self._SafeDB()

	class _SafeDB:
		"""Restricted database operations"""

		def exists(self, doctype, name):
			return frappe.db.exists(doctype, name)

		def get_value(self, doctype, filters, fieldname=None, **kwargs):
			return frappe.db.get_value(doctype, filters, fieldname, **kwargs)

		def get_all(self, doctype, filters=None, fields=None, **kwargs):
			return frappe.db.get_all(doctype, filters=filters, fields=fields, **kwargs)

		# Explicitly deny write operations
		def set_value(self, *args, **kwargs):
			raise PermissionError("db.set_value is not allowed in rule conditions.")

		def sql(self, *args, **kwargs):
			raise PermissionError("db.sql is not allowed in rule conditions.")

		# Transaction control restricted (following Frappe restrict_commit_rollback)
		def commit(self, *args, **kwargs):
			raise PermissionError("db.commit is not allowed during doc event rules.")

		def rollback(self, *args, **kwargs):
			raise PermissionError("db.rollback is not allowed during doc event rules.")

		def add_index(self, *args, **kwargs):
			raise PermissionError("db.add_index is not allowed during doc event rules.")


# Singleton instance
_safe_frappe = SafeFrappeAPI()


class RuleEngine:
	"""
	Production-ready rule execution engine with:
	- Validation and error handling
	- Performance optimization
	- Security enforcement
	- Audit logging
	"""

	def __init__(self, rule_doc, execution_context=None):
		"""
		Args:
		        rule_doc: Rule DocType document
		        execution_context: Dict with user, timestamp, test_mode, etc.
		"""
		if isinstance(rule_doc, str):
			rule_doc = frappe.get_doc("Rule", rule_doc)
		self.rule = rule_doc
		self.actions = [a for a in rule_doc.actions if a.is_enabled]

		self.context = execution_context or {}
		if frappe.flags.in_test and "test_mode" not in self.context:
			self.context["test_mode"] = True

		self.execution_log = []
		self.cache = {}
		self.execution_id = self.context.get("execution_id")
		self.last_execution_payload = None
		self.last_log_enqueued = False

		# Build action maps for fast lookup
		self.action_map_by_id = {a.action_id: a for a in self.actions if a.action_id}
		self.action_map_by_label = {a.action_label: a for a in self.actions}
		self.action_map_by_name = {a.name: a for a in self.actions}

	@staticmethod
	def _get_action_config(action):
		"""Get config JSON from action"""
		config_str = getattr(action, "config", None)
		if not config_str:
			return {}
		try:
			return json.loads(config_str)
		except (json.JSONDecodeError, TypeError):
			return {}

	def execute(self, doc, event_name=None, **kwargs):
		"""
		Execute rule with comprehensive error handling

		Args:
		        doc: Frappe document to process
		        event_name: Trigger event name (e.g. 'Before Save')
		        **kwargs: Additional context variables

		Returns:
		        Execution context with results
		"""
		# Tracking vars
		start_time = time.time()
		status = "Success"
		error_detail = None
		self.path_trace = []
		self.execution_id = self.execution_id or str(uuid.uuid4())
		self.context["execution_id"] = self.execution_id
		self.context["event_name"] = event_name or self.rule.trigger_event
		context = None

		try:
			# Pre-execution validation
			self._validate_execution()

			# Initialize context
			context = self._initialize_context(doc, **kwargs)
			self.context = context

			# Check role-based skipping
			skip_for_roles_docs = self.rule.get("skip_for_roles")
			if skip_for_roles_docs:
				user_roles = frappe.get_roles()
				skip_roles = [row.get("role") for row in skip_for_roles_docs]
				if any(role in user_roles for role in skip_roles):
					self._log(
						"INFO",
						f"Skipping rule execution for user with role(s): {skip_roles}",
					)
					status = "Skipped"
					return context

			# Log start
			self._log("INFO", f"Starting rule execution: {self.rule.name}")

			# Expose execution log to frappe.local for API response
			frappe.local.execution_log = self.execution_log

			# Execute with timeout if configured
			timeout = self.rule.max_execution_time or 30
			context["_timeout"] = timeout
			context["_start_time"] = start_time

			if self.context.get("test_mode"):
				# No timeout in test mode
				result = self._execute_graph(context)
			else:
				with time_limit(timeout):
					result = self._execute_graph(context)

			# Post-execution cleanup
			self._log("INFO", "Rule execution completed successfully")

			return result

		except frappe.PermissionError as e:
			status = "Skipped"
			# Ensure the exact message expected by tests is logged
			self._log("INFO", f"Skipping rule execution: {e}")
			return self.context

		except (TimeoutException, FuturesTimeoutError, FlexiRuleTimeoutError):
			status = "Failed"
			error_msg = _("Rule execution exceeded timeout ({0}s)").format(
				timeout if "timeout" in locals() else "unknown"
			)
			error_detail = traceback.format_exc()
			self._log("ERROR", error_msg)
			raise FlexiRuleTimeoutError(error_msg)

		except Exception as e:
			status = "Failed"
			error_msg = str(e)
			error_detail = traceback.format_exc()
			self._log("ERROR", _("Rule execution failed: {0}").format(error_msg))
			raise

		finally:
			# Persist Log
			duration = time.time() - start_time
			self.last_log_enqueued = self._save_execution_log(
				self._normalize_execution_status(status),
				duration,
				error_detail,
				context=context,
				message=self.execution_log[-1]["message"] if self.execution_log else None,
			)
			self.last_execution_payload = self._build_execution_payload(
				context=context,
				status=self._normalize_execution_status(status),
				duration=duration,
				error_detail=error_detail,
				log_enqueued=self.last_log_enqueued,
			)
			frappe.local.execution_payload = self.last_execution_payload

			# Update last_error on Rule for get_computed_status()
			if not self.context.get("dry_run") and not self.context.get("test_mode"):
				self._update_last_error(error_detail if status == "Failed" else None)

	def _validate_execution(self):
		"""Validate rule is executable"""
		if not self.rule.is_active and not self.context.get("allow_inactive_rule_test"):
			raise RuleDisabledError(_("Rule {0} is disabled").format(self.rule.name))

		if not self.actions:
			raise EmptyRuleError(_("Rule {0} has no enabled actions").format(self.rule.name))

		disabled_actions = [
			a.action_label or a.action_id for a in self.actions if is_release_disabled_action(a.action_type)
		]
		if disabled_actions:
			raise frappe.ValidationError(
				_("Rule {0} contains action types that are not available in this release: {1}").format(
					self.rule.name, ", ".join(disabled_actions)
				)
			)

		# Check Rule Permission table if defined
		rule_permissions = self.rule.get("permissions")
		if rule_permissions:
			user_roles = set(frappe.get_roles())
			# System Manager always bypasses
			if "System Manager" not in user_roles:
				can_exec = any(p.can_execute and p.role in user_roles for p in rule_permissions)
				if not can_exec:
					raise frappe.PermissionError(
						_("User does not have execute permission for rule {0}").format(self.rule.name)
					)

	def _initialize_context(self, doc, **kwargs):
		meta_overrides = kwargs.pop("meta", None) if isinstance(kwargs, dict) else None
		vars_payload = kwargs.pop("vars", None) if isinstance(kwargs, dict) else None
		if not isinstance(vars_payload, dict):
			vars_payload = self.context.get("vars", {})
		if not isinstance(vars_payload, dict):
			vars_payload = {}

		base_meta = {
			"rule": self.rule.name,
			"rule_version": self.rule.version,
			"engine_version": "1.0",
			"user": frappe.session.user,
			"timestamp": frappe.utils.now(),
			"test_mode": self.context.get("test_mode", False),
			"execution_id": self.execution_id,
		}
		if isinstance(meta_overrides, dict):
			base_meta.update(meta_overrides)

		if isinstance(doc, dict):
			doc = frappe._dict(doc)

		return {
			**self.context,
			"doc": doc,
			"frappe": self._get_safe_frappe_api(),
			"vars": vars_payload,
			"meta": base_meta,
			"stop": False,
			**kwargs,
		}

	def _get_safe_frappe_api(self):
		"""Return a restricted frappe API object for condition evaluation"""
		return _safe_frappe

	def _execute_graph(self, context):
		"""Execute action graph with cycle detection and loop support"""

		# Change strict cycle detection to visit counting for loops
		node_visits: dict[str, int] = {}  # node_id -> count
		max_visits_per_node = 100  # Safety for infinite loops

		execution_path = []
		start_time = context.get("_start_time", time.time())
		current = self._get_start_node()
		max_iterations = 1000  # Total step limit

		for _iteration in range(max_iterations):
			# Internal timeout check
			if "_timeout" in context and "_start_time" in context and not context.get("test_mode"):
				if time.time() - context["_start_time"] > context["_timeout"]:
					raise FlexiRuleTimeoutError(
						_("Rule execution exceeded timeout of {0}s").format(context["_timeout"])
					)

			if not current:
				self._log("INFO", _("Reached end of flow (no next action)"))
				break

			if context.get("stop"):
				self._log("INFO", _("Flow stopped by action"))
				break

			# Cycle/Loop detection
			node_id = current.action_id or current.name

			# Track visits
			visits = node_visits.get(node_id, 0) + 1
			node_visits[node_id] = visits

			if visits > max_visits_per_node:
				raise CycleDetectedError(
					_("Infinite loop detected: Action {0} visited {1} times").format(
						current.action_label, visits
					)
				)

			execution_path.append(current.action_label)
			step_start_time = time.time()
			path_entry = {
				"action": current.action_label,
				"action_id": current.action_id or current.name,
				"type": current.action_type,
				"timestamp": step_start_time,
				"status": "running",
			}
			self.path_trace.append(path_entry)

			# Log execution
			self._log(
				"INFO",
				_("Executing action: {0} (type: {1})").format(current.action_label, current.action_type),
			)

			try:
				# Use Strategy Pattern with Handler Registry
				from flexirule.ruleflow.core.action_handlers import HandlerRegistry

				handler = HandlerRegistry.get(normalize_action_type(current.action_type))
				if not handler:
					self._log(
						"WARNING",
						_("Unknown action type: {0}").format(current.action_type),
					)
					result = None
					next_id = current.next_step_if_true
				else:
					# Execute handler - returns (result, next_id)
					result, next_id = handler.execute(current, context, self)

				step_end_time = time.time()
				duration_ms = round((step_end_time - step_start_time) * 1000, 2)

				# Store result in path trace
				try:
					path_entry["result"] = result
					path_entry["status"] = "success"
					path_entry["duration_ms"] = duration_ms
				except Exception:
					pass

				# Enhance path trace with result/inputs for Process
				if current.action_type == "Process":
					# Use JSON serialization for output if possible (better for JS UI)
					try:
						path_entry["output"] = json.dumps(result, default=str)
					except Exception:
						path_entry["output"] = str(result)
					try:
						path_entry["input"] = self._get_action_config(current)
					except Exception:
						pass

				# Shared post-processing (output mapping, return validation, mutation)
				self._post_process_action_result(current, result, context)

				# Move to next node
				current = self._get_action_by_id(next_id) if next_id else None

			except Exception as e:
				step_end_time = time.time()
				duration_ms = round((step_end_time - step_start_time) * 1000, 2)
				try:
					path_entry["status"] = "error"
					path_entry["error"] = str(e)
					path_entry["duration_ms"] = duration_ms
				except Exception:
					pass
				# Handle error based on on_error setting
				if hasattr(current, "on_error"):
					if current.on_error == "Continue":
						self._log(
							"WARNING",
							_("Error in action {0}, continuing: {1}").format(current.action_label, str(e)),
						)
						current = self._get_action_by_id(current.next_step_if_true)
						continue
					elif current.on_error == "Retry":
						# Fix 4: Implement Retry with exponential backoff
						retry_count = getattr(current, "retry_count", 3) or 3
						retry_key = f"_retry_{current.action_id or current.name}"
						current_attempt = context.get("vars", {}).get(retry_key, 0)

						if current_attempt < retry_count:
							# Increment retry counter
							context.setdefault("vars", {})[retry_key] = current_attempt + 1
							wait_time = 2**current_attempt  # Exponential backoff
							self._log(
								"WARNING",
								_("Error in action {0}, retrying ({1}/{2}) after {3}s: {4}").format(
									current.action_label,
									current_attempt + 1,
									retry_count,
									wait_time,
									str(e),
								),
							)
							if context.get("_in_sync_hook"):
								raise frappe.ValidationError(
									f"Cannot retry action {current.action_label} inside a synchronous hook"
								)
							time.sleep(wait_time)
							continue  # Retry same action
						else:
							self._log(
								"ERROR",
								_("Error in action {0}, max retries ({1}) exceeded: {2}").format(
									current.action_label, retry_count, str(e)
								),
							)
							raise
					elif current.on_error == "Rollback":
						# Fix 5: Use savepoint instead of full rollback
						savepoint_name = f"flexirule_action_{current.action_id or current.name}"
						self._log(
							"ERROR",
							_("Error in action {0}, rolling back to savepoint: {1}").format(
								current.action_label, str(e)
							),
						)
						try:
							frappe.db.rollback(save_point=savepoint_name)
						except Exception:
							# Savepoint might not exist, log and continue to raise
							self._log("WARNING", _("Savepoint rollback failed, raising error"))
						raise
					elif current.on_error == "Escalate":
						self._log(
							"ERROR",
							_("Error in action {0}, escalating: {1}").format(current.action_label, str(e)),
						)
						raise

				# Default: stop on error
				self._log(
					"ERROR",
					_("Error in action {0}: {1}").format(current.action_label, str(e)),
				)
				raise

		if _iteration >= max_iterations - 1:
			raise CycleDetectedError(_("Max total iterations ({0}) exceeded").format(max_iterations))

		self._log("INFO", _("Execution path: {0}").format(" → ".join(execution_path)))
		return context

	def _get_start_node(self):
		"""Get the first action to execute (one with no incoming edges)"""
		# 1. Look for explicit Root / Entry Action
		for action in self.actions:
			if action.action_id == "root" or action.action_type == "Entry Action":
				self._log(
					"INFO",
					_("Start node: {0} ({1})").format(action.action_label, action.action_id),
				)
				return action

		# 2. Backward compatibility: Find action with no incoming edges
		has_incoming = set()

		for action in self.actions:
			action_id = action.action_id or action.name

			# Check all actions' next_step fields
			for other in self.actions:
				if other.next_step_if_true == action_id:
					has_incoming.add(action_id)
				if other.next_step_if_false == action_id:
					has_incoming.add(action_id)

				# Check Switch cases for incoming edges
				if other.action_type == "Switch":
					try:
						switch_config = self._get_action_config(other)
						for target_id in switch_config.get("cases", {}).values():
							if target_id == action_id:
								has_incoming.add(action_id)
					except Exception:
						pass

		# Find action with no incoming edges (true start node)
		for action in self.actions:
			action_id = action.action_id or action.name
			if action_id not in has_incoming:
				self._log(
					"INFO",
					_("Start node (deduced): {0} ({1})").format(action.action_label, action_id),
				)
				return action

		# Fallback to first action if no clear start
		self._log("WARNING", _("No clear start node, using first action"))
		return self.actions[0] if self.actions else None

	def _get_action_by_id(self, action_id):
		"""Get action by ID (supports action_id, name, or label)"""
		if not action_id:
			return None

		# Try different lookup methods
		return (
			self.action_map_by_id.get(action_id)
			or self.action_map_by_name.get(action_id)
			or self.action_map_by_label.get(action_id)
		)

	# Legacy _execute_* methods removed - now using Handler Strategy Pattern
	# See flexirule/ruleflow/core/action_handlers/ for implementations

	def _build_eval_locals(self, context):
		"""Build safe locals for expression evaluation."""
		doc = context.get("doc")
		if isinstance(doc, dict):
			doc = frappe._dict(doc)
		old_doc = context.get("old_doc")
		if isinstance(old_doc, dict):
			old_doc = frappe._dict(old_doc)
		rule_meta = context.get("rule") or {
			"name": self.rule.name,
			"trigger_type": self.rule.trigger_type,
			"trigger_event": context.get("event_name") or self.rule.trigger_event,
			"document_type": self.rule.document_type,
		}
		caller_meta = context.get("caller")
		if not isinstance(caller_meta, dict):
			meta_ctx = context.get("meta", {}) or {}
			caller_meta = {
				"name": meta_ctx.get("caller_rule"),
				"trigger_type": meta_ctx.get("caller_trigger_type"),
				"trigger_event": meta_ctx.get("caller_trigger_event"),
				"document_type": meta_ctx.get("caller_document_type"),
			}
		doctype_name = (
			context.get("doctype")
			or rule_meta.get("document_type")
			or getattr(doc, "doctype", None)
			or self.rule.document_type
		)

		def _get_meta(doctype):
			if not doctype:
				return None
			try:
				return frappe.get_meta(doctype)
			except Exception:
				return None

		def _is_submittable(doctype):
			meta = _get_meta(doctype)
			return bool(getattr(meta, "is_submittable", 0)) if meta else False

		def _has_field(doctype, fieldname):
			meta = _get_meta(doctype)
			return bool(meta and fieldname and meta.has_field(fieldname))

		def _length_of(value):
			if value is None:
				return 0
			if isinstance(value, str):
				return len(value.strip())
			if isinstance(value, list | tuple | dict | set):
				return len(value)
			try:
				return len(value)
			except Exception:
				return 0

		def _is_empty_value(value):
			if value is None:
				return True
			if isinstance(value, str):
				return value.strip() == ""
			if isinstance(value, list | tuple | dict | set):
				return len(value) == 0
			return False

		return {
			"doc": doc,
			"old_doc": old_doc,
			"vars": context.get("vars", {}),
			"item": context.get("item"),
			"loop": context.get("loop"),
			"frappe": context.get("frappe", _safe_frappe),
			"caller": frappe._dict(caller_meta or {}),
			"rule": frappe._dict(rule_meta or {}),
			"doctype": doctype_name,
			"is_submittable": _is_submittable,
			"has_field": _has_field,
			"get_meta": _get_meta,
			"resolve": FieldResolver.resolve,
			"check_link_match": check_link_match,
			"length_of": _length_of,
			"is_empty_value": _is_empty_value,
			"any": any,
			"all": all,
			"True": True,
			"False": False,
			"None": None,
		}

	def _evaluate_python_condition(self, expression, context):
		"""Evaluate Python expression safely and coerce to bool.

		``NameError`` is always re-raised so that missing helper functions
		or undefined variables surface as visible failures rather than
		silently returning False.
		"""
		if not expression:
			return True

		safe_locals = self._build_eval_locals(context)

		try:
			return eval_condition_bool(expression, safe_locals, default=False)
		except NameError:
			self._log(
				"ERROR", f"Condition evaluation failed — undefined name in expression: {expression[:200]}"
			)
			raise
		except Exception as e:
			self._log("ERROR", f"Condition evaluation failed: {e}")
			return False

	def _evaluate_python_value(self, expression, context, default=None):
		"""Evaluate Python expression safely and return raw value.

		``NameError`` is always re-raised so that missing helper functions
		or undefined variables surface as visible failures.
		"""
		if not expression:
			return default

		safe_locals = self._build_eval_locals(context)

		try:
			return eval_value(expression, safe_locals, default=default)
		except NameError:
			self._log("ERROR", f"Value evaluation failed — undefined name in expression: {expression[:200]}")
			raise
		except Exception as e:
			self._log("ERROR", f"Value evaluation failed: {e}")
			return default

	def _post_process_action_result(self, action, result, context):
		"""
		Apply shared post-processing:
		- Output mapping (result -> context)
		- Return variable storage + type/key validation
		- Mutation mode application
		"""
		cm = ContextManager(context)
		operation_result = None

		# Special Case: If result is a dict with 'columns' and 'result',
		# extract the actual data list for mapping, validation and storage.
		validation_result = result
		if (
			getattr(action, "action_type", None) == "Process"
			and isinstance(result, dict)
			and "status" in result
			and "data" in result
		):
			operation_result = result
			status = (operation_result.get("status") or "success").lower()
			if status == "failed":
				errors = operation_result.get("errors") or []
				raise MethodExecutionError(
					errors[0]
					if errors
					else _("Process operation failed for action {0}").format(action.action_label)
				)
			if status == "skipped":
				validation_result = None
			else:
				validation_result = operation_result.get("data")
		if isinstance(result, dict) and "columns" in result and "result" in result:
			validation_result = result["result"]

		# 1. Output Mapping (Result -> Context)
		action_config_raw = frappe.parse_json(getattr(action, "config", "{}") or "{}")
		action_config = action_config_raw if isinstance(action_config_raw, dict) else {}
		output_mapping = action_config.get("output_mapping")
		if output_mapping:
			if getattr(action, "is_async", 0):
				raise MethodExecutionError(_("Async actions cannot map outputs"))
			apply_output_mapping(validation_result, output_mapping, context)

		# 2. Return Variable + Type/Schema Validation
		return_variable = getattr(action, "return_variable", None)
		return_type = getattr(action, "return_type", None)
		resolved_output_schema = getattr(action, "resolved_output_schema", None)
		process_operation_def = None
		if (
			getattr(action, "action_type", None) == "Process"
			and getattr(action, "process_name", None)
			and getattr(action, "operation", None)
		):
			try:
				process_doc = frappe.get_cached_doc("Process", action.process_name)
				process_operation = process_doc.get_operation(action.operation)
				if process_operation:
					process_operation_def = (
						process_operation.as_dict()
						if hasattr(process_operation, "as_dict")
						else dict(process_operation)
					)
			except Exception:
				process_operation_def = None

		effective_policy = get_effective_action_policy(
			getattr(action, "action_type", None),
			operation=getattr(action, "operation", None),
			process_operation=process_operation_def,
		)
		allowed_return_types = effective_policy.get("allowed_return_types") or []
		if return_type and allowed_return_types and return_type not in allowed_return_types:
			raise MethodExecutionError(
				_("Return Type '{0}' is not allowed for {1} / {2}").format(
					return_type,
					getattr(action, "action_type", _("Action")),
					getattr(action, "operation", _("default")),
				)
			)

		if return_variable and validation_result is not None:
			cm.set_variable(return_variable, validation_result, return_type)

			# Optional return keys validation
			expected_keys = []
			if resolved_output_schema:
				try:
					expected_keys = (
						json.loads(resolved_output_schema)
						if isinstance(resolved_output_schema, str)
						else resolved_output_schema
					)
				except Exception:
					self._log("WARNING", _("Invalid Return Keys Schema JSON for {0}").format(return_variable))
					expected_keys = []

			if expected_keys:
				cm.validate_return_keys(validation_result, expected_keys, return_variable)

		# 3. Mutation Mode (Result -> Doc/Context/DB)
		mutation_mode = getattr(action, "mutation_mode", None)
		if mutation_mode:
			contract = get_contract(action.action_type)
			allowed = effective_policy.get("allowed_mutations") or contract.get("allowed_mutations")
			if not allowed:
				# Ignore mutation_mode for action types that don't declare it
				raise MethodExecutionError(
					_("Mutation mode is not supported for action type '{0}'").format(action.action_type)
				)
			if mutation_mode not in allowed:
				raise MethodExecutionError(
					_("Mutation mode '{0}' is not allowed for action type '{1}'").format(
						mutation_mode, action.action_type
					)
				)
			if not return_variable:
				raise MethodExecutionError(
					_("Mutation Mode '{0}' requires a Return Variable Name").format(mutation_mode)
				)
			cm.apply_mutation(mutation_mode, return_variable, validation_result, context)

		# 4. Declarative Runtime v2 mutation intents
		if operation_result:
			self._apply_operation_result_mutations(action, operation_result, context)

	def _apply_operation_result_mutations(self, action, operation_result: dict, context: dict):
		"""Apply mutation intents returned by declarative process adapters."""
		mutations = operation_result.get("mutations") or []
		if not isinstance(mutations, list):
			return

		allowed = set(
			get_effective_action_policy("Process", operation=getattr(action, "operation", None)).get(
				"allowed_mutations"
			)
			or []
		)
		cm = ContextManager(context)
		for mutation in mutations:
			if not isinstance(mutation, dict):
				continue
			mode = mutation.get("mutation_mode")
			target = mutation.get("target")
			value = mutation.get("value")
			if not mode or not target:
				continue
			if allowed and mode not in allowed:
				raise MethodExecutionError(
					_("Mutation mode '{0}' is not allowed for action '{1}'").format(mode, action.action_label)
				)
			cm.apply_mutation(mode, target, value, context)

	# Legacy _execute_* methods have been removed.
	# All action execution now uses the Handler Strategy Pattern.
	# See flexirule/ruleflow/core/action_handlers/ for implementations.

	def _call_process_with_retry(self, process_doc, operation, config, context, retry_count, timeout):
		"""Execute new Process with retry logic and runtime contract enforcement"""
		last_error = None

		# Get operation metadata for contract enforcement
		op_def = None
		try:
			op_def = process_doc.get_operation(operation)
		except Exception:
			pass  # Operation might not exist in child table

		# 1. Runtime Contract: requires_doc
		if op_def and op_def.requires_doc:
			if not context.get("doc"):
				raise MethodExecutionError(
					_("Operation {0} requires a document but context.doc is not set").format(operation)
				)

		# 2. Runtime Contract: writes_to Document check in restricted events
		if op_def and op_def.writes_to == "Document":
			event_name = context.get("event_name")
			after_events = [
				"After Insert",
				"After Save",
				"On Submit",
				"Before Cancel",
				"On Cancel",
				"On Trash",
				"On Update After Submit",
				"On Change",
			]
			if event_name in after_events:
				self._log(
					"WARNING",
					_(
						"Operation {0} writes to Document in an 'After' event ({1}). "
						"This may cause inconsistent state or recursive triggers."
					).format(operation, event_name),
				)

		# 3. Runtime Contract: has_side_effect in transactional context
		if op_def and op_def.has_side_effect:
			self._log("INFO", _("Executing operation {0} with side effects").format(operation))

		for attempt in range(retry_count + 1):
			try:
				if attempt > 0:
					self._log(
						"INFO",
						_("Retry attempt {0}/{1} for {2}:{3}").format(
							attempt, retry_count, process_doc.name, operation
						),
					)

				# 2. Runtime Contract: transactional (wrap in savepoint)
				use_savepoint = op_def and op_def.transactional
				savepoint_name = f"process_{process_doc.name}_{operation}_{attempt}"

				if use_savepoint:
					frappe.db.savepoint(savepoint_name)

				try:
					# Call the Process execute method
					result = process_doc.execute(context, func=operation, config=config)

					# 3. Runtime Contract: output_schema validation
					if op_def and op_def.output_schema:
						self._validate_output_against_schema(result, op_def.output_schema, operation)

					if use_savepoint:
						frappe.db.release_savepoint(savepoint_name)

					return result

				except Exception:
					if use_savepoint:
						try:
							frappe.db.rollback(save_point=savepoint_name)
							self._log(
								"INFO",
								_("Rolled back to savepoint for {0}:{1}").format(process_doc.name, operation),
							)
						except Exception:
							pass  # Savepoint might not exist
					raise

			except Exception as e:
				last_error = e
				self._log(
					"ERROR",
					_("Process execution failed (attempt {0}): {1}").format(attempt + 1, str(e)),
				)
				if attempt < retry_count:
					time.sleep(2**attempt)
				else:
					break

		raise MethodExecutionError(
			_("Process {0}:{1} failed after {2} attempts: {3}").format(
				process_doc.name, operation, retry_count + 1, str(last_error)
			)
		)

	def _validate_output_against_schema(self, result, output_schema, operation_name):
		"""
		Validate execution result against output_schema.
		Logs warning if schema validation fails (doesn't throw to avoid breaking existing rules).
		"""
		if not output_schema:
			return

		try:
			schema = json.loads(output_schema) if isinstance(output_schema, str) else output_schema

			if not schema or not schema.get("properties"):
				return

			# Basic validation: check required fields exist in result
			if schema.get("required") and isinstance(result, dict):
				for field in schema["required"]:
					if field not in result:
						self._log(
							"WARNING",
							_("Operation {0} output missing required field: {1}").format(
								operation_name, field
							),
						)

			# Type check for top-level result
			expected_type = schema.get("type")
			if expected_type:
				actual_type = type(result).__name__
				type_map = {
					"object": (dict,),
					"array": (list, tuple),
					"string": (str,),
					"number": (int, float),
					"integer": (int,),
					"boolean": (bool,),
					"null": (type(None),),
				}
				if expected_type in type_map:
					if not isinstance(result, type_map[expected_type]):
						self._log(
							"WARNING",
							_("Operation {0} output type mismatch: expected {1}, got {2}").format(
								operation_name, expected_type, actual_type
							),
						)

		except Exception as e:
			self._log(
				"WARNING",
				_("Failed to validate output_schema for {0}: {1}").format(operation_name, str(e)),
			)

	def _log(self, level, message):
		"""Add entry to execution log"""
		entry = {"timestamp": frappe.utils.now(), "level": level, "message": message}
		self.execution_log.append(entry)

		# Also log to console if debug mode
		if self.rule.debug_mode or self.context.get("test_mode"):
			frappe.logger().info(f"[{self.rule.name}] [{level}] {message}")

	def _update_last_error(self, error=None):
		"""Update last_error on Rule for get_computed_status(). Non-blocking."""
		try:
			frappe.db.set_value(
				"Rule",
				self.rule.name,
				"last_error",
				error,
				update_modified=False,
			)
		except Exception as e:
			frappe.logger().error(f"Failed to update rule last_error: {e!s}")

	def _normalize_execution_status(self, status):
		"""Map internal execution states to persisted terminal states."""
		if status in ("Success", "Failed", "Stopped"):
			return status
		if status == "Skipped":
			return "Stopped"
		return "Failed"

	def _build_trigger_source(self, active_context):
		"""Build a stable execution source label for audit logs."""
		if not active_context:
			return f"Rule: {self.rule.name}"

		scheduler_name = active_context.get("scheduler")
		if scheduler_name:
			return f"Scheduler: {scheduler_name}"

		doc = active_context.get("doc")
		event_name = active_context.get("event_name") or active_context.get("meta", {}).get("event_name")
		if doc and event_name:
			return f"Doc Event: {doc.doctype}/{doc.name} [{event_name}]"
		if doc:
			return f"Doc: {doc.doctype}/{doc.name}"

		return f"Rule: {self.rule.name}"

	def _should_include_doc_snapshot(self, active_context):
		"""Return whether execution logs may persist the full document snapshot."""
		if self.rule.debug_mode:
			return True

		if active_context and (
			active_context.get("include_doc_snapshot") or active_context.get("full_context_snapshot")
		):
			return True

		try:
			settings = frappe.get_cached_doc("RuleFlow Settings")
			return bool(getattr(settings, "enable_debug_logging", 0))
		except Exception:
			return False

	def _build_context_snapshot(self, active_context):
		"""Build the persisted context snapshot according to the log data policy."""
		if not active_context:
			return {}

		context_snapshot = {
			k: v
			for k, v in active_context.get("vars", {}).items()
			if isinstance(v, str | int | float | bool | list | dict | type(None))
		}

		if active_context.get("doc") and self._should_include_doc_snapshot(active_context):
			try:
				context_snapshot["doc"] = active_context["doc"].as_dict()
			except Exception:
				context_snapshot["doc"] = "<Not Serializable>"

		return context_snapshot

	def _save_execution_log(self, status, duration, error_trace=None, context=None, message=None):
		"""Save execution details to Rule Execution Log"""
		try:
			active_context = context or getattr(self, "context", {})
			context_snapshot = self._build_context_snapshot(active_context)

			# Handle Local Documents (New Docs)
			# If we rollback, the doc might disappear, so the link will be broken.
			# We still save the name for reference.
			doc = active_context.get("doc") if active_context else None
			doc_name = doc.name if doc else None

			if doc and doc.get("__islocal"):
				# If it's local, it might not exist after rollback
				pass

			message_text = message or (
				error_trace.split("\n")[-2] if error_trace else _("Executed successfully")
			)

			log_doc = frappe.get_doc(
				{
					"doctype": "Rule Execution Log",
					"rule": self.rule.name,
					"execution_id": self.execution_id,
					"rule_version": self.rule.version,
					"status": status,
					"duration": duration,
					"trigger_source": self._build_trigger_source(active_context),
					"reference_doctype": doc.doctype if doc else self.rule.document_type,
					"reference_docname": doc_name,
					"executed_by": (
						active_context.get("meta", {}).get("user") if active_context else frappe.session.user
					),
					"message": message_text,
					"execution_path": json.dumps(self.path_trace, default=str),
					"context_snapshot": json.dumps(context_snapshot, default=str),
					"error_trace": error_trace,
					# Batch / Scheduler fields from context
					"scheduler": active_context.get("scheduler"),
					"batch_id": active_context.get("batch_id"),
					"batch_index": active_context.get("batch_index"),
					"batch_total": active_context.get("batch_total"),
				}
			)
			log_data = log_doc.as_dict()
			log_data.pop("name", None)
			self.last_execution_log_payload = log_data

			# PERSISTENCE LOGIC
			# Enqueue all logs to avoid adding writes to the user's transaction.
			# Failed logs are still persisted even if the main transaction rolls back.
			skip_log_enqueue = bool(
				(self.context or {}).get("skip_log_enqueue") or (active_context or {}).get("skip_log_enqueue")
			)
			if self.context.get("dry_run") or skip_log_enqueue:
				return False
			else:
				frappe.enqueue(
					"flexirule.ruleflow.utils.logging.persist_execution_log",
					queue="short",
					now=frappe.flags.in_test,
					log_data=log_data,
				)
				return True

		except Exception as e:
			# Fallback if logging itself fails
			frappe.logger().error(f"Failed to save Rule Execution Log: {e!s}")
			return False

	def _build_execution_payload(self, context, status, duration, error_detail, log_enqueued):
		"""Build deterministic execution payload for API/UI consumers."""
		active_context = context or self.context or {}
		vars_snapshot = {}
		for key, value in (active_context.get("vars") or {}).items():
			if isinstance(value, str | int | float | bool | list | dict | type(None)):
				vars_snapshot[key] = value
			else:
				vars_snapshot[key] = str(value)

		messages = [entry.get("message") for entry in self.execution_log if entry.get("message")]
		errors = [entry.get("message") for entry in self.execution_log if entry.get("level") == "ERROR"]
		if error_detail:
			errors.append(error_detail)

		return {
			"execution_id": self.execution_id,
			"status": status,
			"duration": duration,
			"path_trace": list(self.path_trace or []),
			"vars": vars_snapshot,
			"messages": messages,
			"errors": errors,
			"log_enqueued": bool(log_enqueued),
		}
