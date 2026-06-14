# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import random_string

def create_test_rule(rule_name=None, document_type="ToDo", actions=None, **kwargs):
    """Factory to create a Rule for testing."""
    rule_data = {
        "doctype": "Rule",
        "rule_name": rule_name or f"Test Rule {random_string(5)}",
        "document_type": document_type,
        "trigger_type": kwargs.get("trigger_type", "DocType Event"),
        "trigger_event": kwargs.get("trigger_event", "Validate"),
        "is_active": kwargs.get("is_active", 1),
        "actions": actions or []
    }
    rule_data.update(kwargs)

    rule = frappe.get_doc(rule_data)
    rule.insert(ignore_permissions=True)
    return rule

def create_process_action(action_id, process_name, operation, next_step=None, config=None, **kwargs):
    """Helper to create a Process action dict."""
    action = {
        "action_id": action_id,
        "action_type": "Process",
        "action_label": f"Run {process_name}:{operation}",
        "process_name": process_name,
        "operation": operation,
        "next_step_if_true": next_step,
        "config": config or "{}",
        "is_enabled": 1
    }
    action.update(kwargs)
    return action

def create_condition_action(action_id, expression, next_true, next_false, **kwargs):
    """Helper to create a Condition action dict."""
    action = {
        "action_id": action_id,
        "action_type": "Condition",
        "action_label": f"Check {action_id}",
        "compiled_expression": expression,
        "next_step_if_true": next_true,
        "next_step_if_false": next_false,
        "is_enabled": 1
    }
    action.update(kwargs)
    return action
