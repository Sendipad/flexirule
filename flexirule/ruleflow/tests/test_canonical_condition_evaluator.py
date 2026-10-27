import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from flexirule.ruleflow.core.condition_evaluator import (
    CanonicalConditionEvaluator,
)


class TestCanonicalConditionEvaluator(unittest.TestCase):
    def test_evaluate_simple_comparison(self):
        node = {
            "type": "comparison",
            "operator": "eq",
            "left": {
                "mode": "variable",
                "path": {"scope": "doc", "segments": ["status"]},
            },
            "right": {"mode": "static", "value_type": "string", "value": "Open"},
        }

        evaluator = CanonicalConditionEvaluator({"doc": {"status": "Open"}})
        self.assertTrue(evaluator.evaluate(node))

        evaluator_false = CanonicalConditionEvaluator({"doc": {"status": "Closed"}})
        self.assertFalse(evaluator_false.evaluate(node))

    def test_numeric_and_decimal_comparison(self):
        node = {
            "type": "comparison",
            "operator": "gt",
            "left": {
                "mode": "variable",
                "path": {"scope": "doc", "segments": ["grand_total"]},
            },
            "right": {"mode": "static", "value_type": "decimal", "value": "100"},
        }

        evaluator = CanonicalConditionEvaluator({"doc": {"grand_total": 150}})
        self.assertTrue(evaluator.evaluate(node))

        evaluator_dec = CanonicalConditionEvaluator({"doc": {"grand_total": Decimal("150.00")}})
        self.assertTrue(evaluator_dec.evaluate(node))

    def test_short_circuit_and_group(self):
        node = {
            "type": "group",
            "operator": "and",
            "children": [
                {
                    "type": "comparison",
                    "operator": "eq",
                    "left": {
                        "mode": "variable",
                        "path": {"scope": "doc", "segments": ["status"]},
                    },
                    "right": {"mode": "static", "value_type": "string", "value": "Closed"},
                },
                {
                    # Invalid node that would fail if evaluated
                    "type": "comparison",
                    "operator": "gt",
                    "left": {
                        "mode": "variable",
                        "path": {"scope": "doc", "segments": ["non_existent"]},
                    },
                    "right": {"mode": "static", "value_type": "integer", "value": 10},
                },
            ],
        }

        evaluator = CanonicalConditionEvaluator({"doc": {"status": "Open"}})
        # Should return False without raising error on second child because first child was False
        self.assertFalse(evaluator.evaluate(node))

    def test_collection_predicate_any(self):
        node = {
            "type": "collection_predicate",
            "source": {
                "mode": "variable",
                "path": {"scope": "doc", "segments": ["items"]},
            },
            "quantifier": "any",
            "as": "item",
            "where": {
                "type": "comparison",
                "operator": "gt",
                "left": {
                    "mode": "variable",
                    "path": {"scope": "item", "segments": ["amount"]},
                },
                "right": {"mode": "static", "value_type": "decimal", "value": "500"},
            },
        }

        context = {
            "doc": {
                "items": [
                    {"amount": 100},
                    {"amount": 600},
                ]
            }
        }
        evaluator = CanonicalConditionEvaluator(context)
        self.assertTrue(evaluator.evaluate(node))

    @patch("frappe.get_meta")
    def test_metadata_operators(self, mock_get_meta):
        mock_meta = MagicMock()
        mock_meta.is_submittable = 1
        mock_meta.has_field.side_effect = lambda f: f == "status"
        mock_get_meta.return_value = mock_meta

        # is_submittable
        subm_node = {
            "type": "comparison",
            "operator": "is_submittable",
            "left": {"mode": "static", "value_type": "string", "value": "Sales Order"},
        }
        evaluator = CanonicalConditionEvaluator()
        self.assertTrue(evaluator.evaluate(subm_node))

        # has_field
        has_field_node = {
            "type": "comparison",
            "operator": "has_field",
            "left": {"mode": "static", "value_type": "string", "value": "Sales Order"},
            "right": {"mode": "static", "value_type": "string", "value": "status"},
        }
        self.assertTrue(evaluator.evaluate(has_field_node))


if __name__ == "__main__":
    unittest.main()
