# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Rule Scheduler - Schedule rule execution on document batches.

Mirrors Frappe's Scheduled Job Type pattern:
- croniter for cron parsing
- is_event_due() for timing checks
- rq_job_id for deduplication
"""

import json
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime
from frappe.utils.background_jobs import is_job_enqueued


class RuleScheduler(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		batch_size: DF.Int
		cron_format: DF.Data | None
		filter_doctype: DF.Link | None
		filter_json: DF.Code | None
		frequency: DF.Literal["All", "Hourly", "Daily", "Weekly", "Monthly", "Cron"]
		last_error: DF.Text | None
		last_execution: DF.Datetime | None
		module: DF.Link | None
		on_error: DF.Literal["Skip", "Stop"]
		rule: DF.Link
		stopped: DF.Check
		next_execution_at: "DF.Datetime | None"

	# end: auto-generated types

	def validate(self):
		self._validate_cron_format()
		rule_doc = self._validate_rule()
		self._validate_filter_target(rule_doc)
		self._validate_filter_json()
		self.set_initial_next_execution()

	def set_initial_next_execution(self):
		"""Compute and set initial next_execution_at if not set or on frequency change."""
		is_new = self.is_new()
		has_changed = False
		if not is_new:
			old_doc = self.get_doc_before_save()
			if old_doc:
				has_changed = (
					self.frequency != old_doc.frequency
					or self.cron_format != old_doc.cron_format
					or self.stopped != old_doc.stopped
				)

		if is_new or has_changed or not self.next_execution_at:
			if self.stopped:
				self.next_execution_at = None
			else:
				self.next_execution_at = self.get_next_execution()

	def _validate_cron_format(self):
		"""Validate cron expression if frequency is Cron."""
		if self.frequency == "Cron" and self.cron_format:
			try:
				from croniter import croniter

				croniter(self.cron_format)
			except Exception:
				frappe.throw(_("{0} is not a valid Cron expression").format(self.cron_format))

	def _validate_rule(self):
		"""Ensure linked rule exists and has compatible trigger_type."""
		if self.rule:
			rule_doc = frappe.get_cached_doc("Rule", self.rule)
			if rule_doc.trigger_type not in ("Scheduler Event", "Callable Event"):
				frappe.throw(
					_(
						"Rule '{0}' has trigger type '{1}'. Only Scheduler Event or Callable Event rules can be scheduled."
					).format(self.rule, rule_doc.trigger_type)
				)
			if not rule_doc.is_active:
				frappe.msgprint(
					_("Warning: Rule {0} is not active. Scheduler will be stopped.").format(self.rule),
					indicator="orange",
				)
				self.stopped = 1
			return rule_doc
		return None

	def _get_filter_doctype(self, rule_doc=None):
		"""Resolve the DocType used for scheduler batch discovery."""
		return self.filter_doctype or (rule_doc.document_type if rule_doc else None)

	def _validate_filter_target(self, rule_doc=None):
		"""Require an explicit batch DocType or a linked scheduler rule DocType."""
		doctype = self._get_filter_doctype(rule_doc)
		if not doctype:
			frappe.throw(_("Rule Scheduler requires Filter DocType or a Document Type on the linked Rule."))

		if not frappe.db.exists("DocType", doctype):
			frappe.throw(_("Filter DocType '{0}' does not exist.").format(doctype))

	def _validate_filter_json(self):
		"""Validate scheduler filters at save time instead of failing silently at runtime."""
		if not self.filter_json:
			return

		filters = self._parse_filter_json(raise_on_error=True)
		if not isinstance(filters, dict | list):
			frappe.throw(_("Filter JSON must be a JSON object or array."))

		doctype = self._get_filter_doctype(frappe.get_cached_doc("Rule", self.rule) if self.rule else None)
		try:
			frappe.get_all(doctype, filters=filters, pluck="name", limit=1)
		except Exception as exc:
			frappe.throw(_("Filter JSON is not valid for {0}: {1}").format(doctype, str(exc)))

	def _parse_filter_json(self, raise_on_error=False):
		if not self.filter_json:
			return {}

		try:
			return json.loads(self.filter_json)
		except json.JSONDecodeError as exc:
			if raise_on_error:
				frappe.throw(_("Filter JSON is invalid: {0}").format(str(exc)))
			raise

	@property
	def next_execution(self):
		"""Virtual field - computed next execution time."""
		return self.get_next_execution()

	def get_next_execution(self):
		"""
		Calculate next execution time based on frequency.
		Mirrors Frappe Scheduled Job Type pattern.
		"""
		from croniter import croniter

		CRON_MAP = {
			"All": "*/5 * * * *",  # Every 5 minutes
			"Hourly": "0 * * * *",
			"Daily": "0 0 * * *",
			"Weekly": "0 0 * * 0",
			"Monthly": "0 0 1 * *",
		}

		cron = self.cron_format or CRON_MAP.get(self.frequency, "0 * * * *")
		last = get_datetime(self.last_execution or self.creation or now_datetime())
		return croniter(cron, last).get_next(datetime)

	def is_event_due(self, current_time=None):
		"""Check if scheduler should run."""
		return self.get_next_execution() <= (current_time or now_datetime())

	@property
	def rq_job_id(self):
		"""Unique ID for job deduplication."""
		return f"rule_scheduler::{self.name}"

	def enqueue(self, force=False):
		"""
		Enqueue scheduler for execution if due.
		Returns True if enqueued.
		"""
		if self.stopped:
			return False

		if self.is_event_due() or force:
			if not is_job_enqueued(self.rq_job_id):
				frappe.enqueue(
					"flexirule.ruleflow.scheduler.run_scheduled_rule",
					scheduler_name=self.name,
					queue=self.get_queue_name(),
					job_id=self.rq_job_id,
					timeout=3600,  # 1 hour max
					enqueue_after_commit=True,
				)
				return True
			else:
				frappe.logger("flexirule").debug(f"Skipped {self.name}: already in queue")
		return False

	def get_queue_name(self):
		"""Determine queue based on frequency."""
		if self.frequency in ("Daily", "Weekly", "Monthly"):
			return "long"
		return "default"

	def execute(self):
		"""
		Execute the scheduled rule batch.
		Called from background job.
		"""
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		batch_id = f"BATCH-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}-{self.name}"

		try:
			rule_doc = frappe.get_cached_doc("Rule", self.rule)
			if not rule_doc.is_active:
				frappe.log_error(f"Scheduler {self.name}: Rule {self.rule} is not active")
				return

			# Get documents to process
			documents = self._get_documents()

			if not documents:
				frappe.logger("flexirule").info(f"Scheduler {self.name}: No documents to process")
				self._update_last_execution(
					success_count=0, error_count=0, status="No Documents", summary="No documents to process"
				)
				return

			success_count = 0
			error_count = 0

			for i, doc_name in enumerate(documents):
				try:
					doc = frappe.get_doc(self.filter_doctype or rule_doc.document_type, doc_name)

					context = {
						"doc": doc,
						"batch_id": batch_id,
						"batch_index": i + 1,
						"batch_total": len(documents),
						"scheduler": self.name,
					}

					RuleCoordinator.execute_rule(rule_doc, context)
					success_count += 1

				except Exception as e:
					error_count += 1
					frappe.log_error(f"Scheduler {self.name}: Failed on {doc_name}", str(e))
					if self.on_error == "Stop":
						break

				# Commit every batch_size documents
				if (i + 1) % (self.batch_size or 100) == 0:
					if not getattr(frappe.flags, "in_test", False):
						frappe.db.commit()  # nosemgrep: frappe-manual-commit
					frappe.publish_realtime(  # nosemgrep: frappe-realtime-pick-room
						"batch_progress",
						{
							"batch_id": batch_id,
							"processed": i + 1,
							"total": len(documents),
							"success": success_count,
							"errors": error_count,
						},
					)

			if not getattr(frappe.flags, "in_test", False):
				frappe.db.commit()  # nosemgrep: frappe-manual-commit

			status = "Success"
			if error_count > 0:
				if success_count > 0:
					status = "Partial Success"
				else:
					status = "Failed"

			summary = f"Processed {len(documents)} documents: {success_count} success, {error_count} failed."
			self._update_last_execution(
				success_count=success_count, error_count=error_count, status=status, summary=summary
			)

			frappe.logger("flexirule").info(
				f"Scheduler {self.name}: Completed. Success: {success_count}, Errors: {error_count}"
			)

		except Exception as e:
			error_msg = str(e)
			frappe.log_error(f"Scheduler {self.name} failed", error_msg)
			status = "Failed"
			summary = f"Error during scheduler execution: {error_msg[:500]}"
			self._update_last_execution(success_count=0, error_count=0, status=status, summary=summary)
			self.db_set("last_error", error_msg[:2000], update_modified=False)

	def _get_documents(self):
		"""Get documents matching filter criteria."""
		rule_doc = frappe.get_cached_doc("Rule", self.rule)
		doctype = self._get_filter_doctype(rule_doc)

		filters = {}
		if self.filter_json:
			filters = self._parse_filter_json(raise_on_error=True)

		return frappe.get_all(
			doctype,
			filters=filters,
			pluck="name",
			limit=self.batch_size or 100,
		)

	def _update_last_execution(self, success_count=None, error_count=None, status=None, summary=None):
		"""Update last_execution and related metrics."""
		now = now_datetime()
		self.last_execution = now
		next_exec = self.get_next_execution()

		update_dict = {
			"last_execution": now,
			"next_execution_at": next_exec,
		}
		if status is not None:
			update_dict["last_run_status"] = status
		if success_count is not None:
			update_dict["last_success_count"] = success_count
		if error_count is not None:
			update_dict["last_error_count"] = error_count
		if summary is not None:
			update_dict["last_run_summary"] = summary

		for field, val in update_dict.items():
			self.db_set(field, val, update_modified=False)


@frappe.whitelist()
def execute_now(doc: str):
	"""Server action: Execute scheduler immediately."""
	frappe.only_for("System Manager")
	doc_dict = json.loads(doc)
	scheduler = frappe.get_doc("Rule Scheduler", doc_dict.get("name"))
	scheduler.enqueue(force=True)
	frappe.msgprint(_("Scheduler enqueued for execution"))
	return doc_dict
