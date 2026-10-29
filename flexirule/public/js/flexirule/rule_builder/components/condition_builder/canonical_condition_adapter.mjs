/**
 * canonical_condition_adapter.mjs
 * Adapter between Canonical Condition AST and Generic TreeBuilder UI Model.
 */

// Mapping of legacy comparison operator symbols/aliases to canonical operator IDs
const LEGACY_OPERATOR_MAP = {
	"==": "eq",
	"=": "eq",
	"!=": "ne",
	"<>": "ne",
	">": "gt",
	">=": "gte",
	"<": "lt",
	"<=": "lte",
	in: "in",
	"not in": "not_in",
	contains: "contains",
	"not contains": "not_contains",
	starts_with: "starts_with",
	ends_with: "ends_with",
	is_empty: "is_empty",
	is_not_empty: "is_not_empty",
	is_set: "is_set",
	is_not_set: "is_not_set",
	is_null: "is_null",
	is_not_null: "is_not_null",
};

/**
 * Coerces raw/legacy left or right value inputs into a canonical FlexValue object.
 */
export function normalizeFlexValue(val) {
	if (val === null || val === undefined) {
		return { value_type: "static", value: null };
	}

	if (typeof val === "object" && val.value_type) {
		return val;
	}

	// Legacy string field path or variable (e.g., "doc.status", "customer_group", "vars.total")
	if (typeof val === "string") {
		const trimmed = val.trim();
		if (
			trimmed.startsWith("doc.") ||
			trimmed.startsWith("old_doc.") ||
			trimmed.startsWith("vars.") ||
			trimmed.startsWith("caller.") ||
			trimmed.startsWith("rule.") ||
			trimmed.startsWith("context.") ||
			trimmed.includes(".")
		) {
			return { value_type: "variable", path: trimmed };
		}
		// Pure string literal
		return { value_type: "static", value: trimmed };
	}

	// Primitive static value
	return { value_type: "static", value: val };
}

/**
 * Normalizes a raw/legacy condition node payload into canonical AST shape before adapter processing.
 */
export function normalizeConditionNode(node) {
	if (!node || typeof node !== "object") {
		return null;
	}

	// Group node format (canonical or legacy)
	if (node.type === "group" || (node.op && (node.conditions || node.children))) {
		const rawChildren = node.conditions || node.children || [];
		const normalizedChildren = rawChildren
			.map((child) => normalizeConditionNode(child))
			.filter(Boolean);

		return {
			type: "group",
			op: (node.op || "and").toLowerCase(),
			children: normalizedChildren,
		};
	}

	// Collection predicate format
	if (node.type === "collection_predicate" || node.quantifier || node.collection) {
		const quantifier = (node.quantifier || "any").toLowerCase();
		const collectionPath = normalizeFlexValue(node.collection || node.source || "");
		const alias = node.alias || "item";
		const rawWhere = node.where || node.conditions || node.predicate;
		const normalizedWhere = rawWhere
			? normalizeConditionNode(rawWhere)
			: { type: "group", op: "and", children: [] };

		return {
			type: "collection_predicate",
			quantifier,
			collection: collectionPath,
			alias,
			where: normalizedWhere,
		};
	}

	// Comparison format
	const rawOp = node.op || node.operator || "eq";
	const canonicalOp = LEGACY_OPERATOR_MAP[rawOp] || rawOp;

	const left = normalizeFlexValue(node.left !== undefined ? node.left : node.field);
	const right =
		node.right !== undefined
			? normalizeFlexValue(node.right)
			: node.value !== undefined
				? normalizeFlexValue(node.value)
				: null;

	return {
		type: "comparison",
		op: canonicalOp,
		left,
		right,
	};
}

/**
 * Hydrates a canonical (or normalized legacy) Condition AST into a Generic TreeBuilder UI state tree.
 *
 * Generic TreeBuilder state node formats:
 * - Group node: { id, type: 'group', operator: 'and'|'or', children: [...] }
 * - Leaf node: { id, type: 'leaf', domain: { type: 'comparison', op, left, right } }
 * - Collection group: { id, type: 'collection', quantifier, collection, alias, children: [...] }
 */
export function hydrateToTreeBuilder(ast) {
	if (!ast) {
		return {
			id: frappe.utils.get_random(12),
			type: "group",
			operator: "and",
			children: [],
		};
	}

	const normalized = normalizeConditionNode(ast);
	if (!normalized) {
		return {
			id: frappe.utils.get_random(12),
			type: "group",
			operator: "and",
			children: [],
		};
	}

	return astToUiNode(normalized);
}

function astToUiNode(node) {
	const id = frappe.utils.get_random(12);

	if (node.type === "group") {
		return {
			id,
			type: "group",
			operator: (node.op || "and").toLowerCase(),
			children: (node.children || []).map((child) => astToUiNode(child)),
		};
	}

	if (node.type === "collection_predicate") {
		const childGroup = astToUiNode(node.where || { type: "group", op: "and", children: [] });
		return {
			id,
			type: "collection",
			quantifier: node.quantifier || "any",
			collection: node.collection || { value_type: "variable", path: "" },
			alias: node.alias || "item",
			children: childGroup.type === "group" ? childGroup.children : [childGroup],
		};
	}

	// Comparison
	return {
		id,
		type: "leaf",
		domain: {
			type: "comparison",
			op: node.op || "eq",
			left: node.left || { value_type: "static", value: "" },
			right: node.right,
		},
	};
}

/**
 * Serializes a Generic TreeBuilder UI state tree back to a strict Canonical Condition AST.
 * Ephemeral UI fields (`id`, wrapper fields) are completely purged.
 */
export function serializeToCanonicalAst(uiNode) {
	if (!uiNode || typeof uiNode !== "object") {
		return null;
	}

	if (uiNode.type === "group") {
		const children = (uiNode.children || [])
			.map((child) => serializeToCanonicalAst(child))
			.filter(Boolean);

		// If root group is empty, return an empty group AST
		return {
			type: "group",
			op: (uiNode.operator || "and").toLowerCase(),
			children,
		};
	}

	if (uiNode.type === "collection") {
		const childNodes = (uiNode.children || [])
			.map((child) => serializeToCanonicalAst(child))
			.filter(Boolean);

		const whereGroup = {
			type: "group",
			op: "and",
			children: childNodes,
		};

		return {
			type: "collection_predicate",
			quantifier: uiNode.quantifier || "any",
			collection: uiNode.collection || { value_type: "variable", path: "" },
			alias: uiNode.alias || "item",
			where: whereGroup,
		};
	}

	if (uiNode.type === "leaf") {
		const domain = uiNode.domain || {};
		const ast = {
			type: "comparison",
			op: domain.op || "eq",
			left: domain.left || { value_type: "static", value: "" },
		};

		if (domain.right !== undefined && domain.right !== null) {
			ast.right = domain.right;
		}

		return ast;
	}

	return null;
}
