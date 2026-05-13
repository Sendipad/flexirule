# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.exceptions import MethodExecutionError
from flexirule.ruleflow.core.process_contract_v2 import ExecutionContext, OperationInvocation
from flexirule.ruleflow.core.process_runtime_v2 import (
	OperationAdapterRegistry,
	ProcessOperationExecutor,
)


class _Action:
	def __init__(self, is_async=0):
		self.is_async = is_async


class TestProcessRuntimeV2(FrappeTestCase):
	def _invocation(self, *, event_name="Before Save", writes_to="Context", config=None):
		return OperationInvocation(
			operation_key="Validation.value_in_range",
			adapter_key="validate",
			process_name="Validation",
			operation_name="value_in_range",
			config=config if config is not None else {"field": "amount"},
			process_operation={},
			config_schema={
				"type": "object",
				"additionalProperties": False,
				"properties": {"field": {"type": "string"}},
				"required": ["field"],
			},
			result_schema={
				"type": "object",
				"additionalProperties": False,
				"properties": {"ok": {"type": "boolean"}},
				"required": ["ok"],
			},
			capabilities={
				"requires_doc": True,
				"writes_to": writes_to,
				"allows_async": False,
				"transactional": False,
				"can_stop_save": False,
				"has_side_effect": False,
			},
			policy={"allowed_mutations": ["Set Context Variable"]},
			context=ExecutionContext(
				doc={"name": "X"},
				vars={},
				event_name=event_name,
				is_async=False,
				raw_context={"doc": {"name": "X"}, "vars": {}, "event_name": event_name},
			),
		)

	def test_unknown_adapter_is_rejected(self):
		with self.assertRaises(MethodExecutionError):
			OperationAdapterRegistry.execute("unknown_adapter", self._invocation(), object())

	def test_validate_invocation_blocks_after_event_doc_writes(self):
		executor = ProcessOperationExecutor()
		invocation = self._invocation(event_name="After Save", writes_to="Document")
		with self.assertRaises(MethodExecutionError):
			executor.validate_invocation(invocation, _Action(is_async=0))

	def test_validate_invocation_rejects_invalid_config_schema(self):
		executor = ProcessOperationExecutor()
		invocation = self._invocation(config={"bad": "value"})
		with self.assertRaises(MethodExecutionError):
			executor.validate_invocation(invocation, _Action(is_async=0))

	def test_validate_result_enforces_result_schema(self):
		executor = ProcessOperationExecutor()
		invocation = self._invocation()
		result = executor.normalize_result({"status": "success", "data": {"bad": True}})
		with self.assertRaises(MethodExecutionError):
			executor.validate_result(invocation, result)

	def test_execute_returns_standardized_result(self):
		executor = ProcessOperationExecutor()
		invocation = self._invocation()

		with (
			patch.object(executor, "build_invocation", return_value=(invocation, object())),
			patch.object(
				OperationAdapterRegistry,
				"execute",
				return_value={
					"status": "success",
					"data": {"ok": True},
					"mutations": [
						{
							"mutation_mode": "Set Context Variable",
							"target": "result_var",
							"value": {"ok": True},
						}
					],
					"errors": [],
					"warnings": [],
				},
			),
		):
			result = executor.execute(_Action(is_async=0), {"doc": {"name": "X"}, "vars": {}}, {"field": "x"})
		self.assertEqual(result["status"], "success")
		self.assertEqual(result["data"], {"ok": True})
		self.assertEqual(result["mutations"][0]["target"], "result_var")
