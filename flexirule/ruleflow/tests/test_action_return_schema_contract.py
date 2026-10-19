# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.contract_dto import ContractDTOBuilder
from flexirule.ruleflow.core.validation_service import _validate_action_contracts


class TestActionReturnSchemaContract(FrappeTestCase):
	def _validate_action(self, action_type: str, **overrides) -> list[str]:
		action = {
			"action_type": action_type,
			"action_label": f"Test {action_type}",
			"operation": None,
			"return_type": None,
			"return_variable": None,
			"resolved_output_schema": "[]",
			"mutation_mode": None,
			"config": "{}",
			**overrides,
		}
		errors: list[str] = []
		_validate_action_contracts(
			action,
			action_type,
			action["action_label"],
			operation_metadata={},
			errors=errors,
			mode="draft",
		)
		return errors

	def test_empty_serialized_schema_does_not_require_return_variable_for_non_result_actions(self):
		for action_type in ("Entry Action", "Condition", "Assignment", "Stop"):
			with self.subTest(action_type=action_type):
				errors = self._validate_action(
					action_type,
					return_type="List of Records",
					resolved_output_schema="[]",
				)
				self.assertFalse(
					any("requires Return Variable Name for Return Schema" in error for error in errors),
					errors,
				)

	def test_hidden_return_type_with_empty_schema_does_not_require_return_variable(self):
		errors = self._validate_action(
			"Query Records",
			operation="Fetch Records",
			return_type="List of Records",
			resolved_output_schema="[]",
		)
		self.assertFalse(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_populated_schema_requires_return_variable_for_schema_capable_action(self):
		errors = self._validate_action(
			"Query Records",
			operation="Fetch Records",
			return_type="List of Records",
			resolved_output_schema='[{"fieldname": "name", "label": "Name"}]',
		)
		self.assertTrue(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_selected_visible_return_type_requires_return_variable(self):
		errors = self._validate_action(
			"Document Action",
			operation="Create New",
			return_type="Single Record",
			resolved_output_schema="[]",
		)
		self.assertTrue(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_loop_item_alias_requirement_is_preserved(self):
		errors = self._validate_action("Loop", operation=None, return_variable=None)
		self.assertTrue(
			any("requires Return Variable Name" in error for error in errors),
			errors,
		)

	def test_sub_rule_return_schema_capability_is_shared_with_frontend_dto(self):
		contract = HandlerRegistry.get_action_contract("Sub-Rule")
		self.assertTrue(contract.get("supports_return_schema"))
		dto = ContractDTOBuilder.build()
		self.assertIn("Sub-Rule", dto["action_types_with_return_schema"])
		self.assertNotIn("Condition", dto["action_types_with_return_schema"])
		self.assertNotIn("Assignment", dto["action_types_with_return_schema"])

	def test_object_schema_forms_without_properties_or_fields_do_not_require_return_variable(self):
		for empty_schema in ('{"fields": []}', '{"properties": {}}', "{}", "[]"):
			with self.subTest(empty_schema=empty_schema):
				errors = self._validate_action(
					"Query Records",
					operation="Fetch Records",
					return_type="List of Records",
					resolved_output_schema=empty_schema,
				)
				self.assertFalse(
					any("requires Return Variable Name for Return Schema" in error for error in errors),
					errors,
				)

	def test_populated_object_schema_forms_require_return_variable_for_schema_capable_action(self):
		for populated_schema in (
			'{"fields": [{"fieldname": "name"}]}',
			'{"properties": {"name": {"type": "string"}}}',
		):
			with self.subTest(populated_schema=populated_schema):
				errors = self._validate_action(
					"Query Records",
					operation="Fetch Records",
					return_type="List of Records",
					resolved_output_schema=populated_schema,
				)
				self.assertTrue(
					any("requires Return Variable Name for Return Schema" in error for error in errors),
					errors,
				)

	def test_yes_no_return_type_does_not_require_return_variable(self):
		errors = self._validate_action(
			"Document Action",
			operation="Save Doc",
			return_type="Yes / No",
			resolved_output_schema="[]",
		)
		self.assertFalse(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)

	def test_operation_level_supports_return_schema_false_override(self):
		errors = self._validate_action(
			"Query Records",
			operation="Exists",
			return_type="Yes / No",
			resolved_output_schema="[]",
		)
		self.assertFalse(
			any("requires Return Variable Name for Return Schema" in error for error in errors),
			errors,
		)
