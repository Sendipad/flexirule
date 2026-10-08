import { TREE_NODE_TYPES, DEFAULT_GROUP_OPERATORS } from "./tree_builder_types.js";

export function createNodeId(prefix = "tree") {
	if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function")
		return crypto.randomUUID();
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
export function isScopeNode(node) {
	return !!node && node.type === TREE_NODE_TYPES.SCOPE;
}
export function isLeafNode(node) {
	return !!node && node.type === TREE_NODE_TYPES.LEAF;
}
export function isContainerNode(node) {
	return isGroupNode(node) || isScopeNode(node);
}
export function createGroup(operator = DEFAULT_GROUP_OPERATORS[0], children = []) {
	return {
		id: createNodeId("group"),
		type: "group",
		operator,
		children: Array.isArray(children) ? children : [],
	};
}
export function createScope(scope = {}, children = []) {
	return {
		id: createNodeId("scope"),
		type: "scope",
		scope: cloneTree(scope) || {},
		children: Array.isArray(children) ? children : [],
	};
}
export function createLeaf(payload = {}) {
	return { id: createNodeId("leaf"), type: "leaf", ...cloneTree(payload) };
}
export function walkTree(tree, visitor) {
	if (!tree || typeof tree !== "object") return;
	visitor(tree);
	if (isContainerNode(tree)) (tree.children || []).forEach((c) => walkTree(c, visitor));
}
export function findNode(tree, nodeId) {
	let found = null;
	walkTree(tree, (n) => {
		if (!found && n.id === nodeId) found = n;
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
			for (const c of node.children || []) if (visit(c)) return true;
		}
		path.pop();
		return false;
	}
	return visit(tree, nodeId) ? path : [];
}
export function isDescendant(node, targetId) {
	if (!node || !targetId) return false;
	if (node.id === targetId) return true;
	return isContainerNode(node) && (node.children || []).some((c) => isDescendant(c, targetId));
}
export function mapTree(tree, mapper) {
	if (!tree || typeof tree !== "object") return tree;
	const mapped = mapper(tree);
	if (!mapped || typeof mapped !== "object") return mapped;
	if (isContainerNode(mapped))
		mapped.children = (mapped.children || []).map((c) => mapTree(c, mapper));
	return mapped;
}
export function normalizeTree(value, { groupOperators = DEFAULT_GROUP_OPERATORS, rootId } = {}) {
	const ops =
		Array.isArray(groupOperators) && groupOperators.length
			? groupOperators.filter(Boolean)
			: [...DEFAULT_GROUP_OPERATORS];
	function norm(node) {
		if (!node || typeof node !== "object") return null;
		const id = node.id || createNodeId(node.type || "tree");
		if (isGroupNode(node))
			return {
				...cloneTree(node),
				id,
				type: "group",
				operator: ops.includes(node.operator) ? node.operator : ops[0],
				children: Array.isArray(node.children)
					? node.children.map(norm).filter(Boolean)
					: [],
			};
		if (isScopeNode(node))
			return {
				...cloneTree(node),
				id,
				type: "scope",
				scope: cloneTree(node.scope) || {},
				children: Array.isArray(node.children)
					? node.children.map(norm).filter(Boolean)
					: [],
			};
		if (isLeafNode(node)) {
			const { children, operator, scope, ...payload } = cloneTree(node);
			return { ...payload, id, type: "leaf" };
		}
		return { ...cloneTree(node), id, type: "leaf" };
	}
	const normalized = norm(value);
	if (normalized && isGroupNode(normalized)) {
		normalized.id = normalized.id || rootId || createNodeId("root");
		return normalized;
	}
	return createGroup(ops[0], normalized ? [normalized] : []);
}
export function treesEqual(left, right) {
	return JSON.stringify(left) === JSON.stringify(right);
}
