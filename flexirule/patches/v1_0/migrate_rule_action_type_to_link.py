import frappe

from flexirule.ruleflow.utils.action_type_registry import ensure_action_type_exists, seed_default_action_types


def execute():
	# 1. Ensure the new DocType exists before migrating data
	# (Frappe handles DocType creation during migration, but we ensure it's synced)
	frappe.reload_doc("Ruleflow", "doctype", "Action Type")

	# 2. Seed default Action Types
	seed_default_action_types()

	# 3. Handle legacy data in Rule Action
	# Even if they are not in the default list, we ensure they exist in the registry
	legacy_action_types = frappe.db.get_all("Rule Action", fields=["action_type"], distinct=True)
	for row in legacy_action_types:
		if row.action_type:
			ensure_action_type_exists(
				name=row.action_type,
				category="Flow Control",
				is_multi_mode=0,
				description="Auto-generated from legacy data",
			)

	# 4. Update the Rule Action DocType field metadata
	# We change the fieldtype from 'Select' to 'Link' and set options to 'Action Type'
	frappe.reload_doc("Ruleflow", "doctype", "Rule Action")

	# Force update the field in the database if reload_doc doesn't reflect it immediately
	# though usually Frappe handles this. But let's be safe.
	# Actually, we should let Frappe handle the schema change during migrate.
	# The important part is that the data now points to valid records.
