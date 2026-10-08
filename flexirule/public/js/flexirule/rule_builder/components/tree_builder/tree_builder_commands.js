import {
	cloneTree,
	createGroup,
	createLeaf,
	createScope,
	findNode,
	findParent,
	isContainerNode,
	isDescendant,
} from "./tree_builder_utils.js";
function parentFor(tree, id) {
	const p = findNode(tree, id);
	return isContainerNode(p) ? p : null;
}
export function addLeaf(tree, parentId, payload = {}) {
	const p = parentFor(tree, parentId);
	if (!p) return null;
	const n = createLeaf(payload);
	p.children.push(n);
	return n;
}
export function addGroup(tree, parentId, operator = "and") {
	const p = parentFor(tree, parentId);
	if (!p) return null;
	const n = createGroup(operator);
	p.children.push(n);
	return n;
}
export function addScope(tree, parentId, scope = {}, children = []) {
	const p = parentFor(tree, parentId);
	if (!p) return null;
	const n = createScope(scope, cloneTree(children));
	p.children.push(n);
	return n;
}
export function removeNode(tree, id) {
	const p = findParent(tree, id);
	if (!p) return null;
	const i = p.children.findIndex((c) => c.id === id);
	return i < 0 ? null : p.children.splice(i, 1)[0] || null;
}
export function moveNode(tree, id, targetId, pos = -1) {
	const n = findNode(tree, id),
		target = parentFor(tree, targetId),
		source = findParent(tree, id);
	if (
		!n ||
		!target ||
		!source ||
		n.id === tree.id ||
		n.id === target.id ||
		isDescendant(n, target.id)
	)
		return false;
	const si = source.children.findIndex((c) => c.id === id);
	if (si < 0) return false;
	source.children.splice(si, 1);
	let ti = pos < 0 ? target.children.length : pos;
	if (source === target && si < ti) ti--;
	ti = Math.max(0, Math.min(ti, target.children.length));
	target.children.splice(ti, 0, n);
	return true;
}
export function setOperator(tree, id, operator) {
	const g = findNode(tree, id);
	if (!g || g.type !== "group") return false;
	g.operator = operator;
	return true;
}
export function replaceNode(tree, id, replacement) {
	const p = findParent(tree, id);
	if (!p) return false;
	const i = p.children.findIndex((c) => c.id === id);
	if (i < 0) return false;
	p.children[i] = cloneTree(replacement);
	return true;
}
