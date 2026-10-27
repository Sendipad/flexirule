import unittest

from flexirule.ruleflow.core.condition_contract import (
	CanonicalOperatorRegistry,
	ConditionValidationError,
	validate_condition_payload,
)
from flexirule.ruleflow.tests.fixtures.canonical_conditions.fixture_helper import (
	load_canonical_fixture,
)


class TestConditionContract(unittest.TestCase):
	def test_valid_fixtures(self):
		comp = load_canonical_fixture("valid_comparison.json")
		validate_condition_payload(comp)

		grp = load_canonical_fixture("valid_group.json")
		validate_condition_payload(grp)

		coll = load_canonical_fixture("valid_collection_predicate.json")
		validate_condition_payload(coll)

	def test_invalid_fixtures(self):
		transient_id = load_canonical_fixture("invalid_transient_id.json")
		with self.assertRaises(ConditionValidationError) as cm:
			validate_condition_payload(transient_id)
		self.assertIn("Transient UI property 'id'", str(cm.exception))

		one_child = load_canonical_fixture("invalid_one_child_group.json")
		with self.assertRaises(ConditionValidationError) as cm:
			validate_condition_payload(one_child)
		self.assertIn("at least two children", str(cm.exception))

	def test_operator_registry_defaults(self):
		self.assertTrue(CanonicalOperatorRegistry.exists("eq"))
		self.assertTrue(CanonicalOperatorRegistry.exists("is_submittable"))
		self.assertTrue(CanonicalOperatorRegistry.exists("has_field"))

		meta = CanonicalOperatorRegistry.get("is_submittable")
		self.assertIsNotNone(meta)
		if meta is not None:
			self.assertEqual(meta["arity"], 1)
			self.assertTrue(meta["is_metadata_operator"])


if __name__ == "__main__":
	unittest.main()
