import frappe

from flexirule.ruleflow.core.evaluator import check_link_match

doc = frappe._dict({"items": [frappe._dict({"t_warehouse": "_Test Warehouse - _TC"})]})

safe_locals = {"doc": doc, "check_link_match": check_link_match, "any": any}

expr = "((any((check_link_match(i.get('t_warehouse'), ['Warehouse', ['_Test Warehouse - _TC']], 'in')) for i in (doc.get('items') or []))))"
try:
	print("Result:", frappe.safe_eval(expr, None, safe_locals))
except Exception as e:
	print("Error:", e)
