import {
	cloneTree,
	createGroup,
	createLeaf,
	findNode,
	findParent,
	isContainerNode,
	isDescendant,
} from "./tree_builder_utils.js";

function parentFor(tree, id) {
	const node = findNode(tree, id);
	return isContainerNode(node) ? node : null;
}

export function addCollection(tree, parentId, payload = {}) {
	const parent = parentFor(tree, parentId);
	if (!parent) return null;
	const node = {
		...cloneTree(payload),
		id: undefined,
		type: "collection",
		children: [],
	};
	delete node.id;
	return node.id === undefined ? (() => {
		const created = {
			...node,
			id: `collection-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
		};
		parent.children.push(created);
		return created;
	})() : null;
}

export function addLeaf(tree, parentId, payload = {}) {
	const parent = parentFor(tree, parentId);
	if (!parent) return null;
	const node = createLeaf(payload);
	parent.children.push(node);
	return node;
}

export function addGroup(tree, parentId, operator = "and") {
	const parent = parentFor(tree, parentId);
	if (!parent) return null;
	const node = createGroup(operator);
	parent.children.push(node);
	return node;
}

export function removeNode(tree, id) {
	const parent = findParent(tree, id);
	if (!parent) return null;
	const index = parent.children.findIndex((child) => child.id === id);
	return index < 0 ? null : parent.children.splice(index, 1)[0] || null;
}

export function moveNode(tree, id, targetId, pos = -1) {
	const node = findNode(tree, id);
	const target = parentFor(tree, targetId);
	const source = findParent(tree, id);
	if (
		!node ||
		!target ||
		!source ||
		node.id === tree.id ||
		node.id === target.id ||
		isDescendant(node, target.id)
	) {
		return false;
	}
	const sourceIndex = source.children.findIndex((child) => child.id === id);
	if (sourceIndex < 0) return false;
	source.children.splice(sourceIndex, 1);
	let targetIndex = pos < 0 ? target.children.length : pos;
	if (source === target && sourceIndex < targetIndex) targetIndex--;
	targetIndex = Math.max(0, Math.min(targetIndex, target.children.length));
	target.children.splice(targetIndex, 0, node);
	return true;
}

export function setOperator(tree, id, operator) {
	const group = findNode(tree, id);
	if (!group || group.type !== "group") return false;
	group.operator = operator;
	return true;
}

export function replaceNode(tree, id, replacement) {
	const parent = findParent(tree, id);
	if (!parent) return false;
	const index = parent.children.findIndex((child) => child.id === id);
	if (index < 0) return false;
	parent.children[index] = cloneTree(replacement);
	return true;
}
