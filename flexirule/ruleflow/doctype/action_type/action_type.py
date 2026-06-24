# Copyright (c) 2026, Abdo Ruzaqi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ActionType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Literal["", "Flow Control", "Data", "Process", "Communication", "Orchestration"]
		description: DF.SmallText | None
		is_multi_mode: DF.Check
	# end: auto-generated types

	def validate(self):
		if not frappe.flags.in_install and not frappe.flags.in_migrate:
			frappe.throw(_("Action Types are managed automatically by FlexiRule."))

	def before_rename(self, old, new, merge=False):
		if not frappe.flags.in_install and not frappe.flags.in_migrate:
			frappe.throw(_("Renaming Action Types is not allowed."))

	def on_trash(self):
		if not frappe.flags.in_install and not frappe.flags.in_migrate:
			frappe.throw(_("Deleting Action Types is not allowed."))
