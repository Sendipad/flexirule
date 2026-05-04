# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Runtime-safe evaluators used by the rule engine.

Splits boolean condition evaluation from value evaluation so callers can
explicitly choose semantics.

IMPORTANT: These functions log all evaluation failures to Frappe's Error Log
and the application logger so operators can diagnose silent rule divergence.
A caught exception here means the rule's condition/value *did not* evaluate
as intended — callers receive a safe default, but the failure is always
recorded for forensic analysis.
"""

from __future__ import annotations

import frappe


def eval_condition_bool(expression: str, safe_locals: dict, default: bool = False) -> bool:
	"""Evaluate expression and coerce to bool.

	On failure, logs the expression and exception details to both
	``frappe.logger`` and the Error Log DocType, then returns *default*.
	"""
	if not expression:
		return True

	try:
		return bool(frappe.safe_eval(expression, None, safe_locals))
	except Exception as exc:
		_log_eval_failure("eval_condition_bool", expression, exc)
		return default


def eval_value(expression: str, safe_locals: dict, default=None):
	"""Evaluate expression and return raw value.

	On failure, logs the expression and exception details to both
	``frappe.logger`` and the Error Log DocType, then returns *default*.
	"""
	if not expression:
		return default

	try:
		return frappe.safe_eval(expression, None, safe_locals)
	except Exception as exc:
		_log_eval_failure("eval_value", expression, exc)
		return default


def _log_eval_failure(func_name: str, expression: str, exc: Exception) -> None:
	"""Centralised logging for evaluation failures.

	Writes to both:
	- ``frappe.logger("flexirule.eval")`` — for application-level log files.
	- ``frappe.log_error`` — for the Error Log DocType, giving operators
	  UI-visible traceability.

	The expression is truncated to 500 chars to avoid log bloat from
	extremely large compiled expressions.
	"""
	truncated_expr = expression[:500] + ("…" if len(expression) > 500 else "")
	message = (
		f"FlexiRule {func_name} failed.\n"
		f"Expression: {truncated_expr}\n"
		f"Error: {exc!s}"
	)

	frappe.logger("flexirule.eval").warning(message)
	frappe.log_error(
		title=f"FlexiRule Expression Evaluation Error ({func_name})",
		message=message,
	)
