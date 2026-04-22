/**
 * Validates a condition tree recursively.
 * Returns an object with { valid: boolean, message?: string }
 */
export function validateConditions(node, isRoot = false, isMandatory = true) {
	// 1. Check for Groups (including Root)
	// A group is identified by the presence of a 'conditions' array
	if (node.conditions !== undefined) {
		if (!node.conditions || node.conditions.length === 0) {
			// If it's an optional root group, empty is allowed
			if (isRoot && !isMandatory) return { valid: true };

			return {
				valid: false,
				message: isRoot
					? __("Please add at least one condition.")
					: __("Empty condition groups are not allowed."),
			};
		}

		for (const child of node.conditions) {
			const result = validateConditions(child);
			if (!result.valid) return result;
		}
	}
	// 2. Check for Collections
	// A collection is identified by the presence of a 'collection' field
	else if (node.collection !== undefined) {
		if (!node.collection) {
			return {
				valid: false,
				message: __("Please select a table for the collection condition."),
			};
		}

		if (!node.where || !node.where.conditions || node.where.conditions.length === 0) {
			return {
				valid: false,
				message: __("Collection '{0}' must have at least one condition.").replace(
					"{0}",
					node.collection
				),
			};
		}

		const result = validateConditions(node.where);
		if (!result.valid) return result;
	}

	// 3. Check for Simple Conditions (Field Comparison)
	else if (node.left !== undefined) {
		const fieldRef = node.left.ref || "";
		if (!fieldRef || fieldRef.endsWith(".")) {
			return {
				valid: false,
				message: __("Please select a valid field for the condition."),
			};
		}

		if (!node.op) {
			return {
				valid: false,
				message: __("Please select an operator for the condition."),
			};
		}

		// Operators that don't need a value
		const valueNotRequired = ["is_set", "is_not_set", "is_submittable"];
		if (!valueNotRequired.includes(node.op)) {
			const hasValue =
				(node.right && node.right.value !== undefined && node.right.value !== "") ||
				(node.right && node.right.ref);

			if (!hasValue) {
				return {
					valid: false,
					message: __("Please provide a value for field '{0}'.").replace("{0}", fieldRef),
				};
			}
		}
	}

	return { valid: true };
}
