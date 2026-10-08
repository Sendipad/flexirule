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
	const node = createCollection(payload);
	parent.children.push(node);
	return node;
}

