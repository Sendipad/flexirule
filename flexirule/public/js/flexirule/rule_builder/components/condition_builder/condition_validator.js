/**
 * Validates a condition tree recursively.
 * Returns an object with { valid: boolean, message?: string }
 */
export function validateConditions(node, isRoot = false, isMandatory = true) {
	const errors = [];
	const invalidNodes = new Set();

	function walk(n, root = false, mandatory = true) {
		let nodeValid = true;

		// 1. Check for Groups (including Root)
		if (n.conditions !== undefined) {
			if (!n.conditions || n.conditions.length === 0) {
				if (!(root && !mandatory)) {
					errors.push(
						root
							? __("Please add at least one condition.")
							: __("Empty condition groups are not allowed.")
					);
					nodeValid = false;
				}
			} else {
				for (const child of n.conditions) {
					if (!walk(child)) nodeValid = false;
				}
			}
		}
		// 2. Check for Collections
		else if (n.collection !== undefined) {
			if (!n.collection) {
				errors.push(__("Please select a table for the collection condition."));
				nodeValid = false;
			}

			if (!n.where || !n.where.conditions || n.where.conditions.length === 0) {
				errors.push(
					__("Collection '{0}' must have at least one condition.").replace(
						"{0}",
						n.collection || __("Unnamed")
					)
				);
				nodeValid = false;
			} else {
				if (!walk(n.where)) nodeValid = false;
			}
		}
		// 3. Check for Simple Conditions
		else if (n.left !== undefined) {
			const fieldRef = n.left.ref || "";
			if (!fieldRef || fieldRef.endsWith(".")) {
				errors.push(__("Please select a valid field for the condition."));
				nodeValid = false;
			}

			if (!n.op) {
				errors.push(__("Please select an operator for the condition."));
				nodeValid = false;
			}

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
					errors.push(
						__("Please provide a value for field '{0}'.").replace(
							"{0}",
							fieldRef || __("Unknown")
						)
					);
					nodeValid = false;
				}
			}
		}

		if (!nodeValid && n.id) {
			invalidNodes.add(n.id);
		}
		return nodeValid;
	}

	walk(node, isRoot, isMandatory);

	return {
		valid: errors.length === 0,
		errors: [...new Set(errors)],
		invalidNodes: Array.from(invalidNodes),
	};
}
