# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for FlexiRule Exceptions
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.exceptions import (
	CycleDetectedError,
	EmptyRuleError,
	MethodExecutionError,
	RuleDisabledError,
	RuleEngineError,
)
from flexirule.ruleflow.core.exceptions import TimeoutError as FlexiRuleTimeoutError


class TestRuleEngineExceptions(FrappeTestCase):
	"""Test cases for Rule Engine exceptions"""

	def test_rule_engine_error(self):
		"""Test RuleEngineError base exception"""
		with self.assertRaises(RuleEngineError):
			raise RuleEngineError("Test RuleEngineError")

	def test_rule_disabled_error(self):
		"""Test RuleDisabledError"""
		with self.assertRaises(RuleDisabledError):
			raise RuleDisabledError("Test RuleDisabledError")

	def test_empty_rule_error(self):
		"""Test EmptyRuleError"""
		with self.assertRaises(EmptyRuleError):
			raise EmptyRuleError("Test EmptyRuleError")

	def test_method_execution_error(self):
		"""Test MethodExecutionError"""
		with self.assertRaises(MethodExecutionError):
			raise MethodExecutionError("Test MethodExecutionError")

	def test_cycle_detected_error(self):
		"""Test CycleDetectedError"""
		with self.assertRaises(CycleDetectedError):
			raise CycleDetectedError("Test CycleDetectedError")

	def test_timeout_error(self):
		"""Test TimeoutError"""
		with self.assertRaises(FlexiRuleTimeoutError):
			raise FlexiRuleTimeoutError("Test TimeoutError")

	def test_exception_inheritance(self):
		"""Test exception inheritance hierarchy"""
		# All custom exceptions should inherit from RuleEngineError
		self.assertTrue(issubclass(RuleDisabledError, RuleEngineError))
		self.assertTrue(issubclass(EmptyRuleError, RuleEngineError))
		self.assertTrue(issubclass(MethodExecutionError, RuleEngineError))
		self.assertTrue(issubclass(CycleDetectedError, RuleEngineError))
		self.assertTrue(issubclass(FlexiRuleTimeoutError, RuleEngineError))

	def test_exception_messages(self):
		"""Test exception message preservation"""
		msg = "Custom error message"

		try:
			raise RuleDisabledError(msg)
		except RuleDisabledError as e:
			self.assertEqual(str(e), msg)

		try:
			raise EmptyRuleError(msg)
		except EmptyRuleError as e:
			self.assertEqual(str(e), msg)

		try:
			raise MethodExecutionError(msg)
		except MethodExecutionError as e:
			self.assertEqual(str(e), msg)

		try:
			raise CycleDetectedError(msg)
		except CycleDetectedError as e:
			self.assertEqual(str(e), msg)

		try:
			raise FlexiRuleTimeoutError(msg)
		except FlexiRuleTimeoutError as e:
			self.assertEqual(str(e), msg)

	def test_exception_with_frappe_validation_error(self):
		"""Test that exceptions are compatible with Frappe's validation error"""
		# RuleEngineError inherits from frappe.ValidationError
		self.assertTrue(issubclass(RuleEngineError, frappe.ValidationError))

	def test_rule_disabled_error_usage(self):
		"""Test RuleDisabledError in a realistic scenario"""
		rule_name = "NonExistentRule"
		try:
			raise RuleDisabledError(f"Rule {rule_name} is disabled")
		except RuleDisabledError as e:
			self.assertIn(rule_name, str(e))

	def test_empty_rule_error_usage(self):
		"""Test EmptyRuleError in a realistic scenario"""
		rule_name = "EmptyRule"
		try:
			raise EmptyRuleError(f"Rule {rule_name} has no enabled actions")
		except EmptyRuleError as e:
			self.assertIn(rule_name, str(e))

	def test_method_execution_error_usage(self):
		"""Test MethodExecutionError in a realistic scenario"""
		process_name = "TestProcess"
		operation = "test_operation"
		try:
			raise MethodExecutionError(f"Process {process_name}:{operation} failed")
		except MethodExecutionError as e:
			self.assertIn(process_name, str(e))
			self.assertIn(operation, str(e))

	def test_cycle_detected_error_usage(self):
		"""Test CycleDetectedError in a realistic scenario"""
		action_label = "TestAction"
		visits = 101
		try:
			raise CycleDetectedError(f"Infinite loop detected: Action {action_label} visited {visits} times")
		except CycleDetectedError as e:
			self.assertIn(action_label, str(e))
			self.assertIn(str(visits), str(e))

	def test_timeout_error_usage(self):
		"""Test TimeoutError in a realistic scenario"""
		timeout = 30
		try:
			raise FlexiRuleTimeoutError(f"Rule execution exceeded timeout ({timeout}s)")
		except FlexiRuleTimeoutError as e:
			self.assertIn(str(timeout), str(e))

	def test_exception_attributes(self):
		"""Test that exceptions preserve attributes properly"""
		msg = "Test error message"

		# Test RuleDisabledError
		exc = RuleDisabledError(msg)
		self.assertEqual(str(exc), msg)

		# Test EmptyRuleError
		exc = EmptyRuleError(msg)
		self.assertEqual(str(exc), msg)

		# Test MethodExecutionError
		exc = MethodExecutionError(msg)
		self.assertEqual(str(exc), msg)

		# Test CycleDetectedError
		exc = CycleDetectedError(msg)
		self.assertEqual(str(exc), msg)

		# Test TimeoutError
		exc = FlexiRuleTimeoutError(msg)
		self.assertEqual(str(exc), msg)
