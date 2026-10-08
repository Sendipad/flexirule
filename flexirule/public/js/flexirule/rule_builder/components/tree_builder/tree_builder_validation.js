import { isCollectionNode, isGroupNode, isLeafNode } from "./tree_builder_utils.js";

export function validateTree(
	tree,
	{
		groupOperators = ["and", "or"],
		allowEmptyRoot = true,
		allowEmptyGroups = true,
		maxDepth = Infinity,
		validateLeaf,
		validateCollection,
	} = {}
) {
	const errors = [];
	const ids = new Set();
	const add = (path, code, message) => errors.push({ path, code, message });

	function visit(node, path, depth, isRoot = false) {
		if (!node || typeof node !== "object" || Array.isArray(node)) {
			add(path, "malformed", "Tree node is malformed.");
			return;
		}
		if (!node.id || typeof node.id !== "string")
			add(path, "id", "Every tree node requires an id.");
		if (node.id && ids.has(node.id)) add(path, "duplicate_id", "Tree node ids must be unique.");
		if (node.id) ids.add(node.id);
		if (Number.isFinite(maxDepth) && depth > maxDepth)
			add(path, "max_depth", "Tree nesting depth exceeds the configured maximum.");

		if (isGroupNode(node)) {
			if (!groupOperators.includes(node.operator))
				add([...path, "operator"], "operator", "Group operator is not allowed.");
			if (!Array.isArray(node.children)) {
				add([...path, "children"], "children", "Children must be an array.");
				return;
			}
			if (!node.children.length && !isRoot && !allowEmptyGroups)
				add(path, "empty_group", "Group cannot be empty.");
			if (!node.children.length && isRoot && !allowEmptyRoot)
				add(path, "empty_root", "Tree root cannot be empty.");
			node.children.forEach((child, index) =>
				visit(child, [...path, "children", index], depth + 1)
			);
			return;
		}

		if (isCollectionNode(node)) {
			if (!Array.isArray(node.children)) {
				add([...path, "children"], "children", "Collection children must be an array.");
				return;
			}
			if (!node.children.length && !isRoot && !allowEmptyGroups)
				add(path, "empty_collection", "Collection cannot be empty.");
			if (validateCollection) {
				const result = validateCollection(node);
				if (result === false) add(path, "invalid_collection", "Collection is invalid.");
				else if (result?.errors) {
					result.errors.forEach((error) =>
						add(
							[...path, ...(error.path || [])],
							error.code || "invalid_collection",
							error.message || "Collection is invalid."
						)
					);
				}
			}
			node.children.forEach((child, index) =>
				visit(child, [...path, "children", index], depth + 1)
			);
			return;
		}

		if (isLeafNode(node)) {
			if (Object.prototype.hasOwnProperty.call(node, "children")) {
				add([...path, "children"], "leaf_children", "Leaf nodes cannot own children.");
			}
			if (validateLeaf) {
				const result = validateLeaf(node);
				if (result === false) add(path, "invalid_leaf", "Leaf is invalid.");
				else if (result?.errors) {
					result.errors.forEach((error) =>
						add(
							[...path, ...(error.path || [])],
							error.code || "invalid_leaf",
							error.message || "Leaf is invalid."
						)
					);
				}
			}
			return;
		}

		add(path, "node_type", "Unknown tree node type.");
	}

	visit(tree, [], 0, true);
	if (!isGroupNode(tree)) add([], "root_type", "Tree root must be a group node.");
	return { valid: errors.length === 0, errors };
}
