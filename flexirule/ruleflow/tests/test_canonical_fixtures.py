# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest
from typing import Any, cast

from flexirule.ruleflow.core.condition_contract import (
	ConditionContractError,
	validate_condition_node,
)
from flexirule.ruleflow.core.condition_evaluator import (
	evaluate_canonical_condition,
)
from flexirule.ruleflow.tests.canonical_fixtures import (
	NEGATIVE_VALIDATION_FIXTURES,
	POSITIVE_FIXTURES,
)


class TestCanonicalFixtures(unittest.TestCase):
	def test_positive_fixtures(self):
		for fixture in POSITIVE_FIXTURES:
			with self.subTest(name=fixture["name"]):
				cond = cast(dict[str, Any], fixture["condition"])
				ctx = cast(dict[str, Any], fixture["context"])
				expected = fixture["expected"]

				# Validate first
				validate_condition_node(cond)

				# Evaluate
				result = evaluate_canonical_condition(cond, ctx)
				self.assertEqual(result, expected)

	def test_negative_validation_fixtures(self):
		for fixture in NEGATIVE_VALIDATION_FIXTURES:
			with self.subTest(name=fixture["name"]):
				cond = cast(dict[str, Any], fixture["condition"])
				expected_code = cast(str, fixture["expected_error_code"])

				with self.assertRaises(ConditionContractError) as cm:
					validate_condition_node(cond)
				self.assertEqual(cm.exception.code, expected_code)
