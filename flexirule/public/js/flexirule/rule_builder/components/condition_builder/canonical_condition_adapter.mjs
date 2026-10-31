/** Adapter between the canonical condition contract and TreeBuilder's UI model. */

const SCOPES = new Set(["doc", "old_doc", "vars", "item", "loop", "row", "caller", "rule", "doctype"]);

const LEGACY_OPERATOR_MAP = {
	"==": "eq", "=": "eq", "!=": "ne", "<>": "ne", ">": "gt", ">=": "gte", "<": "lt", "<=": "lte",
	in: "in", "not in": "not_in", contains: "contains", "not contains": "not_contains",
	starts_with: "starts_with", ends_with: "ends_with", is_empty: "is_empty", is_not_empty: "is_not_empty",
	is_set: "is_set", is_not_set: "is_not_set", is_null: "is_null", is_not_null: "is_not_null",
};

export function normalizeFlexValue(value) {
	if (value && typeof value === "object" && value.mode === "variable") {
		if (value.path && typeof value.path === "object" && Array.isArray(value.path.segments)) return value;
		return { mode: "variable", path: textToCanonicalPath(value.value ?? value.path) };
	}
	if (value && typeof value === "object" && value.mode === "static" && value.value_type) {
		return value;
	}
	if (value && typeof value === "object" && value.mode === "resolver") {
		if (typeof value.family === "string" && typeof value.operation === "string" && value.config && typeof value.config === "object") return value;
		throw new TypeError("Legacy resolver operands must be migrated to an explicitly registered canonical resolver.");
	}
	if (value && typeof value === "object" && value.mode) {
		throw new TypeError(`Unsupported FlexValue mode: ${String(value.mode)}`);
	}
	if (value && typeof value === "object" && value.value_type === "variable") {
		return { mode: "variable", path: textToCanonicalPath(value.path) };
	}
	if (value && typeof value === "object" && value.value_type === "static") {
		return { mode: "static", ...inferStaticType(value.value) };
	}
	if (value && typeof value === "object" && value.value_type === "resolver") {
		throw new TypeError("Legacy resolver operands must be migrated to an explicitly registered canonical resolver.");
	}
	if (typeof value === "string") {
		const trimmed = value.trim();
		const first = trimmed.split(".")[0];
		if (trimmed.includes(".") && SCOPES.has(first) && first !== "doctype") {
			return { mode: "variable", path: textToCanonicalPath(trimmed) };
		}
		return { mode: "static", value_type: "string", value };
	}
	return { mode: "static", ...inferStaticType(value) };
}

export function normalizeConditionNode(node) {
	assertObject(node, "Condition node");
	if (node.type === "group" || (Array.isArray(node.conditions) && typeof node.op === "string")) {
		const children = node.children ?? node.conditions;
		if (!Array.isArray(children)) throw new TypeError("Condition group children must be an array.");
		return {
			type: "group",
			operator: node.operator ?? node.op,
			children: children.map(normalizeConditionNode),
		};
	}
	if (node.type === "collection_predicate" || node.quantifier || node.collection || node.source) {
		const source = node.source ?? node.collection;
		const canonicalSource = source?.mode === "variable" && source.path?.scope && Array.isArray(source.path?.segments)
			? source
			: { mode: "variable", path: textToCanonicalPath(typeof source === "string" ? source : source?.value ?? source?.path) };
		return {
			type: "collection_predicate",
			quantifier: node.quantifier ?? "any",
			source: canonicalSource,
			as: node.as ?? node.alias ?? "item",
			where: normalizeConditionNode(node.where ?? node.predicate ?? {
				type: "group", operator: "and", children: node.conditions ?? [],
			}),
		};
	}
	if (node.type !== "comparison" && !("operator" in node) && !("op" in node)) {
		throw new TypeError("Unsupported condition payload; expected a canonical or migratable condition node.");
	}
	const rawOperator = node.operator ?? node.op;
	const operator = LEGACY_OPERATOR_MAP[rawOperator] ?? rawOperator;
	const right = node.right !== undefined ? node.right : node.value;
	const left = node.left !== undefined
		? normalizeFlexValue(node.left)
		: typeof node.field === "string"
			? { mode: "variable", path: textToCanonicalPath(node.field) }
			: normalizeFlexValue(node.field);
	const result = { type: "comparison", operator, left };
	if (right !== undefined && right !== null) result.right = normalizeFlexValue(right);
	return result;
}

function newId() {
	return globalThis.frappe?.utils?.get_random?.(12) || `condition-${globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2)}`;
}

function assertObject(value, label) {
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		throw new TypeError(`${label} must be an object.`);
	}
}

function canonicalPathToText(path) {
	assertObject(path, "Canonical variable path");
	const { scope, segments } = path;
	if (!SCOPES.has(scope) || !Array.isArray(segments) || !segments.length ||
		segments.some((segment) => typeof segment !== "string" || !/^[A-Za-z0-9_]+$/.test(segment) || segment.includes("__"))) {
		throw new TypeError("Canonical variable path is invalid.");
	}
	return [scope, ...segments].join(".");
}

function textToCanonicalPath(value) {
	if (typeof value !== "string" || !value.trim()) {
		throw new TypeError("Variable path is required.");
	}
	const parts = value.trim().split(".");
	let scope = parts.length > 1 && SCOPES.has(parts[0]) ? parts.shift() : "doc";
	if (scope === "doctype") {
		throw new TypeError("The doctype scope is not a field-value scope.");
	}
	if (!parts.length || parts.some((part) => !/^[A-Za-z0-9_]+$/.test(part) || part.includes("__"))) {
		throw new TypeError("Variable path contains an invalid segment.");
	}
	return { scope, segments: parts };
}

function inferStaticType(value) {
	if (value === null || value === undefined) return { value_type: "null", value: null };
	if (typeof value === "boolean") return { value_type: "boolean", value };
	if (typeof value === "number") {
		if (!Number.isFinite(value)) throw new TypeError("Static numeric values must be finite.");
		return Number.isInteger(value)
			? { value_type: "integer", value }
			: { value_type: "decimal", value: String(value) };
	}
	if (typeof value === "string") return { value_type: "string", value };
	if (Array.isArray(value)) return { value_type: "list", value };
	if (typeof value === "object") return { value_type: "object", value };
	throw new TypeError("Unsupported static value type.");
}

/** Convert the canonical FlexValue contract into the shape FlexValueControl can edit. */
export function canonicalFlexValueToUi(value) {
	assertObject(value, "FlexValue");
	switch (value.mode) {
		case "static":
			return { mode: "static", value_type: value.value_type, value: value.value };
		case "variable":
			return { mode: "variable", value: canonicalPathToText(value.path) };
		case "resolver":
			return { mode: "resolver", family: value.family, operation: value.operation, config: value.config };
		default:
			throw new TypeError(`Unsupported canonical FlexValue mode: ${String(value.mode)}`);
	}
}

/** Convert FlexValueControl output into a strict canonical FlexValue. */
export function uiFlexValueToCanonical(value) {
	assertObject(value, "Operand");
	switch (value.mode) {
		case "static": {
			if (Object.hasOwn(value, "value_type")) {
				const typed = { mode: "static", value_type: value.value_type, value: value.value };
				if (!["string", "integer", "decimal", "boolean", "null", "date", "datetime", "time", "list", "object"].includes(typed.value_type)) {
					throw new TypeError("Static operand has an unsupported value type.");
				}
				if (typed.value_type === "decimal" && typeof typed.value !== "string") {
					typed.value = String(typed.value);
				}
				return typed;
			}
			return { mode: "static", ...inferStaticType(value.value) };
		}
		case "variable":
			return { mode: "variable", path: textToCanonicalPath(value.value ?? value.path) };
		case "resolver":
			if (typeof value.family !== "string" || !value.family || typeof value.operation !== "string" || !value.operation || !value.config || typeof value.config !== "object" || Array.isArray(value.config)) {
				throw new TypeError("Resolver operands must use an explicitly supported family, operation, and configuration.");
			}
			return { mode: "resolver", family: value.family, operation: value.operation, config: value.config };
		default:
			throw new TypeError(`Unsupported operand mode: ${String(value.mode)}`);
	}
}

function astToUiNode(node) {
	assertObject(node, "Condition node");
	const id = newId();
	if (node.type === "group") {
		if (!["and", "or"].includes(node.operator) || !Array.isArray(node.children)) {
			throw new TypeError("Canonical group requires operator and children.");
		}
		return { id, type: "group", operator: node.operator, children: node.children.map(astToUiNode) };
	}
	if (node.type === "comparison") {
		if (typeof node.operator !== "string" || !node.left) {
			throw new TypeError("Canonical comparison requires operator and left operand.");
		}
		const domain = { type: "comparison", op: node.operator, left: canonicalFlexValueToUi(node.left) };
		if (Object.hasOwn(node, "right")) domain.right = canonicalFlexValueToUi(node.right);
		return { id, type: "leaf", domain };
	}
	if (node.type === "collection_predicate") {
		if (!["any", "all", "none"].includes(node.quantifier) || typeof node.as !== "string" || !node.source || !node.where) {
			throw new TypeError("Canonical collection predicate is incomplete.");
		}
		if (node.source.mode !== "variable") {
			throw new TypeError("Collection source must be a variable path.");
		}
		const where = astToUiNode(node.where);
		return {
			id, type: "collection", quantifier: node.quantifier,
			collection: canonicalFlexValueToUi(node.source), alias: node.as,
			children: where.type === "group" ? where.children : [where],
		};
	}
	throw new TypeError(`Unsupported canonical condition node type: ${String(node.type)}`);
}

/** Hydrate a canonical AST. Invalid input throws instead of silently becoming an empty condition. */
export function hydrateToTreeBuilder(ast) {
	if (ast == null) return { id: newId(), type: "group", operator: "and", children: [] };
	return astToUiNode(ast);
}

function uiNodeToAst(node, operators = []) {
	if (!node || typeof node !== "object") throw new TypeError("Tree node is invalid.");
	if (node.type === "group") {
		return {
			type: "group",
			operator: node.operator,
			children: (node.children || []).map((child) => uiNodeToAst(child, operators)),
		};
	}
	if (node.type === "leaf") {
		const domain = node.domain || {};
		const ast = { type: "comparison", operator: domain.op, left: uiFlexValueToCanonical(domain.left) };
		const operator = operators.find((item) => item?.id === domain.op);
		if (!operator) throw new TypeError(`Unsupported canonical condition operator: ${String(domain.op)}`);
		if (operator.arity === 2) ast.right = uiFlexValueToCanonical(domain.right);
		return ast;
	}
	if (node.type === "collection") {
		return {
			type: "collection_predicate",
			quantifier: node.quantifier,
			source: uiFlexValueToCanonical(node.collection),
			as: node.alias,
			where: (() => {
				const children = (node.children || []).map((child) => uiNodeToAst(child, operators));
				if (children.length === 1) return children[0];
				return { type: "group", operator: "and", children };
			})(),
		};
	}
	throw new TypeError(`Unsupported TreeBuilder node type: ${String(node.type)}`);
}

/** Serialize to the exact backend AST contract; ephemeral TreeBuilder fields are discarded. */
export function serializeToCanonicalAst(uiNode, options = {}) {
	if (!uiNode || typeof uiNode !== "object") return null;
	if (uiNode.type === "group" && (!Array.isArray(uiNode.children) || uiNode.children.length === 0)) return null;
	return uiNodeToAst(uiNode, options.operators || []);
}
