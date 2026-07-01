import frappe

from flexirule.ruleflow.tests.catalog import Workflows
from flexirule.ruleflow.tests.factories import make_test_contact, make_test_customer
from flexirule.ruleflow.tests.test_case import FlexiRuleTestCase


class TestOrchestration(FlexiRuleTestCase):
	def test_contact_validation_workflow_success(self):
		# 1. Setup
		rule = Workflows.contact_validation()
		contact = make_test_contact(email_id="  USER@Example.Com  ")

		# 2. Execute
		result = self.execute_rule(rule.name, contact)

		# 3. Assert
		self.assert_success(result)
		self.assert_rule_executed(result, "Normalize Email")
		self.assert_document_updated(contact, "email_id", "user@example.com")

	def test_contact_validation_workflow_failure(self):
		rule = Workflows.contact_validation()
		contact = make_test_contact(email_id="", do_not_save=True)

		with self.assertRaises(frappe.ValidationError):
			self.execute_rule(rule.name, contact)

	def test_composed_customer_workflow(self):
		# 1. Setup - Create a sub-rule for contact validation
		sub_rule = Workflows.contact_validation("Sub Contact Validation")

		# 2. Create parent rule that calls the sub-rule
		parent_rule = Workflows.customer_workflow(
			"Parent Customer Flow", sub_rule=sub_rule.name, check_credit=True
		)

		customer = make_test_customer(credit_limit=5000)

		# 3. Execute
		result = self.execute_rule(parent_rule.name, customer)

		# 4. Assert
		self.assert_success(result)
		self.assert_rule_executed(result, "Within Credit Limit?")
		self.assert_rule_executed(result, "Call Sub-Rule")

	def test_credit_limit_exceeded(self):
		rule = Workflows.customer_workflow(check_credit=True)
		customer = make_test_customer(credit_limit=15000, do_not_save=True)

		with self.assertRaises(frappe.ValidationError):
			self.execute_rule(rule.name, customer)
