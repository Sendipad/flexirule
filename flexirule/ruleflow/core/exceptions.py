# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Custom exceptions for the FlexiRule Rule Engine
"""

import frappe


class RuleEngineError(frappe.ValidationError):
	"""Base exception for rule engine errors"""

	pass


class RuleDisabledError(RuleEngineError):
	"""Raised when attempting to execute a disabled rule"""

	pass


class EmptyRuleError(RuleEngineError):
	"""Raised when rule has no actions defined"""

	pass


class MethodExecutionError(RuleEngineError):
	"""Raised when a process method execution fails"""

	pass


class TimeoutError(RuleEngineError):
	"""Raised when rule execution exceeds timeout"""

	pass


class CycleDetectedError(RuleEngineError):
	"""Raised when infinite loop detected in rule graph"""

	pass


class ConfigurationValidationError(RuleEngineError):
	"""Raised when configuration fails schema validation"""

	pass


class PermissionDeniedError(frappe.PermissionError):
	"""Raised when user lacks permission to execute process method"""

	pass
