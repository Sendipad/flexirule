import frappe


def test():
	print("--- Test 1: Query Child DocType directly ---")
	try:
		# e.g., 'Has Role' is a child of 'User'
		res = frappe.get_list(
			"Has Role",
			filters={"role": "System Manager"},
			parent_doctype="User",
			fields=["name", "parent", "role"],
		)
		print(f"Success: {len(res)} rows returned")
		if res:
			print("Sample:", res[0])
	except Exception as e:
		print("Error:", str(e))

	print("\n--- Test 2: Dotted path in filters (Parent query) ---")
	try:
		res = frappe.get_list("User", filters={"roles.role": "System Manager"}, fields=["name"])
		print(f"Success: {len(res)} rows returned")
	except Exception as e:
		print("Error:", str(e))

	print("\n--- Test 3: List-of-list child filter (Parent query) ---")
	try:
		# The frappe way of doing child filters in list of lists:
		# [ChildDocType, child_fieldname, operator, value]
		res = frappe.get_list("User", filters=[["Has Role", "role", "=", "System Manager"]], fields=["name"])
		print(f"Success: {len(res)} rows returned")
	except Exception as e:
		print("Error:", str(e))

	print("\n--- Test 4: Dotted path in fields (Parent query) ---")
	try:
		res = frappe.get_list(
			"User", filters=[["Has Role", "role", "=", "System Manager"]], fields=["name", "roles.role"]
		)
		print(f"Success: {len(res)} rows returned")
	except Exception as e:
		print("Error:", str(e))


if __name__ == "__main__":
	frappe.init(site="tests.local")
	frappe.connect()
	test()
