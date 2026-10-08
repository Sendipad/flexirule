import { DEFAULT_GROUP_OPERATORS, TREE_NODE_TYPES } from "./tree_builder_types.js";

export function createNodeId(prefix = "tree") {
	if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
	return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
export const createId = createNodeId;

export function cloneTree(value) {
	if (value === undefined || value === null) return value;
	return JSON.parse(JSON.stringify(value));
}

export function isGroupNode(node) {
	return !!node && node.type === TREE_NODE_TYPES.GROUP;
}
export function isLeafNode(node) {
	return !!node && node.type === TREE_NODE_TYPES.LEAF;
}
export function isContainerNode(node) {
	return isGroupNode(node);
}

export function createGroup(operator = DEFAULT_GROUP_OPERATORS[0], children = []) {
	return {
		id: createNodeId("group"),
		type: TREE_NODE_TYPES.GROUP,
		operator,
		children: Array.isArray(children) ? children : [],
	};
}

export function createLeaf(payload = {}) {
	return {
		id: createNodeId("leaf"),
		type: TREE_NODE_TYPES.LEAF,
		...cloneTree(payload),
	};
}

export function walkTree(tree, visitor) {
	if (!tree || typeof tree !== "object") return;
	visitor(tree);
	if (isContainerNode(tree)) (tree.children || []).forEach((child) => walkTree(child, visitor));
}

export function findNode(tree, nodeId) {
	let found = null;
	walkTree(tree, (node) => {
		if (!found && node.id === nodeId) found = node;
	});
	return found;
}

export function findParent(tree, nodeId) {
	let parent = null;
	function visit(node) {
		if (!isContainerNode(node) || parent) return;
		for (const child of node.children || []) {
			if (child.id === nodeId) {
				parent = node;
				return;
			}
			visit(child);
			if (parent) return;
		}
	}
	visit(tree);
	return parent;
}

export function findPath(tree, nodeId) {
	const path = [];
	function visit(node) {
		if (!node) return false;
		path.push(node);
		if (node.id === nodeId) return true;
		if (isContainerNode(node)) {
			for (const child of node.children || []) if (visit(child)) return true;
		}
		path.pop();
		return false;
	}
	return visit(tree, nodeId) ? path : [];
}

export function isDescendant(node, targetId) {
	if (!node || !targetId) return false;
	if (node.id === targetId) return true;
	return isContainerNode(node) && (node.children || []).some((child) => isDescendant(child, targetId));
}

export function treesEqual(left, right) {
	return JSON.stringify(left) === JSON.stringify(right);
}

export class TreeModelError extends Error {
	constructor(message, path = []) {
		super(message);
		this.name = "TreeModelError";
		this.path = path;
	}
}

export function normalizeTree(value, { groupOperators = DEFAULT_GROUP_OPERATORS, rootId } = {}) {
	const operators =
		Array.isArray(groupOperators) && groupOperators.length
			? groupOperators.filter(Boolean)
			: [...DEFAULT_GROUP_OPERATORS];

	function normalizeNode(node, path = []) {
		if (!node || typeof node !== "object" || Array.isArray(node)) {
			throw new TreeModelError("Tree node must be an object.", path);
		}
		if (!node.type) throw new TreeModelError("Tree node type is required.", path);
		if (node.type !== TREE_NODE_TYPES.GROUP && node.type !== TREE_NODE_TYPES.LEAF) {
			throw new TreeModelError(`Unsupported tree node type: ${node.type}`, path);
		}
		const id = typeof node.id === "string" && node.id ? node.id : createNodeId(node.type);
		if (node.type === TREE_NODE_TYPES.GROUP) {
			const operator = operators.includes(node.operator) ? node.operator : operators[0];
			if (!operator) throw new TreeModelError("A group operator is required.", [...path, "operator"]);
			const children = Array.isArray(node.children)
				? node.children.map((child, index) => normalizeNode(child, [...path, "children", index]))
				: [];
			return { id, type: TREE_NODE_TYPES.GROUP, operator, children };
		}
		const { children, operator, ...payload } = cloneTree(node);
		if (children !== undefined) throw new TreeModelError("Leaf nodes cannot own children.", [...path, "children"]);
		return { ...payload, id, type: TREE_NODE_TYPES.LEAF };
	}

	if (value === undefined || value === null || value === "") {
		return createGroup(operators[0], []);
	}
	const normalized = normalizeNode(value);
	if (normalized.type !== TREE_NODE_TYPES.GROUP) {
		return {
			id: rootId || createNodeId("root"),
			type: TREE_NODE_TYPES.GROUP,
			operator: operators[0],
			children: [normalized],
		};
	}
	return normalized;
}
