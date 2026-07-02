import time

import frappe
from frappe.utils import now

from flexirule.ruleflow.core.coordinator import RuleCoordinator


def test_benchmark_hooks():
	"""
	Benchmark the overhead of execute_rules hook.
	Run via: bench execute flexirule.ruleflow.tests.benchmark_hooks.test_benchmark_hooks
	"""
	print("Starting Benchmark...")

	# Ensure clean slate
	cleanup_dummy_rules()

	# Setup: Create a dummy DocType if needed, or use ToDo
	doctype = "ToDo"

	# Baseline: No Rules
	print("\n--- Baseline (No Active Rules) ---")
	active_rules = frappe.db.get_all("Rule", filters={"is_active": 1}, pluck="name")

	# Temporarily deactivate all rules
	frappe.db.sql("UPDATE `tabRule` SET is_active=0")
	# frappe.db.commit() removed for test isolation
	RuleCoordinator.clear_cache()

	avg_base = measure_save(doctype, 10)
	print(f"Base Save Time: {avg_base * 1000:.2f} ms")

	# Scenario 1: 100 Inactive Rules (Testing Filter Overhead)
	print("\n--- 100 Inactive Rules ---")
	create_dummy_rules(doctype, 100, active=False)
	RuleCoordinator.clear_cache()

	avg_inactive = measure_save(doctype, 10)
	print(f"Inactive Save Time: {avg_inactive * 1000:.2f} ms")
	print(f"Overhead: {(avg_inactive - avg_base) * 1000:.2f} ms")

	# Scenario 2: 1 Active Rule (Applicable)
	print("\n--- 1 Active Rule (Applicable) ---")
	# Activate one rule
	rules = frappe.get_all("Rule", filters={"rule_name": ["like", "Bench %"]}, limit=1)
	if rules:
		frappe.db.set_value("Rule", rules[0].name, "is_active", 1)
		frappe.db.set_value("Rule", rules[0].name, "trigger_event", "Before Save")

	RuleCoordinator.clear_cache()

	avg_active_1 = measure_save(doctype, 10)
	print(f"1 Active Rule Time: {avg_active_1 * 1000:.2f} ms")
	print(f"Overhead: {(avg_active_1 - avg_base) * 1000:.2f} ms")

	# Cleanup
	cleanup_dummy_rules()

	# Restore original state
	if active_rules:
		frappe.db.sql("UPDATE `tabRule` SET is_active=1 WHERE name IN %s", (tuple(active_rules),))
	# frappe.db.commit() removed for test isolation
	RuleCoordinator.clear_cache()
	print("\nBenchmark Complete.")


def measure_save(doctype, iterations=10):
	total_time: float = 0.0
	for i in range(iterations):
		doc = frappe.new_doc(doctype)
		doc.description = f"Benchmark {i}"

		start = time.perf_counter()
		doc.insert()
		end = time.perf_counter()

		total_time += end - start
		# Cleanup with force to remove linked Execution Logs
		frappe.delete_doc(doc.doctype, doc.name, force=1)

	return total_time / iterations


def create_dummy_rules(doctype, count, active=False):
	frappe.db.auto_commit_on_many_writes = True
	for i in range(count):
		r = frappe.new_doc("Rule")
		r.rule_name = f"Bench {i}"
		r.document_type = doctype
		r.trigger_event = "Before Save"
		r.is_active = 1 if active else 0
		r.execution_mode = "Synchronous"
		r.insert()
	# frappe.db.commit() removed for test isolation


def cleanup_dummy_rules():
	frappe.db.sql("DELETE FROM `tabRule` WHERE rule_name LIKE 'Bench %'")
	frappe.db.sql("DELETE FROM `tabRule Action` WHERE parent LIKE 'Bench %'")
	frappe.db.sql("DELETE FROM `tabRule Execution Log` WHERE rule LIKE 'Bench %'")
	# frappe.db.commit() removed for test isolation
