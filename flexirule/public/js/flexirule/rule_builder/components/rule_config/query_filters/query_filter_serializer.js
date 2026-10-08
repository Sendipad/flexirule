import { cloneTree } from "../../tree_builder/tree_builder_utils.js";

const OPERATORS = new Set(["and", "or"]);

export class QueryFilterSerializationError extends Error {
	constructor(message, errors = []) {
		super(message);
		this.name = "QueryFilterSerializationError";
		this.errors = errors;
	}
}

function isGroup(value) {
	return value?.type === "group";
}
function isLeaf(value) {
	return value?.type === "leaf";
}
function isTuple(value) {
	if (!Array.isArray(value) || (value.length !== 3 && value.length !== 4)) return false;
	if (typeof value[0] !== "string" || typeof value[1] !== "string") return false;
	return value.length === 3 || typeof value[2] === "string";
}

function stableId(prefix, path) {
	return path.length ? `${prefix}-${path.join("-")}` : prefix;
}

function tupleToLeaf(tuple, defaultDoctype, path) {
	return {
		id: stableId("filter", path),
		type: "leaf",
		doctype: tuple.length === 4 ? tuple[0] || defaultDoctype : defaultDoctype,
		field: tuple.length === 4 ? tuple[1] : tuple[0],
		operator: tuple.length === 4 ? tuple[2] : tuple[1],
		value: cloneTree(tuple.length === 4 ? tuple[3] : tuple[2]),
	};
}

function parse(value, defaultDoctype, path = []) {
	if (isGroup(value)) {
		if (!OPERATORS.has(value.operator))
			throw new QueryFilterSerializationError("Unsupported filter group operator.");
		return {
			id: value.id || stableId("group", path),
			type: "group",
			operator: value.operator,
			children: Array.isArray(value.children)
				? value.children.map((child, index) =>
						parse(child, defaultDoctype, [...path, index])
				  )
				: [],
		};
	}
	if (isLeaf(value)) {
		return { ...cloneTree(value), id: value.id || stableId("filter", path), type: "leaf" };
	}
	if (isTuple(value)) return tupleToLeaf(value, defaultDoctype, path);
	if (Array.isArray(value)) {
		const items = value.filter((item) => item !== undefined && item !== null);
		if (!items.length)
			return { id: stableId("root", path), type: "group", operator: "and", children: [] };
		let current = null;
		let pending = "and";
		for (const item of items) {
			if (typeof item === "string" && OPERATORS.has(item.toLowerCase())) {
				pending = item.toLowerCase();
				continue;
			}
			const node = parse(item, defaultDoctype, [
				...path,
				current ? current.children.length : 0,
			]);
			if (!current) {
				current = {
					id: stableId("group", path),
					type: "group",
					operator: pending,
					children: [node],
				};
				continue;
			}
			if (current.operator === pending) {
				current.children.push(node);
				continue;
			}
			current = {
				id: stableId("group", path),
				type: "group",
				operator: pending,
				children: [current, node],
			};
		}
		return (
			current || { id: stableId("root", path), type: "group", operator: "and", children: [] }
		);
	}
	if (value == null || value === "")
		return { id: "root", type: "group", operator: "and", children: [] };
	throw new QueryFilterSerializationError("Unsupported Query Filter backend value.");
}

export function deserializeQueryFilters(payload, { defaultDoctype = "" } = {}) {
	return parse(payload, defaultDoctype);
}

function validateCanonical(tree) {
	const errors = [];
	function visit(node, path = []) {
		if (!node || typeof node !== "object") {
			errors.push({ path, message: "Filter node is malformed." });
			return;
		}
		if (isGroup(node)) {
			if (!OPERATORS.has(node.operator))
				errors.push({
					path: [...path, "operator"],
					message: "Unsupported group operator.",
				});
			if (!Array.isArray(node.children))
				errors.push({
					path: [...path, "children"],
					message: "Group children must be an array.",
				});
			else
				node.children.forEach((child, index) => visit(child, [...path, "children", index]));
			return;
		}
		if (isLeaf(node)) {
			// Serialization is intentionally permissive for editable leaves. A newly
			// added filter is incomplete until the user selects a field/operator/value.
			// Component validation remains responsible for preventing an invalid rule
			// from being saved.
			if (typeof node.field !== "string")
				errors.push({
					path: [...path, "field"],
					message: "Filter field must be a string.",
				});
			if (typeof node.operator !== "string")
				errors.push({
					path: [...path, "operator"],
					message: "Filter operator must be a string.",
				});
			return;
		}
		errors.push({ path, message: "Unknown filter node type." });
	}
	visit(tree, []);
	if (!isGroup(tree)) errors.push({ path: [], message: "Filter root must be a group." });
	return errors;
}

export function toPersistedQueryFilterTree(tree) {
	const errors = validateCanonical(tree);
	if (errors.length)
		throw new QueryFilterSerializationError("Invalid Query Filter tree.", errors);
	function persist(node) {
		if (isLeaf(node))
			return {
				type: "leaf",
				doctype: node.doctype || "",
				field: node.field || "",
				operator: node.operator || "=",
				value: cloneTree(node.value),
			};
		return { type: "group", operator: node.operator, children: node.children.map(persist) };
	}
	return persist(tree);
}
export function serializeQueryFilters(tree, { defaultDoctype = "" } = {}) {
	const persisted = toPersistedQueryFilterTree(tree);
	function serialize(node) {
		if (isLeaf(node))
			return [
				node.doctype || defaultDoctype || "",
				node.field,
				node.operator,
				cloneTree(node.value),
			];
		const children = node.children.map(serialize);
		if (!children.length) return [];
		if (children.length === 1) return children[0];
		const result = [children[0]];
		for (let index = 1; index < children.length; index += 1)
			result.push(node.operator, children[index]);
		return result;
	}
	return serialize(persisted);
}
