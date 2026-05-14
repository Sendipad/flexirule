# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RuleExecutionLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		context_snapshot: DF.Code | None
		duration: DF.Float
		error_trace: DF.Code | None
		executed_by: DF.Link | None
		execution_id: DF.Data | None
		execution_path: DF.Code | None
		message: DF.SmallText | None
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		rule: DF.Link
		status: DF.Literal["Success", "Failed", "Stopped"]
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=30):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Rule Execution Log")
		frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))

	def before_insert(self):
		if not self.executed_by:
			self.executed_by = frappe.session.user
