import { computed, nextTick, reactive, ref, watch } from "vue";
import { cloneTree, findNode, findPath, isContainerNode, normalizeTree, normalizeTreeNode, treesEqual, TreeModelError } from "./tree_builder_utils.js";
import * as commands from "./tree_builder_commands.js";
import { validateTree } from "./tree_builder_validation.js";

function depthOf(tree, id) {
	const path = findPath(tree, id);
	return path.length ? path.length - 1 : -1;
}
function subtreeHeight(node) {
	if (!isContainerNode(node) || !node.children.length) return 0;
	return 1 + Math.max(...node.children.map(subtreeHeight));
}

export function useTreeBuilder({
	modelValue,
	emit,
	readOnly = false,
	groupOperators = ["and", "or"],
	leafFactory = () => ({}),
	allowGroups = true,
	allowEmptyGroups = true,
	maxDepth = Infinity,
	validateLeaf,
} = {}) {
	const operators = computed(() => groupOperators.filter(Boolean));
	const normalizedMaxDepth = computed(() =>
		Number.isFinite(Number(maxDepth)) ? Math.max(0, Number(maxDepth)) : Infinity
	);
	const modelError = ref(null);

	function safeNormalize(value) {
		try {
			const normalized = normalizeTree(value, { groupOperators: operators.value });
			const structural = validateTree(normalized, {
				groupOperators: operators.value,
				allowEmptyGroups,
				maxDepth: normalizedMaxDepth.value,
			});
			if (!structural.valid) throw new TreeModelError(structural.errors[0]?.message || "Invalid tree.", structural.errors[0]?.path || []);
			modelError.value = null;
			return normalized;
		} catch (error) {
			modelError.value = error instanceof TreeModelError ? error : new TreeModelError(String(error));
			return normalizeTree(null, { groupOperators: operators.value });
		}
	}

	const root = reactive(safeNormalize(modelValue?.value ?? modelValue));
	const selectedNodeId = ref(null);
	const focusedNodeId = ref(null);
	const editingNodeId = ref(null);
	const expandedNodes = reactive(new Set([root.id]));
	const dragState = reactive({ nodeId: null });
	let syncing = false;

	const selectedNode = computed(() => findNode(root, selectedNodeId.value));
	const focusedNode = computed(() => findNode(root, focusedNodeId.value));

	function replaceRoot(next) {
		const normalized = safeNormalize(next);
		Object.keys(root).forEach((key) => delete root[key]);
		Object.assign(root, normalized);
		expandedNodes.clear();
		expandedNodes.add(root.id);
		return modelError.value ? false : true;
	}

	function emitChange() {
		if (syncing || !emit) return;
		const next = cloneTree(root);
		emit("update:modelValue", next);
		emit("change", next);
	}

	function mutate(fn) {
		if (readOnly) return null;
		const result = fn(root);
		if (result !== false) emitChange();
		return result;
	}

	function canAddChild(parentId) {
		const parent = findNode(root, parentId);
		return !!parent && isContainerNode(parent) && depthOf(root, parentId) + 1 <= normalizedMaxDepth.value;
	}

	const addLeaf = (parentId = root.id, payload) =>
		canAddChild(parentId) ? mutate((tree) => commands.addLeaf(tree, parentId, payload ?? leafFactory())) : null;

	const addGroup = (parentId = root.id, operator = operators.value[0]) =>
		allowGroups && canAddChild(parentId) ? mutate((tree) => commands.addGroup(tree, parentId, operator)) : null;

	function removeNode(id) {
		const result = mutate((tree) => commands.removeNode(tree, id));
		if (result) {
			if (selectedNodeId.value === id) selectedNodeId.value = null;
			if (focusedNodeId.value === id) focusedNodeId.value = null;
			if (editingNodeId.value === id) editingNodeId.value = null;
		}
		return result;
	}

	function canMove(id, targetId) {
		if (!id || !targetId || id === root.id || id === targetId) return false;
		const node = findNode(root, id);
		const target = findNode(root, targetId);
		if (!node || !target || !isContainerNode(target)) return false;
		if (findPath(root, targetId).some((ancestor) => ancestor.id === id)) return false;
		return depthOf(root, targetId) + 1 + subtreeHeight(node) <= normalizedMaxDepth.value;
	}

	function moveNode(id, targetId, position = -1) {
		if (!canMove(id, targetId)) return false;
		return mutate((tree) => commands.moveNode(tree, id, targetId, position));
	}

	function setOperator(id, operator) {
		if (!operators.value.includes(operator)) return false;
		return mutate((tree) => commands.setOperator(tree, id, operator));
	}

	function replaceNode(id, replacement) {
		if (readOnly) return null;
		const result = normalizeTreeNode(replacement, { groupOperators: operators.value });
		const candidate = cloneTree(root);
		if (!commands.replaceNode(candidate, id, result)) return false;
		const structural = validateTree(candidate, {
			groupOperators: operators.value,
			allowEmptyGroups,
			maxDepth: normalizedMaxDepth.value,
		});
		if (!structural.valid) return false;
		return mutate((tree) => commands.replaceNode(tree, id, result));
	}

	function validate() {
		const structural = validateTree(root, {
			groupOperators: operators.value,
			allowEmptyGroups,
			maxDepth: normalizedMaxDepth.value,
			validateLeaf,
		});
		return {
			...structural,
			valid: structural.valid && !modelError.value,
			modelError: modelError.value,
		};
	}

	function beginDrag(id) {
		if (!readOnly && canMove(id, root.id)) dragState.nodeId = id;
	}

	function dropNode(targetId, position = -1) {
		const id = dragState.nodeId;
		if (!id) return false;
		const result = moveNode(id, targetId, position);
		dragState.nodeId = null;
		return result;
	}

	function reset(next = modelValue?.value ?? modelValue) {
		syncing = true;
		replaceRoot(next);
		nextTick().then(() => {
			syncing = false;
	});
	}

	function toggleExpanded(id) {
		expandedNodes.has(id) ? expandedNodes.delete(id) : expandedNodes.add(id);
	}

	watch(modelValue, async (value) => {
		const normalized = safeNormalize(value);
		if (!modelError.value && treesEqual(normalized, root)) return;
		syncing = true;
		replaceRoot(value);
		await nextTick();
		syncing = false;
	}, { deep: true });

	return {
		root,
		modelError,
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
		canAddChild,
		canMove,
		validate,
		beginDrag,
		dropNode,
		getTree: () => cloneTree(root),
	};
}
