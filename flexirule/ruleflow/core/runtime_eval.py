# Copyright (c) 2026, FlexiRule and contributors
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

NOTE on Python 3 eval() scoping:
    Generator/comprehension expressions create their own scope in Python 3.
    Free variables inside the generator body (e.g. ``check_link_match``,
    ``resolve``) are resolved through the **globals** dict, NOT the locals
    dict passed to ``eval()``. To ensure utility functions are visible inside
    ``any(f(x) for x in items)`` patterns, we pass ``safe_locals`` as BOTH
    ``eval_globals`` (merged with ``{"__builtins__": {}}``) and
    ``eval_locals``.
"""

from __future__ import annotations

import frappe


def _build_eval_globals(safe_locals: dict) -> dict:
	"""Build a globals dict that includes safe_locals for generator scoping.

	Python 3 generator/comprehension expressions create an implicit nested
	scope.  Free variables used inside that scope are resolved via the
	**globals** dict of the enclosing ``eval()`` call, not the locals dict.

	By promoting ``safe_locals`` into the globals dict (alongside a locked-
	down ``__builtins__``), every name the compiled expression references
	— including helper functions like ``check_link_match`` — becomes
	visible inside ``any(…)``, ``all(…)``, list comprehensions, etc.
	"""
	eval_globals: dict = {"__builtins__": {}}
	eval_globals.update(safe_locals)
	return eval_globals


def eval_condition_bool(expression: str, safe_locals: dict, default: bool = False) -> bool:
	"""Evaluate expression and coerce to bool.

	On failure, logs the expression and exception details to both
	``frappe.logger`` and the Error Log DocType, then returns *default*.

	``NameError`` is **never** silently swallowed — it is always re-raised
	so that misconfigured expressions surface immediately rather than
	producing quietly wrong results.
	"""
	if not expression:
		return True

	eval_globals = _build_eval_globals(safe_locals)

	try:
		return bool(frappe.safe_eval(expression, eval_globals, safe_locals))
	except NameError as exc:
		# NameError means a variable/function the expression references
		# does not exist.  This is always a configuration or compilation
		# bug and must NEVER be swallowed silently.
		_log_eval_failure("eval_condition_bool", expression, exc)
		raise
	except Exception as exc:
		_log_eval_failure("eval_condition_bool", expression, exc)
		return default


def eval_value(expression: str, safe_locals: dict, default=None):
	"""Evaluate expression and return raw value.

	On failure, logs the expression and exception details to both
	``frappe.logger`` and the Error Log DocType, then returns *default*.

	``NameError`` is **never** silently swallowed — it is always re-raised.
	"""
	if not expression:
		return default

	eval_globals = _build_eval_globals(safe_locals)

	try:
		return frappe.safe_eval(expression, eval_globals, safe_locals)
	except NameError as exc:
		_log_eval_failure("eval_value", expression, exc)
		raise
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
	message = f"FlexiRule {func_name} failed.\n" f"Expression: {truncated_expr}\n" f"Error: {exc!s}"

	frappe.logger("flexirule.eval").warning(message)
	frappe.log_error(
		title=f"FlexiRule Expression Evaluation Error ({func_name})",
		message=message,
	)
