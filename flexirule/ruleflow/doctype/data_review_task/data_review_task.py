# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DataReviewTask(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from flexirule.ruleflow.doctype.data_review_related_document.data_review_related_document import (
			DataReviewRelatedDocument,
		)

		context_json: DF.Code | None
		description: DF.TextEditor | None
		method_inputs: DF.Code | None
		priority: DF.Literal["Low", "Medium", "High", "Critical"]
		process_method: DF.Link | None
		related_documents: DF.Table[DataReviewRelatedDocument]
		resolution_notes: DF.Text | None
		resolved_by: DF.Link | None
		resolved_on: DF.Datetime | None
		rule: DF.Link | None
		similarity_score: DF.Percent
		source_doctype: DF.Link
		source_document: DF.DynamicLink
		status: DF.Literal["Open", "In Progress", "Resolved", "Rejected"]
		task_type: DF.Literal["Duplicate Review", "Data Quality", "Merge Request", "Validation Error"]

	# end: auto-generated types
	def validate(self):
		pass

	def before_save(self):
		# Auto-set resolved info when status changes to Resolved
		if self.status == "Resolved" and not self.resolved_by:
			self.resolved_by = frappe.session.user
			self.resolved_on = frappe.utils.now()

	def on_update(self):
		pass
