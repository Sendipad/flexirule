/**
 * Canonical Condition Adapter
 *
 * Provides bidirectional translation between:
 * 1. Canonical Condition AST (persisted backend contract, direct node without envelopes)
 * 2. TreeBuilder UI model (hierarchical UI tree with ephemeral IDs, group/leaf/collection nodes)
 *
 * Also provides safe deterministic legacy configuration conversion and diagnostic reporting
 * for unsupported legacy conditions without data loss.
 */

import { TREE_NODE_TYPES, DEFAULT_GROUP_OPERATORS } from "../tree_builder/tree_builder_types.mjs";
import { createNodeId } from "../tree_builder/tree_builder_utils.mjs";

/**
 * Backend reserved scopes and aliases. Cannot be used as collection aliases.
 */
export const RESERVED_ALIASES = new Set([
	"doc",
	"old_doc",
	"vars",
	"item",
	"loop",
	"row",
	"caller",
	"rule",
	"doctype",
	"and",
	"or",
	"any",
	"all",
	"none",
]);

/**
 * Generates a safe, deterministic collection alias from a table field name.
 * Avoids reserved aliases (such as 'row') and handles collisions deterministically.
 */
export function generateCollectionAlias(tableFieldName, existingAliases = new Set()) {
	let raw = (tableFieldName || "item").trim();
	if (raw.includes(".")) {
		const parts = raw.split(".");
		raw = parts[parts.length - 1];
	}
	let cleaned = raw
		.replace(/[^a-zA-Z0-9_]/g, "_")
		.replace(/_+/g, "_")
		.replace(/^_|_$/g, "");
	if (!cleaned || /^[0-9]/.test(cleaned)) {
		cleaned = `tbl_${cleaned}`;
	}

	let candidate = `${cleaned}_row`;
	if (candidate === "row" || RESERVED_ALIASES.has(candidate)) {
		candidate = `${cleaned}_item`;
	}

	let finalAlias = candidate;
	let counter = 1;
	while (RESERVED_ALIASES.has(finalAlias) || existingAliases.has(finalAlias)) {
		counter += 1;
		finalAlias = `${candidate}_${counter}`;
	}
	return finalAlias;
}

/**
 * Return aliases belonging to collections with the same lexical parent.
 * The parent may be the root, a group, or a collection's child group.
 */
export function getCollectionSiblingAliases(tree, nodeId) {
	function findParent(current) {
		if (!current || !Array.isArray(current.children)) return null;
		for (const child of current.children) {
			if (child?.id === nodeId) return current;
			const parent = findParent(child);
			if (parent) return parent;
		}
		return null;
	}

	const parent = findParent(tree);
	return (parent?.children || [])
		.filter((child) => child && child.id !== nodeId && child.type === TREE_NODE_TYPES.COLLECTION)
		.map((child) => child.alias)
		.filter(Boolean);
}

/**
 * Deterministic legacy operator to canonical operator mapping.
 */
export const LEGACY_OPERATOR_MAP = Object.freeze({
	"==": "eq",
	"=": "eq",
	eq: "eq",
	"!=": "ne",
	ne: "ne",
	">": "gt",
	gt: "gt",
	">=": "gte",
	gte: "gte",
	"<": "lt",
	lt: "lt",
	"<=": "lte",
	lte: "lte",
	in: "in",
	"not in": "not_in",
	not_in: "not_in",
	is_set: "is_set",
	is_not_set: "is_not_set",
	is_null: "is_null",
	is_not_null: "is_not_null",
	is_empty: "is_empty",
	is_not_empty: "is_not_empty",
	contains: "contains",
	not_contains: "not_contains",
	starts_with: "starts_with",
	ends_with: "ends_with",
	is_submittable: "is_submittable",
	has_field: "has_field",
	length_eq: "length_eq",
	length_gt: "length_gt",
	length_gte: "length_gte",
	length_lt: "length_lt",
	length_lte: "length_lte",
});

/**
 * Unary operators that take no right operand.
 */
export const UNARY_OPERATORS = new Set([
	"is_set",
	"is_not_set",
	"is_null",
	"is_not_null",
	"is_empty",
	"is_not_empty",
	"is_submittable",
]);

/**
 * Known legacy operators that cannot be automatically/deterministically migrated.
 */
export const UNSUPPORTED_LEGACY_OPERATORS = new Set([
	"like",
	"not like",
	"regex",
	"between",
	"not between",
	"in list",
	"not in list",
]);

/**
 * Deep clones an object safely.
 */
export function deepClone(val) {
	if (val === undefined || val === null) return val;
	return JSON.parse(JSON.stringify(val));
}

/**
 * Checks if a value is a plain object.
 */
function isPlainObject(val) {
	return Boolean(val && typeof val === "object" && !Array.isArray(val));
}

/**
 * Converts a dot-notated field expression (e.g. "status", "doc.status", "vars.my_var", "item_row.qty")
 * to a canonical variable FlexValue: { mode: "variable", path: { scope, segments: [...] } }.
 */
export function fieldExpressionToCanonicalVariable(expr, defaultScope = "doc") {
	if (isPlainObject(expr) && expr.mode) {
		return deepClone(expr);
	}

	const str = typeof expr === "string" ? expr.trim() : "";
	if (!str) {
		return {
			mode: "variable",
			path: {
				scope: defaultScope,
				segments: [],
			},
		};
	}

	const parts = str.split(".").filter(Boolean);
	if (parts.length === 0) {
		return {
			mode: "variable",
			path: {
				scope: defaultScope,
				segments: [],
			},
		};
	}

	const knownScopes = new Set(["doc", "old_doc", "vars", "caller", "rule", "doctype"]);
	if (knownScopes.has(parts[0])) {
		return {
			mode: "variable",
			path: {
				scope: parts[0],
				segments: parts.slice(1),
			},
		};
	}

	if (parts.length > 1) {
		return {
			mode: "variable",
			path: {
				scope: parts[0],
				segments: parts.slice(1),
			},
		};
	}

	return {
		mode: "variable",
		path: {
			scope: defaultScope,
			segments: parts,
		},
	};
}

/**
 * Converts a canonical variable FlexValue to dot-notation (e.g. "doc.status", "vars.counter").
 */
export function canonicalVariableToFieldExpression(flexValue) {
	if (!isPlainObject(flexValue)) return "";
	if (flexValue.mode !== "variable") return "";
	const path = flexValue.path;
	if (!path || typeof path !== "object") return "";
	const scope = path.scope || "doc";
	const segments = Array.isArray(path.segments) ? path.segments : [];
	if (scope === "doctype" && !segments.length) return "doctype";
	if (segments.length === 0) return scope;
	return `${scope}.${segments.join(".")}`;
}

/**
 * Infers a canonical static value type from raw JS value and optional fieldtype hint.
 */
export function inferCanonicalValueType(val, fieldtype = null) {
	if (val === null || val === undefined) return "null";
	if (typeof val === "boolean") return "boolean";
	if (Array.isArray(val)) return "list";

	if (fieldtype) {
		const ft = String(fieldtype).toLowerCase();
		if (ft === "check") return "boolean";
		if (ft === "int") return "integer";
		if (ft === "currency" || ft === "float" || ft === "percent") return "decimal";
		if (ft === "date") return "date";
		if (ft === "datetime") return "datetime";
		if (ft === "time") return "time";
	}

	if (typeof val === "number") {
		return Number.isInteger(val) ? "integer" : "decimal";
	}

	if (typeof val === "string") {
		if (/^\d{4}-\d{2}-\d{2}$/.test(val)) return "date";
		if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/.test(val)) return "datetime";
		if (/^\d{2}:\d{2}(:\d{2})?$/.test(val)) return "time";
		return "string";
	}

	if (typeof val === "object") return "object";
	return "string";
}

/**
 * Safely parses integer without silent truncation or NaN fallback to 0.
 * Throws TypeError / RangeError if invalid integer string.
 */
export function safeCoerceInteger(val) {
	if (typeof val === "number") {
		if (!Number.isFinite(val))
			throw new TypeError(`Non-finite number cannot be coerced to integer: ${val}`);
		if (!Number.isInteger(val))
			throw new TypeError(`Fractional number cannot be coerced to integer: ${val}`);
		return val;
	}
	if (typeof val === "string") {
		const trimmed = val.trim();
		if (!/^-?\d+$/.test(trimmed)) {
			throw new TypeError(`Invalid integer format: '${val}'`);
		}
		const parsed = Number(trimmed);
		if (!Number.isSafeInteger(parsed)) {
			throw new RangeError(`Integer out of safe range: '${val}'`);
		}
		return parsed;
	}
	throw new TypeError(`Cannot coerce value of type ${typeof val} to integer`);
}

/**
 * Safely parses decimal without losing precision or silent coercion.
 */
export function safeCoerceDecimal(val) {
	if (typeof val === "number") {
		if (!Number.isFinite(val))
			throw new TypeError(`Non-finite number cannot be coerced to decimal: ${val}`);
		return String(val);
	}
	if (typeof val === "string") {
		const trimmed = val.trim();
		if (!/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(trimmed)) {
			throw new TypeError(`Invalid decimal format: '${val}'`);
		}
		return trimmed;
	}
	throw new TypeError(`Cannot coerce value of type ${typeof val} to decimal`);
}

/**
 * Safely parses boolean string or value strictly.
 */
export function safeCoerceBoolean(val) {
	if (typeof val === "boolean") return val;
	if (typeof val === "string") {
		const lower = val.trim().toLowerCase();
		if (lower === "true" || lower === "1") return true;
		if (lower === "false" || lower === "0") return false;
		throw new TypeError(`Invalid boolean string: '${val}'`);
	}
	if (typeof val === "number") {
		if (val === 1) return true;
		if (val === 0) return false;
		throw new TypeError(`Invalid boolean numeric value: ${val}`);
	}
	throw new TypeError(`Cannot coerce value of type ${typeof val} to boolean`);
}

/**
 * Converts a right operand or raw value into a canonical FlexValue.
 * Preserves 2-item arrays verbatim unless authoritative fieldtype confirms Link tuple
 * AND the operator is not a membership list operator ('in', 'not_in').
 */
export function toCanonicalFlexValue(rawRight, fieldtype = null, operator = null) {
	if (rawRight === undefined || rawRight === null) {
		return {
			mode: "static",
			value_type: "null",
			value: null,
		};
	}

	if (isPlainObject(rawRight) && rawRight.mode) {
		const mode = rawRight.mode;
		if (mode === "variable") {
			if (rawRight.path && typeof rawRight.path === "object") {
				return {
					mode: "variable",
					path: {
						scope: rawRight.path.scope || "doc",
						segments: Array.isArray(rawRight.path.segments)
							? [...rawRight.path.segments]
							: [],
					},
				};
			}
			return fieldExpressionToCanonicalVariable(rawRight.value || "");
		}
		if (mode === "static") {
			const v = rawRight.value;
			let vt = rawRight.value_type;
			if (vt === "MultiSelectList" || vt === "MultiSelect") vt = "list";
			if (!vt) {
				vt = inferCanonicalValueType(v, fieldtype);
			}
			if (vt === "list" && !Array.isArray(v)) {
				throw new TypeError("List FlexValue requires an array value");
			}
			let formattedValue = v;
			if (vt === "decimal") {
				formattedValue = safeCoerceDecimal(v);
			} else if (vt === "integer") {
				formattedValue = safeCoerceInteger(v);
			} else if (vt === "boolean") {
				formattedValue = safeCoerceBoolean(v);
			} else if (vt === "null") {
				formattedValue = null;
			}
			return {
				mode: "static",
				value_type: vt,
				value: formattedValue,
			};
		}
		if (mode === "resolver") {
			return {
				mode: "resolver",
				family: rawRight.family,
				operation: rawRight.operation,
				config: deepClone(rawRight.config || {}),
			};
		}
		if (mode === "template") {
			return {
				mode: "template",
				segments: Array.isArray(rawRight.segments) ? deepClone(rawRight.segments) : [],
			};
		}
	}

	let val = rawRight;
	if (isPlainObject(rawRight) && Object.prototype.hasOwnProperty.call(rawRight, "value")) {
		val = rawRight.value;
	}

	// Only unwrap a 2-item array if authoritative Link metadata is provided AND it is a legacy Link tuple [DocType, Name]
	// AND the operator is NOT a membership comparison ('in', 'not_in').
	// Membership lists for Link fields must NEVER be interpreted as Link tuples.
	const isMembershipOp = operator === "in" || operator === "not_in";
	const isLinkField = fieldtype && (fieldtype === "Link" || fieldtype === "Dynamic Link");
	if (
		!isMembershipOp &&
		isLinkField &&
		Array.isArray(val) &&
		val.length === 2 &&
		typeof val[0] === "string" &&
		typeof val[1] === "string"
	) {
		val = val[1];
	}

	if (isPlainObject(val) && val.mode) {
		return toCanonicalFlexValue(val, fieldtype, operator);
	}

	const vt = inferCanonicalValueType(val, fieldtype);
	let formatted = val;
	if (vt === "decimal") {
		formatted = safeCoerceDecimal(val);
	} else if (vt === "integer") {
		formatted = safeCoerceInteger(val);
	} else if (vt === "boolean") {
		formatted = safeCoerceBoolean(val);
	}

	return {
		mode: "static",
		value_type: vt,
		value: formatted,
	};
}

/**
 * Detects whether a payload is canonical AST.
 */
export function isCanonicalConditionPayload(payload) {
	if (!isPlainObject(payload)) return false;
	const type = payload.type;
	return type === "comparison" || type === "group" || type === "collection_predicate";
}

/**
 * Detects whether a payload is a legacy condition format.
 */
export function isLegacyConditionPayload(payload) {
	if (!payload) return false;
	if (Array.isArray(payload)) return true;
	if (!isPlainObject(payload)) return false;
	if (isCanonicalConditionPayload(payload)) return false;
	return (
		Array.isArray(payload.conditions) ||
		Boolean(payload.left) ||
		(Boolean(payload.collection) && Boolean(payload.where)) ||
		Boolean(payload.op && payload.conditions)
	);
}

/**
 * Deserializes a canonical comparison node into a TreeBuilder leaf.
 */
function deserializeCanonicalComparison(node) {
	return {
		id: createNodeId("leaf"),
		type: TREE_NODE_TYPES.LEAF,
		operator: node.operator || "eq",
		left: isPlainObject(node.left)
			? deepClone(node.left)
			: { mode: "variable", path: { scope: "doc", segments: [] } },
		right: isPlainObject(node.right)
			? deepClone(node.right)
			: UNARY_OPERATORS.has(node.operator)
			? null
			: { mode: "static", value_type: "string", value: "" },
	};
}

/**
 * Deserializes a canonical collection predicate into a TreeBuilder collection node.
 */
/**
 * Recursively updates variable scope references within a subtree from oldAlias to newAlias.
 */
export function updateSubtreeScopeReferences(node, oldAlias, newAlias) {
	if (!node || typeof node !== "object" || !oldAlias || !newAlias || oldAlias === newAlias) {
		return;
	}

	if (node.type === TREE_NODE_TYPES.LEAF || node.type === "comparison") {
		if (node.left?.mode === "variable" && node.left.path?.scope === oldAlias) {
			node.left.path.scope = newAlias;
		}
		if (node.right?.mode === "variable" && node.right.path?.scope === oldAlias) {
			node.right.path.scope = newAlias;
		}
		return;
	}

	if (node.type === TREE_NODE_TYPES.COLLECTION || node.type === "collection_predicate") {
		if (node.source?.scope === oldAlias) {
			node.source.scope = newAlias;
		}
		if (node.children && Array.isArray(node.children)) {
			for (const child of node.children) {
				updateSubtreeScopeReferences(child, oldAlias, newAlias);
			}
		}
		if (node.where) {
			updateSubtreeScopeReferences(node.where, oldAlias, newAlias);
		}
		return;
	}

	if (node.type === TREE_NODE_TYPES.GROUP || node.type === "group") {
		if (node.children && Array.isArray(node.children)) {
			for (const child of node.children) {
				updateSubtreeScopeReferences(child, oldAlias, newAlias);
			}
		}
	}
}

function deserializeCanonicalCollection(node) {
	const source = node.source || {};
	const scope = source.scope || "doc";
	const segments = Array.isArray(source.segments) ? source.segments : [];
	const collectionPath = segments.length ? `${scope}.${segments.join(".")}` : scope;

	const whereNode = node.where;
	let children = [];
	let rowQuantifier = "and"; // 'and' -> Match all conditions; 'or' -> Match any condition

	if (whereNode) {
		if (whereNode.type === "group" && Array.isArray(whereNode.children)) {
			rowQuantifier = whereNode.operator === "or" ? "or" : "and";
			children = whereNode.children.map((c) => deserializeNode(c));
		} else {
			children = [deserializeNode(whereNode)];
		}
	}

	let alias = node.as;
	const isInvalidAlias =
		!alias ||
		RESERVED_ALIASES.has(alias) ||
		!/^[A-Za-z][A-Za-z0-9_]*$/.test(alias) ||
		alias.includes("__");
	if (isInvalidAlias) {
		const oldAlias = alias;
		alias = generateCollectionAlias(collectionPath);
		if (oldAlias) {
			for (const child of children) {
				updateSubtreeScopeReferences(child, oldAlias, alias);
			}
		}
	}

	return {
		id: createNodeId("collection"),
		type: TREE_NODE_TYPES.COLLECTION,
		quantifier: node.quantifier || "any",
		collection: collectionPath,
		source: deepClone(source),
		alias,
		rowQuantifier,
		children,
	};
}

/**
 * Deserializes a canonical group node into a TreeBuilder group node.
 */
function deserializeCanonicalGroup(node) {
	const children = Array.isArray(node.children)
		? node.children.map((child) => deserializeNode(child))
		: [];
	return {
		id: createNodeId("group"),
		type: TREE_NODE_TYPES.GROUP,
		operator: node.operator || "and",
		children,
	};
}

/**
 * Deserializes any canonical node into a TreeBuilder node.
 */
function deserializeCanonicalNode(node) {
	if (!isPlainObject(node)) {
		return {
			id: createNodeId("leaf"),
			type: TREE_NODE_TYPES.LEAF,
			operator: "eq",
			left: { mode: "variable", path: { scope: "doc", segments: [] } },
			right: { mode: "static", value_type: "string", value: "" },
		};
	}

	if (node.type === "comparison") {
		return deserializeCanonicalComparison(node);
	}
	if (node.type === "group") {
		return deserializeCanonicalGroup(node);
	}
	if (node.type === "collection_predicate") {
		return deserializeCanonicalCollection(node);
	}

	// Unknown canonical node type
	return {
		id: createNodeId("leaf"),
		type: TREE_NODE_TYPES.LEAF,
		operator: "eq",
		is_unsupported: true,
		unsupported_reason: `Unknown condition node type '${node.type || "unspecified"}'`,
		original_payload: deepClone(node),
	};
}

/**
 * Converts a legacy leaf condition to a TreeBuilder leaf.
 */
function convertLegacyLeaf(legacy) {
	const rawOp = legacy.op || legacy.operator || "==";
	const canonicalOp = LEGACY_OPERATOR_MAP[rawOp];

	if (!canonicalOp || UNSUPPORTED_LEGACY_OPERATORS.has(rawOp)) {
		return {
			id: createNodeId("leaf"),
			type: TREE_NODE_TYPES.LEAF,
			operator: "eq",
			is_unsupported: true,
			unsupported_reason: `Unsupported legacy operator '${rawOp}'`,
			original_payload: deepClone(legacy),
		};
	}

	let left = { mode: "variable", path: { scope: "doc", segments: [] } };
	if (legacy.left) {
		if (typeof legacy.left === "string") {
			left = fieldExpressionToCanonicalVariable(legacy.left);
		} else if (legacy.left.ref) {
			left = fieldExpressionToCanonicalVariable(legacy.left.ref);
		} else if (legacy.left.mode) {
			left = deepClone(legacy.left);
		}
	}

	let right = null;
	if (!UNARY_OPERATORS.has(canonicalOp)) {
		right = toCanonicalFlexValue(legacy.right, null, canonicalOp);
	}

	return {
		id: createNodeId("leaf"),
		type: TREE_NODE_TYPES.LEAF,
		operator: canonicalOp,
		left,
		right,
		legacy_migrated: true,
	};
}

/**
 * Converts a legacy collection condition to a TreeBuilder collection node.
 */
function convertLegacyCollection(legacy) {
	const quantifier = legacy.op || "any";
	const collection = legacy.collection || "";

	const parts = collection.split(".").filter(Boolean);
	const scope = parts.length > 1 ? parts[0] : "doc";
	const segments = parts.length > 1 ? parts.slice(1) : parts.length === 1 ? [parts[0]] : [];

	let rawAlias = legacy.alias || "";
	if (!rawAlias || RESERVED_ALIASES.has(rawAlias)) {
		rawAlias = generateCollectionAlias(collection);
	}

	let children = [];
	let rowQuantifier = "and";
	if (legacy.where) {
		if (Array.isArray(legacy.where.conditions)) {
			rowQuantifier = legacy.where.op === "or" ? "or" : "and";
			children = legacy.where.conditions.map((c) => deserializeLegacyNode(c));
		} else if (legacy.where.left) {
			children = [convertLegacyLeaf(legacy.where)];
		}
	}

	return {
		id: createNodeId("collection"),
		type: TREE_NODE_TYPES.COLLECTION,
		quantifier: ["any", "all", "none"].includes(quantifier) ? quantifier : "any",
		collection,
		source: { scope, segments },
		alias: rawAlias,
		rowQuantifier,
		children,
		legacy_migrated: true,
	};
}

/**
 * Converts any legacy node into a TreeBuilder node.
 */
function deserializeLegacyNode(node) {
	if (!node || typeof node !== "object") {
		return {
			id: createNodeId("leaf"),
			type: TREE_NODE_TYPES.LEAF,
			operator: "eq",
			left: { mode: "variable", path: { scope: "doc", segments: [] } },
			right: { mode: "static", value_type: "string", value: "" },
		};
	}

	if (node.collection || (node.where && node.alias)) {
		return convertLegacyCollection(node);
	}

	if (Array.isArray(node.conditions)) {
		return {
			id: createNodeId("group"),
			type: TREE_NODE_TYPES.GROUP,
			operator: node.op || "and",
			children: node.conditions.map((child) => deserializeLegacyNode(child)),
			legacy_migrated: true,
		};
	}

	if (node.left || node.op) {
		return convertLegacyLeaf(node);
	}

	return {
		id: createNodeId("leaf"),
		type: TREE_NODE_TYPES.LEAF,
		operator: "eq",
		is_unsupported: true,
		unsupported_reason: "Unrecognized legacy condition shape",
		original_payload: deepClone(node),
	};
}

/**
 * Master deserialization dispatch.
 */
function deserializeNode(node) {
	if (isCanonicalConditionPayload(node)) {
		return deserializeCanonicalNode(node);
	}
	if (isLegacyConditionPayload(node)) {
		return deserializeLegacyNode(node);
	}
	if (isPlainObject(node) && node.type === TREE_NODE_TYPES.LEAF) {
		return deepClone(node);
	}
	return deserializeCanonicalNode(node);
}

/**
 * Deserializes any persisted condition (canonical or legacy) into a TreeBuilder UI Root.
 */
export function deserializeConditionTree(payload) {
	if (payload === null || payload === undefined || payload === "") {
		return {
			id: "root",
			type: TREE_NODE_TYPES.GROUP,
			operator: "and",
			children: [],
		};
	}

	let data = payload;
	if (typeof payload === "string") {
		const trimmed = payload.trim();
		if (!trimmed) {
			return {
				id: "root",
				type: TREE_NODE_TYPES.GROUP,
				operator: "and",
				children: [],
			};
		}
		try {
			data = JSON.parse(trimmed);
			// Fix: Correct double-encoded JSON check (explicit checks for '{' or '[')
			if (typeof data === "string") {
				const innerTrimmed = data.trim();
				if (innerTrimmed.startsWith("{") || innerTrimmed.startsWith("[")) {
					data = JSON.parse(innerTrimmed);
				}
			}
		} catch {
			return {
				id: "root",
				type: TREE_NODE_TYPES.GROUP,
				operator: "and",
				children: [
					{
						id: createNodeId("leaf"),
						type: TREE_NODE_TYPES.LEAF,
						operator: "eq",
						is_unsupported: true,
						unsupported_reason: "Malformed condition JSON string",
						original_payload: payload,
					},
				],
			};
		}
	}

	if (Array.isArray(data)) {
		return {
			id: "root",
			type: TREE_NODE_TYPES.GROUP,
			operator: "and",
			children: data.map((item) => deserializeLegacyNode(item)),
		};
	}

	if (isCanonicalConditionPayload(data)) {
		if (data.type === "group") {
			const groupNode = deserializeCanonicalGroup(data);
			return {
				...groupNode,
				id: "root",
			};
		}
		return {
			id: "root",
			type: TREE_NODE_TYPES.GROUP,
			operator: "and",
			children: [deserializeCanonicalNode(data)],
		};
	}

	if (isLegacyConditionPayload(data)) {
		if (Array.isArray(data.conditions)) {
			return {
				id: "root",
				type: TREE_NODE_TYPES.GROUP,
				operator: data.op || "and",
				children: data.conditions.map((child) => deserializeLegacyNode(child)),
				legacy_migrated: true,
			};
		}
		return {
			id: "root",
			type: TREE_NODE_TYPES.GROUP,
			operator: "and",
			children: [deserializeLegacyNode(data)],
			legacy_migrated: true,
		};
	}

	// Unknown or malformed object root
	if (isPlainObject(data)) {
		return {
			id: "root",
			type: TREE_NODE_TYPES.GROUP,
			operator: "and",
			children: [
				{
					id: createNodeId("leaf"),
					type: TREE_NODE_TYPES.LEAF,
					operator: "eq",
					is_unsupported: true,
					unsupported_reason: `Unsupported root condition structure: ${
						data.type || "unknown"
					}`,
					original_payload: deepClone(data),
				},
			],
		};
	}

	return {
		id: "root",
		type: TREE_NODE_TYPES.GROUP,
		operator: "and",
		children: [],
	};
}

/**
 * Serializes a TreeBuilder leaf node into a Canonical Comparison AST node.
 */
function hasSelectedVariablePath(value) {
	if (!isPlainObject(value) || value.mode !== "variable") return true;
	const path = value.path;
	if (!isPlainObject(path) || typeof path.scope !== "string" || !path.scope) return false;
	if (path.scope === "doctype") return Array.isArray(path.segments) && path.segments.length === 0;
	return Array.isArray(path.segments) && path.segments.length > 0 &&
		path.segments.every((segment) => typeof segment === "string" && segment.length > 0);
}

function hasCompleteFlexValue(value) {
	if (!isPlainObject(value) || !value.mode) return false;
	if (value.mode === "static") return value.value === null || (value.value !== undefined && value.value !== "");
	if (value.mode === "variable") return hasSelectedVariablePath(value);
	if (value.mode === "resolver") return Boolean(value.family && value.operation);
	if (value.mode === "template") return Array.isArray(value.segments) && value.segments.length > 0;
	return false;
}

function serializeLeafToCanonical(leaf, operatorSpecs = {}) {
	if (leaf.is_unsupported && leaf.original_payload) {
		return deepClone(leaf.original_payload);
	}

	const operator = leaf.operator;
	if (!operator) return null;
	const isUnary = UNARY_OPERATORS.has(operator) || operatorSpecs?.[operator]?.arity === 1;
	if (leaf.is_incomplete_draft && (!hasCompleteFlexValue(leaf.left) || (!isUnary && !hasCompleteFlexValue(leaf.right)))) {
		return null;
	}

	let left = leaf.left;
	if (!isPlainObject(left) || !left.mode) {
		left = fieldExpressionToCanonicalVariable(left || "");
	} else {
		left = deepClone(left);
	}

	const node = { type: "comparison", operator, left };
	if (!isUnary) {
		node.right = toCanonicalFlexValue(leaf.right, null, operator);
	}
	return node;
}

/**
 * Serializes a TreeBuilder collection node into a Canonical Collection Predicate AST node.
 */
function serializeCollectionToCanonical(colNode, operatorSpecs = {}) {
	if (colNode.is_unsupported && colNode.original_payload) {
		return deepClone(colNode.original_payload);
	}

	let source = colNode.source;
	if (!source || !Array.isArray(source.segments) || !source.scope) {
		const collStr = colNode.collection || "";
		const parts = collStr.split(".").filter(Boolean);
		const scope = parts.length > 1 ? parts[0] : "doc";
		const segments = parts.length > 1 ? parts.slice(1) : parts.length === 1 ? [parts[0]] : [];
		source = { scope, segments };
	} else {
		source = deepClone(source);
	}

	let alias = colNode.alias || "";
	if (
		!alias ||
		RESERVED_ALIASES.has(alias) ||
		!/^[A-Za-z][A-Za-z0-9_]*$/.test(alias) ||
		alias.includes("__")
	) {
		alias = generateCollectionAlias(colNode.collection || "items");
	}

	const quantifier = ["any", "all", "none"].includes(colNode.quantifier)
		? colNode.quantifier
		: "any";

	const children = Array.isArray(colNode.children) ? colNode.children : [];
	let where = null;

	const rowQuantifier = colNode.rowQuantifier === "or" ? "or" : "and";

	if (children.length === 1) {
		where = serializeNodeToCanonical(children[0], operatorSpecs);
	} else if (children.length >= 2) {
		where = {
			type: "group",
			operator: rowQuantifier,
			children: children.map((c) => serializeNodeToCanonical(c, operatorSpecs)).filter(Boolean),
		};
	}

	return {
		type: "collection_predicate",
		quantifier,
		source,
		as: alias,
		where,
	};
}

/**
 * Serializes a TreeBuilder group node into a Canonical Group AST node.
 */
function serializeGroupToCanonical(groupNode, operatorSpecs = {}) {
	if (groupNode.is_unsupported && groupNode.original_payload) {
		return deepClone(groupNode.original_payload);
	}

	const children = Array.isArray(groupNode.children)
		? groupNode.children.map((c) => serializeNodeToCanonical(c, operatorSpecs)).filter(Boolean)
		: [];

	return {
		type: "group",
		operator: groupNode.operator || "and",
		children,
	};
}

/**
 * Serializes any TreeBuilder node into canonical AST.
 */
function serializeNodeToCanonical(node, operatorSpecs = {}) {
	if (!node || typeof node !== "object") return null;

	if (node.type === TREE_NODE_TYPES.LEAF) {
		return serializeLeafToCanonical(node, operatorSpecs);
	}
	if (node.type === TREE_NODE_TYPES.COLLECTION) {
		return serializeCollectionToCanonical(node, operatorSpecs);
	}
	if (node.type === TREE_NODE_TYPES.GROUP) {
		return serializeGroupToCanonical(node, operatorSpecs);
	}
	return null;
}

/**
 * Serializes the TreeBuilder root into canonical AST or null.
 */
export function serializeConditionTree(treeRoot, operatorSpecs = {}) {
	if (!treeRoot || typeof treeRoot !== "object") return null;

	const children = Array.isArray(treeRoot.children)
		? treeRoot.children.map((child) => serializeNodeToCanonical(child, operatorSpecs)).filter(Boolean)
		: [];

	if (children.length === 0) {
		return null;
	}

	if (children.length === 1) {
		return children[0];
	}

	return {
		type: "group",
		operator: treeRoot.operator || "and",
		children,
	};
}

/**
 * Scans a UI tree for any unsupported nodes or diagnostics.
 */
export function findUnsupportedDiagnostics(tree) {
	const diagnostics = [];
	function scan(node) {
		if (!node || typeof node !== "object") return;
		if (node.is_unsupported) {
			diagnostics.push({
				id: node.id,
				reason: node.unsupported_reason || "Unsupported condition format",
				payload: node.original_payload,
			});
		}
		if (Array.isArray(node.children)) {
			node.children.forEach(scan);
		}
	}
	scan(tree);
	return diagnostics;
}
