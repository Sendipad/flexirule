from frappe.tests.utils import FrappeTestCase


def _field(overrides, fieldname):
	for row in overrides:
		if row.get("fieldname") == fieldname:
			return row
	return None


class TestContractFieldOverrides(FrappeTestCase):
	def test_terminal_action_hides_next_step_fields(self):
		from flexirule.ruleflow.core.contracts import get_operation_field_overrides

		overrides = get_operation_field_overrides("Stop", "Rule Action")

		next_true = _field(overrides, "next_step_if_true")
		next_false = _field(overrides, "next_step_if_false")

		self.assertIsNotNone(next_true)
		self.assertEqual(next_true.get("hidden"), 1)
		self.assertEqual(next_true.get("reqd"), 0)
		self.assertIsNotNone(next_false)
		self.assertEqual(next_false.get("hidden"), 1)
		self.assertEqual(next_false.get("reqd"), 0)

	def test_operation_contract_inherits_action_next_step_overrides(self):
		from flexirule.ruleflow.core.contracts import get_operation_field_overrides

		overrides = get_operation_field_overrides("Success", "Rule Action")

		next_true = _field(overrides, "next_step_if_true")
		next_false = _field(overrides, "next_step_if_false")

		self.assertEqual(next_true.get("hidden"), 1)
		self.assertEqual(next_false.get("hidden"), 1)

	def test_condition_keeps_next_step_fields_visible(self):
		from flexirule.ruleflow.core.contracts import get_operation_field_overrides

		overrides = get_operation_field_overrides("Condition", "Rule Action")

		next_true = _field(overrides, "next_step_if_true")
		next_false = _field(overrides, "next_step_if_false")

		self.assertIsNone(next_true)
		self.assertNotEqual(next_false.get("hidden"), 1)

	def test_notify_hides_false_branch_only(self):
		from flexirule.ruleflow.core.contracts import get_operation_field_overrides

		overrides = get_operation_field_overrides("Notify", "Rule Action")

		next_true = _field(overrides, "next_step_if_true")
		next_false = _field(overrides, "next_step_if_false")

		self.assertIsNone(next_true)
		self.assertEqual(next_false.get("hidden"), 1)

	def test_schema_endpoint_applies_contract_field_overrides(self):
		from flexirule.ruleflow.core.graph_service import get_node_config_schema

		schema = get_node_config_schema("Stop", operation="Success")
		fields = {row.get("fieldname"): row for row in schema.get("fields", [])}

		self.assertEqual(fields["next_step_if_true"].get("hidden"), 1)
		self.assertEqual(fields["next_step_if_false"].get("hidden"), 1)
