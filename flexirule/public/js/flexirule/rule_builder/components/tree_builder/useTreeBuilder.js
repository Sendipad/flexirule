import { computed, nextTick, reactive, ref, watch } from "vue";
import {
	cloneTree,
	findNode,
	findPath,
	isContainerNode,
	normalizeTree,
	treesEqual,
} from "./tree_builder_utils.js";
import * as commands from "./tree_builder_commands.js";
import { validateTree } from "./tree_builder_validation.js";

function nodeDepth(tree, id) {
	const path = findPath(tree, id);
	return path.length ? path.length - 1 : -1;
}

function getSubtreeHeight(node) {
	if (!isContainerNode(node) || !node.children?.length) return 0;
	return 1 + Math.max(...node.children.map(getSubtreeHeight));
}

export function useTreeBuilder({
	modelValue,
	emit,
	readOnly = false,
	groupOperators = ["and", "or"],
	leafFactory = () => ({}),
	scopeFactory = () => ({}),
	allowScopes = true,
	allowEmptyGroups = true,
	validateLeaf,
	validateScope,
	maxDepth = Infinity,
} = {}) {
	const root = reactive(normalizeTree(modelValue?.value ?? modelValue, { groupOperators })),
		selectedNodeId = ref(null),
		focusedNodeId = ref(null),
		editingNodeId = ref(null),
		expandedNodes = reactive(new Set([root.id])),
		dragState = reactive({ nodeId: null });
	let syncing = false;

	const normalizedMaxDepth = computed(() =>
		Number.isFinite(Number(maxDepth)) ? Math.max(0, Number(maxDepth)) : Infinity
	);
	const operators = computed(() => groupOperators.filter(Boolean)),
		selectedNode = computed(() => findNode(root, selectedNodeId.value)),
		focusedNode = computed(() => findNode(root, focusedNodeId.value));

	function replaceRoot(next) {
		const n = normalizeTree(next, { groupOperators });
		Object.keys(root).forEach((k) => delete root[k]);
		Object.assign(root, n);
		expandedNodes.clear();
		expandedNodes.add(root.id);
	}

	function emitChange() {
		if (syncing || !emit) return;
		const n = cloneTree(root);
		emit("update:modelValue", n);
		emit("change", n);
	}

	function mutate(fn) {
		if (readOnly) return null;
		const result = fn(root);
		if (result !== false) emitChange();
		return result;
	}

	function canAddChild(parentId) {
		const parent = findNode(root, parentId);
		if (!parent || !isContainerNode(parent)) return false;
		return nodeDepth(root, parentId) + 1 <= normalizedMaxDepth.value;
	}

	const addLeaf = (p = root.id, payload) =>
		canAddChild(p) && mutate((t) => commands.addLeaf(t, p, payload ?? leafFactory()));

	const addGroup = (p = root.id, op = operators.value[0] || "and") =>
		canAddChild(p) && mutate((t) => commands.addGroup(t, p, op));

	const addScope = (p = root.id, scope) =>
		allowScopes &&
		canAddChild(p) &&
		mutate((t) => commands.addScope(t, p, scope ?? scopeFactory()));

	const removeNode = (id) => {
		const r = mutate((t) => commands.removeNode(t, id));
		if (r) {
			if (selectedNodeId.value === id) selectedNodeId.value = null;
			if (focusedNodeId.value === id) focusedNodeId.value = null;
			if (editingNodeId.value === id) editingNodeId.value = null;
		}
		return r;
	};

	const moveNode = (id, p, pos = -1) =>
		mutate((t) => {
			const node = findNode(t, id);
			const target = findNode(t, p);
			if (!node || !target || !isContainerNode(target)) return false;
			const targetDepth = nodeDepth(t, p);
			const resultingDepth = targetDepth + 1 + getSubtreeHeight(node);
			if (resultingDepth > normalizedMaxDepth.value) return false;
			return commands.moveNode(t, id, p, pos);
		});

	const setOperator = (id, op) =>
		operators.value.includes(op) && mutate((t) => commands.setOperator(t, id, op));

	const replaceNode = (id, n) => mutate((t) => commands.replaceNode(t, id, n));

	function reset(next = modelValue?.value ?? modelValue) {
		syncing = true;
		replaceRoot(next);
		nextTick().then(() => (syncing = false));
	}

	function toggleExpanded(id) {
		expandedNodes.has(id) ? expandedNodes.delete(id) : expandedNodes.add(id);
	}

	function getNodeContext(id) {
		const path = findPath(root, id);
		return {
			scopes: path.filter((n) => n.type === "scope").map((n) => cloneTree(n.scope)),
			path: path.map((n) => ({ id: n.id, type: n.type })),
		};
	}

	function canMove(id, target) {
		if (!id || !target || id === root.id || id === target) return false;
		const targetPath = findPath(root, target).map((n) => n.id);
		if (!findNode(root, id) || !isContainerNode(findNode(root, target)) || targetPath.includes(id))
			return false;
		return (
			nodeDepth(root, target) + 1 + getSubtreeHeight(findNode(root, id)) <=
			normalizedMaxDepth.value
		);
	}

	function validate() {
		return validateTree(root, {
			groupOperators: operators.value,
			allowScopes,
			allowEmptyGroups,
			maxDepth: normalizedMaxDepth.value,
			validateLeaf,
			validateScope,
		});
	}

	function beginDrag(id) {
		if (!readOnly && canMove(id, root.id)) dragState.nodeId = id;
	}

	function dropNode(target, pos = -1) {
		if (!dragState.nodeId || !canMove(dragState.nodeId, target)) return false;
		const r = moveNode(dragState.nodeId, target, pos);
		dragState.nodeId = null;
		return r;
	}

	watch(
		modelValue,
		async (v) => {
			const n = normalizeTree(v, { groupOperators });
			if (treesEqual(n, root)) return;
			syncing = true;
			replaceRoot(n);
			await nextTick();
			syncing = false;
		},
		{ deep: true }
	);

	return {
		root,
		selectedNode,
		focusedNode,
		selectedNodeId,
		focusedNodeId,
		editingNodeId,
		expandedNodes,
		dragState,
		operators,
		maxDepth: normalizedMaxDepth,
		addLeaf,
		addGroup,
		addScope,
		removeNode,
		moveNode,
		setOperator,
		replaceNode,
		reset,
		selectNode: (id) => (selectedNodeId.value = id),
		focusNode: (id) => (focusedNodeId.value = id),
		setEditing: (id) => (editingNodeId.value = id),
		toggleExpanded,
		isExpanded: (id) => expandedNodes.has(id),
		getNodeContext,
		canAddChild,
		canMove,
		validate,
		beginDrag,
		dropNode,
		getTree: () => cloneTree(root),
	};
}
