# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.value_resolver import NormalizationResolver
from flexirule.ruleflow.utils.normalization import execute_normalization_pipeline


class TestNormalizationRefactor(FrappeTestCase):
	def test_pipeline_execution(self):
		# Test basic pipeline
		res = execute_normalization_pipeline("  Hello World  ", pipeline=["trim", "lowercase"])
		self.assertEqual(res["normalized_value"], "hello world")

		# Test profile
		res = execute_normalization_pipeline("  Hello World  ", profile="URL Safe")
		self.assertEqual(res["normalized_value"], "hello-world")

	def test_normalization_resolver(self):
		context = {"doc": {"name_field": "  John Doe  "}}

		# Test with custom pipeline
		resolver = NormalizationResolver(norm_field="doc.name_field", norm_pipeline=["trim", "uppercase"])
		self.assertEqual(resolver.resolve(context), "JOHN DOE")

		# Test with profile
		resolver = NormalizationResolver(norm_field="doc.name_field", norm_profile="URL Safe")
		self.assertEqual(resolver.resolve(context), "john-doe")

		# Test legacy fallback
		resolver = NormalizationResolver(norm_field="doc.name_field", norm_op="trim")
		self.assertEqual(resolver.resolve(context), "John Doe")

	def test_api_endpoint(self):
		from flexirule.ruleflow.api import normalize_test_value

		# Mock builder access
		frappe.set_user("Administrator")

		res = normalize_test_value("  Test Value  ", pipeline=["trim", "lowercase"])
		self.assertEqual(res["normalized_value"], "test value")
		self.assertTrue(len(res["breakdown"]) > 0)
		self.assertIn("trim", res["available_operations"])
		self.assertIn("URL Safe", res["available_profiles"])

	def test_new_utilities(self):
		# Arabic/Indic translation
		res = execute_normalization_pipeline("أحمد ١٢٣", pipeline=["translate_chars"])
		self.assertEqual(res["normalized_value"], "احمد 123")

		# Diacritics
		res = execute_normalization_pipeline("Café", pipeline=["remove_diacritics"])
		self.assertEqual(res["normalized_value"], "Cafe")

		# Phone normalization
		res = execute_normalization_pipeline("+20 123-456-789", pipeline=["phone_normalize"])
		self.assertEqual(res["normalized_value"], "+20123456789")

		res = execute_normalization_pipeline("(01) ٢٣٤-٥٦٧", pipeline=["phone_normalize"])
		self.assertEqual(res["normalized_value"], "01234567")
