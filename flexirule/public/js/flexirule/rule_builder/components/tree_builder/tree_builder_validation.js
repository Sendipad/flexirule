import { isGroupNode, isLeafNode, isScopeNode } from "./tree_builder_utils.js";
export function validateTree(
	tree,
	{
		groupOperators = ["and", "or"],
		allowEmptyRoot = true,
		allowEmptyGroups = true,
		allowScopes = true,
		validateLeaf,
		validateScope,
	} = {}
) {
	const errors = [],
		ids = new Set();
	const add = (path, code, message) => errors.push({ path, code, message });
	function visit(n, path, isRoot = false) {
		if (!n || typeof n !== "object") {
			add(path, "malformed", "Tree node is malformed.");
			return;
		}
		if (!n.id || typeof n.id !== "string") add(path, "id", "Every tree node requires an id.");
		if (n.id && ids.has(n.id)) add(path, "duplicate_id", "Tree node ids must be unique.");
		ids.add(n.id);
		if (isGroupNode(n)) {
			if (!groupOperators.includes(n.operator))
				add([...path, "operator"], "operator", "Group operator is not allowed.");
			if (!Array.isArray(n.children)) {
				add([...path, "children"], "children", "Children must be an array.");
				return;
			}
			if (!n.children.length && !isRoot && !allowEmptyGroups)
				add(path, "empty_group", "Group cannot be empty.");
			n.children.forEach((c, i) => visit(c, [...path, "children", i]));
			return;
		}
		if (isScopeNode(n)) {
			if (!allowScopes) add(path, "scope_not_allowed", "Scope nodes are not allowed.");
			if (!n.scope || typeof n.scope !== "object" || Array.isArray(n.scope))
				add([...path, "scope"], "scope", "Scope metadata must be an object.");
			if (!Array.isArray(n.children)) {
				add([...path, "children"], "children", "Children must be an array.");
				return;
			}
			if (validateScope) {
				const r = validateScope(n.scope, n);
				if (r === false) add([...path, "scope"], "invalid_scope", "Scope is invalid.");
				else if (r?.errors)
					r.errors.forEach((e) =>
						add(
							[...path, "scope", ...(e.path || [])],
							e.code || "invalid_scope",
							e.message || "Scope is invalid."
						)
					);
			}
			n.children.forEach((c, i) => visit(c, [...path, "children", i]));
			return;
		}
		if (isLeafNode(n)) {
			if (Object.prototype.hasOwnProperty.call(n, "children"))
				add([...path, "children"], "leaf_children", "Leaf nodes cannot own children.");
			if (validateLeaf) {
				const r = validateLeaf(n);
				if (r === false) add(path, "invalid_leaf", "Leaf is invalid.");
				else if (r?.errors)
					r.errors.forEach((e) =>
						add(
							[...path, ...(e.path || [])],
							e.code || "invalid_leaf",
							e.message || "Leaf is invalid."
						)
					);
			}
			return;
		}
		add(path, "node_type", "Unknown tree node type.");
	}
	visit(tree, [], true);
	if (!isGroupNode(tree)) add([], "root_type", "Tree root must be a group node.");
	if (isGroupNode(tree) && !tree.children.length && !allowEmptyRoot)
		add([], "empty_root", "Tree root cannot be empty.");
	return { valid: !errors.length, errors };
}
