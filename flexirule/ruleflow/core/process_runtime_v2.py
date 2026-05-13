# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any, ClassVar, Literal, cast

import frappe
from frappe import _
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as jsonschema_validate

from flexirule.ruleflow.core.exceptions import MethodExecutionError
from flexirule.ruleflow.core.process_contract_v2 import (
	ExecutionContext,
	MutationIntent,
	OperationInvocation,
	OperationResult,
	resolve_process_operation_contract_v2,
)

AFTER_EVENT_MUTATION_BLOCKLIST = {
	"After Insert",
	"After Save",
	"On Submit",
	"Before Cancel",
	"On Cancel",
	"On Trash",
	"On Update After Submit",
	"On Change",
}


class OperationAdapterRegistry:
	"""Built-in declarative adapter registry for Process operation execution."""

	_registry: ClassVar[dict[str, Any]] = {}
	_initialized: ClassVar[bool] = False

	@classmethod
	def register(cls, adapter_key: str, executor) -> None:
		cls._registry[adapter_key] = executor

	@classmethod
	def _ensure_initialized(cls) -> None:
		if cls._initialized:
			return
		for adapter_key in ("validate", "transform", "lookup", "dedupe", "batch"):
			cls.register(adapter_key, _execute_python_process_operation)
		cls._initialized = True

	@classmethod
	def execute(cls, adapter_key: str, invocation: OperationInvocation, process_doc):
		cls._ensure_initialized()
		executor = cls._registry.get(adapter_key)
		if not executor:
			raise MethodExecutionError(_("Undefined Process adapter_key: {0}").format(adapter_key))
		return executor(invocation, process_doc)


def _execute_python_process_operation(invocation: OperationInvocation, process_doc):
	"""Execute one declarative operation via process module function lookup."""
	from flexirule.ruleflow.doctype.process.process import get_process_module_dotted_path

	module_path = get_process_module_dotted_path(process_doc.module, process_doc.name)
	method_path = f"{module_path}.{invocation.operation_name}"
	try:
		method = frappe.get_attr(method_path)
	except Exception as exc:
		raise MethodExecutionError(
			_(
				"Operation method '{0}' not found. Declarative runtime v2 requires a "
				"module function per operation."
			).format(method_path)
		) from exc
	return method(invocation.context.raw_context, invocation.config)


class ProcessOperationExecutor:
	"""Centralized executor for Process operations under declarative contract v2."""

	def build_invocation(
		self, action, context: dict[str, Any], config: dict[str, Any]
	) -> tuple[OperationInvocation, Any]:
		process_name = getattr(action, "process_name", None)
		operation_name = getattr(action, "operation", None)
		if not process_name or not operation_name:
			raise MethodExecutionError(_("Process action requires process_name and operation"))

		if not frappe.db.exists("Process", process_name):
			raise MethodExecutionError(_("Process {0} not found").format(process_name))

		process_doc = frappe.get_cached_doc("Process", process_name)
		process_operation = process_doc.get_operation(operation_name)
		process_operation_dict = (
			process_operation.as_dict() if hasattr(process_operation, "as_dict") else dict(process_operation)
		)
		contract_v2 = resolve_process_operation_contract_v2(
			process_name,
			operation_name,
			process_operation_dict,
			strict=True,
		)

		invocation = OperationInvocation(
			operation_key=contract_v2["operation_key"],
			adapter_key=contract_v2["adapter_key"],
			process_name=process_name,
			operation_name=operation_name,
			config=config or {},
			process_operation=process_operation_dict,
			config_schema=contract_v2["config_schema"],
			result_schema=contract_v2["result_schema"],
			capabilities=contract_v2["capabilities"],
			policy=contract_v2["policy"],
			return_type=getattr(action, "return_type", None),
			return_variable=getattr(action, "return_variable", None),
			action_id=getattr(action, "action_id", None) or getattr(action, "name", None),
			context=ExecutionContext.from_runtime_context(context),
		)
		return invocation, process_doc

	def validate_invocation(self, invocation: OperationInvocation, action) -> None:
		capabilities = invocation.capabilities or {}
		if capabilities.get("requires_doc") and not invocation.context.doc:
			raise MethodExecutionError(
				_("Process operation {0} requires context doc").format(invocation.operation_key)
			)

		action_is_async = bool(getattr(action, "is_async", 0))
		if action_is_async and not capabilities.get("allows_async"):
			raise MethodExecutionError(
				_("Operation {0} does not allow async execution").format(invocation.operation_key)
			)

		event_name = invocation.context.event_name
		writes_to = str(capabilities.get("writes_to") or "None")
		if (
			not action_is_async
			and event_name in AFTER_EVENT_MUTATION_BLOCKLIST
			and writes_to in {"Document", "Database"}
		):
			raise MethodExecutionError(
				_(
					"Operation {0} writes to {1} and cannot run in event '{2}' under declarative runtime v2"
				).format(invocation.operation_key, writes_to, event_name)
			)

		try:
			jsonschema_validate(invocation.config or {}, invocation.config_schema or {})
		except JsonSchemaValidationError as exc:
			raise MethodExecutionError(
				_("Config schema validation failed for {0}: {1}").format(
					invocation.operation_key, exc.message
				)
			) from exc

	def normalize_result(self, raw_result: Any) -> OperationResult:
		if isinstance(raw_result, OperationResult):
			return raw_result

		if isinstance(raw_result, dict) and {"status", "data", "mutations"} & set(raw_result.keys()):
			status_value = raw_result.get("status") or "success"
			status: Literal["success", "failed", "skipped"]
			if status_value in {"success", "failed", "skipped"}:
				status = cast(Literal["success", "failed", "skipped"], status_value)
			else:
				status = "success"
			mutations: list[MutationIntent] = []
			for row in raw_result.get("mutations") or []:
				if not isinstance(row, dict):
					continue
				mode = row.get("mutation_mode")
				target = row.get("target")
				if not mode or not target:
					continue
				mutations.append(
					MutationIntent(
						mutation_mode=mode,
						target=target,
						value=row.get("value"),
					)
				)
			return OperationResult(
				status=status,
				data=raw_result.get("data"),
				mutations=mutations,
				errors=list(raw_result.get("errors") or []),
				warnings=list(raw_result.get("warnings") or []),
				metrics=dict(raw_result.get("metrics") or {}),
			)

		return OperationResult(status="success", data=raw_result)

	def validate_result(self, invocation: OperationInvocation, result: OperationResult) -> None:
		try:
			jsonschema_validate(result.data, invocation.result_schema or {})
		except JsonSchemaValidationError as exc:
			raise MethodExecutionError(
				_("Result schema validation failed for {0}: {1}").format(
					invocation.operation_key, exc.message
				)
			) from exc

	def execute(self, action, context: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
		invocation, process_doc = self.build_invocation(action, context, config)
		self.validate_invocation(invocation, action)
		raw_result = OperationAdapterRegistry.execute(invocation.adapter_key, invocation, process_doc)
		result = self.normalize_result(raw_result)
		self.validate_result(invocation, result)
		return result.as_dict()
