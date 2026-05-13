# Copyright (c) 2025, Abdo Ruzaqi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ProcessOperation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allows_async: DF.Check
		can_stop_save: DF.Check
		color: DF.Data | None
		config_schema: DF.Code | None
		action_overrides: DF.Code | None
		description: DF.SmallText | None
		doctype_filters: DF.Code | None
		enabled: DF.Check
		for_doctype: DF.Link | None
		func_name: DF.Data
		has_side_effect: DF.Check
		icon: DF.Data | None
		is_terminal: DF.Check
		label: DF.Data | None
		output_schema: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reads_vars: DF.Code | None
		requires_doc: DF.Check
		transactional: DF.Check
		visible_in_builder: DF.Check
		writes_to: DF.Literal["None", "Context", "Document", "Database"]
		writes_vars: DF.Code | None
	# end: auto-generated types

	def validate(self):
		"""Hard-cut validation for declarative Process contract v2."""
		if not self.func_name:
			return
		if not getattr(self, "parent", None):
			return
		try:
			from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2

			resolve_process_operation_contract_v2(
				self.parent,
				self.func_name,
				self.as_dict(),
				strict=True,
			)
		except Exception as exc:
			frappe.throw(
				_("Invalid Process Operation contract v2 for '{0}.{1}': {2}").format(
					self.parent, self.func_name, str(exc)
				)
			)
