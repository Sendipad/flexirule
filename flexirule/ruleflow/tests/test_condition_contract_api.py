# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest

import frappe

from flexirule.ruleflow.api import get_condition_contract, get_operator_config


class TestConditionContractAPI(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_get_condition_contract_structure(self):
		contract = get_condition_contract()

		self.assertIn("node_types", contract)
		self.assertEqual(contract["node_types"], ["comparison", "group", "collection_predicate"])

		self.assertIn("flexvalue_modes", contract)
		self.assertIn("value_types", contract)
		self.assertIn("scopes", contract)
		self.assertIn("quantifiers", contract)
		self.assertIn("operators", contract)
		self.assertIn("limits", contract)
		self.assertIn("contract_version_hash", contract)

		# Verify limits
		limits = contract["limits"]
		self.assertEqual(limits["max_condition_depth"], 32)
		self.assertEqual(limits["max_condition_nodes"], 1000)
		self.assertEqual(limits["max_collection_rows"], 10000)

		# Verify default resolver policy
		self.assertFalse(contract["resolvers"]["condition_operand_allowed_default"])

		# Verify operators list contains stable IDs
		op_ids = [op["operator_id"] for op in contract["operators"]]
		self.assertIn("eq", op_ids)
		self.assertIn("gt", op_ids)
		self.assertIn("is_set", op_ids)
		self.assertIn("is_null", op_ids)

	def test_get_operator_config_backwards_compatibility(self):
		legacy_config = get_operator_config()
		self.assertIn("fieldtype_operators", legacy_config)
		self.assertIn("operator_labels", legacy_config)
