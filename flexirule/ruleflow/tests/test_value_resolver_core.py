# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest

import frappe

from flexirule.ruleflow.core.value_resolver import (
	NoneResolver,
	StaticResolver,
	ValueResolver,
	VariableResolver,
	get_compiled_resolver,
	get_context_value,
)


class TestValueResolverCore(unittest.TestCase):
	def setUp(self):
		self.context = {
			"doc": frappe._dict({"name": "DocName", "details": {"color": "blue"}}),
			"vars": {"status": "Active", "count": 10},
			"item": {"id": "ITEM001"},
			"loop": {"index": 0},
			"row": {"idx": 1},
		}

	def test_get_context_value_scopes(self):
		# Test explicit scopes
		self.assertEqual(get_context_value(self.context, "doc.name"), "DocName")
		self.assertEqual(get_context_value(self.context, "vars.status"), "Active")
		self.assertEqual(get_context_value(self.context, "item.id"), "ITEM001")
		self.assertEqual(get_context_value(self.context, "loop.index"), 0)
		self.assertEqual(get_context_value(self.context, "row.idx"), 1)

	def test_get_context_value_nested(self):
		self.assertEqual(get_context_value(self.context, "doc.details.color"), "blue")
		self.assertIsNone(get_context_value(self.context, "doc.details.size"))
		self.assertIsNone(get_context_value(self.context, "doc.non_existent.path"))

	def test_get_context_value_fallback(self):
		# Fallback to doc
		self.assertEqual(get_context_value(self.context, "name"), "DocName")
		# Fallback to vars
		self.assertEqual(get_context_value(self.context, "status"), "Active")
		# Missing
		self.assertIsNone(get_context_value(self.context, "non_existent"))

	def test_get_context_value_edge_cases(self):
		self.assertIsNone(get_context_value(self.context, None))
		self.assertIsNone(get_context_value(self.context, ""))
		self.assertIsNone(get_context_value(self.context, "   "))

	def test_value_resolver_compile_basic(self):
		self.assertIsInstance(ValueResolver.compile(None), NoneResolver)

		# Static values
		self.assertIsInstance(ValueResolver.compile(123), StaticResolver)
		self.assertEqual(ValueResolver.compile(123).resolve({}), 123)

		self.assertIsInstance(ValueResolver.compile("hello"), StaticResolver)
		self.assertEqual(ValueResolver.compile("hello").resolve({}), "hello")

		# Dict with mode
		self.assertIsInstance(ValueResolver.compile({"mode": "static", "value": "val"}), StaticResolver)
		self.assertIsInstance(
			ValueResolver.compile({"mode": "variable", "path": "doc.name"}), VariableResolver
		)

	def test_value_resolver_compile_string_special(self):
		from flexirule.ruleflow.core.value_resolver import JinjaResolver, SafeEvalResolver

		# Jinja
		resolver = ValueResolver.compile("{{ doc.name }}")
		self.assertIsInstance(resolver, JinjaResolver)

		# SafeEval
		resolver = ValueResolver.compile("{ doc.name }")
		self.assertIsInstance(resolver, SafeEvalResolver)

	def test_get_compiled_resolver_caching(self):
		# Initialize local cache if not exists (usually handled by the function)
		if hasattr(frappe.local, "flexirule_compiled_resolvers"):
			delattr(frappe.local, "flexirule_compiled_resolvers")

		action = frappe._dict({"name": "test_action"})
		payload = {"mode": "static", "value": 100}

		res1 = get_compiled_resolver(action, "field1", payload)
		res2 = get_compiled_resolver(action, "field1", payload)

		self.assertIs(res1, res2)  # Should be same instance from cache

		res3 = get_compiled_resolver(action, "field2", payload)
		self.assertIsNot(res1, res3)

	def test_none_resolver(self):
		self.assertIsNone(NoneResolver().resolve({}))

	def test_static_resolver(self):
		self.assertEqual(StaticResolver("fixed").resolve({}), "fixed")
