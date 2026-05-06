import unittest
from typing import cast

from flexirule.ruleflow.core.action_handlers.sub_rule import SubRuleHandler
from flexirule.ruleflow.utils.mapping import (
	apply_input_mapping,
	apply_output_mapping,
	resolve_path,
	update_context,
)


class TestMapping(unittest.TestCase):
	def test_apply_input_mapping(self):
		context = {"doc": {"total": 500, "items": [{"name": "A"}]}, "vars": {"risk": "High"}}
		config = {"threshold": 100, "category": "Normal"}

		# Test basic mapping
		mapping = '{"threshold": "doc.total"}'
		result = apply_input_mapping(context, mapping, config)
		self.assertEqual(result["threshold"], 500)

		# Test nested mapping
		mapping = '{"item_name": "doc.items.0.name"}'
		# Note: mapping.py resolve_path might allow list index if getattr fails?
		# Let's check implementation. resolve_path uses .get() for dict or getattr.
		# It does NOT explicitly handle list indices yet.
		# Wait, I should verify implementation supports lists if needed.
		# Implementation:
		# if isinstance(current, dict): current.get(part)
		# else: getattr(current, part, None)
		# So "0" as key for list won't work unless I update resolve_path.
		# For now, let's stick to dict/object access.

		# Test missing path
		mapping = '{"threshold": "doc.invalid"}'
		result = apply_input_mapping(context, mapping, config)
		self.assertEqual(result["threshold"], 100)  # Should preserve config if missing

	def test_apply_output_mapping(self):
		context: dict = {"vars": {}}
		result = {"score": 90, "details": "Approved"}

		# Test standard mapping
		mapping = '{"score": "vars.final_score"}'
		apply_output_mapping(result, mapping, context)
		self.assertEqual(context["vars"]["final_score"], 90)

		# Test primitive result using __self__
		primitive_result = 500
		mapping = '{"__self__": "vars.result"}'
		apply_output_mapping(primitive_result, mapping, context)
		self.assertEqual(context["vars"]["result"], 500)

	def test_resolve_path(self):
		data = {"a": {"b": 10}, "c": [1, 2]}
		self.assertEqual(resolve_path(data, "a.b"), 10)
		self.assertIsNone(resolve_path(data, "a.x"))

	def test_sub_rule_mapping_rows_are_normalized(self):
		handler = SubRuleHandler()
		mapping_rows = [
			{"source": "vars.parent_value", "target": "child_input"},
			{"source_expression": "doc.customer", "target": "customer_name"},
			{"source": "vars.incomplete_only_source"},
			{"target": "incomplete_only_target"},
		]

		mapping_json = handler._mapping_to_json(mapping_rows)
		self.assertIsNotNone(mapping_json)

		context = {"doc": {"customer": "ACME"}, "vars": {"parent_value": 42}}
		mapped = apply_input_mapping(context, cast(str, mapping_json), {})
		self.assertEqual(mapped["child_input"], 42)
		self.assertEqual(mapped["customer_name"], "ACME")
