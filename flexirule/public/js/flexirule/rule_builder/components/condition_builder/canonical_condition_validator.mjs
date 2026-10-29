/**
 * canonical_condition_validator.mjs
 * Validation utilities for Canonical Condition AST and Generic TreeBuilder UI model.
 */

/**
 * Validates a single FlexValue operand object.
 */
export function validateFlexValue(flexValue, fieldName = "Operand") {
	if (!flexValue || typeof flexValue !== "object") {
		return `${fieldName} is missing or invalid.`;
	}

	if (!flexValue.value_type) {
		return `${fieldName} must specify a valid value type.`;
	}

	if (flexValue.value_type === "variable" && (!flexValue.path || !flexValue.path.trim())) {
		return `${fieldName} requires a variable path.`;
	}

	if (flexValue.value_type === "resolver" && !flexValue.resolver) {
		return `${fieldName} requires a configured resolver function.`;
	}

	return null;
}

/**
 * Validates a comparison domain object against the operator contract.
 *
 * @param {Object} domain - Leaf domain containing { type: 'comparison', op, left, right }
 * @param {Array} operators - Operators array from contract DTO
 * @returns {Array<string>} Array of error message strings
 */
export function validateComparisonDomain(domain, operators = []) {
	const errors = [];

	if (!domain || domain.type !== "comparison") {
		errors.push("Invalid comparison data.");
		return errors;
	}

	if (!domain.op) {
		errors.push("Comparison operator is required.");
	}

	const leftErr = validateFlexValue(domain.left, "Left operand");
	if (leftErr) {
		errors.push(leftErr);
	}

	// Lookup operator arity from contract
	const opMeta = operators.find((o) => o.id === domain.op);
	const arity = opMeta ? opMeta.arity : 2; // Default arity 2 if contract uninitialized

	if (arity === 2) {
		const rightErr = validateFlexValue(domain.right, "Right operand");
		if (rightErr) {
			errors.push(rightErr);
		}
	}

	return errors;
}

/**
 * Validates a UI tree node (or canonical AST) recursively.
 *
 * @param {Object} uiNode - TreeBuilder UI node or canonical AST node
 * @param {Object} options
 * @param {Array} [options.operators=[]] - Contract operators
 * @param {boolean} [options.isMandatory=false] - Whether a non-empty condition is mandatory
 * @returns {Object} { isValid: boolean, errors: Array<string> }
 */
export function validateConditionTree(uiNode, options = {}) {
	const { operators = [], isMandatory = false } = options;
	const errors = [];

	if (!uiNode) {
		if (isMandatory) {
			return { isValid: false, errors: ["Condition is required."] };
		}
		return { isValid: true, errors: [] };
	}

	function walk(node, path = "") {
		if (!node) return;

		if (node.type === "group") {
			const children = node.children || [];
			if (children.length === 0 && isMandatory && path === "") {
				errors.push("At least one condition rule is required.");
			}
			children.forEach((child, idx) => walk(child, `${path}.children[${idx}]`));
		} else if (node.type === "collection") {
			if (!node.collection || (node.collection.value_type === "variable" && !node.collection.path)) {
				errors.push("Collection path is required for collection predicate.");
			}
			const children = node.children || [];
			if (children.length === 0) {
				errors.push("Collection predicate requires at least one nested condition.");
			}
			children.forEach((child, idx) => walk(child, `${path}.collection[${idx}]`));
		} else if (node.type === "leaf" || node.domain) {
			const leafErrors = validateComparisonDomain(node.domain || node, operators);
			leafErrors.forEach((err) => errors.push(err));
		}
	}

	walk(uiNode);

	return {
		isValid: errors.length === 0,
		errors,
	};
}
