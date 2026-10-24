# Copyright (c) 2026, FlexiRule and contributors

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import _is_output_schema_field


class TestQueryDocOutputSchemaFields(FrappeTestCase):
	@patch("flexirule.ruleflow.api.frappe.model.no_value_fields", ["Section Break", "Column Break"])
	def test_excludes_layout_fields_even_when_not_in_frappe_no_value_list(self):
		for fieldtype in ("Tab Break", "Section Break", "Column Break", "HTML", "Fold", "Heading"):
			with self.subTest(fieldtype=fieldtype):
				self.assertFalse(_is_output_schema_field(frappe._dict({"fieldtype": fieldtype})))

	def test_keeps_data_fields(self):
		for fieldtype in ("Data", "Link", "Date", "Check", "Table"):
			with self.subTest(fieldtype=fieldtype):
				self.assertTrue(_is_output_schema_field({"fieldtype": fieldtype}))
