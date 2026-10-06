/**
 * Pure boundary between the interactive Query Filter tree and Fetch Records.
 *
 * The UI tree owns editing concerns (ids, node types, nesting and editor state).
 * This adapter owns only structural normalization/validation/serialization.
 * Runtime value resolution and Frappe Query Builder compatibility stay backend-side.
 */

const LOGICAL_OPERATORS = new Set(["and", "or"]);

export class FilterTreeValidationError extends Error {
	constructor(errors) {
		super("Invalid filter tree");
		this.name = "FilterTreeValidationError";
		this.errors = errors;
	}
}

export function createFilterId(createId) {
	if (typeof createId === "function") return createId();
	if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
		return crypto.randomUUID();
	}
	return "filter-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
}

export function createFilterLeaf({ doctype = "", createId } = {}) {
	return {
		id: createFilterId(createId),
		type: "leaf",
		doctype,
		field: "",
		operator: "=",
		value: { mode: "static", value: "" },
	};
}

export function createFilterGroup({ operator = "and", children = [], createId } = {}) {
	return {
		id: createFilterId(createId),
		type: "group",
		operator: LOGICAL_OPERATORS.has(String(operator).toLowerCase())
			? String(operator).toLowerCase()
			: "and",
		children: Array.isArray(children) ? children : [],
	};
}

export function isFilterGroup(node) {
	return !!node && node.type === "group";
}

export function isFilterLeaf(node) {
	return !!node && node.type === "leaf";
}

function clone(value) {
	if (value === undefined || value === null) return value;
	return JSON.parse(JSON.stringify(value));
}

function normalizeLegacyValue(value) {
	if (!value || typeof value !== "object" || Array.isArray(value)) return clone(value);
	if ("mode" in value) return clone(value);

	// Legacy FilterGroup payloads used { value, value_type, builder }.
	if ("value" in value || "value_type" in value || "builder" in value) {
		const type = String(value.value_type || "Value").toLowerCase();
		if (value.builder && typeof value.builder === "object") {
			return {
				mode: "resolver",
				value: value.value ?? "",
				config: clone(value.builder),
			};
		}
		if (type === "variable") {
			const path = String(value.value ?? "")
				.trim()
				.replace(/^\{/, "")
				.replace(/\}$/, "");
			return { mode: "variable", value: path };
		}
		if (type === "expression") return { mode: "resolver", value: value.value ?? "" };
		return { mode: "static", value: clone(value.value) };
	}

	return clone(value);
}

function looksLikeLeafTuple(value) {
	if (!Array.isArray(value)) return false;
	if (value.length === 4) {
		return (
			typeof value[0] === "string" &&
			typeof value[1] === "string" &&
			typeof value[2] === "string" &&
			!LOGICAL_OPERATORS.has(value[0].toLowerCase())
		);
	}
	if (value.length === 3) {
		return (
			typeof value[0] === "string" &&
			typeof value[1] === "string" &&
			!LOGICAL_OPERATORS.has(value[0].toLowerCase())
		);
	}
	return false;
}

function tupleToLeaf(tuple, { defaultDoctype = "", createId } = {}) {
	if (tuple.length === 4) {
		return {
			id: createFilterId(createId),
			type: "leaf",
			doctype: tuple[0] || defaultDoctype,
			field: tuple[1] || "",
			operator: tuple[2] || "=",
			value: normalizeLegacyValue(tuple[3]),
		};
	}
	return {
		id: createFilterId(createId),
		type: "leaf",
		doctype: defaultDoctype,
		field: tuple[0] || "",
		operator: tuple[1] || "=",
		value: normalizeLegacyValue(tuple[2]),
	};
}

function objectToLeaf(value, { defaultDoctype = "", createId } = {}) {
	return {
		id: value.id || createFilterId(createId),
		type: "leaf",
		doctype: value.doctype || defaultDoctype,
		field: value.field || value.fieldname || "",
		operator: value.operator || value.op || "=",
		value: normalizeLegacyValue(value.value),
	};
}

function parseLegacySequence(value, context) {
	const items = value.filter((item) => item !== undefined && item !== null);
	if (!items.length) return createFilterGroup({ createId: context.createId });

	let current = null;
	let pending = "and";

	for (const item of items) {
		if (typeof item === "string" && LOGICAL_OPERATORS.has(item.toLowerCase())) {
			pending = item.toLowerCase();
			continue;
		}

		const node = parseNode(item, context);
		if (!node) continue;

		if (!current) {
			current = createFilterGroup({
				operator: pending,
				children: [node],
				createId: context.createId,
			});
			continue;
		}

		if (current.operator === pending) {
			current.children.push(node);
			continue;
		}

		// A mixed flat expression cannot be represented by one group operator.
		// Preserve its left-associative meaning by nesting the previous expression.
		current = createFilterGroup({
			operator: pending,
			children: [current, node],
			createId: context.createId,
		});
	}

	return current || createFilterGroup({ createId: context.createId });
}

function parseNode(value, context) {
	if (isFilterGroup(value)) {
		return {
			id: value.id || createFilterId(context.createId),
			type: "group",
			operator: String(value.operator || "and").toLowerCase(),
			children: Array.isArray(value.children)
				? value.children.map((child) => parseNode(child, context)).filter(Boolean)
				: [],
		};
	}
	if (isFilterLeaf(value)) return objectToLeaf(value, context);
	if (looksLikeLeafTuple(value)) return tupleToLeaf(value, context);
	if (Array.isArray(value)) return parseLegacySequence(value, context);
	if (value && typeof value === "object") return objectToLeaf(value, context);
	return null;
}

export function deserializeFilterPayload(payload, { defaultDoctype = "", createId } = {}) {
	const context = { defaultDoctype, createId };
	if (payload === undefined || payload === null || payload === "") {
		return createFilterGroup({ createId });
	}

	if (isFilterGroup(payload)) return parseNode(payload, context);
	if (isFilterLeaf(payload)) {
		return createFilterGroup({ children: [parseNode(payload, context)], createId });
	}
	if (looksLikeLeafTuple(payload)) {
		return createFilterGroup({
			children: [tupleToLeaf(payload, context)],
			createId,
		});
	}
	if (Array.isArray(payload)) return parseLegacySequence(payload, context);
	if (payload && typeof payload === "object") {
		return createFilterGroup({ children: [objectToLeaf(payload, context)], createId });
	}

	return createFilterGroup({ createId });
}

export function normalizeFilterTree(value, options = {}) {
	return deserializeFilterPayload(value, options);
}

function addError(errors, path, code, message) {
	errors.push({ path, code, message });
}

export function validateFilterTree(tree, { allowEmptyRoot = true, validateOperator } = {}) {
	const errors = [];

	function visit(node, path, isRoot = false) {
		if (!node || typeof node !== "object") {
			addError(errors, path, "malformed", "Filter node is malformed.");
			return;
		}

		if (isFilterLeaf(node)) {
			if (typeof node.doctype !== "string" || !node.doctype.trim()) {
				addError(errors, [...path, "doctype"], "required", "A filter DocType is required.");
			}
			if (typeof node.field !== "string" || !node.field.trim()) {
				addError(errors, [...path, "field"], "required", "A filter field is required.");
			}
			if (typeof node.operator !== "string" || !node.operator.trim()) {
				addError(
					errors,
					[...path, "operator"],
					"required",
					"A filter operator is required."
				);
			} else if (validateOperator && !validateOperator(node.operator, node)) {
				addError(
					errors,
					[...path, "operator"],
					"unsupported",
					"The selected filter operator is not supported."
				);
			}
			return;
		}

		if (!isFilterGroup(node)) {
			addError(errors, path, "malformed", "Filter node type is invalid.");
			return;
		}

		const operator = String(node.operator || "").toLowerCase();
		if (!LOGICAL_OPERATORS.has(operator)) {
			addError(
				errors,
				[...path, "operator"],
				"unsupported",
				"Filter group operator must be AND or OR."
			);
		}
		const children = Array.isArray(node.children) ? node.children : [];
		if (!children.length && !isRoot) {
			addError(errors, path, "empty_group", "Filter groups cannot be empty.");
		}
		if (!children.length && isRoot && !allowEmptyRoot) {
			addError(errors, path, "empty_group", "At least one filter is required.");
		}
		children.forEach((child, index) => visit(child, [...path, "children", index]));
	}

	visit(tree, [], true);
	return { valid: errors.length === 0, errors };
}

export function serializeFilterTree(tree, options = {}) {
	const normalized = normalizeFilterTree(tree, options);
	const validation = validateFilterTree(normalized, options);
	if (!validation.valid && !options.skipInvalid)
		throw new FilterTreeValidationError(validation.errors);

	function serialize(node) {
		if (isFilterLeaf(node)) {
			if (options.skipInvalid && (!node.field || !node.field.trim())) {
				return null;
			}
			return [
				node.doctype || options.defaultDoctype || "",
				node.field,
				node.operator,
				clone(node.value),
			];
		}

		const children = (node.children || []).map(serialize).filter(Boolean);
		if (!children.length) return [];
		if (children.length === 1) return children[0];

		const result = [children[0]];
		for (let index = 1; index < children.length; index += 1) {
			result.push(String(node.operator || "and").toLowerCase(), children[index]);
		}
		return result;
	}

	return serialize(normalized);
}
