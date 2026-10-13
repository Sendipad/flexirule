from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import _aggregate_source, _output_schema_source, _reqd_flag
from flexirule.ruleflow.core.contract_dto import ContractDTOBuilder
from flexirule.ruleflow.core.contracts import get_contract
from flexirule.ruleflow.core.validation_service import (
	_has_configured_output_schema,
	_validate_return_schema_requirements,
)


class TestResolvedOutputSchemaContract(FrappeTestCase):
	def test_reqd_flag_normalizes_frappe_values(self):
		self.assertEqual(_reqd_flag(1), 1)
		self.assertEqual(_reqd_flag(True), 1)
		self.assertEqual(_reqd_flag("1"), 1)
		self.assertEqual(_reqd_flag(0), 0)
		self.assertEqual(_reqd_flag("0"), 0)
		self.assertEqual(_reqd_flag(None), 0)

	def test_aggregate_source_carries_expression_provenance(self):
		self.assertEqual(
			_aggregate_source("Count", {"field": "name"}),
			{
				"kind": "aggregate",
				"fieldname": "name",
				"expression": "count(name)",
				"function": "count",
			},
		)
		self.assertEqual(
			_aggregate_source("Count", {}),
			{"kind": "aggregate", "expression": "count(*)", "function": "count"},
		)

	def test_output_source_omits_unknown_metadata(self):
		self.assertEqual(
			_output_schema_source("field", fieldname="title", expression="title", optional=None),
			{"kind": "field", "fieldname": "title", "expression": "title"},
		)



class TestActionReturnSchemaValidation(FrappeTestCase):
	def test_contract_dto_derives_schema_capabilities_from_handlers(self):
		dto = ContractDTOBuilder.build()
		self.assertEqual(
			set(dto["action_types_with_return_schema"]),
			{"Process", "Query Records", "Document Action"},
		)

	def test_empty_schema_payloads_are_not_configured(self):
		for value in (None, "", "[]", [], "  []  "):
			with self.subTest(value=value):
				self.assertFalse(_has_configured_output_schema(value))

		# The schema contract is an array. Even an empty object is an invalid,
		# explicitly supplied shape and must not be normalized as "not configured".
		self.assertTrue(_has_configured_output_schema({}))

	def test_non_schema_actions_ignore_empty_schema_serialization(self):
		for action_type in ("Entry Action", "Condition", "Stop", "Assignment"):
			with self.subTest(action_type=action_type):
				errors = _validate_return_schema_requirements(
					action_type,
					action_type,
					{"resolved_output_schema": "[]"},
					get_contract(action_type),
					{},
				)
				self.assertEqual(errors, [])

	def test_non_schema_actions_reject_nonempty_output_contract(self):
		errors = _validate_return_schema_requirements(
			"Stop action",
			"Stop",
			{"resolved_output_schema": '[{"fieldname":"name"}]'},
			get_contract("Stop"),
			{},
		)
		self.assertEqual(len(errors), 1)
		self.assertIn("does not support a Return Schema", errors[0])
		self.assertNotIn("requires Return Variable Name", errors[0])

	def test_schema_actions_require_variable_for_nonempty_schema(self):
		for action_type in ("Process", "Query Records", "Document Action"):
			with self.subTest(action_type=action_type):
				errors = _validate_return_schema_requirements(
					action_type,
					action_type,
					{"resolved_output_schema": '[{"fieldname":"name"}]'},
					get_contract(action_type),
					{"show_return_type": False},
				)
				self.assertEqual(len(errors), 1)
				self.assertIn("requires Return Variable Name for Return Schema", errors[0])

	def test_schema_actions_do_not_require_variable_for_empty_schema_alone(self):
		for action_type in ("Process", "Query Records", "Document Action"):
			with self.subTest(action_type=action_type):
				errors = _validate_return_schema_requirements(
					action_type,
					action_type,
					{"resolved_output_schema": "[]"},
					get_contract(action_type),
					{},
				)
				self.assertEqual(errors, [])
