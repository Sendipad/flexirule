/**
 * Validates a condition tree recursively.
 * Returns an object with { valid: boolean, errors: Array<{ id, field, message }>, message?: string }
 */
export function validateConditions(node, isRoot = false, isMandatory = true) {
	const result = {
		valid: true,
		errors: [], // Array of { id: string, field: string, message: string }
		message: "", // Legacy support for first error message
	};

	function addError(id, field, message) {
		result.valid = false;
		result.errors.push({ id, field, message });
		if (!result.message) result.message = message;
	}

	function walk(n, is_root = false) {
		if (!n) return;

		// 1. Check for Groups (including Root)
		if (n.conditions !== undefined) {
			if (!n.conditions || n.conditions.length === 0) {
				if (is_root && !isMandatory) return;
				addError(
					n.id,
					"conditions",
					is_root
						? __("Please add at least one condition.")
						: __("Empty condition groups are not allowed.")
				);
			} else {
				n.conditions.forEach((child) => walk(child));
			}
		}
		// 2. Check for Collections
		else if (n.collection !== undefined || n.where !== undefined) {
			if (!n.collection) {
				addError(n.id, "collection", __("Please select a table for the collection."));
			}

			if (!n.where || !n.where.conditions || n.where.conditions.length === 0) {
				addError(
					n.id,
					"where",
					__("Collection '{0}' must have at least one condition.").replace(
						"{0}",
						n.collection || __("Table")
					)
				);
			} else {
				walk(n.where);
			}
		}
		// 3. Check for Simple Conditions
		else if (n.left !== undefined) {
			const fieldRef = n.left.ref || "";
			if (!fieldRef || fieldRef.endsWith(".")) {
				addError(n.id, "left", __("Please select a valid field for the condition."));
			}

			if (!n.op) {
				addError(n.id, "op", __("Please select an operator for the condition."));
			} else {
				// Operators that don't need a value
				const valueNotRequired = [
					"is_set",
					"is_not_set",
					"is_submittable",
					"is_empty",
					"is_not_empty",
				];
				if (!valueNotRequired.includes(n.op)) {
					const hasValue =
						(n.right && n.right.value !== undefined && n.right.value !== "") ||
						(n.right && n.right.ref);

					if (!hasValue) {
						addError(
							n.id,
							"right",
							__("Please provide a value for field '{0}'.").replace("{0}", fieldRef)
						);
					}
				}
			}
		}
	}

	walk(node, isRoot);
	return result;
}
