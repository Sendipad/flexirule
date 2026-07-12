# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Permission checking for FlexiRule Rule Engine
"""

import json

import frappe
from frappe import _

DEFAULT_IGNORE_PERMISSIONS_ROLES = {"System Manager"}
DEFAULT_ALLOWED_METHOD_PREFIXES = ("flexirule.",)


def require_builder_access() -> None:
	"""Ensure the current user has the 'System Manager' or 'Rule Builder' role.

	Centralised gate used by all FlexiRule whitelisted API endpoints.
	Raises ``frappe.PermissionError`` when the caller lacks sufficient roles.
	"""
	if frappe.session.user == "Administrator":
		return

	roles = frappe.get_roles(frappe.session.user)
	if "System Manager" not in roles and "Rule Builder" not in roles:
		frappe.throw(
			_("Not permitted. Requires 'System Manager' or 'Rule Builder' role."), frappe.PermissionError
		)


def check_rule_permission(rule_doc, throw=True):
	"""
	Check if current user can execute a rule

	Args:
	    rule_doc: Rule DocType document
	    throw: Whether to throw error or return bool

	Returns:
	    Boolean if throw=False
	"""
	user = frappe.session.user
	user_roles = frappe.get_roles(user)

	def safe_get(obj, key, default=None):
		if hasattr(obj, "get"):
			return obj.get(key, default)
		return getattr(obj, key, default)

	# 1. Check if Rule is actually active
	if not safe_get(rule_doc, "is_active"):
		if throw:
			frappe.throw(
				_("Rule {0} is disabled (inactive)").format(safe_get(rule_doc, "rule_name") or rule_doc.name),
				frappe.ValidationError,
			)
		return False

	# 2. Check for Role-based Skipping (Blacklist)
	skip_for_roles_docs = safe_get(rule_doc, "skip_for_roles")
	if skip_for_roles_docs:
		skip_roles = [
			(row.get("role") if hasattr(row, "get") else getattr(row, "role", None))
			for row in skip_for_roles_docs
		]
		# DEBUG
		if any(role in user_roles for role in skip_roles):
			if throw:
				frappe.throw(
					_("Rule execution is skipped for your current role(s)"),
					frappe.PermissionError,
				)
			return False

	# 3. System Manager can always execute if active and not skipped
	if "System Manager" in user_roles:
		return True

	# 3b. Check rule-specific permissions table (if defined)
	rule_permissions = safe_get(rule_doc, "permissions")
	if rule_permissions:
		can_exec = any(
			(getattr(p, "can_execute", 0) or (hasattr(p, "get") and p.get("can_execute")))
			and (getattr(p, "role", None) or (hasattr(p, "get") and p.get("role"))) in user_roles
			for p in rule_permissions
		)
		if not can_exec:
			if throw:
				frappe.throw(
					_("You don't have the required role to execute rule '{0}'").format(
						safe_get(rule_doc, "rule_name") or rule_doc.name
					),
					frappe.PermissionError,
				)
			return False

	# 4. Check if user has permission on the target doctype
	target_doctype = rule_doc.document_type
	if not frappe.has_permission(target_doctype, "write"):
		if throw:
			frappe.throw(
				_("You need write permission on {0} to execute this rule").format(target_doctype),
				frappe.PermissionError,
			)
		return False

	return True


def check_method_permission(method_path, throw=True):
	"""
	Check if method is allowed to be executed

	Args:
	    method_path: Full dotted path to method
	    throw: Whether to throw error or return bool
	"""
	blocklist = set(frappe.get_hooks("flexirule_method_blocklist") or [])
	allowlist = set(frappe.get_hooks("flexirule_method_allowlist") or [])

	if method_path in blocklist:
		if throw:
			frappe.throw(
				_("Method '{0}' is not allowed").format(method_path),
				frappe.PermissionError,
			)
		return False

	if allowlist and method_path not in allowlist:
		if throw:
			frappe.throw(
				_("Method '{0}' is not in the allowlist").format(method_path),
				frappe.PermissionError,
			)
		return False

	if not allowlist and not method_path.startswith(DEFAULT_ALLOWED_METHOD_PREFIXES):
		if throw:
			frappe.throw(
				_("Method '{0}' is not in allowed namespaces").format(method_path),
				frappe.PermissionError,
			)
		return False

	return True


def can_ignore_permissions(action, context=None, throw=True):
	"""
	Guard ignore_permissions usage behind explicit role policy and audit reason.

	Audit reason is read from:
	- action.permission_audit_reason (if field exists), or
	- action.config.permission_audit_reason
	"""
	if not int(getattr(action, "ignore_permissions", getattr(action, "skip_permissions", 0)) or 0):
		return False

	user = frappe.session.user
	user_roles = set(frappe.get_roles(user))
	allowed_roles = set(
		frappe.get_hooks("flexirule_ignore_permissions_roles")
		or frappe.get_hooks("flexirule_skip_permissions_roles")
		or []
	)
	if not allowed_roles:
		allowed_roles = set(DEFAULT_IGNORE_PERMISSIONS_ROLES)

	if user != "Administrator" and not user_roles.intersection(allowed_roles):
		if throw:
			frappe.throw(
				_("ignore_permissions is restricted. Requires one of roles: {0}").format(
					", ".join(sorted(allowed_roles))
				),
				frappe.PermissionError,
			)
		return False

	audit_reason = _extract_ignore_permissions_audit_reason(action)
	if not audit_reason:
		if throw:
			frappe.throw(
				_("ignore_permissions requires 'permission_audit_reason' in action configuration."),
				frappe.ValidationError,
			)
		return False

	frappe.logger("flexirule.security").warning(
		"ignore_permissions override by user=%s action=%s action_id=%s reason=%s",
		user,
		getattr(action, "action_label", None) or getattr(action, "name", None),
		getattr(action, "action_id", None),
		audit_reason,
	)
	return True


def _extract_ignore_permissions_audit_reason(action) -> str:
	direct_reason = getattr(action, "permission_audit_reason", None)
	if direct_reason:
		return str(direct_reason).strip()

	config_raw = getattr(action, "config", None)
	if not config_raw:
		return ""

	try:
		config = json.loads(config_raw) if isinstance(config_raw, str) else config_raw
	except Exception:
		return ""

	if not isinstance(config, dict):
		return ""

	reason = config.get("permission_audit_reason")
	return str(reason).strip() if reason else ""


def can_modify_rule(rule_doc, throw=True):
	"""Check if user can modify a rule"""
	user = frappe.session.user

	# System Manager can always modify
	if "System Manager" in frappe.get_roles(user):
		return True

	# Rule Builder role can modify
	if "Rule Builder" in frappe.get_roles(user):
		return True

	# Check if user owns the rule
	if rule_doc.owner == user:
		return True

	if throw:
		frappe.throw(_("You don't have permission to modify this rule"), frappe.PermissionError)
	return False


def validate_safe_eval(expression):
	"""
	Validate that an expression is safe to evaluate

	Args:
	    expression: Python expression string

	Raises:
	    ValidationError if unsafe
	"""
	try:
		compile(expression, "<string>", "eval")
	except SyntaxError as e:
		frappe.throw(_("Invalid syntax in expression: {0}").format(str(e)), frappe.ValidationError)
	except Exception as e:
		frappe.throw(_("Invalid expression: {0}").format(str(e)), frappe.ValidationError)

	return True  # Expression is safe
