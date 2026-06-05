# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json
import time

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

# Import the class under test
from flexirule.ruleflow.doctype.rule_scheduler.rule_scheduler import RuleScheduler


class TestRuleScheduler(FrappeTestCase):
	def _insert_with_retry(self, doc, retries=3):
		last_error = None
		for _ in range(retries):
			try:
				return doc.insert(ignore_permissions=True)
			except frappe.QueryDeadlockError as e:
				last_error = e
				frappe.db.rollback()
				time.sleep(0.05)
		if last_error:
			raise last_error
		return doc

	def setUp(self):
		# Create a dummy rule for testing
		rule_name = f"Test Scheduler Rule {frappe.generate_hash(length=6)}"
		if not frappe.db.exists("Rule", rule_name):
			self.rule = frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": rule_name,
					"document_type": "ToDo",
					"trigger_type": "Scheduler Event",
					"is_active": 1,
					"actions": [
						{
							"action_type": "Entry Action",
							"config": '[{"target": "doc.priority", "operator": "set", "value": "High"}]',
							"action_label": "Make High Priority",
							"action_id": "root",
							"next_step_if_true": None,
						}
					],
				}
			)
			self.rule = self._insert_with_retry(self.rule)
		else:
			self.rule = frappe.get_doc("Rule", rule_name)

	def tearDown(self):
		frappe.db.rollback()

	def test_frequency_calculation(self):
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		next_run = scheduler.get_next_execution()
		self.assertTrue(next_run > now_datetime())
		# Roughly 1 day from now/creation
		diff = next_run - now_datetime()
		# Should be within 24 hours from now (Daily = next midnight)
		self.assertTrue(diff.total_seconds() <= 86400 + 3600)
		self.assertTrue(diff.total_seconds() > 0)

	def test_cron_validation(self):
		scheduler = frappe.new_doc("Rule Scheduler")
		scheduler.rule = self.rule.name
		scheduler.frequency = "Cron"
		scheduler.cron_format = "invalid-cron"

		with self.assertRaises(frappe.ValidationError):
			scheduler.save()

		scheduler.cron_format = "0 0 * * *"  # Valid
		scheduler.save()
		self.assertTrue(scheduler.name)

	def test_scheduler_requires_filter_or_rule_doctype(self):
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": f"Test Scheduler No DocType {frappe.generate_hash(length=6)}",
				"trigger_type": "Scheduler Event",
				"is_active": 0,
				"actions": [
					{
						"action_type": "Stop",
						"operation": "Success",
						"action_label": "End",
						"action_id": "node_end",
						"is_enabled": 1,
					}
				],
			}
		).insert(ignore_permissions=True)

		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": rule.name,
				"frequency": "Daily",
			}
		)

		with self.assertRaisesRegex(
			frappe.ValidationError,
			"requires Filter DocType or a Document Type",
		):
			scheduler.insert(ignore_permissions=True)

	def test_filter_json_validates_on_save(self):
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"filter_doctype": "ToDo",
				"filter_json": '{"description": ["like", "Batch Test%"]',
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "Filter JSON is invalid"):
			scheduler.insert(ignore_permissions=True)

		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"filter_doctype": "ToDo",
				"filter_json": json.dumps("not a filter object"),
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "must be a JSON object or array"):
			scheduler.insert(ignore_permissions=True)

	def test_filter_json_is_checked_against_filter_doctype(self):
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"filter_doctype": "ToDo",
				"filter_json": json.dumps({"definitely_not_a_todo_field": "Open"}),
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "Filter JSON is not valid for ToDo"):
			scheduler.insert(ignore_permissions=True)

	def test_is_event_due(self):
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Hourly",
			}
		).insert()

		# Should NOT be due immediately (next run is 1 hour later)
		self.assertFalse(scheduler.is_event_due())

		# Mock last_execution to be old
		scheduler.db_set("last_execution", add_days(now_datetime(), -1))
		# Now it should be due (re-fetch to clear cached properties)
		scheduler.reload()

		# We need to manually trigger calculation or rely on property
		# The property `.next_execution` uses `get_next_execution()` which uses `last_execution`
		# So it should return a time in the past if last_execution is old + Hourly frequency?
		# Wait, croniter(cron, last_execution).get_next() will return next occurrence AFTER last_execution.
		# If last_execution was yesterday, next would be yesterday + 1 hour.
		# So next_execution < now.

		self.assertTrue(scheduler.is_event_due())

	def test_batch_execution_flow(self):
		# Create unique ToDos to avoid data pollution from previous runs (due to commit)
		unique_id = frappe.generate_hash(length=8)

		todo1 = frappe.get_doc({"doctype": "ToDo", "description": f"Batch Test {unique_id} 1"}).insert()
		todo2 = frappe.get_doc({"doctype": "ToDo", "description": f"Batch Test {unique_id} 2"}).insert()

		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"filter_doctype": "ToDo",
				"filter_json": json.dumps({"description": ["like", f"Batch Test {unique_id}%"]}),
				"batch_size": 2,
			}
		).insert()

		# Mock enqueue to run synchronously or just call execute directly
		scheduler.execute()

		# Check logs
		logs = frappe.get_all(
			"Rule Execution Log",
			filters={"scheduler": scheduler.name},
			fields=["reference_docname", "batch_id", "batch_index", "batch_total"],
		)

		self.assertEqual(len(logs), 2)
		docnames = [l.reference_docname for l in logs]
		self.assertIn(todo1.name, docnames)
		self.assertIn(todo2.name, docnames)

		# Check batch fields
		self.assertEqual(logs[0].batch_total, 2)
		self.assertTrue(logs[0].batch_id.startswith("BATCH-"))

	def test_next_execution_at_on_save(self):
		"""Verify that next_execution_at is calculated and saved on insert."""
		# Set creation to a fixed time to make test deterministic
		creation = get_datetime("2026-06-01 12:00:00")
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Hourly",
				"creation": creation,
			}
		)
		scheduler.insert(ignore_permissions=True)
		self.assertIsNotNone(scheduler.next_execution_at)

		# Change frequency and verify it updates
		# Hourly (every hour) -> All (every 5 mins) should always be different
		scheduler.frequency = "All"
		scheduler.save(ignore_permissions=True)

		old_next = scheduler.next_execution_at
		scheduler.frequency = "Hourly"
		scheduler.save(ignore_permissions=True)
		self.assertNotEqual(scheduler.next_execution_at, old_next)

	def test_next_execution_at_when_stopped(self):
		"""Verify that next_execution_at is cleared when scheduler is stopped."""
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Hourly",
				"stopped": 0,
			}
		).insert(ignore_permissions=True)
		self.assertIsNotNone(scheduler.next_execution_at)

		scheduler.stopped = 1
		scheduler.save(ignore_permissions=True)
		self.assertIsNone(scheduler.next_execution_at)

	def test_execution_metrics_and_status_updates(self):
		"""Verify scheduler execution updates status, counters, summary, and next_execution_at."""
		unique_id = frappe.generate_hash(length=8)
		# Create test documents
		frappe.get_doc({"doctype": "ToDo", "description": f"Metrics Test {unique_id} 1"}).insert()

		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"filter_doctype": "ToDo",
				"filter_json": json.dumps({"description": ["like", f"Metrics Test {unique_id}%"]}),
				"batch_size": 10,
			}
		).insert(ignore_permissions=True)

		# Set next_execution_at to the past so execution recalculates and pushes it forward
		past_time = add_days(now_datetime(), -1)
		scheduler.db_set("next_execution_at", past_time, update_modified=False)
		old_next_execution_at = past_time

		# Execute
		scheduler.execute()

		scheduler.reload()
		self.assertEqual(scheduler.last_run_status, "Success")
		self.assertEqual(scheduler.last_success_count, 1)
		self.assertEqual(scheduler.last_error_count, 0)
		self.assertIn("Processed 1 documents: 1 success, 0 failed.", scheduler.last_run_summary)
		# Verify next_execution_at is updated and pushed forward
		self.assertTrue(scheduler.next_execution_at > old_next_execution_at)

	def test_execution_status_no_documents(self):
		"""Verify status is 'No Documents' when no documents match."""
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"filter_doctype": "ToDo",
				"filter_json": json.dumps({"description": "non-existent-todo-description-12345"}),
			}
		).insert(ignore_permissions=True)

		scheduler.execute()
		scheduler.reload()
		self.assertEqual(scheduler.last_run_status, "No Documents")
		self.assertEqual(scheduler.last_success_count, 0)
		self.assertEqual(scheduler.last_error_count, 0)
		self.assertIn("No documents to process", scheduler.last_run_summary)

	def test_scheduler_filtering_by_next_execution_at(self):
		"""Verify check_scheduled_rules filters correctly by next_execution_at with null fallback."""
		# Create two schedulers
		# One due (mocked past next_execution_at)
		due_scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Hourly",
				"stopped": 0,
			}
		).insert(ignore_permissions=True)

		# Set next_execution_at to the past
		past_time = add_days(now_datetime(), -1)
		due_scheduler.db_set("next_execution_at", past_time, update_modified=False)

		# One future (not due)
		future_scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"stopped": 0,
			}
		).insert(ignore_permissions=True)
		# Set next_execution_at to the future
		future_time = add_days(now_datetime(), 1)
		future_scheduler.db_set("next_execution_at", future_time, update_modified=False)

		# One with null next_execution_at (fallback should pick it up)
		null_scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"stopped": 0,
			}
		).insert(ignore_permissions=True)
		null_scheduler.db_set("next_execution_at", None, update_modified=False)

		# One stopped but due (should NOT run)
		stopped_due_scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Hourly",
				"stopped": 1,
			}
		).insert(ignore_permissions=True)
		stopped_due_scheduler.db_set("next_execution_at", past_time, update_modified=False)

		# We'll patch frappe.get_doc to track which ones are loaded/enqueued
		enqueued = []
		original_enqueue = RuleScheduler.enqueue

		def mock_enqueue(self, force=False):
			enqueued.append(self.name)
			return True

		RuleScheduler.enqueue = mock_enqueue  # type: ignore[method-assign]
		try:
			from flexirule.ruleflow.scheduler import check_scheduled_rules

			check_scheduled_rules()
		finally:
			RuleScheduler.enqueue = original_enqueue  # type: ignore[method-assign]

		self.assertIn(due_scheduler.name, enqueued)
		self.assertIn(null_scheduler.name, enqueued)
		self.assertNotIn(future_scheduler.name, enqueued)
		self.assertNotIn(stopped_due_scheduler.name, enqueued)
