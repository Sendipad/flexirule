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

	def _leaf(self, field, operator, value, doctype="ToDo"):
		return {
			"type": "leaf",
			"doctype": doctype,
			"field": field,
			"operator": operator,
			"value": value if isinstance(value, dict) and "mode" in value else {"mode": "static", "value": value},
		}

	def _group(self, operator, *children):
		return {"type": "group", "operator": operator, "children": list(children)}

	def test_basic_fetch_records_default_fields(self):
		prefix = f"FetchBasic_{random_string(5)}"
		t1 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_1"}).insert(ignore_permissions=True)
		t2 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix}_2"}).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Fetch Records",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": self._group("and", self._leaf("description", "like", f"{prefix}%")),
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": ["name", "description as task_desc", "status"],
						"filters": self._group("and", self._leaf("description", "=", f"{prefix}_1")),
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": self._group(
							"and",
							self._leaf("description", "like", f"{prefix}%"),
							self._leaf("status", "!=", "Closed"),
						)
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": self._group(
							"and",
							self._leaf("description", "like", f"{prefix}%"),
							self._leaf("priority", "in", ["High", "Medium"]),
						)
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
		filter_tree = self._group(
			"and",
			self._leaf("description", "like", f"{prefix}%"),
			self._group(
				"or",
				self._leaf("status", "=", "Open"),
				self._leaf("status", "=", "Closed"),
			),
		)

		action = frappe._dict(
			{
				"operation": "Fetch Records",
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
				"reference_doctype": "User",
				"config": frappe.as_json(
					{
						"fields": ["name", "email"],
						"filters": self._group(
							"and",
							self._leaf("email", "=", user_email, doctype="User"),
							self._leaf("roles.role", "like", "%Manager%", doctype="User"),
						),
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": ["name", "description"],
						"filters": self._group("and", self._leaf("description", "like", f"{prefix}%")),
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"fields": ["name", "description"],
						"filters": self._group("and", self._leaf("description", "=", "{vars.target_pattern}")),
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

		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": self._group(
							"and",
							self._leaf("status", "=", "Open"),
							self._group(
								"or",
								self._leaf("description", "like", "%task%"),
								self._leaf("missing_nested_field", "=", "x"),
							),
						)
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": self._group("and", self._leaf("description", "starts with", f"{prefix}_invoice")),
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": self._group("and", self._leaf("description", "ends with", "invoice")),
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
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": self._group(
							"and",
							self._leaf("description", "like", f"{prefix}%"),
							self._leaf("status", "=", {"value": "Open", "value_type": "Value"}),
						),
					}
				),
			}
		)
		res_true, _ = self.handler.execute(action_true, {}, None)
		res_names = {r.get("name") for r in res_true}
		self.assertEqual(res_names, {t_open.name})
		self.assertNotIn(t_closed.name, res_names)
