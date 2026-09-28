# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import datetime
import unittest
from typing import Any, cast
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.value_resolver import (
	ChildAggregationResolver,
	DateBoundaryResolver,
	DateCurrentResolver,
	DateDiffResolver,
	DateExtractResolver,
	DateFormulaResolver,
	ExpressionResolver,
	JinjaResolver,
	SafeEvalResolver,
	StaticResolver,
	StringFormulaResolver,
	SystemContextResolver,
	ValueResolver,
	VariableResolver,
)


class TestValueResolversComplex(FrappeTestCase):
	doc_data: dict[str, Any]
	context: dict[str, Any]

	def setUp(self) -> None:
		self.doc_data = cast(
			dict[str, Any],
			{
				"creation": "2026-01-01",
				"amount": 100,
				"items": [
					{"qty": 2, "price": 10},
					{"qty": 1, "price": 20},
				],
			},
		)
		self.context = {
			"doc": self.doc_data,
			"vars": {"test_var": "test_val"},
		}

	def test_date_time_family_resolver(self):
		# 1. Date & Time Formula (calculate) via canonical family compile
		with patch("frappe.utils.nowdate", return_value="2026-01-01"):
			val_calc = {
				"family": "date_time",
				"operation": "calculate",
				"config": {
					"base_type": "today",
					"offset_value": 5,
					"offset_unit": "days",
					"offset_sign": "+",
				},
			}
			resolver = ValueResolver.compile_resolver_config(val_calc)
			self.assertEqual(str(resolver.resolve(self.context)), "2026-01-06")

		# From field + 1 month
		val_calc_field = {
			"family": "date_time",
			"operation": "calculate",
			"config": {
				"base_type": "doc_field",
				"base_field": "doc.creation",
				"offset_value": 1,
				"offset_unit": "months",
				"offset_sign": "+",
			},
		}
		resolver = ValueResolver.compile_resolver_config(val_calc_field)
		self.assertEqual(str(resolver.resolve(self.context)), "2026-02-01")

		# 2. Date & Time Difference (diff) via canonical family compile
		val_diff = {
			"family": "date_time",
			"operation": "diff",
			"config": {
				"diff_start_type": "doc_field",
				"diff_start_field": "doc.start",
				"diff_end_type": "doc_field",
				"diff_end_field": "doc.end",
				"diff_unit": "days",
			},
		}
		self.doc_data.update({"start": "2026-01-01", "end": "2026-01-11"})
		resolver = ValueResolver.compile_resolver_config(val_diff)
		self.assertEqual(resolver.resolve(self.context), 10)

		# 3. Date & Time Format (format) via canonical family compile
		val_fmt = {
			"family": "date_time",
			"operation": "format",
			"config": {
				"fmt_field": "doc.creation",
				"fmt_config": "YYYY-MM-DD",
			},
		}
		resolver = ValueResolver.compile_resolver_config(val_fmt)
		self.assertEqual(resolver.resolve(self.context), "2026-01-01")

	def test_date_formula_resolver(self):
		# Direct DateFormulaResolver test
		with patch("frappe.utils.nowdate", return_value="2026-01-01"):
			resolver = DateFormulaResolver(
				base_type="today", base_field=None, offset_value=5, offset_unit="days", offset_sign="+"
			)
			self.assertEqual(str(resolver.resolve(self.context)), "2026-01-06")

			# Today - 5 days
			resolver = DateFormulaResolver(
				base_type="today", base_field=None, offset_value=5, offset_unit="days", offset_sign="-"
			)
			self.assertEqual(str(resolver.resolve(self.context)), "2025-12-27")

		# From field + 1 month
		resolver = DateFormulaResolver(
			base_type="field",
			base_field="doc.creation",
			offset_value=1,
			offset_unit="months",
			offset_sign="+",
		)
		self.assertEqual(str(resolver.resolve(self.context)), "2026-02-01")

		# Leap year test: 2024-02-28 + 1 day
		self.doc_data["creation"] = "2024-02-28"
		resolver = DateFormulaResolver(
			base_type="field", base_field="doc.creation", offset_value=1, offset_unit="days", offset_sign="+"
		)
		self.assertEqual(str(resolver.resolve(self.context)), "2024-02-29")

		# Month rollover: 2026-01-31 + 1 month -> 2026-02-28
		self.doc_data["creation"] = "2026-01-31"
		resolver = DateFormulaResolver(
			base_type="field",
			base_field="doc.creation",
			offset_value=1,
			offset_unit="months",
			offset_sign="+",
		)
		self.assertEqual(str(resolver.resolve(self.context)), "2026-02-28")

		# Null base date
		self.doc_data["creation"] = None
		resolver = DateFormulaResolver(
			base_type="field", base_field="doc.creation", offset_value=1, offset_unit="days", offset_sign="+"
		)
		self.assertIsNone(resolver.resolve(self.context))

	def test_date_diff_resolver(self):
		# Direct DateDiffResolver test
		resolver = DateDiffResolver(
			diff_start_type="field",
			diff_start_field="doc.start",
			diff_end_type="field",
			diff_end_field="doc.end",
			diff_unit="days",
		)
		self.doc_data.update({"start": "2026-01-01", "end": "2026-01-11"})
		self.assertEqual(resolver.resolve(self.context), 10)

		# Diff in months
		self.doc_data.update({"start": "2026-01-01", "end": "2026-03-01"})
		resolver.diff_unit = "months"
		self.assertEqual(resolver.resolve(self.context), 3)

		# Diff in years
		self.doc_data.update({"start": "2026-01-01", "end": "2028-01-01"})
		resolver.diff_unit = "years"
		self.assertEqual(resolver.resolve(self.context), 2)

		# Today comparison
		with patch("frappe.utils.nowdate", return_value="2026-01-15"):
			resolver = DateDiffResolver(
				diff_start_type="field",
				diff_start_field="doc.start",
				diff_end_type="today",
				diff_end_field=None,
				diff_unit="days",
			)
			self.doc_data["start"] = "2026-01-01"
			self.assertEqual(resolver.resolve(self.context), 14)

		# Missing dates
		self.doc_data["start"] = None
		self.assertEqual(resolver.resolve(self.context), 0)

	def test_date_time_current_resolver(self):
		with patch("frappe.utils.nowdate", return_value="2026-01-15"):
			with patch("frappe.utils.now_datetime", return_value=datetime.datetime(2026, 1, 15, 10, 30, 0)):
				with patch("frappe.utils.nowtime", return_value="10:30:00"):
					res_date = ValueResolver.compile_resolver_config(
						{"family": "date_time", "operation": "current", "config": {"token": "date"}}
					).resolve(self.context)
					self.assertIsInstance(res_date, datetime.date)
					self.assertEqual(res_date, datetime.date(2026, 1, 15))

					res_dt = ValueResolver.compile_resolver_config(
						{"family": "date_time", "operation": "current", "config": {"token": "datetime"}}
					).resolve(self.context)
					self.assertIsInstance(res_dt, datetime.datetime)
					self.assertEqual(res_dt, datetime.datetime(2026, 1, 15, 10, 30, 0))

					res_time = ValueResolver.compile_resolver_config(
						{"family": "date_time", "operation": "current", "config": {"token": "time"}}
					).resolve(self.context)
					self.assertIsInstance(res_time, datetime.time)
					self.assertEqual(res_time, datetime.time(10, 30, 0))

	def test_date_formula_extended(self):
		doc = self.doc_data
		# Datetime + minutes and seconds
		doc["created_at"] = "2026-01-01 12:00:00"
		val_calc = {
			"family": "date_time",
			"operation": "calculate",
			"config": {
				"base_type": "doc_field",
				"base_field": "doc.created_at",
				"offset_value": 30,
				"offset_unit": "minutes",
				"offset_sign": "+",
			},
		}
		resolver = ValueResolver.compile_resolver_config(val_calc)
		self.assertEqual(resolver.resolve(self.context), datetime.datetime(2026, 1, 1, 12, 30, 0))

		# Datetime - 45 seconds
		val_calc_cfg = cast(dict[str, Any], val_calc["config"])
		val_calc_cfg["offset_value"] = 45
		val_calc_cfg["offset_unit"] = "seconds"
		val_calc_cfg["offset_sign"] = "-"
		resolver = ValueResolver.compile_resolver_config(val_calc)
		self.assertEqual(resolver.resolve(self.context), datetime.datetime(2026, 1, 1, 11, 59, 15))

		# Time + 90 minutes
		doc["shift_start"] = "10:00:00"
		val_calc_time = {
			"family": "date_time",
			"operation": "calculate",
			"config": {
				"base_type": "doc_field",
				"base_field": "doc.shift_start",
				"offset_value": 90,
				"offset_unit": "minutes",
				"offset_sign": "+",
			},
		}
		resolver = ValueResolver.compile_resolver_config(val_calc_time)
		self.assertEqual(resolver.resolve(self.context), datetime.time(11, 30, 0))

		# Dynamic offset from variable
		doc["payment_terms_days"] = 15
		val_dynamic = {
			"family": "date_time",
			"operation": "calculate",
			"config": {
				"base_type": "doc_field",
				"base_field": "doc.creation",
				"offset_value": "doc.payment_terms_days",
				"offset_unit": "days",
				"offset_sign": "+",
			},
		}
		doc["creation"] = "2026-01-01"
		resolver = ValueResolver.compile_resolver_config(val_dynamic)
		self.assertEqual(resolver.resolve(self.context), datetime.date(2026, 1, 16))

	def test_date_diff_extended(self):
		# Duration diff across midnight
		self.doc_data.update(
			{
				"start_time": "2026-01-01 23:59:00",
				"end_time": "2026-01-02 00:01:00",
			}
		)
		# Seconds
		val_diff_sec = {
			"family": "date_time",
			"operation": "diff",
			"config": {
				"diff_start_type": "doc_field",
				"diff_start_field": "doc.start_time",
				"diff_end_type": "doc_field",
				"diff_end_field": "doc.end_time",
				"diff_unit": "seconds",
			},
		}
		resolver = ValueResolver.compile_resolver_config(val_diff_sec)
		self.assertEqual(resolver.resolve(self.context), 120)

		# Minutes
		val_diff_cfg = cast(dict[str, Any], val_diff_sec["config"])
		val_diff_cfg["diff_unit"] = "minutes"
		resolver = ValueResolver.compile_resolver_config(val_diff_sec)
		self.assertEqual(resolver.resolve(self.context), 2.0)

		# Calendar day diff
		val_diff_cfg["diff_unit"] = "days"
		resolver = ValueResolver.compile_resolver_config(val_diff_sec)
		self.assertEqual(resolver.resolve(self.context), 1)

	def test_date_extract_resolver(self):
		doc = self.doc_data
		# Date input extractions
		doc["posting_date"] = "2026-02-15"
		for comp, expected in [("year", 2026), ("month", 2), ("day", 15), ("weekday", 7), ("quarter", 1)]:
			val_extract = {
				"family": "date_time",
				"operation": "extract",
				"config": {"source": "doc.posting_date", "component": comp},
			}
			resolver = ValueResolver.compile_resolver_config(val_extract)
			self.assertEqual(resolver.resolve(self.context), expected, f"Failed on {comp}")

		# Datetime input extractions
		doc["log_time"] = "2026-02-15 14:35:50"
		for comp, expected in [("hour", 14), ("minute", 35), ("second", 50)]:
			val_extract = {
				"family": "date_time",
				"operation": "extract",
				"config": {"source": "doc.log_time", "component": comp},
			}
			resolver = ValueResolver.compile_resolver_config(val_extract)
			self.assertEqual(resolver.resolve(self.context), expected, f"Failed on {comp}")

		# Invalid component/type combinations
		# Extract hour from Date -> None
		val_invalid = {
			"family": "date_time",
			"operation": "extract",
			"config": {"source": "doc.posting_date", "component": "hour"},
		}
		resolver = ValueResolver.compile_resolver_config(val_invalid)
		self.assertIsNone(resolver.resolve(self.context))

		# Extract year from Time -> None
		doc["pure_time"] = "10:30:00"
		val_invalid_time = {
			"family": "date_time",
			"operation": "extract",
			"config": {"source": "doc.pure_time", "component": "year"},
		}
		resolver = ValueResolver.compile_resolver_config(val_invalid_time)
		self.assertIsNone(resolver.resolve(self.context))

	def test_date_boundary_resolver(self):
		# Date boundaries
		self.doc_data["posting_date"] = "2026-02-15"
		# start_of_month -> 2026-02-01
		res = ValueResolver.compile_resolver_config(
			{
				"family": "date_time",
				"operation": "boundary",
				"config": {"source": "doc.posting_date", "boundary_type": "start_of_month"},
			}
		).resolve(self.context)
		self.assertEqual(res, datetime.date(2026, 2, 1))

		# end_of_month -> 2026-02-28
		res = ValueResolver.compile_resolver_config(
			{
				"family": "date_time",
				"operation": "boundary",
				"config": {"source": "doc.posting_date", "boundary_type": "end_of_month"},
			}
		).resolve(self.context)
		self.assertEqual(res, datetime.date(2026, 2, 28))

		# start_of_year -> 2026-01-01
		res = ValueResolver.compile_resolver_config(
			{
				"family": "date_time",
				"operation": "boundary",
				"config": {"source": "doc.posting_date", "boundary_type": "start_of_year"},
			}
		).resolve(self.context)
		self.assertEqual(res, datetime.date(2026, 1, 1))

		# Datetime boundaries
		self.doc_data["log_time"] = "2026-02-15 14:35:50"
		# start_of_day -> 2026-02-15 00:00:00
		res = ValueResolver.compile_resolver_config(
			{
				"family": "date_time",
				"operation": "boundary",
				"config": {"source": "doc.log_time", "boundary_type": "start_of_day"},
			}
		).resolve(self.context)
		self.assertEqual(res, datetime.datetime(2026, 2, 15, 0, 0, 0))

		# end_of_day -> 2026-02-15 23:59:59
		res = ValueResolver.compile_resolver_config(
			{
				"family": "date_time",
				"operation": "boundary",
				"config": {"source": "doc.log_time", "boundary_type": "end_of_day"},
			}
		).resolve(self.context)
		self.assertEqual(res, datetime.datetime(2026, 2, 15, 23, 59, 59))

		# end_of_month on Datetime -> 2026-02-28 23:59:59
		res = ValueResolver.compile_resolver_config(
			{
				"family": "date_time",
				"operation": "boundary",
				"config": {"source": "doc.log_time", "boundary_type": "end_of_month"},
			}
		).resolve(self.context)
		self.assertEqual(res, datetime.datetime(2026, 2, 28, 23, 59, 59))

	def test_system_settings_week_boundary_and_iso_weekday(self):
		# Test date: 2026-02-15 is a Sunday
		self.doc_data["posting_date"] = "2026-02-15"
		self.doc_data["log_time"] = "2026-02-15 14:35:50"

		# 1. extract(weekday) returns ISO 1-7 (Sunday = 7)
		res_extract = ValueResolver.compile_resolver_config(
			{
				"family": "date_time",
				"operation": "extract",
				"config": {"source": "doc.posting_date", "component": "weekday"},
			}
		).resolve(self.context)
		self.assertEqual(res_extract, 7)

		# 2. start_of_week and end_of_week follow Frappe System Settings
		with patch("frappe.get_system_settings", return_value="Sunday"):
			frappe.clear_cache()
			res_start_sun = ValueResolver.compile_resolver_config(
				{
					"family": "date_time",
					"operation": "boundary",
					"config": {"source": "doc.posting_date", "boundary_type": "start_of_week"},
				}
			).resolve(self.context)
			self.assertEqual(res_start_sun, datetime.date(2026, 2, 15))
			self.assertIsInstance(res_start_sun, datetime.date)

			res_end_sun = ValueResolver.compile_resolver_config(
				{
					"family": "date_time",
					"operation": "boundary",
					"config": {"source": "doc.posting_date", "boundary_type": "end_of_week"},
				}
			).resolve(self.context)
			self.assertEqual(res_end_sun, datetime.date(2026, 2, 21))

		# 3. Test when first_day_of_the_week is "Monday"
		with patch("frappe.get_system_settings", return_value="Monday"):
			frappe.clear_cache()
			res_start_mon = ValueResolver.compile_resolver_config(
				{
					"family": "date_time",
					"operation": "boundary",
					"config": {"source": "doc.posting_date", "boundary_type": "start_of_week"},
				}
			).resolve(self.context)
			self.assertEqual(res_start_mon, datetime.date(2026, 2, 9))

			res_end_mon = ValueResolver.compile_resolver_config(
				{
					"family": "date_time",
					"operation": "boundary",
					"config": {"source": "doc.posting_date", "boundary_type": "end_of_week"},
				}
			).resolve(self.context)
			self.assertEqual(res_end_mon, datetime.date(2026, 2, 15))

			# 4. Verify extract(weekday) remains ISO 7 (Sunday) even when system first_day is Monday
			res_extract_mon = ValueResolver.compile_resolver_config(
				{
					"family": "date_time",
					"operation": "extract",
					"config": {"source": "doc.posting_date", "component": "weekday"},
				}
			).resolve(self.context)
			self.assertEqual(res_extract_mon, 7)

			# 5. Datetime week boundary returns Datetime
			res_dt_start = ValueResolver.compile_resolver_config(
				{
					"family": "date_time",
					"operation": "boundary",
					"config": {"source": "doc.log_time", "boundary_type": "start_of_week"},
				}
			).resolve(self.context)
			self.assertIsInstance(res_dt_start, datetime.datetime)
			self.assertEqual(res_dt_start, datetime.datetime(2026, 2, 9, 0, 0, 0))

			res_dt_end = ValueResolver.compile_resolver_config(
				{
					"family": "date_time",
					"operation": "boundary",
					"config": {"source": "doc.log_time", "boundary_type": "end_of_week"},
				}
			).resolve(self.context)
			self.assertIsInstance(res_dt_end, datetime.datetime)
			self.assertEqual(res_dt_end, datetime.datetime(2026, 2, 15, 23, 59, 59))

	def test_child_aggregation_resolver(self):
		# Sum
		resolver = ChildAggregationResolver(agg_table="doc.items", agg_field="qty", agg_op="sum")
		self.assertEqual(resolver.resolve(self.context), 3.0)

		# Count
		resolver.agg_op = "count"
		self.assertEqual(resolver.resolve(self.context), 2)

		# Avg
		resolver.agg_op = "avg"
		self.assertEqual(resolver.resolve(self.context), 1.5)

		# Empty table
		self.doc_data["items"] = []
		resolver.agg_op = "sum"
		self.assertEqual(resolver.resolve(self.context), 0)

		# Table is None
		self.doc_data["items"] = None
		self.assertEqual(resolver.resolve(self.context), 0)

		# agg_field is None for some rows
		self.doc_data["items"] = [{"qty": 5}, {"other": 10}]
		resolver.agg_op = "sum"
		self.assertEqual(resolver.resolve(self.context), 5.0)

	def test_text_transform_resolver(self):
		# Combine operation via ValueResolver.compile
		val_combine = {
			"family": "text",
			"operation": "combine",
			"config": {
				"str_a_type": "field",
				"str_a": "doc.first",
				"str_b_type": "field",
				"str_b": "doc.last",
			},
		}
		self.doc_data.update({"first": "John", "last": "Doe"})
		resolver = ValueResolver.compile_resolver_config(val_combine)
		self.assertEqual(resolver.resolve(self.context), "JohnDoe")

		# Case operation
		val_case = {
			"family": "text",
			"operation": "case",
			"config": {"field": "doc.first", "case_mode": "uppercase"},
		}
		resolver = ValueResolver.compile_resolver_config(val_case)
		self.assertEqual(resolver.resolve(self.context), "JOHN")

		# Normalize operation
		val_norm = {
			"family": "text",
			"operation": "normalize",
			"config": {"norm_field": "doc.raw", "norm_pipeline": ["trim", "lowercase"]},
		}
		self.doc_data["raw"] = "  HELLO WORLD  "
		resolver = ValueResolver.compile_resolver_config(val_norm)
		self.assertEqual(resolver.resolve(self.context), "hello world")

		# Format operation
		val_fmt = {
			"family": "text",
			"operation": "format",
			"config": {"fmt_field": "doc.first", "fmt_config": "Hello {0}!"},
		}
		resolver = ValueResolver.compile_resolver_config(val_fmt)
		self.assertEqual(resolver.resolve(self.context), "Hello John!")

	def test_system_context_resolver(self):
		# User
		# Use frappe.session directly instead of patching a member that might be a property or None
		with patch("frappe.session", frappe._dict({"user": "test@example.com"})):
			resolver = SystemContextResolver(sys_token="user", sys_role="")
			self.assertEqual(resolver.resolve(self.context), "test@example.com")

		# Role check
		with patch("frappe.get_roles", return_value=["System Manager", "Rule Manager"]):
			with patch("frappe.session", frappe._dict({"user": "test@example.com"})):
				resolver = SystemContextResolver(sys_token="role_check", sys_role="System Manager")
				self.assertTrue(resolver.resolve(self.context))

				resolver = SystemContextResolver(sys_token="role_check", sys_role="Guest")
				self.assertFalse(resolver.resolve(self.context))

	def test_jinja_resolver(self):
		resolver = JinjaResolver(template="Hello {{ doc.first }}!")
		self.doc_data["first"] = "Jules"
		self.assertEqual(resolver.resolve(self.context), "Hello Jules!")

	def test_safe_eval_resolver(self):
		resolver = SafeEvalResolver(expression="doc.amount * 2")
		self.doc_data["amount"] = 50
		self.assertEqual(resolver.resolve(self.context), 100)

	def test_expression_resolver(self):
		# Mixed text and variable
		segments = [StaticResolver("Val: "), VariableResolver("vars.test_var"), StaticResolver("!")]
		resolver = ExpressionResolver(segments)
		self.assertEqual(resolver.resolve(self.context), "Val: test_val!")

		# None handling in expression
		segments.append(VariableResolver("non_existent"))
		self.assertEqual(resolver.resolve(self.context), "Val: test_val!")

	def test_value_resolver_compile_expression_complex(self):
		# Test compiling a complex expression with various token types
		val = {
			"mode": "expression",
			"value": [
				{"type": "text", "value": "Name: "},
				{
					"type": "resolverToken",
					"attrs": {
						"config": {
							"family": "text",
							"operation": "format",
							"config": {
								"fmt_field": "doc.first",
								"fmt_config": "{0}",
							},
						}
					},
				},
				{"type": "text", "value": " - "},
				{"type": "jsonToken", "attrs": {"value": "{{ doc.first }}"}},
			],
		}
		self.doc_data.update({"first": "Jules"})
		resolver = ValueResolver.compile(val)
		self.assertIsInstance(resolver, ExpressionResolver)
		self.assertEqual(resolver.resolve(self.context), "Name: Jules - Jules")

	def test_value_resolver_compile_resolver_token_eval(self):
		# Test resolverToken with expression/resolver instead of config
		val = {
			"mode": "expression",
			"value": [{"type": "resolverToken", "attrs": {"expression": "doc.amount + 10"}}],
		}
		self.doc_data["amount"] = 90
		resolver = ValueResolver.compile(val)
		self.assertEqual(resolver.resolve(self.context), "100")
