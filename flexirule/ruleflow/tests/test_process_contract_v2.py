# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2


class TestProcessContractV2(FrappeTestCase):
	def _op(self, *, adapter_key="lookup"):
		return {
			"func_name": "sample_operation",
			"writes_to": "Context",
			"requires_doc": 1,
			"allows_async": 0,
			"transactional": 0,
			"can_stop_save": 0,
			"has_side_effect": 0,
			"action_overrides": json.dumps(
				{
					"contract_v2": {
						"adapter_key": adapter_key,
						"capabilities": {
							"requires_doc": True,
							"writes_to": "Context",
							"allows_async": False,
							"transactional": False,
							"can_stop_save": False,
							"has_side_effect": False,
						},
						"policy": {
							"allowed_mutations": ["Set Context Variable", "Update Context Variable"],
							"allowed_return_types": ["Single Record"],
							"default_return_type": "Single Record",
							"require_return_variable": False,
							"require_return_type": False,
						},
						"config_schema": {
							"type": "object",
							"additionalProperties": False,
							"properties": {"field": {"type": "string"}},
							"required": ["field"],
						},
						"result_schema": {
							"type": "object",
							"properties": {"ok": {"type": "boolean"}},
							"required": ["ok"],
						},
					}
				}
			),
		}

	def test_resolve_contract_v2_success(self):
		resolved = resolve_process_operation_contract_v2(
			"Validation",
			"value_in_range",
			self._op(),
			strict=True,
		)
		self.assertEqual(resolved["operation_key"], "Validation.value_in_range")
		self.assertEqual(resolved["adapter_key"], "lookup")
		self.assertEqual(resolved["config_schema"]["required"], ["field"])
		self.assertEqual(resolved["result_schema"]["required"], ["ok"])

	def test_rejects_unknown_adapter_key(self):
		with self.assertRaises(frappe.ValidationError):
			resolve_process_operation_contract_v2(
				"Validation",
				"value_in_range",
				self._op(adapter_key="unsupported"),
				strict=True,
			)

	def test_rejects_missing_contract_v2(self):
		op = self._op()
		op["action_overrides"] = "{}"
		with self.assertRaises(frappe.ValidationError):
			resolve_process_operation_contract_v2(
				"Validation",
				"value_in_range",
				op,
				strict=True,
			)
