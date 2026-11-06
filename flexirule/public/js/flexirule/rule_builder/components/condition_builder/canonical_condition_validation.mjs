/**
 * Canonical Condition Frontend Draft-State Validator
 *
 * Implements lightweight UI draft-state checks for immediate authoring feedback:
 * - Left operand selection
 * - Operator selection
 * - Required right operand presence for binary operators
 * - Nested group minimum children
 * - Collection alias and where presence
 *
 * Semantic validation (operator compatibility, type compatibility, DocType field existence,
 * path traversal safety) is strictly owned and enforced by the backend validate_condition API.
 */

import { UNARY_OPERATORS } from "./canonical_condition_adapter.mjs";

/**
 * Performs draft-state checks on a condition tree or canonical node.
 *
 * @param {Object} tree - The TreeBuilder root or direct canonical node.
 * @param {Object} options - Validation options:
 *   - contract: Backend contract DTO (optional, for arity check)
 *   - isMandatory: Boolean, whether condition is required
 * @returns {Object} { valid: boolean, errors: string[], nodeErrors: Map<string, string[]> }
 */
export function validateCanonicalCondition(tree, { contract = null, isMandatory = false } = {}) {
	const errors = [];
	const nodeErrors = new Map();

	function addError(msg, nodeId = null) {
		errors.push(msg);
		if (nodeId) {
			const existing = nodeErrors.get(nodeId) || [];
			existing.push(msg);
			nodeErrors.set(nodeId, existing);
		}
	}

	if (!tree) {
		if (isMandatory) {
			addError("Condition is required.");
		}
		return { valid: errors.length === 0, errors, nodeErrors };
	}

	// Distinguish TreeBuilder root group from direct canonical node
	const isTreeBuilderRoot = tree.type === "group" && tree.id === "root";
	const children = isTreeBuilderRoot ? tree.children || [] : null;

	if (isTreeBuilderRoot) {
		if (children.length === 0) {
			if (isMandatory) {
				addError("Condition cannot be empty.");
			}
			return { valid: errors.length === 0, errors, nodeErrors };
		}
		for (const child of children) {
			validateSubNode(child);
		}
	} else {
		validateSubNode(tree);
	}

	function validateSubNode(node) {
		if (!node || typeof node !== "object") {
			addError("Invalid condition node.");
			return;
		}

		if (node.is_unsupported) {
			addError(
				node.unsupported_reason || "Unsupported condition requires manual resolution.",
				node.id
			);
			return;
		}

		const type = node.type;

		// Comparison node (or leaf in TreeBuilder)
		if (type === "comparison" || type === "leaf") {
			if (node._invalid_right_error || node._draft_invalid_right !== undefined) {
				addError(node._invalid_right_error || "Invalid right operand value.", node.id);
				return;
			}

			// 1. Left operand check
			const left = node.left;
			const hasLeft = Boolean(
				left &&
					(typeof left === "string" ? left.trim().length > 0 : left.mode)
			);
			if (!hasLeft) {
				addError("Left operand is required (choose a value source).", node.id);
			}

			// 2. Operator check
			const operator = node.operator;
			if (!operator) {
				addError("Comparison operator is required.", node.id);
			}

			// 3. Right operand check (for binary operators)
			const isUnary =
				UNARY_OPERATORS.has(operator) || contract?.operators?.[operator]?.arity === 1;
			if (operator && !isUnary) {
				const right = node.right;
				const hasRight = Boolean(
					right &&
						(typeof right === "string"
							? right.trim().length > 0
							: right.mode === "static"
							? right.value_type === "list"
								? Array.isArray(right.value) && right.value.length > 0
								: right.value === null || (right.value !== undefined && right.value !== "")
							: right.mode)
				);
				if (!hasRight) {
					addError("Right operand value is required (choose a comparison value).", node.id);
				}
			}
			return;
		}

		// Group node
		if (type === "group") {
			const op = node.operator;
			if (op !== "and" && op !== "or") {
				addError("Group operator must be 'and' or 'or'.", node.id);
			}
			const groupChildren = node.children;
			if (!Array.isArray(groupChildren) || groupChildren.length < 2) {
				addError("A nested group must have at least two conditions.", node.id);
			}
			if (Array.isArray(groupChildren)) {
				for (const child of groupChildren) {
					validateSubNode(child);
				}
			}
			return;
		}

		// Collection predicate node
		if (type === "collection_predicate" || type === "collection") {
			const quantifier = node.quantifier;
			if (!["any", "all", "none"].includes(quantifier)) {
				addError("Collection quantifier must be any, all, or none.", node.id);
			}

			const alias = node.as || node.alias;
			if (!alias || !/^[A-Za-z][A-Za-z0-9_]*$/.test(alias) || alias.includes("__")) {
				addError("Collection alias must be a valid identifier without '__'.", node.id);
			}

			const source = node.source;
			if (!source && !node.collection) {
				addError("Collection source table is required.", node.id);
			}

			if (type === "collection") {
				const colChildren = node.children || [];
				if (colChildren.length === 0) {
					addError("Collection must contain at least one condition.", node.id);
				} else {
					for (const child of colChildren) {
						validateSubNode(child);
					}
				}
			} else {
				const where = node.where;
				if (!where) {
					addError("Collection 'where' condition is required.", node.id);
				} else {
					validateSubNode(where);
				}
			}
			return;
		}

		addError(`Unknown condition node type '${type}'.`, node.id);
	}

	return {
		valid: errors.length === 0,
		errors: [...new Set(errors)],
		nodeErrors,
	};
}
