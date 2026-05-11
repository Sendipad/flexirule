# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
RuleCoordinator - Main entry point for rule execution
Finds applicable rules and dispatches them to appropriate executors
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Any, ClassVar, cast

import frappe
from frappe import _
from frappe.utils import cint


class RuleCoordinator:
	"""Coordinates rule loading, filtering, and execution"""

	# Compiled runtime registry (Redis)
	CACHE_KEY = "flexirule_runtime_registry_v2"
	CACHE_VERSION = 2

	# Request-local memoization keys
	LOCAL_REGISTRY_KEY = "flexirule_runtime_registry"
	LOCAL_RUNTIME_KEY = "flexirule_runtime_doctype_runtime"
	LOCAL_REENTRY_STACK_KEY = "flexirule_runtime_reentry_stack"
	LOCAL_CHANGED_FIELDS_KEY = "flexirule_runtime_changed_fields"

	# Registry-relevant fields on Rule
	RUNTIME_SIGNATURE_FIELDS: ClassVar[set[str]] = {
		"is_active",
		"trigger_type",
		"document_type",
		"trigger_event",
		"priority",
		"compiled_expression",
		"execution_mode",
		"debug_mode",
	}

	BLOCKING_EVENTS: ClassVar[set[str]] = {
		"Before Naming",
		"Before Insert",
		"Before Save",
		"Validate",
		"Before Submit",
		"On Submit",
		"Before Cancel",
		"On Cancel",
		"On Trash",
		"On Update After Submit",
		"Before Rename",
		"After Rename",
		"Before Print",
	}

	FIELD_FILTER_EVENTS: ClassVar[set[str]] = {
		"Before Save",
		"Validate",
		"After Save",
		"On Update After Submit",
		"On Change",
	}

	COMPILED_FIELD_PATTERNS: ClassVar[tuple[re.Pattern[str], ...]] = (
		re.compile(r"\b(?:doc|old_doc)\.([A-Za-z_][A-Za-z0-9_]*)"),
		re.compile(r"\b(?:doc|old_doc)\.get\(\s*['\"]([^'\"]+)['\"]"),
		re.compile(r"\bresolve\(\s*(?:doc|old_doc)\s*,\s*['\"]([^'\"]+)['\"]"),
	)

	IGNORED_DOC_ATTRS: ClassVar[set[str]] = {
		"doctype",
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"flags",
	}

	@staticmethod
	def execute_rule(rule: Any, context: dict | None = None, dry_run: bool = False) -> dict:
		"""
		Pure execution API for a single rule.
		Can be used for replay, dry-runs, and deterministic testing.

		Args:
		    rule: Rule name or Rule document
		    context: Execution context (doc, vars, etc.)
		    dry_run: If True, wraps execution in a transaction that is rolled back.

		Returns:
		    Final execution context
		"""
		if isinstance(rule, str):
			rule = frappe.get_doc("Rule", rule)

		context = context or {}
		doc = context.get("doc")

		if not doc:
			frappe.throw(_("Document is required for rule execution"))

		# Convert to Document object if it's a dict/string (for API calls)
		if isinstance(doc, dict) and doc.get("doctype") and doc.get("name"):
			doc = frappe.get_doc(doc.get("doctype"), doc.get("name"))
			context["doc"] = doc
		elif isinstance(doc, str):
			# If doc is just name, try to use rule's document_type
			if rule.document_type:
				doc = frappe.get_doc(rule.document_type, doc)
				context["doc"] = doc
			else:
				frappe.throw(_("Cannot resolve document from name without document type"))

		from flexirule.ruleflow.core.engine import RuleEngine

		def _run():
			engine = RuleEngine(rule, execution_context=context)
			# Ensure engine knows about dry_run (it can use it for logging/behavior)
			engine.context["dry_run"] = dry_run
			return engine.execute(doc, event_name=rule.trigger_event)

		if dry_run:
			savepoint_name = "flexirule_dry_run"
			try:
				frappe.db.savepoint(savepoint_name)
				result = _run()
				return result
			finally:
				frappe.db.rollback(save_point=savepoint_name)
		else:
			return _run()

	@staticmethod
	def _get_local_dict(attr: str) -> dict:
		store = getattr(frappe.local, attr, None)
		if not isinstance(store, dict):
			store = {}
			setattr(frappe.local, attr, store)
		return store

	@staticmethod
	def _get_local_set(attr: str) -> set:
		store = getattr(frappe.local, attr, None)
		if not isinstance(store, set):
			store = set()
			setattr(frappe.local, attr, store)
		return store

	@staticmethod
	def _normalized_priority(value: Any) -> int:
		try:
			return int(value)
		except Exception:
			return 0

	@staticmethod
	def _is_active_value(value: Any) -> bool:
		return cint(value) == 1

	@staticmethod
	def _extract_watched_fields(compiled_expression: str | None) -> list[str]:
		"""Extract direct doc field dependencies for fast change filtering."""
		if not compiled_expression:
			return []

		fields: set[str] = set()
		for pattern in RuleCoordinator.COMPILED_FIELD_PATTERNS:
			for match in pattern.findall(compiled_expression):
				if not match:
					continue
				field = str(match).strip()
				if not field or field in RuleCoordinator.IGNORED_DOC_ATTRS:
					continue
				fields.add(field)

		return sorted(fields)

	@staticmethod
	def _build_runtime_registry() -> dict:
		"""Build immutable compiled registry from DB (only invoked on cache miss/rebuild)."""
		rules_index: dict[str, dict[str, Any]] = {}
		event_map: dict[str, dict[str, list[str]]] = {}
		registry: dict[str, Any] = {
			"cache_version": RuleCoordinator.CACHE_VERSION,
			"rules": rules_index,
			"doctype_event_map": event_map,
		}

		runtime_fields = [
			"name",
			"document_type",
			"trigger_event",
			"priority",
			"compiled_expression",
			"trigger_condition",
			"execution_mode",
			"debug_mode",
		]
		try:
			if frappe.get_meta("Rule").has_field("watched_fields") and frappe.db.has_column(
				"Rule", "watched_fields"
			):
				runtime_fields.append("watched_fields")
		except Exception:
			pass

		active_rules = frappe.get_all(
			"Rule",
			filters={"is_active": 1, "trigger_type": "DocType Event"},
			fields=runtime_fields,
			order_by="priority desc, modified desc",
		)

		for row in active_rules:
			doctype = row.get("document_type")
			event = row.get("trigger_event")
			rule_name = row.get("name")
			if not doctype or not event or not rule_name:
				continue

			explicit_watched = row.get("watched_fields")
			if isinstance(explicit_watched, str):
				explicit_watched = [f.strip() for f in explicit_watched.split(",") if f.strip()]
			elif isinstance(explicit_watched, list | tuple | set):
				explicit_watched = [str(f).strip() for f in explicit_watched if str(f).strip()]
			else:
				explicit_watched = []

			spec = {
				"name": rule_name,
				"doctype": doctype,
				"event": event,
				"priority": RuleCoordinator._normalized_priority(row.get("priority")),
				"execution_mode": row.get("execution_mode") or "Synchronous",
				"debug_mode": bool(row.get("debug_mode")),
				"compiled_expression": row.get("compiled_expression") or "",
				"has_trigger_condition": bool(row.get("trigger_condition")),
				# Only use explicitly configured watched fields for dispatch-time pruning.
				# Trigger-condition dependencies are evaluated in eligibility and are not safe skip keys.
				"watched_fields": sorted(set(explicit_watched)),
				"compiled_dependencies": RuleCoordinator._extract_watched_fields(
					row.get("compiled_expression")
				),
			}

			rules_index[rule_name] = spec
			event_map.setdefault(doctype, {}).setdefault(event, []).append(rule_name)

		return registry

	@staticmethod
	def _is_registry_valid(registry: Any) -> bool:
		return isinstance(registry, dict) and registry.get("cache_version") == RuleCoordinator.CACHE_VERSION

	@staticmethod
	def get_runtime_registry() -> dict:
		"""
		Layered cache for compiled runtime registry:
		1) frappe.local
		2) Redis (frappe.cache)
		3) DB rebuild
		"""
		local_registry = getattr(frappe.local, RuleCoordinator.LOCAL_REGISTRY_KEY, None)
		if RuleCoordinator._is_registry_valid(local_registry):
			return cast(dict[str, Any], local_registry)

		registry: dict[str, Any] | None = None
		try:
			cached_registry = frappe.cache.get_value(RuleCoordinator.CACHE_KEY)
			if RuleCoordinator._is_registry_valid(cached_registry):
				registry = cast(dict[str, Any], cached_registry)
		except Exception:
			frappe.log_error("FlexiRule: runtime registry cache read failed, rebuilding from DB.")

		if registry is None:
			registry = RuleCoordinator._build_runtime_registry()
			try:
				frappe.cache.set_value(RuleCoordinator.CACHE_KEY, registry)
			except Exception:
				frappe.log_error("FlexiRule: runtime registry cache write failed.")

		setattr(frappe.local, RuleCoordinator.LOCAL_REGISTRY_KEY, registry)
		return registry

	@staticmethod
	def get_rule_map() -> dict:
		"""Backward-compatible map accessor: {doctype: {event: [rule_names]}}."""
		registry = RuleCoordinator.get_runtime_registry()
		return registry.get("doctype_event_map", {})

	@staticmethod
	def _get_event_runtime(doctype: str, event_name: str) -> list[dict]:
		"""
		Resolve compiled rule specs for doctype/event with doctype-level request memoization.
		First load for a doctype hydrates all events; subsequent event lookups are local dict reads.
		"""
		cache = RuleCoordinator._get_local_dict(RuleCoordinator.LOCAL_RUNTIME_KEY)
		doctype_cache = cache.get(doctype)
		if not isinstance(doctype_cache, dict):
			registry = RuleCoordinator.get_runtime_registry()
			event_map = registry.get("doctype_event_map", {}).get(doctype, {}) or {}
			rules_index = registry.get("rules", {})
			doctype_cache = {}
			for event, rule_names in event_map.items():
				rule_specs = [rules_index.get(name) for name in (rule_names or [])]
				doctype_cache[event] = [spec for spec in rule_specs if spec]
			cache[doctype] = doctype_cache

		return doctype_cache.get(event_name, [])

	@staticmethod
	def has_active_rules(doctype: str, event_name: str) -> bool:
		"""Check if there are any active rules for this doctype/event."""
		return bool(RuleCoordinator._get_event_runtime(doctype, event_name))

	@staticmethod
	def _get_doc_execution_key(doc: Any, event_name: str) -> str:
		docname = getattr(doc, "name", None)
		if docname:
			key_doc = str(docname)
		else:
			# Unsaved docs share no stable name; include object identity to avoid cross-doc collisions.
			key_doc = f"__new__:{id(doc)}"
		return f"{getattr(doc, 'doctype', '')}:{key_doc}:{event_name}"

	@staticmethod
	@contextmanager
	def _event_reentry_guard(doc: Any, event_name: str):
		"""Protect against recursive lifecycle explosions for same doc/event within a request."""
		stack = RuleCoordinator._get_local_set(RuleCoordinator.LOCAL_REENTRY_STACK_KEY)
		execution_key = RuleCoordinator._get_doc_execution_key(doc, event_name)
		if execution_key in stack:
			yield False
			return

		stack.add(execution_key)
		try:
			yield True
		finally:
			stack.discard(execution_key)

	@staticmethod
	def _get_changed_fields(doc: Any) -> set[str] | None:
		"""
		Compute changed field set once per request/docname.
		Returns None when diff cannot be computed (new doc, missing old_doc, or errors).
		"""
		cache = RuleCoordinator._get_local_dict(RuleCoordinator.LOCAL_CHANGED_FIELDS_KEY)
		cache_key = RuleCoordinator._get_doc_execution_key(doc, "__changes__")
		if cache_key in cache:
			return cache[cache_key]

		if not hasattr(doc, "get_doc_before_save"):
			cache[cache_key] = None
			return None

		try:
			old_doc = doc.get_doc_before_save()
		except Exception:
			old_doc = None

		if not old_doc:
			cache[cache_key] = None
			return None

		changed_fields: set[str] = set()
		try:
			meta = frappe.get_meta(doc.doctype)
			for field in meta.fields:
				fieldname = field.fieldname
				if not fieldname:
					continue
				if doc.get(fieldname) != old_doc.get(fieldname):
					changed_fields.add(fieldname)
		except Exception:
			cache[cache_key] = None
			return None

		cache[cache_key] = changed_fields
		return changed_fields

	@staticmethod
	def _passes_watched_field_filter(rule_spec: dict, doc: Any, event_name: str) -> bool:
		watched_fields = rule_spec.get("watched_fields") or []
		if not watched_fields or event_name not in RuleCoordinator.FIELD_FILTER_EVENTS:
			return True

		changed_fields = RuleCoordinator._get_changed_fields(doc)
		if changed_fields is None:
			# Cannot compute diff safely; do not skip rule.
			return True

		return bool(changed_fields.intersection(set(watched_fields)))

	@staticmethod
	def execute_rules_from_event(doc: Any, event_name: str):
		"""
		Find and execute rules triggered by a specific document event.
		Logic decoupled from Frappe hook flags.

		Args:
		    doc: Frappe document
		    event_name: Event name (Before Save, Validate, etc.)
		"""
		runtime_specs = RuleCoordinator._get_event_runtime(doc.doctype, event_name)
		if not runtime_specs:
			return

		with RuleCoordinator._event_reentry_guard(doc, event_name) as should_execute:
			if not should_execute:
				return

			# Fetch old_doc once for all rules
			old_doc = None
			if hasattr(doc, "get_doc_before_save"):
				try:
					old_doc = doc.get_doc_before_save()
				except Exception:
					old_doc = None

			valid_rules: list[Any] = []
			for rule_spec in runtime_specs:
				if not RuleCoordinator._passes_watched_field_filter(rule_spec, doc, event_name):
					continue

				try:
					rule_doc = frappe.get_cached_doc("Rule", rule_spec["name"])
				except frappe.DoesNotExistError:
					# Stale registry entry: clear caches and skip this cycle.
					RuleCoordinator.clear_cache()
					return

				is_eligible, reason = RuleCoordinator.check_eligibility(
					rule_doc,
					doc,
					event_name,
					old_doc=old_doc,
				)
				if is_eligible:
					valid_rules.append(rule_doc)
				elif bool(rule_spec.get("debug_mode")):
					frappe.log_error(
						title=_("Rule Skipped: {0}").format(rule_doc.name),
						message=_(reason),
					)

			for rule_doc in valid_rules:
				try:
					RuleCoordinator.execute_single_rule(
						doc,
						rule_doc,
						old_doc=old_doc,
						event_name=event_name,
					)
				except Exception as e:
					if getattr(rule_doc, "debug_mode", False):
						frappe.log_error(
							title=_("Rule Execution Failed: {0}").format(rule_doc.name),
							message=_("DocType: {0} Doc: {1} Error: {2}").format(
								doc.doctype,
								getattr(doc, "name", None),
								str(e),
							),
						)

					if event_name in RuleCoordinator.BLOCKING_EVENTS or isinstance(e, frappe.ValidationError):
						raise

	@staticmethod
	def execute_rules(doc, event_name: str):
		"""
		Main entry point called from doc_events hooks

		Args:
		        doc: Frappe document
		        event_name: Event that triggered execution (before_save, validate, etc.)
		"""
		# Skip during import/migration
		if frappe.flags.in_import or frappe.flags.in_migrate:
			return

		return RuleCoordinator.execute_rules_from_event(doc, event_name)

	@staticmethod
	def check_eligibility(
		rule_doc,
		doc,
		event_name,
		execution_mode="Synchronous",
		skip_event_check=False,
		allow_inactive=False,
		old_doc=None,
	) -> tuple[bool, str]:
		"""
		Strict V1 Contract Eligibility Check
		Returns: (is_eligible: bool, reason: str)
		"""
		# 1. Active Check
		if not allow_inactive and not RuleCoordinator._is_active_value(rule_doc.get("is_active")):
			return False, _("Rule is not active")

		# 2. Event Check
		if not skip_event_check and rule_doc.trigger_event != event_name:
			# This might happen if cache returns mixed results or during manual triggers
			return False, _("Event mismatch: Rule expects {0}, got {1}").format(
				rule_doc.trigger_event, event_name
			)

		# 3. Mode Check (Strict)
		# For V1, we enforce that Sync rules run in Sync context.
		# Async is handled by the executor, but we should flag mismatch if needed.
		# Currently, we don't have explicit 'mode' passed from hooks, so we assume Sync.
		# If Rule is Async, it will be queued by execute_single_rule.

		# 4. Condition Check (Compiled Expression)
		# We now rely solely on compiled_expression which is the compiled version of trigger_condition
		if rule_doc.get("compiled_expression"):
			try:
				from flexirule.ruleflow.core.evaluator import check_link_match
				from flexirule.ruleflow.utils.field_resolver import FieldResolver

				# Fetch old_doc if missing
				if not old_doc and hasattr(doc, "get_doc_before_save"):
					old_doc = doc.get_doc_before_save()

				# Use SafeFrappeAPI to prevent write operations in trigger conditions
				from flexirule.ruleflow.core.engine import SafeFrappeAPI

				rule_meta = {
					"name": rule_doc.name,
					"trigger_type": rule_doc.trigger_type,
					"trigger_event": rule_doc.trigger_event,
					"document_type": rule_doc.document_type,
				}
				doctype_name = rule_doc.document_type or getattr(doc, "doctype", None)

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

				eval_globals = {
					"doc": doc,
					"old_doc": old_doc,
					"vars": {},
					"frappe": SafeFrappeAPI(),
					"caller": frappe._dict({}),
					"rule": frappe._dict(rule_meta),
					"doctype": doctype_name,
					"is_submittable": _is_submittable,
					"has_field": _has_field,
					"get_meta": _get_meta,
					"resolve": FieldResolver.resolve,
					"check_link_match": check_link_match,
					"True": True,
					"False": False,
					"None": None,
				}

				if not frappe.safe_eval(rule_doc.get("compiled_expression"), None, eval_globals):
					return False, _("Trigger Conditions failed")

			except Exception as e:
				return False, _("Trigger Evaluation Error: {0}").format(str(e))

		# Conditions MUST be pre-compiled - no runtime JSON parsing
		elif rule_doc.get("trigger_condition"):
			return False, _("Rule has trigger_condition but no compiled_expression. Please re-save the Rule.")

		return True, _("Eligible")

	@staticmethod
	def get_applicable_rules(doctype: str, event_name: str, doc=None, _allow_retry: bool = True) -> list:
		"""
		Get active rules for a doctype and event.
		Uses compiled runtime registry for fast lookup, then cached docs.
		"""
		runtime_specs = RuleCoordinator._get_event_runtime(doctype, event_name)
		if not runtime_specs:
			return []

		rules = []
		stale_registry_detected = False
		for spec in runtime_specs:
			try:
				rule_doc = frappe.get_cached_doc("Rule", spec["name"])
			except frappe.DoesNotExistError:
				# Rule was deleted but cache not cleared - rebuild
				RuleCoordinator.clear_cache()
				return RuleCoordinator.get_applicable_rules(
					doctype,
					event_name,
					doc,
					_allow_retry=False,
				)

			if (
				not RuleCoordinator._is_active_value(rule_doc.get("is_active"))
				or rule_doc.trigger_type != "DocType Event"
				or rule_doc.document_type != doctype
				or rule_doc.trigger_event != event_name
			):
				stale_registry_detected = True
				continue

			rules.append(rule_doc)

		if stale_registry_detected and _allow_retry:
			RuleCoordinator.clear_cache(doctype=doctype)
			return RuleCoordinator.get_applicable_rules(doctype, event_name, doc, _allow_retry=False)

		return rules

	@staticmethod
	def execute_single_rule(doc, rule_doc, old_doc=None, event_name=None):
		"""
		Execute a single rule against a document

		Args:
		        doc: Frappe document
		        rule_doc: Rule document
		        old_doc: Document state before save (optional)
		        event_name: Trigger event name (optional)
		"""
		# Check if rule should run asynchronously
		if rule_doc.execution_mode == "Asynchronous":
			# Async only works for saved documents
			if not doc.get("__islocal"):
				frappe.enqueue(
					"flexirule.ruleflow.core.coordinator.RuleCoordinator.run_rule_background",
					rule_name=rule_doc.name,
					doc_doctype=doc.doctype,
					doc_name=doc.name,
					queue="default",
					timeout=rule_doc.max_execution_time or 300,
				)
				return

		from flexirule.ruleflow.core.engine import RuleEngine

		# Execute using new Engine
		# Pass old_doc in context
		execution_context = {"old_doc": old_doc}
		if frappe.flags.in_test:
			execution_context["test_mode"] = True

		engine = RuleEngine(rule_doc, execution_context=execution_context)
		engine.execute(doc, event_name=event_name)

	@staticmethod
	def run_rule_background(rule_name, doc_doctype, doc_name):
		"""
		Background job entry point
		"""
		try:
			rule_doc = frappe.get_doc("Rule", rule_name)
			doc = frappe.get_doc(doc_doctype, doc_name)

			from flexirule.ruleflow.core.engine import RuleEngine

			engine = RuleEngine(rule_doc)
			engine.execute(doc)

		except Exception as e:
			frappe.log_error(_("Async Rule Execution Failed: {0}").format(rule_name), str(e))

	@staticmethod
	def should_rebuild_registry_for_rule_change(rule_doc: Any, method: str | None = None) -> bool:
		"""
		Decide whether compiled runtime registry must be rebuilt.
		Rebuild only for active/route-relevant DocType Event rule lifecycle changes.
		"""
		method = method or ""

		if method == "on_trash":
			return bool(
				rule_doc.get("trigger_type") == "DocType Event"
				and RuleCoordinator._is_active_value(rule_doc.get("is_active"))
			)

		# Inserted active doc-event rules must be discoverable immediately.
		if method == "after_insert":
			return bool(
				rule_doc.get("trigger_type") == "DocType Event"
				and RuleCoordinator._is_active_value(rule_doc.get("is_active"))
			)

		# Updates: compare previous state and current state.
		try:
			old_doc = rule_doc.get_doc_before_save()
		except Exception:
			old_doc = None

		if not old_doc:
			return bool(
				rule_doc.get("trigger_type") == "DocType Event"
				and RuleCoordinator._is_active_value(rule_doc.get("is_active"))
			)

		old_is_doc_event = old_doc.get("trigger_type") == "DocType Event"
		new_is_doc_event = rule_doc.get("trigger_type") == "DocType Event"
		old_active = RuleCoordinator._is_active_value(old_doc.get("is_active"))
		new_active = RuleCoordinator._is_active_value(rule_doc.get("is_active"))

		# If both old and new are outside active DocType Event runtime, skip rebuild.
		if not (old_is_doc_event and old_active) and not (new_is_doc_event and new_active):
			return False

		# Trigger on active-state transitions.
		if old_active != new_active or old_is_doc_event != new_is_doc_event:
			return True

		# While active in runtime, rebuild if runtime signature changed.
		for fieldname in RuleCoordinator.RUNTIME_SIGNATURE_FIELDS:
			if old_doc.get(fieldname) != rule_doc.get(fieldname):
				return True

		return False

	@staticmethod
	def clear_cache(doctype: str | None = None):
		"""
		Clear compiled runtime registry caches.
		"""
		# Clear Redis cache
		frappe.cache.delete_value(RuleCoordinator.CACHE_KEY)

		# Clear request-level cache
		for attr in (
			RuleCoordinator.LOCAL_REGISTRY_KEY,
			RuleCoordinator.LOCAL_RUNTIME_KEY,
			RuleCoordinator.LOCAL_CHANGED_FIELDS_KEY,
			RuleCoordinator.LOCAL_REENTRY_STACK_KEY,
		):
			if hasattr(frappe.local, attr):
				delattr(frappe.local, attr)

		# Notify distributed workers (v16 pattern)
		frappe.publish_realtime(  # nosemgrep: frappe-realtime-pick-room
			"flexirule_cache_clear",
			{"doctype": doctype},
			after_commit=True,
		)


def execute_rules(doc, event_name):
	"""
	Wrapper for RuleCoordinator.execute_rules to be used in hooks
	"""
	return RuleCoordinator.execute_rules(doc, event_name)
