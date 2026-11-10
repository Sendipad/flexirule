import { defineCommand, UNIFIED_SHORTCUTS } from "../composables/command_action_types.mjs";

function unwrap(val, fallback) {
	if (val && typeof val === "object" && "value" in val) return val.value;
	return val !== undefined ? val : fallback;
}

/**
 * Builds standard action command definitions for GenericGrid rows.
 */
export function useGenericGridActions({
	gridApi,
	canCopyPaste,
	readOnly,
	availableRowActions,
	editShortcut,
}) {
	const getEditShortcut = () => unwrap(editShortcut, UNIFIED_SHORTCUTS.TOGGLE_EDIT);
	const getReadOnly = () => Boolean(unwrap(readOnly, false));
	const getAvailableRowActions = () => unwrap(availableRowActions, ["edit", "move", "remove"]);
	const getCanCopyPaste = () => Boolean(unwrap(canCopyPaste, false));

	const toggleEditCommand = defineCommand({
		id: "row.toggle-edit",
		label: (ctx) =>
			ctx?.isEditing
				? typeof __ !== "undefined"
					? __("Switch to readable view")
					: "Switch to readable view"
				: typeof __ !== "undefined"
				? __("Edit row")
				: "Edit row",
		icon: "fa fa-pencil",
		shortcut: getEditShortcut(),
		group: "edit",
		allowInInputs: true,
		isVisible: (ctx) => {
			const actions = getAvailableRowActions();
			return !getReadOnly() && actions.includes("edit") && Boolean(ctx?.canToggle);
		},
		isEnabled: (ctx) => {
			if (ctx?.isEditing) return Boolean(ctx?.canFinishEditing);
			return Boolean(ctx?.canToggle);
		},
		execute: (ctx) => {
			if (!gridApi?.requestRowAction || !ctx?.entry) return;
			const nextAction = ctx.isEditing ? "view" : "edit";
			gridApi.requestRowAction(nextAction, ctx.entry);
		},
	});

	const selectCommand = defineCommand({
		id: "row.select",
		label: (ctx) =>
			ctx?.isSelected
				? typeof __ !== "undefined"
					? __("Deselect row")
					: "Deselect row"
				: typeof __ !== "undefined"
				? __("Select row")
				: "Select row",
		icon: "fa fa-check-square-o",
		shortcut: UNIFIED_SHORTCUTS.SELECT,
		group: "select",
		isVisible: () => Boolean(unwrap(gridApi?.selectionEnabled, true)),
		isEnabled: () => true,
		execute: (ctx) => {
			if (gridApi?.toggleRowSelection && ctx?.pageIndex !== undefined) {
				gridApi.toggleRowSelection(ctx.pageIndex);
			}
		},
	});

	const insertBelowCommand = defineCommand({
		id: "row.insert-below",
		label: () => (typeof __ !== "undefined" ? __("Insert row below") : "Insert row below"),
		icon: "fa fa-plus",
		shortcut: UNIFIED_SHORTCUTS.INSERT,
		group: "insert",
		isVisible: () => !getReadOnly() && Boolean(unwrap(gridApi?.hasPrimaryAction, true)),
		isEnabled: () => !getReadOnly(),
		execute: (ctx) => {
			if (gridApi?.requestPrimaryAction) {
				gridApi.requestPrimaryAction(ctx?.entry?.index);
			}
		},
	});

	const duplicateCommand = defineCommand({
		id: "row.duplicate",
		label: () => (typeof __ !== "undefined" ? __("Duplicate row") : "Duplicate row"),
		icon: "fa fa-files-o",
		shortcut: UNIFIED_SHORTCUTS.DUPLICATE,
		group: "duplicate",
		isVisible: () => !getReadOnly() && getCanCopyPaste(),
		isEnabled: (ctx) => !getReadOnly() && Boolean(ctx?.entry),
		execute: (ctx) => {
			if (gridApi?.duplicateRow && ctx?.entry) {
				gridApi.duplicateRow(ctx.entry);
			}
		},
	});

	const copyCommand = defineCommand({
		id: "row.copy",
		label: () => (typeof __ !== "undefined" ? __("Copy row") : "Copy row"),
		icon: "fa fa-clone",
		shortcut: UNIFIED_SHORTCUTS.COPY,
		group: "clipboard",
		isVisible: () => getCanCopyPaste(),
		isEnabled: () => getCanCopyPaste(),
		execute: () => {
			if (gridApi?.copySelectedRows) {
				gridApi.copySelectedRows();
			}
		},
	});

	const removeCommand = defineCommand({
		id: "row.remove",
		label: (ctx) =>
			ctx?.selectedCount > 1
				? typeof __ !== "undefined"
					? __("Delete selected rows ({0})", [ctx.selectedCount])
					: `Delete selected rows (${ctx.selectedCount})`
				: typeof __ !== "undefined"
				? __("Delete row")
				: "Delete row",
		icon: "fa fa-trash",
		shortcut: UNIFIED_SHORTCUTS.DELETE,
		group: "destructive",
		isDestructive: true,
		isVisible: () => {
			const actions = getAvailableRowActions();
			return !getReadOnly() && actions.includes("remove");
		},
		isEnabled: () => !getReadOnly(),
		requiresConfirmation: (ctx) => Boolean(ctx?.selectedCount > 1),
		confirmationMessage: (ctx) =>
			typeof __ !== "undefined"
				? __("Are you sure you want to delete {0} selected rows?", [ctx.selectedCount])
				: `Are you sure you want to delete ${ctx.selectedCount} selected rows?`,
		execute: async (ctx) => {
			if (!gridApi || !ctx?.entry) return;
			if (ctx.selectedCount > 1) {
				if (gridApi.requestBulkDelete) gridApi.requestBulkDelete();
			} else {
				if (gridApi.requestRowAction) {
					gridApi.requestRowAction("remove", ctx.entry);
				}
			}
		},
	});

	function getRowActionList(ctx) {
		const list = [];
		if (toggleEditCommand.isVisible(ctx)) list.push(toggleEditCommand);
		if (selectCommand.isVisible(ctx)) list.push(selectCommand);
		list.push({ type: "divider" });
		if (insertBelowCommand.isVisible(ctx)) list.push(insertBelowCommand);
		if (duplicateCommand.isVisible(ctx)) list.push(duplicateCommand);
		if (copyCommand.isVisible(ctx)) list.push(copyCommand);
		list.push({ type: "divider" });
		if (removeCommand.isVisible(ctx)) list.push(removeCommand);
		return list;
	}

	return {
		toggleEditCommand,
		selectCommand,
		insertBelowCommand,
		duplicateCommand,
		copyCommand,
		removeCommand,
		getRowActionList,
	};
}
