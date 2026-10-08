import { createNodeId, cloneTree } from "../../tree_builder/tree_builder_utils.js";

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
	return Array.isArray(value) && (value.length === 3 || value.length === 4) &&
		typeof value[0] === "string" && typeof value[1] === "string" && typeof value[2] === "string";
}

function tupleToLeaf(tuple, defaultDoctype) {
	return {
		id: createNodeId("filter"),
		type: "leaf",
		doctype: tuple.length === 4 ? tuple[0] || defaultDoctype : defaultDoctype,
		field: tuple.length === 4 ? tuple[1] : tuple[0],
		operator: tuple.length === 4 ? tuple[2] : tuple[1],
		value: cloneTree(tuple.length === 4 ? tuple[3] : tuple[2]),
	};
}

function parse(value, defaultDoctype) {
	if (isGroup(value)) {
		if (!OPERATORS.has(value.operator)) throw new QueryFilterSerializationError("Unsupported filter group operator.");
		return {
			id: value.id || createNodeId("group"),
			type: "group",
			operator: value.operator,
			children: Array.isArray(value.children) ? value.children.map((child) => parse(child, defaultDoctype)) : [],
		};
	}
	if (isLeaf(value)) {
		return { ...cloneTree(value), id: value.id || createNodeId("filter"), type: "leaf" };
	}
	if (isTuple(value)) return tupleToLeaf(value, defaultDoctype);
	if (Array.isArray(value)) {
		const children = [];
		let operator = "and";
		let current = [];
		const flush = () => {
			if (current.length) {
				children.push(current.length === 1 ? current[0] : { id: createNodeId("group"), type: "group", operator, children: current });
				current = [];
			}
		};
		for (const item of value) {
			if (typeof item === "string" && OPERATORS.has(item.toLowerCase())) {
				flush();
				operator = item.toLowerCase();
				continue;
			}
			current.push(parse(item, defaultDoctype));
		}
		flush();
		return { id: createNodeId("group"), type: "group", operator: "and", children };
	}
	if (value == null || value === "") return { id: createNodeId("root"), type: "group", operator: "and", children: [] };
	throw new QueryFilterSerializationError("Unsupported Query Filter backend value.");
}

export function deserializeQueryFilters(payload, { defaultDoctype = "" } = {}) {
	return parse(payload, defaultDoctype);
}

function validateCanonical(tree) {
	const errors = [];
	function visit(node, path = [], isRoot = false) {
		if (!node || typeof node !== "object") {
			errors.push({ path, message: "Filter node is malformed." });
			return;
		}
		if (isGroup(node)) {
			if (!OPERATORS.has(node.operator)) errors.push({ path: [...path, "operator"], message: "Unsupported group operator." });
			if (!Array.isArray(node.children)) errors.push({ path: [...path, "children"], message: "Group children must be an array." });
			else node.children.forEach((child, index) => visit(child, [...path, "children", index]));
			return;
		}
		if (isLeaf(node)) {
			if (!node.field) errors.push({ path: [...path, "field"], message: "Filter field is required." });
			if (!node.operator) errors.push({ path: [...path, "operator"], message: "Filter operator is required." });
			return;
		}
		errors.push({ path, message: "Unknown filter node type." });
	}
	visit(tree, [], true);
	if (!isGroup(tree)) errors.push({ path: [], message: "Filter root must be a group." });
	return errors;
}

export function serializeQueryFilters(tree, { defaultDoctype = "" } = {}) {
	const errors = validateCanonical(tree);
	if (errors.length) throw new QueryFilterSerializationError("Invalid Query Filter tree.", errors);

	function serialize(node) {
		if (isLeaf(node)) return [node.doctype || defaultDoctype || "", node.field, node.operator, cloneTree(node.value)];
		const children = node.children.map(serialize);
		if (!children.length) return [];
		if (children.length === 1) return children[0];
		const result = [children[0]];
		for (let index = 1; index < children.length; index += 1) result.push(node.operator, children[index]);
		return result;
	}
	return serialize(tree);
}
