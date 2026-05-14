# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class RulePermission(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		can_disable: DF.Check
		can_edit: DF.Check
		can_execute: DF.Check
		can_view: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		role: DF.Link | None

	# end: auto-generated types
	pass
