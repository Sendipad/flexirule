/**
 * Canonical Condition Frontend Validator
 *
 * Validates a Canonical Condition AST or TreeBuilder model against the backend contract:
 * - Structural constraints (depth, max nodes, min 2 children per group, collection alias)
 * - Operator validity and arity (unary vs binary)
 * - Required FlexValue mode and path constraints
 * - Distinguishing required condition actions from optional execution/entry filters
 */

import { UNARY_OPERATORS } from "./canonical_condition_adapter.mjs";

const DEFAULT_LIMITS = {
	depth: 16,
	nodes: 128,
	path_segments: 8,
};

/**
 * Validates a TreeBuilder UI node or canonical AST condition.
 *
 * @param {Object} tree - The TreeBuilder root or direct canonical node.
 * @param {Object} options - Validation options:
 *   - contract: Result from get_condition_contract()
 *   - isMandatory: Boolean, whether condition is required (e.g. Condition action vs optional entry filter)
 *   - isRoot: Boolean, whether current node is root
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

	const limits = contract?.limits || DEFAULT_LIMITS;
	const operators = contract?.operators || {};
	let totalNodes = 0;

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
		// Validate each child under root
		for (const child of children) {
			validateSubNode(child, 1);
		}
	} else {
		validateSubNode(tree, 1);
	}

	function validateSubNode(node, depth) {
		if (!node || typeof node !== "object") {
			addError("Invalid condition node.");
			return;
		}

		totalNodes += 1;
		if (depth > (limits.depth || 16)) {
			addError("Condition tree exceeds maximum nesting depth.", node.id);
			return;
		}
		if (totalNodes > (limits.nodes || 128)) {
			addError("Condition tree exceeds maximum node count.", node.id);
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

		if (node.is_incomplete_draft && (type === "leaf" || type === "comparison")) {
			const left = node.left;
			const leftReady = Boolean(
				left &&
				left.mode &&
				(left.mode !== "variable" ||
					(left.path?.scope === "doctype" && Array.isArray(left.path?.segments) && left.path.segments.length === 0) ||
					(left.path?.scope && Array.isArray(left.path?.segments) && left.path.segments.length > 0))
			);
			if (!leftReady) addError("Choose a value source.", node.id);
			if (!node.operator) {
				addError("Choose how the value should match.", node.id);
			} else {
				const unary = UNARY_OPERATORS.has(node.operator) || contract?.operators?.[node.operator]?.arity === 1;
				const right = node.right;
				const rightReady = Boolean(
					right &&
					right.mode &&
					(right.mode !== "static" || (right.value_type === "list" ? Array.isArray(right.value) && right.value.length > 0 : right.value === null || (right.value !== undefined && right.value !== ""))) &&
					(right.mode !== "variable" ||
						(right.path?.scope && (right.path.scope === "doctype" || (Array.isArray(right.path.segments) && right.path.segments.length > 0))))
				);
				if (!unary && !rightReady) addError("Choose a comparison value.", node.id);
			}
			return;
		}

		// 1. Comparison node (or leaf in TreeBuilder)
		if (type === "comparison" || type === "leaf") {
			if (node._invalid_right_error || node._draft_invalid_right !== undefined) {
				addError(node._invalid_right_error || "Invalid right operand value.", node.id);
				return;
			}

			const operator = node.operator;
			if (!operator) {
				addError("Comparison operator is required.", node.id);
			}

			// Validate operator against contract if loaded
			if (contract && Object.keys(operators).length > 0) {
				if (!operators[operator]) {
					addError(
						`Operator '${operator}' is not supported by backend contract.`,
						node.id
					);
				}
			}

			// Left operand validation
			const left = node.left;
			if (!left) {
				addError("Left operand is required.", node.id);
			} else if (left.mode === "variable") {
				const path = left.path;
				if (!path || !path.scope) {
					addError("Left operand variable scope is required.", node.id);
				} else if (
					path.scope !== "doctype" &&
					(!Array.isArray(path.segments) || path.segments.length === 0)
				) {
					addError("Left operand must select a document field or variable.", node.id);
				}
			}

			// Right operand validation (for binary operators)
			const isUnary =
				UNARY_OPERATORS.has(operator) || contract?.operators?.[operator]?.arity === 1;
			if (!isUnary) {
				const right = node.right;
				if (!right) {
					addError("Right operand value is required.", node.id);
				} else if (right.mode === "variable") {
					const path = right.path;
					if (!path || !path.scope) {
						addError("Right operand variable scope is required.", node.id);
					}
				} else if (right.mode === "static") {
					if (right.value === "" || right.value === undefined) {
						addError("Right operand static value is required.", node.id);
					}
				}
			}
			return;
		}

		// 2. Group node
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
					validateSubNode(child, depth + 1);
				}
			}
			return;
		}

		// 3. Collection predicate node
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
						validateSubNode(child, depth + 1);
					}
				}
			} else {
				const where = node.where;
				if (!where) {
					addError("Collection 'where' condition is required.", node.id);
				} else {
					validateSubNode(where, depth + 1);
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
