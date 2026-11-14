import { defineCommand, UNIFIED_SHORTCUTS } from "../../composables/command_action_types.mjs";
import { cloneTree, createNodeId, isContainerNode, isLeafNode } from "./tree_builder_utils.mjs";

function unwrap(val, fallback) {
	if (val && typeof val === "object" && "value" in val) return val.value;
	return val !== undefined ? val : fallback;
}

/**
 * Deeply regenerates IDs for a cloned node and all its nested children.
 */
export function regenerateNodeIds(node) {
	if (!node || typeof node !== "object") return node;
	node.id = createNodeId(node.type || "node");
	if (Array.isArray(node.children)) {
		node.children.forEach(regenerateNodeIds);
	}
	return node;
}

/**
 * Builds standard action command definitions for TreeBuilder nodes (leaf, group, collection).
 */
export function useTreeBuilderActions({ treeApi, readOnly, beforeRemove }) {
	const getReadOnly = () => Boolean(unwrap(readOnly, false));

	const toggleEditCommand = defineCommand({
		id: "tree.toggle-edit",
		label: (ctx) =>
			ctx?.isEditing
				? typeof __ !== "undefined"
					? __("Finish editing / Show summary")
					: "Finish editing / Show summary"
				: typeof __ !== "undefined"
				? __("Edit")
				: "Edit",
		icon: "fa fa-pencil",
		shortcut: UNIFIED_SHORTCUTS.TOGGLE_EDIT,
		group: "edit",
		allowInInputs: true,
		isVisible: (ctx) =>
			!getReadOnly() &&
			isLeafNode(ctx?.node) &&
			Boolean(ctx?.hasSummarySlot) &&
			Boolean(ctx?.canToggle),
		isEnabled: (ctx) => {
			if (ctx?.isEditing) return Boolean(ctx?.canFinishEditing);
			return Boolean(ctx?.canToggle);
		},
		execute: (ctx) => {
			if (!treeApi || !ctx?.node?.id) return;
			if (ctx.isEditing) {
				if (typeof treeApi.finishEditing === "function") {
					treeApi.finishEditing(ctx.node.id);
				} else if (typeof treeApi.setEditing === "function") {
					treeApi.setEditing(null);
				}
			} else {
				if (typeof treeApi.setEditing === "function") {
					treeApi.setEditing(ctx.node.id);
				}
			}
		},
	});

	const selectCommand = defineCommand({
		id: "tree.select",
		label: () => (typeof __ !== "undefined" ? __("Select") : "Select"),
		icon: "fa fa-check-square-o",
		shortcut: UNIFIED_SHORTCUTS.SELECT,
		group: "select",
		isVisible: () => true,
		isEnabled: () => true,
		execute: (ctx) => {
			if (typeof treeApi?.selectNode === "function" && ctx?.node?.id) {
				treeApi.selectNode(ctx.node.id);
			}
		},
	});

	const insertLeafCommand = defineCommand({
		id: "tree.insert-leaf",
		label: (ctx) =>
			isContainerNode(ctx?.node)
				? typeof __ !== "undefined"
					? __("Add condition inside")
					: "Add condition inside"
				: typeof __ !== "undefined"
				? __("Insert condition below")
				: "Insert condition below",
		icon: "fa fa-plus",
		shortcut: UNIFIED_SHORTCUTS.INSERT,
		group: "insert",
		isVisible: () => !getReadOnly(),
		isEnabled: () => !getReadOnly(),
		execute: (ctx) => {
			if (!treeApi) return;
			if (isContainerNode(ctx?.node)) {
				treeApi.addLeaf(ctx.node.id);
			} else if (ctx?.parent?.id) {
				treeApi.addLeaf(ctx.parent.id);
			}
		},
	});

	const duplicateCommand = defineCommand({
		id: "tree.duplicate",
		label: () => (typeof __ !== "undefined" ? __("Duplicate") : "Duplicate"),
		icon: "fa fa-files-o",
		shortcut: UNIFIED_SHORTCUTS.DUPLICATE,
		group: "duplicate",
		isVisible: (ctx) => !getReadOnly() && ctx?.node?.id !== "root",
		isEnabled: (ctx) => !getReadOnly() && ctx?.node?.id !== "root",
		execute: (ctx) => {
			if (!treeApi || !ctx?.node) return;
			const targetId = ctx.node.id;
			const clone = cloneTree(ctx.node);
			regenerateNodeIds(clone);
			if (clone && typeof clone === "object") {
				delete clone.isNew;
				delete clone.is_incomplete_draft;
			}
			if (typeof treeApi.duplicateNode === "function") {
				treeApi.duplicateNode(targetId, clone);
			} else {
				const parent =
					ctx.parent ||
					(typeof treeApi.findParent === "function"
						? treeApi.findParent(targetId)
						: null);
				if (parent && Array.isArray(parent.children)) {
					const idx =
						ctx.index !== undefined
							? ctx.index
							: parent.children.findIndex((c) => c.id === targetId);
					const insertIndex = idx >= 0 ? idx + 1 : parent.children.length;
					parent.children.splice(insertIndex, 0, clone);
					if (typeof treeApi.selectNode === "function") {
						treeApi.selectNode(clone.id);
					}
					if (typeof treeApi.setEditing === "function" && isLeafNode(clone)) {
						treeApi.setEditing(clone.id);
					}
				}
			}
		},
	});

	const removeCommand = defineCommand({
		id: "tree.remove",
		label: () => (typeof __ !== "undefined" ? __("Remove") : "Remove"),
		icon: "fa fa-trash",
		shortcut: UNIFIED_SHORTCUTS.DELETE,
		group: "destructive",
		isDestructive: true,
		isVisible: (ctx) => !getReadOnly() && ctx?.node?.id !== "root",
		isEnabled: (ctx) => !getReadOnly() && ctx?.node?.id !== "root",
		execute: async (ctx) => {
			if (!ctx?.node?.id) return;
			const guard = unwrap(beforeRemove, null);
			if (typeof guard === "function") {
				const canRemove = guard(ctx.node.id, treeApi?.root);
				if (canRemove === false) return;
				if (canRemove instanceof Promise) {
					const confirmed = await canRemove;
					if (confirmed === false) return;
				}
			}
			if (typeof treeApi?.removeNode === "function") {
				treeApi.removeNode(ctx.node.id);
			}
		},
	});

	function getNodeActionList(ctx) {
		const list = [];
		if (toggleEditCommand.isVisible(ctx)) list.push(toggleEditCommand);
		if (selectCommand.isVisible(ctx)) list.push(selectCommand);
		list.push({ type: "divider" });
		if (insertLeafCommand.isVisible(ctx)) list.push(insertLeafCommand);
		if (duplicateCommand.isVisible(ctx)) list.push(duplicateCommand);
		list.push({ type: "divider" });
		if (removeCommand.isVisible(ctx)) list.push(removeCommand);
		return list;
	}

	return {
		toggleEditCommand,
		selectCommand,
		insertLeafCommand,
		duplicateCommand,
		removeCommand,
		getNodeActionList,
	};
}
