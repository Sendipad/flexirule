# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler


class TestFetchRecords(FrappeTestCase):
	"""Backend tests for 'Fetch Records' operation backed by frappe.qb.get_query."""

	def setUp(self):
		self.handler = QueryRecordsHandler()

	def tearDown(self):
		frappe.db.rollback()

	def test_basic_fetch_records_default_fields(self):
		prefix = f"FetchBasic_{random_string(5)}"
		t1 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_1"}).insert(ignore_permissions=True)
		t2 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_2"}).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [["ToDo", "description", "like", f"{prefix}%"]],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsInstance(result, list)
		self.assertGreaterEqual(len(result), 2)
		names = [d.get("name") for d in result]
		self.assertIn(t1.name, names)
		self.assertIn(t2.name, names)

	def test_explicit_fields_and_aliases(self):
		prefix = f"FetchFields_{random_string(5)}"
		t1 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_1", "status": "Open"}).insert(
			ignore_permissions=True
		)

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": ["name", "description as task_desc", "status"],
						"filters": [["ToDo", "description", "=", f"{prefix}_1"]],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertEqual(len(result), 1)
		row = result[0]
		self.assertEqual(row.get("name"), t1.name)
		self.assertEqual(row.get("task_desc"), f"{prefix}_1")
		self.assertEqual(row.get("status"), "Open")

	def test_literal_column_adds_static_and_dynamic_values(self):
		prefix = f"FetchLiteral_{random_string(5)}"
		frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_static", "status": "Open"}).insert(
			ignore_permissions=True
		)
		frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_dynamic", "status": "Open"}).insert(
			ignore_permissions=True
		)

		fields = [
			"name",
			{
				"kind": "literal",
				"fieldname": "document_type",
				"label": "Document Type",
				"fieldtype": "Data",
				"reqd": 0,
				"value_spec": {"mode": "static", "value": "Sales Invoice"},
			},
			{
				"kind": "literal",
				"fieldname": "party_kind",
				"label": "Party Kind",
				"fieldtype": "Data",
				"reqd": 0,
				"value_spec": {"mode": "variable", "value": "vars.party_kind"},
			},
		]
		action = frappe._dict(
			{
				"name": f"test-fetch-literal-{prefix}",
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": fields,
						"filters": [["ToDo", "description", "like", f"{prefix}%"]],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {"vars": {"party_kind": "Customer"}}, None)
		self.assertEqual(len(result), 2)
		self.assertEqual({row["document_type"] for row in result}, {"Sales Invoice"})
		self.assertEqual({row["party_kind"] for row in result}, {"Customer"})
		self.assertTrue(all(row.get("name") for row in result))

	def test_literal_integer_column_coerces_to_integer(self):
		prefix = f"FetchLiteralInt_{random_string(5)}"
		frappe.get_doc({"doctype": "ToDo", "description": prefix}).insert(ignore_permissions=True)
		action = frappe._dict(
			{
				"name": f"test-fetch-literal-int-{prefix}",
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": [
							"name",
							{
								"kind": "literal",
								"fieldname": "source_count",
								"label": "Source Count",
								"fieldtype": "Int",
								"value_spec": {"mode": "static", "value": "3"},
							},
						],
						"filters": [["ToDo", "description", "=", prefix]],
					}
				),
			}
		)
		result, _ = self.handler.execute(action, {}, None)
		self.assertEqual(result[0]["source_count"], 3)
		self.assertIsInstance(result[0]["source_count"], int)

	def test_literal_column_cannot_overwrite_selected_field(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": [
							"name",
							{
								"kind": "literal",
								"fieldname": "name",
								"label": "Overwritten Name",
								"fieldtype": "Data",
								"value_spec": {"mode": "static", "value": "unsafe"},
							},
						],
					}
				),
			}
		)
		with self.assertRaises(frappe.ValidationError):
			self.handler.execute(action, {}, None)

	def test_filter_operators(self):
		prefix = f"FetchOps_{random_string(5)}"
		t1 = frappe.get_doc(
			{"doctype": "ToDo", "description": f"{prefix}_A", "priority": "High", "status": "Open"}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{"doctype": "ToDo", "description": f"{prefix}_B", "priority": "Low", "status": "Closed"}
		).insert(ignore_permissions=True)

		# 1. Equals & Not Equals
		action_eq = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [
							["ToDo", "description", "like", f"{prefix}%"],
							["ToDo", "status", "!=", "Closed"],
						]
					}
				),
			}
		)
		res_eq, _ = self.handler.execute(action_eq, {}, None)
		self.assertEqual(len(res_eq), 1)
		self.assertEqual(res_eq[0].get("name"), t1.name)

		# 2. In & Like
		action_in = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [
							["ToDo", "description", "like", f"{prefix}%"],
							["ToDo", "priority", "in", ["High", "Medium"]],
						]
					}
				),
			}
		)
		res_in, _ = self.handler.execute(action_in, {}, None)
		self.assertEqual(len(res_in), 1)
		self.assertEqual(res_in[0].get("name"), t1.name)

	def test_nested_logical_filters_and_or(self):
		prefix = f"FetchLogic_{random_string(5)}"
		t1 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_alpha", "status": "Open"}).insert(
			ignore_permissions=True
		)
		t2 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_beta", "status": "Closed"}).insert(
			ignore_permissions=True
		)
		t3 = frappe.get_doc(
			{"doctype": "ToDo", "description": f"{prefix}_gamma", "status": "Cancelled"}
		).insert(ignore_permissions=True)

		# Tree: description starts with prefix AND (status = 'Open' OR status = 'Closed')
		filter_tree = [
			["ToDo", "description", "like", f"{prefix}%"],
			"and",
			[
				["ToDo", "status", "=", "Open"],
				"or",
				["ToDo", "status", "=", "Closed"],
			],
		]

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json({"filters": filter_tree}),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertEqual(len(result), 2)
		names = [r.get("name") for r in result]
		self.assertIn(t1.name, names)
		self.assertIn(t2.name, names)
		self.assertNotIn(t3.name, names)

	def test_canonical_filter_tree_is_converted_at_backend_boundary(self):
		prefix = f"FetchCanonical_{random_string(5)}"
		t1 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_open", "status": "Open"}).insert(
			ignore_permissions=True
		)
		frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_closed", "status": "Closed"}).insert(
			ignore_permissions=True
		)

		filter_tree = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "leaf",
					"doctype": "ToDo",
					"field": "description",
					"operator": "like",
					"value": {"mode": "static", "value": f"{prefix}%"},
				},
				{
					"type": "group",
					"operator": "or",
					"children": [
						{
							"type": "leaf",
							"doctype": "ToDo",
							"field": "status",
							"operator": "=",
							"value": {"mode": "static", "value": "Open"},
						},
						{
							"type": "leaf",
							"doctype": "ToDo",
							"field": "status",
							"operator": "=",
							"value": {"mode": "static", "value": "Pending"},
						},
					],
				},
			],
		}

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json({"filters": filter_tree}),
			}
		)
		result, _ = self.handler.execute(action, {}, None)

		self.assertEqual([row.get("name") for row in result], [t1.name])

	def test_child_table_field_query_and_distinct(self):
		# Test querying child table field (e.g. roles.role on User)
		user_email = f"fetch_child_{random_string(5).lower()}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user_email,
				"first_name": "Fetch Child Test",
				"roles": [
					{"role": "System Manager"},
					{"role": "Script Manager"},
				],
			}
		).insert(ignore_permissions=True)

		# Query with child table filter 'roles.role' (not in fields) and distinct=True
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "User",
				"config": frappe.as_json(
					{
						"fields": ["name", "email"],
						"filters": [
							["User", "email", "=", user_email],
							["roles.role", "like", "%Manager%"],
						],
						"distinct": True,
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertGreaterEqual(len(result), 1)
		self.assertEqual(result[0].get("email"), user_email)

	def test_ordering_limit_and_offset(self):
		prefix = f"FetchPage_{random_string(5)}"
		frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_1"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_2"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_3"}).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": ["name", "description"],
						"filters": [["ToDo", "description", "like", f"{prefix}%"]],
						"order_by": "description asc",
						"limit": 2,
						"offset": 1,
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertEqual(len(result), 2)
		self.assertEqual(result[0].get("description"), f"{prefix}_2")
		self.assertEqual(result[1].get("description"), f"{prefix}_3")

	def test_dynamic_values_resolution(self):
		prefix = f"FetchDyn_{random_string(5)}"
		t1 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_target", "status": "Open"}).insert(
			ignore_permissions=True
		)

		context = {
			"vars": {
				"target_pattern": f"{prefix}_target",
				"max_count": 5,
				"sort_col": "description asc",
			}
		}

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": ["name", "description"],
						"filters": [["ToDo", "description", "=", "{vars.target_pattern}"]],
						"order_by": "{vars.sort_col}",
						"limit": "{vars.max_count}",
					}
				),
			}
		)

		result, _ = self.handler.execute(action, context, None)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0].get("name"), t1.name)

	def test_permissions_behavior(self):
		# Verify permission check executes when ignore_permissions=False
		action_restricted = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "User",
				"ignore_permissions": 0,
				"config": frappe.as_json({"limit": 1}),
			}
		)

		from flexirule.ruleflow.utils.frappe_query_compat import QUERY_CAPABILITIES

		expected_error = (
			frappe.PermissionError
			if QUERY_CAPABILITIES.supports_ignore_permissions
			else frappe.ValidationError
		)
		frappe.set_user("Guest")
		try:
			with self.assertRaises(expected_error):
				self.handler.execute(action_restricted, {}, None)
		finally:
			frappe.set_user("Administrator")

		# System Manager with ignore_permissions=True succeeds
		action_allowed = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "User",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated system query",
				"config": frappe.as_json({"limit": 1}),
			}
		)
		res, _ = self.handler.execute(action_allowed, {}, None)
		self.assertIsInstance(res, list)

	def test_nested_filter_validation(self):
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [
							["status", "=", "Open"],
							"and",
							[
								["description", "like", "%task%"],
								"or",
								["missing_nested_field", "=", "x"],
							],
						]
					}
				),
			}
		)
		errs = self.handler.validate(action, {})
		self.assertTrue(any("missing_nested_field" in e for e in errs))

	def test_validation_rules(self):
		# 1. Non-existent DocType
		action_bad_dt = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "NonExistentDocType",
				"config": frappe.as_json({}),
			}
		)
		errs = self.handler.validate(action_bad_dt, {})
		self.assertTrue(any("does not exist" in e for e in errs))

		# 2. Non-existent field
		action_bad_field = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json({"fields": ["non_existent_column"]}),
			}
		)
		errs = self.handler.validate(action_bad_field, {})
		self.assertTrue(any("does not exist" in e for e in errs))

		# 3. Invalid limit
		action_bad_limit = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json({"limit": -5}),
			}
		)
		errs = self.handler.validate(action_bad_limit, {})
		self.assertTrue(any("non-negative integer" in e for e in errs))

	def test_fetch_records_starts_with_and_ends_with_wildcards(self):
		prefix = f"Inv_{random_string(5)}"
		t1 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_invoice"}).insert(
			ignore_permissions=True
		)
		t2 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_invoice-001"}).insert(
			ignore_permissions=True
		)
		t3 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_pre-invoice"}).insert(
			ignore_permissions=True
		)
		t4 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_pre-invoice-post"}).insert(
			ignore_permissions=True
		)

		# 'starts with' operator
		action_starts = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [["ToDo", "description", "starts with", f"{prefix}_invoice"]],
					}
				),
			}
		)
		res_starts, _ = self.handler.execute(action_starts, {}, None)
		names_starts = {r.get("name") for r in res_starts}
		self.assertEqual(names_starts, {t1.name, t2.name})
		self.assertNotIn(t4.name, names_starts)

		# 'ends with' operator
		action_ends = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [["ToDo", "description", "ends with", "invoice"]],
					}
				),
			}
		)
		res_ends, _ = self.handler.execute(action_ends, {}, None)
		names_ends = {r.get("name") for r in res_ends}
		self.assertEqual(names_ends, {t1.name, t3.name})
		self.assertNotIn(t4.name, names_ends)

	def test_fetch_records_boolean_coercion_end_to_end(self):
		prefix = f"BoolCoerce_{random_string(5)}"
		t_open = frappe.get_doc(
			{"doctype": "ToDo", "description": f"{prefix}_open", "status": "Open"}
		).insert(ignore_permissions=True)
		t_closed = frappe.get_doc(
			{"doctype": "ToDo", "description": f"{prefix}_closed", "status": "Closed"}
		).insert(ignore_permissions=True)

		# UI structured value payload for boolean status/check filtering
		action_true = frappe._dict(
			{
				"operation": "Fetch Records",
				"ignore_permissions": 1,
				"permission_audit_reason": "Automated test query",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [
							["ToDo", "description", "like", f"{prefix}%"],
							[
								"ToDo",
								"status",
								"=",
								{"value": "Open", "value_type": "Value"},
							],
						],
					}
				),
			}
		)
		res_true, _ = self.handler.execute(action_true, {}, None)
		res_names = {r.get("name") for r in res_true}
		self.assertEqual(res_names, {t_open.name})
		self.assertNotIn(t_closed.name, res_names)

	def test_dynamic_limit_is_not_capped_after_resolution(self):
		from unittest.mock import patch

		limit = 1_000_001
		context = {"vars": {"max_count": limit}}
		action = frappe._dict({"label": "Dynamic limit test"})
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.execute_query",
			return_value=[],
		) as execute_query:
			self.handler._fetch_records(
				reference_doctype="ToDo",
				config={"limit": "{vars.max_count}"},
				context=context,
				action=action,
				ignore_permissions=True,
			)

		self.assertEqual(execute_query.call_args.args[1]["limit"], limit)

	def test_fetch_records_does_not_inject_a_backend_limit_default(self):
		from unittest.mock import patch

		action = frappe._dict({"label": "No default limit test"})
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.execute_query",
			return_value=[],
		) as execute_query:
			self.handler._fetch_records(
				reference_doctype="ToDo",
				config={},
				context={},
				action=action,
				ignore_permissions=True,
			)

		self.assertNotIn("limit", execute_query.call_args.args[1])

	def test_resolved_output_field_is_validated_before_query_execution(self):
		from unittest.mock import patch

		action = frappe._dict({"label": "Dynamic field test"})
		context = {"vars": {"output_field": "definitely_missing_field"}}
		with patch("flexirule.ruleflow.utils.frappe_query_compat.execute_query") as execute_query:
			with self.assertRaises(frappe.ValidationError):
				self.handler._fetch_records(
					reference_doctype="ToDo",
					config={"fields": ["{vars.output_field}"]},
					context=context,
					action=action,
					ignore_permissions=True,
				)
		execute_query.assert_not_called()

	def test_validate_fetch_records_accepts_large_static_limit(self):
		action = frappe._dict({"reference_doctype": "ToDo"})
		errors = self.handler.validate_fetch_records(action, {"limit": 1_000_001})
		self.assertFalse(any("cannot exceed" in error for error in errors))

	def test_zero_limit_returns_no_rows_without_querying(self):
		from unittest.mock import patch

		action = frappe._dict({"label": "Zero limit test"})
		with patch("flexirule.ruleflow.utils.frappe_query_compat.execute_query") as execute_query:
			result = self.handler._fetch_records(
				reference_doctype="ToDo",
				config={"limit": 0},
				context={},
				action=action,
				ignore_permissions=True,
			)

		self.assertEqual(result, [])
		execute_query.assert_not_called()

	def test_frappe15_fetch_records_contract_defaults_skip_permissions_for_new_actions(self):
		from unittest.mock import patch

		from flexirule.ruleflow.utils.frappe_query_compat import FrappeQueryCapabilities

		with patch(
			"flexirule.ruleflow.core.action_handlers.query_records.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			contract = self.handler.get_operation_contracts()["Fetch Records"]

		permission_overrides = [
			override
			for override in contract.action_overrides
			if override.get("fieldname") == "ignore_permissions"
		]
		self.assertTrue(any(override.get("default") == 1 for override in permission_overrides))

	def test_canonical_filter_validator_accepts_nested_set_operators_from_ui(self):
		operators = (
			"descendants of",
			"descendants of (inclusive)",
			"not descendants of",
			"ancestors of",
			"not ancestors of",
		)
		for operator in operators:
			with self.subTest(operator=operator):
				errors = self.handler._validate_canonical_fetch_filter_tree(
					{
						"type": "leaf",
						"field": "name",
						"operator": operator,
						"value": {"mode": "static", "value": "ToDo-example"},
					}
				)
				self.assertEqual(errors, [], msg=operator)

	def test_fetch_records_rejects_child_table_aggregate_field(self):
		errors = self.handler._validate_doctype_field_references(
			"User", {"fields": ["count(roles.role) as role_count"]}
		)
		self.assertTrue(any("child/link aggregates are unsupported" in error for error in errors))

	def test_fetch_records_rejects_empty_and_malformed_filter_trees(self):
		cases = [
			(
				{"type": "group", "operator": "and", "children": []},
				"children must be a non-empty list",
			),
			(
				{"type": "unknown", "operator": "and", "children": []},
				"valid canonical filter tree",
			),
			(
				{
					"type": "group",
					"operator": "and",
					"children": [
						{
							"type": "leaf",
							"field": "",
							"operator": "=",
							"value": {"mode": "static", "value": "Open"},
						}
					],
				},
				"field is required",
			),
		]

		for filters, expected_error in cases:
			with self.subTest(filters=filters):
				action = frappe._dict(
					{
						"operation": "Fetch Records",
						"reference_doctype": "ToDo",
						"ignore_permissions": 1,
						"permission_audit_reason": "Malformed filter validation test",
						"config": frappe.as_json({"filters": filters}),
					}
				)
				errors = self.handler.validate(action, {})
				self.assertTrue(
					any(expected_error in error for error in errors),
					f"Expected {expected_error!r} in validation errors: {errors}",
				)

	def test_legacy_skip_permissions_flag_is_honored_during_execution(self):
		from unittest.mock import patch

		from flexirule.ruleflow.utils.frappe_query_compat import FrappeQueryCapabilities

		description = f"FetchLegacyPermission_{random_string(6)}"
		todo = frappe.get_doc(
			{"doctype": "ToDo", "description": description}
		).insert(ignore_permissions=True)
		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"skip_permissions": 1,
				"permission_audit_reason": "Legacy action permission compatibility regression test",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{"fields": ["name"], "filters": [["ToDo", "description", "=", description]]}
				),
			}
		)

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			result, _ = self.handler.execute(action, {}, None)

		self.assertEqual([row.get("name") for row in result], [todo.name])

	def test_explicit_ignore_permissions_false_is_not_overridden_by_legacy_flag(self):
		from unittest.mock import patch

		from flexirule.ruleflow.utils.frappe_query_compat import FrappeQueryCapabilities

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "ToDo",
				"ignore_permissions": 0,
				"skip_permissions": 1,
				"permission_audit_reason": "Explicit false must win compatibility regression test",
				"config": frappe.as_json({"fields": ["name"], "limit": 1}),
			}
		)
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with self.assertRaisesRegex(
				frappe.ValidationError, "cannot enforce record-level read permissions"
			):
				self.handler.execute(action, {}, None)

	def test_legacy_query_api_uses_persisted_skip_permissions_flag(self):
		from unittest.mock import patch

		from flexirule.ruleflow.utils.frappe_query_compat import FrappeQueryCapabilities

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "ToDo",
				"skip_permissions": 1,
				"permission_audit_reason": "Validated integration use",
				"config": frappe.as_json({}),
			}
		)
		with patch(
			"flexirule.ruleflow.core.action_handlers.query_records.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			errors = self.handler.validate_fetch_records(action, {})

		self.assertFalse(
			any("cannot enforce record-level read permissions" in error.lower() for error in errors),
			f"The persisted skip_permissions flag should be honored: {errors}",
		)
