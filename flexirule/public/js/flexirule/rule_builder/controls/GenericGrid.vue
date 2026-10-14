<template>
	<div
		v-if="!isDataGrid"
		class="fxr-generic-grid fxr-generic-grid-layout"
		:style="gridStyle"
	>
		<slot />
	</div>

	<div
		v-else
		ref="rootRef"
		class="fxr-generic-grid fxr-generic-grid-data"
		:class="{ 'is-compact': compact, 'is-read-only': readOnly }"
		:style="gridStyle"
		role="group"
		:aria-label="gridLabel || __('Editable list')"
		:aria-keyshortcuts="ariaKeyShortcuts"
		tabindex="0"
		@keydown="handleKeydown"
		@pointerup="endDragSelection"
		@pointercancel="endDragSelection"
	>
		<div class="fxr-generic-grid-rows">
			<div v-if="!filteredRows.length" class="fxr-generic-grid-empty">
				<slot name="empty">{{ __('No matching rows.') }}</slot>
			</div>
			<article
				v-for="(entry, pageIndex) in displayedRows"
				:key="entry.key"
				class="fxr-generic-grid-row"
				:class="{
					'is-selected': isSelected(entry.key),
					'is-invalid': getInvalidState(entry.row, entry.index).invalid,
					'is-editing': Boolean(entry.row?.[editStateKey]),
				}"
				:aria-invalid="getInvalidState(entry.row, entry.index).invalid ? 'true' : undefined"
				:title="getInvalidState(entry.row, entry.index).message || undefined"
				:data-row-index="entry.index"
			>
				<div class="fxr-generic-grid-row-toolbar">
					<button
						type="button"
						class="fxr-generic-grid-row-index"
						:class="{ 'is-selected': isSelected(entry.key) }"
						:aria-label="__('Select row') + ' ' + (entry.index + 1)"
						:aria-pressed="String(isSelected(entry.key))"
						:title="__('Click to select; drag across row numbers to select a range')"
						@pointerdown.stop.prevent="beginDragSelection(pageIndex, $event)"
						@pointerenter="extendDragSelection(pageIndex)"
						@click="handleIndexKeyboardClick(pageIndex, $event)"
					>
						{{ entry.index + 1 }}
					</button>

					<div
					v-if="
						!readOnly &&
						showRowActions &&
						(availableRowActions.includes('edit') ||
							availableRowActions.includes('move') ||
							availableRowActions.includes('remove'))
					"
					class="fxr-generic-grid-row-actions"
				>
						<button
							v-if="availableRowActions.includes('edit')"
							type="button"
							class="fxr-grid-icon-button"
							:title="entry.row?.[editStateKey] ? __('Switch to readable row') + ' (' + editShortcut + ')' : __('Edit row') + ' (' + editShortcut + ')'"
							:aria-label="entry.row?.[editStateKey] ? __('Switch to readable row') : __('Edit row')"
							:aria-keyshortcuts="editShortcut"
							@click="requestRowAction(entry.row?.[editStateKey] ? 'view' : 'edit', entry)"
						>
							<i :class="entry.row?.[editStateKey] ? 'fa fa-check' : 'fa fa-pencil'" aria-hidden="true"></i>
						</button>
						<div v-if="availableRowActions.includes('move')" class="fxr-generic-grid-reorder" :aria-label="__('Move row')">
							<button
								type="button"
								class="fxr-grid-icon-button"
								:disabled="entry.index === 0"
								:title="__('Move row up')"
								:aria-label="__('Move row up')"
								@click="requestRowAction('move-up', entry)"
							>
								<i class="fa fa-chevron-up" aria-hidden="true"></i>
							</button>
							<button
								type="button"
								class="fxr-grid-icon-button"
								:disabled="entry.index === sourceRows.length - 1"
								:title="__('Move row down')"
								:aria-label="__('Move row down')"
								@click="requestRowAction('move-down', entry)"
							>
								<i class="fa fa-chevron-down" aria-hidden="true"></i>
							</button>
						</div>
						<button
							v-if="availableRowActions.includes('remove')"
							type="button"
							class="fxr-grid-icon-button is-danger"
							:title="__('Remove row')"
							:aria-label="__('Remove row')"
							@click="requestRowAction('remove', entry)"
						>
							<i class="fa fa-trash" aria-hidden="true"></i>
						</button>
					</div>
				</div>

				<div v-if="hasSummarySlot" class="fxr-generic-grid-row-summary">
					<slot
						name="row-summary"
						:row="entry.row"
						:index="entry.index"
						:selected="isSelected(entry.key)"
						:invalid="getInvalidState(entry.row, entry.index).invalid"
						:invalidMessage="getInvalidState(entry.row, entry.index).message"
						:rowProps="resolveRowProps(entry.row, entry.index)"
					/>
				</div>
				<div
					v-if="!hasSummarySlot || entry.row?.[editStateKey]"
					class="fxr-generic-grid-row-body"
				>
					<slot
						name="row"
						:row="entry.row"
						:index="entry.index"
						:selected="isSelected(entry.key)"
						:invalid="getInvalidState(entry.row, entry.index).invalid"
						:invalidMessage="getInvalidState(entry.row, entry.index).message"
						:rowProps="resolveRowProps(entry.row, entry.index)"
					>
						<component
							v-if="rowComponent"
							:is="rowComponent"
							v-bind="resolveRowProps(entry.row, entry.index)"
							@update:modelValue="
								emit('row-update', {
									row: entry.row,
									index: entry.index,
									value: $event,
								})
							"
						/>
						<div v-else class="fxr-generic-grid-row-fallback">{{ entry.row }}</div>
					</slot>
				</div>
			</article>
		</div>

		<div
			v-if="pagination && filteredRows.length > currentPageSize"
			class="fxr-generic-grid-pagination"
		>
			<label class="fxr-generic-grid-page-size">
				<span>{{ __('Rows per page') }}</span>
				<select :value="currentPageSize" @change="changePageSize($event.target.value)">
					<option v-for="size in availablePageSizes" :key="size" :value="size">
						{{ size }}
					</option>
				</select>
			</label>
			<span class="fxr-generic-grid-page-summary">
				{{ paginationSummary }}
			</span>
			<div class="fxr-generic-grid-page-actions">
				<button
					type="button"
					class="fxr-grid-button fxr-grid-button--quiet"
					:disabled="currentPage <= 1"
					@click="changePage(currentPage - 1)"
				>
					<i class="fa fa-chevron-left" aria-hidden="true"></i>
					{{ __('Previous') }}
				</button>
				<span>{{ currentPage }} / {{ pageCount }}</span>
				<button
					type="button"
					class="fxr-grid-button fxr-grid-button--quiet"
					:disabled="currentPage >= pageCount"
					@click="changePage(currentPage + 1)"
				>
					{{ __('Next') }}
					<i class="fa fa-chevron-right" aria-hidden="true"></i>
				</button>
			</div>
		</div>

		<div v-if="showToolbar" class="fxr-generic-grid-footer">
			<div class="fxr-generic-grid-footer-primary">
				<button
					v-if="activePrimaryAction && !readOnly"
					type="button"
					class="fxr-btn fxr-btn--sm fxr-btn--primary fxr-grid-button fxr-grid-button--primary"
					:aria-keyshortcuts="props.primaryActionShortcut"
					:title="primaryActionTitle"
					:aria-label="primaryActionTitle"
					@click="requestPrimaryAction()"
				>
					<i v-if="activePrimaryAction.icon" :class="activePrimaryAction.icon" aria-hidden="true"></i>
					{{ activePrimaryAction.label || __('Add row') }}
				</button>
				<div v-if="secondaryActions.length && !readOnly" class="fxr-grid-menu fxr-grid-primary-menu">
					<button
						ref="primaryMenuButtonRef"
						type="button"
						class="fxr-btn fxr-btn--sm fxr-grid-menu-toggle"
						:title="__('Choose or run another action')"
						:aria-label="__('Choose or run another action')"
						aria-haspopup="menu"
						:aria-expanded="String(primaryMenuOpen)"
						@click="togglePrimaryMenu"
					>
						<i class="fa fa-chevron-down" aria-hidden="true"></i>
					</button>
					<div
						v-if="primaryMenuOpen"
						class="fxr-grid-menu-items fxr-grid-menu-items--left"
						role="menu"
						@keydown="handleMenuKeydown"
					>
						<div class="fxr-grid-menu-heading">{{ __('Run an action, or pin it as primary') }}</div>
						<div v-for="action in secondaryActions" :key="action.id" class="fxr-grid-menu-action-row">
							<button
								type="button"
								role="menuitem"
								class="fxr-grid-menu-pin"
								:title="__('Make {0} the primary action', [action.label])"
								:aria-label="__('Make {0} the primary action', [action.label])"
								@click.stop="setPrimaryAction(action.id)"
							>
								<i class="fa fa-thumb-tack" aria-hidden="true"></i>
							</button>
							<button
								type="button"
								role="menuitem"
								class="fxr-btn fxr-btn--sm fxr-grid-menu-item"
								:aria-keyshortcuts="action.shortcut || undefined"
								@click="requestGridAction(action)"
							>
								<i v-if="action.icon" :class="action.icon" aria-hidden="true"></i>
								<span>{{ action.label }}</span>
								<kbd v-if="action.shortcut">{{ action.shortcut }}</kbd>
							</button>
						</div>
					</div>
				</div>
			</div>

			<div v-if="selection && selectedRows.length" class="fxr-generic-grid-bulk-actions">
				<span class="fxr-generic-grid-selection-count">
					{{ selectedRows.length }} {{ __('selected') }}
				</span>
				<button type="button" class="fxr-grid-button fxr-grid-button--quiet" @click="selectAllFilteredRows">
					{{ searchQuery ? __('Select all matching') : __('Select all') }}
				</button>
				<button type="button" class="fxr-grid-button fxr-grid-button--quiet" @click="clearSelection">
					{{ __('Clear') }}
				</button>
				<button
					v-if="!readOnly"
					type="button"
					class="fxr-grid-button fxr-grid-button--danger"
					:title="__('Delete selected rows')"
					@click="requestBulkDelete"
				>
					<i class="fa fa-trash" aria-hidden="true"></i>
					{{ __('Delete selected') }}
				</button>
			</div>

			<div class="fxr-generic-grid-footer-actions">
				<div v-if="searchOpen" class="fxr-generic-grid-search-popover">
					<i class="fa fa-search" aria-hidden="true"></i>
					<input
						ref="searchInputRef"
						v-model="searchQuery"
						type="search"
						:placeholder="searchPlaceholder || __('Search rows...')"
						:aria-label="searchPlaceholder || __('Search rows')"
						@keydown.esc.stop.prevent="closeSearch"
					/>
				</div>
				<button
					v-if="hasSearch && showSearch"
					type="button"
					class="fxr-grid-icon-button fxr-grid-icon-button--secondary"
					:title="__('Search rows')"
					:aria-label="__('Search rows')"
					:aria-expanded="String(searchOpen)"
					@click="toggleSearch"
				>
					<i :class="searchOpen ? 'fa fa-times' : 'fa fa-search'" aria-hidden="true"></i>
				</button>
				<button
					v-if="selection && allowCopyPaste"
					type="button"
					class="fxr-grid-button fxr-grid-button--quiet"
					:disabled="!canCopyPaste || !selectedRows.length"
					:title="canCopyPaste ? __('Copy selected rows (Ctrl/Cmd+C)') : __('Provide cloneRow to enable copy/paste with a custom rowKey resolver')"
					@click="copySelectedRows"
				>
					<i class="fa fa-copy" aria-hidden="true"></i>
					{{ __('Copy') }}
				</button>
				<button
					v-if="!readOnly && allowCopyPaste"
					type="button"
					class="fxr-grid-button fxr-grid-button--quiet"
					:disabled="!canCopyPaste"
					:title="canCopyPaste ? __('Paste rows (Ctrl/Cmd+V)') : __('Provide cloneRow to enable copy/paste with a custom rowKey resolver')"
					@click="pasteRows"
				>
					<i class="fa fa-clipboard" aria-hidden="true"></i>
					{{ __('Paste') }}
				</button>
			</div>
		</div>

		<p v-if="feedback" class="fxr-generic-grid-feedback" role="status" aria-live="polite">
			{{ feedback }}
		</p>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useSlots, watch } from "vue";
import {
	GRID_CLIPBOARD_FORMAT,
	getRowKey,
	getBulkEditAction,
	paginateRows,
	parseClipboardRows,
	rowMatchesSearch,
	buildRowProps,
	selectRangeKeys,
} from "./generic_grid_model.mjs";

const props = defineProps({
	// Use the default slot for layout-only mode, or provide rows/modelValue for a data grid.
	rows: { type: Array, default: null },
	modelValue: { type: Array, default: null },
	rowKey: { type: [String, Function], default: "id" },
	gridLabel: { type: String, default: "" },
	keyboardNavigation: { type: Boolean, default: true },
	primaryActionShortcut: { type: String, default: "Alt+Enter" },
	rowComponent: { type: [Object, Function, String], default: null },
	rowProps: { type: [Object, Function], default: null },
	rowInvalid: { type: [Function, Array], default: null },
	searchableFields: { type: [Array, Function, Boolean], default: null },
	searchPlaceholder: { type: String, default: "" },
	minColumnWidth: { type: String, default: "240px" },
	gap: { type: String, default: "var(--fxr-space-3, 12px)" },
	readOnly: { type: Boolean, default: false },
	compact: { type: Boolean, default: true },
	selection: { type: Boolean, default: true },
	allowCopyPaste: { type: Boolean, default: true },
	showSearch: { type: Boolean, default: true },
	showToolbar: { type: Boolean, default: true },
	showRowActions: { type: Boolean, default: true },
	availableRowActions: {
		type: Array,
		default: () => ["edit", "move", "remove"],
	},
	pagination: { type: Boolean, default: true },
	pageSize: { type: Number, default: 10 },
	pageSizeOptions: { type: Array, default: () => [5, 10, 20, 50] },
	primaryAction: { type: Object, default: null },
	actionOptions: { type: Array, default: () => [] },
	defaultPrimaryAction: { type: String, default: "" },
	preferenceKey: { type: String, default: "" },
	editShortcut: { type: String, default: "Alt+E" },
	editStateKey: { type: String, default: "isEditing" },
	cloneRow: { type: Function, default: null },
});

const emit = defineEmits([
	"update:rows",
	"update:modelValue",
	"row-action",
	"row-update",
	"primary-action",
	"grid-action",
	"bulk-delete",
	"primary-action-change",
	"selection-change",
	"copy",
	"paste",
	"page-change",
	"clipboard-error",
]);

const rootRef = ref(null);
const slots = useSlots();
const hasSummarySlot = computed(() => Boolean(slots["row-summary"]));
const searchInputRef = ref(null);
const primaryMenuButtonRef = ref(null);
const primaryMenuOpen = ref(false);
const searchOpen = ref(false);
const searchQuery = ref("");
const selectedPrimaryActionId = ref(props.defaultPrimaryAction || props.primaryAction?.id || "");
const currentPage = ref(1);
const currentPageSize = ref(normalizePageSize(props.pageSize));
const selectedKeys = ref(new Set());
const activeRowIndex = ref(null);
const keyboardSelectionAnchor = ref(null);
const feedback = ref("");
const internalClipboard = ref("");
const dragSelection = ref({
	active: false,
	anchorIndex: -1,
	lastIndex: -1,
	baseKeys: [],
	modifier: false,
	wasSelected: false,
});

const isDataGrid = computed(() => props.rows !== null || props.modelValue !== null);
// A computed row key depends on caller-owned identity. Without cloneRow the grid
// cannot guarantee pasted rows receive a new identity, so disable clipboard mutations.
const canCopyPaste = computed(
	() => props.allowCopyPaste && (typeof props.rowKey !== "function" || typeof props.cloneRow === "function")
);
const sourceList = computed(() => props.rows ?? props.modelValue ?? []);
const sourceRows = computed(() =>
	(Array.isArray(sourceList.value) ? sourceList.value : []).map((row, index) => ({
		row,
		index,
		key: getRowKey(row, index, props.rowKey),
	}))
);
const hasSearch = computed(
	() =>
		(typeof props.searchableFields === "function" ||
			(Array.isArray(props.searchableFields) && props.searchableFields.length > 0)) &&
		props.searchableFields !== false
);
const filteredRows = computed(() =>
	sourceRows.value.filter((entry) =>
		rowMatchesSearch(entry.row, props.searchableFields, searchQuery.value)
	)
);
const currentPageResult = computed(() =>
	paginateRows(filteredRows.value, currentPage.value, currentPageSize.value)
);
const displayedRows = computed(() =>
	props.pagination ? currentPageResult.value.rows : filteredRows.value
);
const pageCount = computed(() =>
	props.pagination ? currentPageResult.value.pageCount : 1
);
const availablePageSizes = computed(() => {
	const values = [
		...new Set(
			(props.pageSizeOptions || [])
				.map((value) => Number(value))
				.filter((value) => Number.isInteger(value) && value > 0)
				.concat(currentPageSize.value)
				.sort((a, b) => a - b)
		),
	];
	return values;
});
const selectedRows = computed(() =>
	sourceRows.value.filter((entry) => selectedKeys.value.has(entry.key)).map((entry) => entry.row)
);
const paginationSummary = computed(() => {
	const result = currentPageResult.value;
	return result.total
		? __('Showing {0}–{1} of {2}', [result.start + 1, result.end, result.total])
		: __('No rows');
});
const resolvedActionOptions = computed(() => {
	if (props.actionOptions.length) return props.actionOptions;
	return props.primaryAction ? [props.primaryAction] : [];
});
const activePrimaryAction = computed(() => {
	return (
		resolvedActionOptions.value.find((action) => action.id === selectedPrimaryActionId.value) ||
		resolvedActionOptions.value.find((action) => action.id === props.defaultPrimaryAction) ||
		resolvedActionOptions.value[0] ||
		props.primaryAction ||
		null
	);
});
const secondaryActions = computed(() =>
	resolvedActionOptions.value.filter((action) => action.id !== activePrimaryAction.value?.id)
);
const primaryActionTitle = computed(() => {
	const label = activePrimaryAction.value?.label || __("Add row");
	return label + " (" + props.primaryActionShortcut + ")";
});
const ariaKeyShortcuts = computed(() => {
	const shortcuts = ["ArrowUp", "ArrowDown", "Home", "End"];
	if (!props.readOnly) {
		shortcuts.push(props.editShortcut, props.primaryActionShortcut);
		for (const action of resolvedActionOptions.value) {
			if (action.shortcut) shortcuts.push(action.shortcut);
		}
	}
	return [...new Set(shortcuts.filter(Boolean))].join(" ");
});
const gridStyle = computed(() => ({
	"--fxr-generic-grid-min-column-width": props.minColumnWidth,
	"--fxr-generic-grid-gap": props.gap,
}));

watch(searchQuery, () => {
	currentPage.value = 1;
});
watch(currentPageSize, () => {
	currentPage.value = 1;
});
watch(
	() => [props.preferenceKey, props.defaultPrimaryAction, props.actionOptions.map((action) => action.id).join("|")],
	loadPrimaryActionPreference
);
watch(
	() => props.pageSize,
	(value) => {
		const nextSize = normalizePageSize(value);
		if (nextSize !== currentPageSize.value) currentPageSize.value = nextSize;
	}
);
watch(
	() => filteredRows.value.length,
	() => {
		if (currentPage.value > pageCount.value) currentPage.value = pageCount.value;
	}
);
onMounted(() => {
	loadPrimaryActionPreference();
	if (typeof window === "undefined") return;
	window.addEventListener("pointerup", endDragSelection);
	window.addEventListener("pointercancel", endDragSelection);
	document.addEventListener("pointerdown", handleOutsideMenuPointerDown);
});
onBeforeUnmount(() => {
	if (typeof window === "undefined") return;
	window.removeEventListener("pointerup", endDragSelection);
	window.removeEventListener("pointercancel", endDragSelection);
	document.removeEventListener("pointerdown", handleOutsideMenuPointerDown);
});

watch(
	() => sourceRows.value.map((entry) => entry.key),
	(keys) => {
		const allowedKeys = new Set(keys);
		const next = new Set([...selectedKeys.value].filter((key) => allowedKeys.has(key)));
		if (next.size !== selectedKeys.value.size) {
			selectedKeys.value = next;
			emitSelectionChange();
		}
		if (currentPage.value > pageCount.value) currentPage.value = pageCount.value;
	}
);

function normalizePageSize(value) {
	const size = Number(value);
	return Number.isInteger(size) && size > 0 ? size : 10;
}

function isSelected(key) {
	return selectedKeys.value.has(String(key));
}

function emitSelectionChange() {
	emit("selection-change", selectedRows.value);
}

function setSelectedKeys(keys) {
	selectedKeys.value = new Set(keys.map(String));
	emitSelectionChange();
}

function selectVisibleRange(startIndex, endIndex, baseKeys = []) {
	const keys = selectRangeKeys(
		displayedRows.value,
		startIndex,
		endIndex,
		(entry) => entry.key
	);
	setSelectedKeys([...new Set([...baseKeys, ...keys])]);
}

function beginDragSelection(pageIndex, event) {
	if (!props.selection) return;
	const entry = displayedRows.value[pageIndex];
	if (!entry) return;
	activeRowIndex.value = entry.index;
	keyboardSelectionAnchor.value = pageIndex;
	const modifier = Boolean(event.ctrlKey || event.metaKey);
	const wasSelected = isSelected(entry.key);
	const baseKeys = modifier ? [...selectedKeys.value] : [];
	dragSelection.value = {
		active: true,
		anchorIndex: pageIndex,
		lastIndex: pageIndex,
		baseKeys,
		modifier,
		wasSelected,
	};
	selectVisibleRange(pageIndex, pageIndex, baseKeys);
	if (props.selection) rootRef.value?.focus({ preventScroll: true });
}

function extendDragSelection(pageIndex) {
	if (!dragSelection.value.active || pageIndex === dragSelection.value.lastIndex) return;
	dragSelection.value.lastIndex = pageIndex;
	selectVisibleRange(
		dragSelection.value.anchorIndex,
		pageIndex,
		dragSelection.value.baseKeys
	);
}

function endDragSelection() {
	if (!dragSelection.value.active) return;
	const drag = dragSelection.value;
	if (drag.modifier && drag.anchorIndex === drag.lastIndex && drag.wasSelected) {
		const entry = displayedRows.value[drag.anchorIndex];
		if (entry) {
			const next = new Set(selectedKeys.value);
			next.delete(entry.key);
			setSelectedKeys([...next]);
		}
	}
	dragSelection.value = {
		active: false,
		anchorIndex: -1,
		lastIndex: -1,
		baseKeys: [],
		modifier: false,
		wasSelected: false,
	};
}

function handleIndexKeyboardClick(pageIndex, event) {
	if (!props.selection || event.detail !== 0) return;
	const entry = displayedRows.value[pageIndex];
	if (!entry) return;
	activeRowIndex.value = entry.index;
	keyboardSelectionAnchor.value = pageIndex;
	selectVisibleRange(pageIndex, pageIndex);
}

function getInvalidState(row, index) {
	let result = false;
	if (typeof props.rowInvalid === "function") result = props.rowInvalid(row, index);
	else if (Array.isArray(props.rowInvalid)) result = props.rowInvalid.includes(index);
	return {
		invalid: Boolean(result),
		message: typeof result === "string" ? result : "",
	};
}

function resolveRowProps(row, index) {
	return buildRowProps(
		row,
		index,
		props.rowProps,
		isSelected(getRowKey(row, index, props.rowKey)),
		getInvalidState(row, index).invalid,
		props.readOnly
	);
}

function requestRowAction(action, entry) {
	if (props.readOnly) return;
	emit("row-action", {
		action,
		row: entry.row,
		index: entry.index,
		key: entry.key,
	});
}

function requestPrimaryAction(afterIndex = null) {
	if (props.readOnly || !activePrimaryAction.value) return;
	emit("primary-action", {
		afterIndex,
		action: activePrimaryAction.value.id || null,
	});
}

async function togglePrimaryMenu() {
	primaryMenuOpen.value = !primaryMenuOpen.value;
	if (primaryMenuOpen.value) {
		await nextTick();
		rootRef.value?.querySelector(".fxr-grid-primary-menu .fxr-grid-menu-item")?.focus();
	}
}

function closeActionMenus() {
	primaryMenuOpen.value = false;
}

function handleOutsideMenuPointerDown(event) {
	if (event.target?.closest?.(".fxr-grid-primary-menu")) return;
	closeActionMenus();
}

async function handleMenuKeydown(event) {
	const menuElement = event.currentTarget;
	if (event.key === "Escape") {
		event.preventDefault();
		closeActionMenus();
		await nextTick();
		primaryMenuButtonRef.value?.focus();
		return;
	}

	const items = Array.from(menuElement.querySelectorAll('[role="menuitem"]:not(:disabled)'));
	if (!items.length) return;
	const currentIndex = items.indexOf(document.activeElement);
	let nextIndex = currentIndex;
	if (event.key === "ArrowDown") nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
	else if (event.key === "ArrowUp") nextIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
	else if (event.key === "Home") nextIndex = 0;
	else if (event.key === "End") nextIndex = items.length - 1;
	else return;
	event.preventDefault();
	items[nextIndex]?.focus();
}

async function requestGridAction(action) {
	if (props.readOnly || !action) return;
	const wasMenuOpen = primaryMenuOpen.value;
	closeActionMenus();
	emit("grid-action", { action: action.id });
	// If invoked from the menu, restore focus after it unmounts. Keyboard shortcuts
	// should preserve the consumer's normal add-row focus behavior.
	if (wasMenuOpen) {
		await nextTick();
		primaryMenuButtonRef.value?.focus({ preventScroll: true });
	}
}

function loadPrimaryActionPreference() {
	const options = resolvedActionOptions.value;
	const fallback = options.some((action) => action.id === props.defaultPrimaryAction)
		? props.defaultPrimaryAction
		: options[0]?.id || "";
	let preferred = fallback;
	try {
		if (typeof window !== "undefined" && props.preferenceKey) {
			const stored = window.localStorage.getItem(props.preferenceKey);
			if (options.some((action) => action.id === stored)) preferred = stored;
		}
	} catch {
		// Local storage can be disabled by privacy settings; use the default action for this session.
	}
	selectedPrimaryActionId.value = preferred;
}

async function setPrimaryAction(actionId) {
	if (!resolvedActionOptions.value.some((action) => action.id === actionId)) return;
	selectedPrimaryActionId.value = actionId;
	closeActionMenus();
	try {
		if (typeof window !== "undefined" && props.preferenceKey) {
			window.localStorage.setItem(props.preferenceKey, actionId);
		}
	} catch {
		// The preference still applies in this component session if persistence is unavailable.
	}
	emit("primary-action-change", actionId);
	await nextTick();
	primaryMenuButtonRef.value?.focus();
}

function selectAllFilteredRows() {
	const keys = filteredRows.value.map((entry) => entry.key);
	setSelectedKeys([...new Set([...selectedKeys.value, ...keys])]);
}

function clearSelection() {
	setSelectedKeys([]);
}

function requestBulkDelete() {
	if (props.readOnly || !selectedRows.value.length) return;
	emit("bulk-delete", selectedRows.value);
}

function emitRowsUpdate(nextRows) {
	if (props.rows !== null) emit("update:rows", nextRows);
	if (props.modelValue !== null) emit("update:modelValue", nextRows);
}

async function copySelectedRows() {
	const selected = sourceRows.value
		.filter((entry) => selectedKeys.value.has(entry.key))
		.map((entry) => entry.row);
	if (!selected.length || !canCopyPaste.value) return;

	const text = JSON.stringify(
		{ format: GRID_CLIPBOARD_FORMAT, version: 1, rows: selected },
		null,
		2
	);
	internalClipboard.value = text;
	try {
		if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) {
			throw new Error("Clipboard API is not available in this context.");
		}
		await navigator.clipboard.writeText(text);
		feedback.value = __('Copied {0} row(s) to the clipboard.', [selected.length]);
	} catch (error) {
		feedback.value = __('Copied {0} row(s) locally; browser clipboard access is unavailable.', [
			selected.length,
		]);
		emit("clipboard-error", error);
	}
	emit("copy", selected);
}

function clonePastedRow(row, index) {
	try {
		if (typeof props.cloneRow === "function") return props.cloneRow(row, index);
		const clone = JSON.parse(JSON.stringify(row));
		if (clone && typeof clone === "object" && clone[props.rowKey] !== undefined) {
			clone[props.rowKey] = "pasted-" + Date.now() + "-" + index + "-" + Math.random().toString(36).slice(2, 7);
		}
		if (clone && typeof clone === "object" && "isEditing" in clone) clone.isEditing = false;
		return clone;
	} catch (error) {
		emit("clipboard-error", error);
		return null;
	}
}

async function pasteRows() {
	if (props.readOnly || !canCopyPaste.value) return;
	let clipboardText = "";
	try {
		if (typeof navigator !== "undefined" && navigator.clipboard?.readText) {
			clipboardText = await navigator.clipboard.readText();
		}
	} catch (error) {
		emit("clipboard-error", error);
	}
	let incoming = parseClipboardRows(clipboardText);
	if (!incoming.length) incoming = parseClipboardRows(internalClipboard.value);
	if (!incoming.length) {
		feedback.value = __("Clipboard does not contain compatible grid rows.");
		return;
	}

	const clonedRows = incoming.map((row, index) => clonePastedRow(row, index)).filter(Boolean);
	if (!clonedRows.length) {
		feedback.value = __("No compatible rows could be pasted.");
		return;
	}
	const nextRows = [...sourceList.value];
	const selectedIndexes = sourceRows.value
		.filter((entry) => selectedKeys.value.has(entry.key))
		.map((entry) => entry.index);
	const insertIndex = selectedIndexes.length
		? Math.max(...selectedIndexes) + 1
		: nextRows.length;
	nextRows.splice(insertIndex, 0, ...clonedRows);
	searchQuery.value = "";
	emitRowsUpdate(nextRows);
	await nextTick();

	const nextKeys = sourceRows.value
		.filter((entry) => entry.index >= insertIndex && entry.index < insertIndex + clonedRows.length)
		.map((entry) => entry.key);
	setSelectedKeys(nextKeys);
	if (props.pagination) currentPage.value = Math.floor(insertIndex / currentPageSize.value) + 1;
	feedback.value = __('Pasted {0} row(s).', [clonedRows.length]);
	emit("paste", { rows: clonedRows, insertIndex });
}

function goToIndex(index) {
	const targetIndex = Math.max(0, Math.floor(Number(index) || 0));
	searchQuery.value = "";
	if (props.pagination) currentPage.value = Math.floor(targetIndex / currentPageSize.value) + 1;
	rootRef.value?.focus({ preventScroll: true });
}

async function toggleSearch() {
	if (searchOpen.value) {
		closeSearch();
		return;
	}
	searchOpen.value = true;
	await nextTick();
	searchInputRef.value?.focus();
}

function closeSearch() {
	searchOpen.value = false;
	searchQuery.value = "";
}

function changePage(page) {
	const nextPage = Math.max(1, Math.min(pageCount.value, Math.floor(Number(page) || 1)));
	currentPage.value = nextPage;
	emit("page-change", { page: nextPage, pageSize: currentPageSize.value });
}

function changePageSize(value) {
	currentPageSize.value = normalizePageSize(value);
	emit("page-change", { page: 1, pageSize: currentPageSize.value });
}

function isInputTarget(target) {
	return Boolean(
		target?.closest?.(
			"input, textarea, select, [contenteditable='true'], [role='textbox'], [role='combobox']"
		)
	);
}

function matchesShortcut(event, shortcut) {
	const keys = String(shortcut || "")
		.toLowerCase()
		.split("+")
		.map((key) => key.trim())
		.filter(Boolean);
	if (!keys.length) return false;

	const key = keys[keys.length - 1];
	const wantsAlt = keys.includes("alt");
	const wantsCtrl = keys.includes("ctrl") || keys.includes("control");
	const wantsMeta = keys.includes("cmd") || keys.includes("meta") || keys.includes("command");
	const wantsShift = keys.includes("shift");
	return (
		event.key.toLowerCase() === key &&
		Boolean(event.altKey) === wantsAlt &&
		Boolean(event.ctrlKey) === wantsCtrl &&
		Boolean(event.metaKey) === wantsMeta &&
		Boolean(event.shiftKey) === wantsShift
	);
}

function getCurrentPageIndex(target) {
	const rowElement = target?.closest?.("[data-row-index]");
	const sourceIndex = rowElement
		? Number(rowElement.getAttribute("data-row-index"))
		: activeRowIndex.value;
	const focusedIndex = displayedRows.value.findIndex((entry) => entry.index === sourceIndex);
	if (focusedIndex >= 0) return focusedIndex;
	const selectedIndex = displayedRows.value.findIndex((entry) => selectedKeys.value.has(entry.key));
	return selectedIndex >= 0 ? selectedIndex : 0;
}

async function focusDisplayedRow(pageIndex) {
	const entry = displayedRows.value[pageIndex];
	if (!entry) {
		rootRef.value?.focus({ preventScroll: true });
		return;
	}
	activeRowIndex.value = entry.index;
	await nextTick();
	const selector =
		'.fxr-generic-grid-row[data-row-index="' +
		entry.index +
		'"] .fxr-generic-grid-row-index';
	rootRef.value?.querySelector(selector)?.focus({ preventScroll: true });
}

function toggleRowSelection(pageIndex, event = {}) {
	if (!props.selection) return;
	const entry = displayedRows.value[pageIndex];
	if (!entry) return;
	activeRowIndex.value = entry.index;
	if (event.shiftKey) {
		const anchor = keyboardSelectionAnchor.value ?? pageIndex;
		selectVisibleRange(anchor, pageIndex);
		return;
	}
	const next = new Set(selectedKeys.value);
	if (next.has(entry.key)) next.delete(entry.key);
	else next.add(entry.key);
	keyboardSelectionAnchor.value = pageIndex;
	setSelectedKeys([...next]);
}

async function moveRowFocus(delta, event) {
	if (!displayedRows.value.length) return;
	const originalPage = currentPage.value;
	const currentIndex = getCurrentPageIndex(event.target);
	let nextIndex = currentIndex + delta;
	if (nextIndex < 0 && props.pagination && currentPage.value > 1) {
		changePage(currentPage.value - 1);
		await nextTick();
		nextIndex = Math.max(0, displayedRows.value.length - 1);
		keyboardSelectionAnchor.value = null;
	} else if (
		nextIndex >= displayedRows.value.length &&
		props.pagination &&
		currentPage.value < pageCount.value
	) {
		changePage(currentPage.value + 1);
		await nextTick();
		nextIndex = 0;
		keyboardSelectionAnchor.value = null;
	} else {
		nextIndex = Math.max(0, Math.min(displayedRows.value.length - 1, nextIndex));
	}
	if (event.shiftKey && originalPage === currentPage.value) {
		const anchor = keyboardSelectionAnchor.value ?? currentIndex;
		keyboardSelectionAnchor.value = anchor;
		selectVisibleRange(anchor, nextIndex);
	} else if (!event.shiftKey) {
		keyboardSelectionAnchor.value = nextIndex;
	}
	await focusDisplayedRow(nextIndex);
}

async function handleKeydown(event) {
	if (!isDataGrid.value) return;

	const target = event.target;
	// Menu keyboard events belong to the open menu, not the grid's row shortcuts.
	if (target?.closest?.(".fxr-grid-menu")) return;

	if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "c") {
		if (!isInputTarget(target) && props.selection && selectedRows.value.length) {
			event.preventDefault();
			copySelectedRows();
		}
		return;
	}
	if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "v") {
		if (!isInputTarget(target) && !props.readOnly && canCopyPaste.value) {
			event.preventDefault();
			pasteRows();
		}
		return;
	}

	// Alt+E works while focus is inside an editable row as well as on the row itself.
	// This makes the edit/read toggle a quick action instead of requiring a pointer click.
	if (
		matchesShortcut(event, props.editShortcut) &&
		(!isInputTarget(target) || target?.closest?.("[data-row-index]"))
	) {
		if (props.readOnly) return;
		const selectedEntries = sourceRows.value.filter((entry) =>
			selectedKeys.value.has(entry.key)
		);
		const rowElement = target?.closest?.("[data-row-index]");
		const activeIndex = rowElement
			? Number(rowElement.getAttribute("data-row-index"))
			: activeRowIndex.value;
		const activeEntry = sourceRows.value.find((entry) => entry.index === activeIndex);
		const targetEntries = selectedEntries.length
			? selectedEntries
			: activeEntry
				? [activeEntry]
				: [];
		if (targetEntries.length) {
			event.preventDefault();
			const action = getBulkEditAction(
				targetEntries.map((entry) => entry.row),
				props.editStateKey
			);
			for (const entry of targetEntries) requestRowAction(action, entry);
		}
		return;
	}

	// Alt+Enter always invokes whichever action is currently pinned as primary.
	if (
		activePrimaryAction.value &&
		!props.readOnly &&
		matchesShortcut(event, props.primaryActionShortcut) &&
		!isInputTarget(target)
	) {
		event.preventDefault();
		const rowElement = target?.closest?.("[data-row-index]");
		const activeIndex = rowElement
			? Number(rowElement.getAttribute("data-row-index"))
			: activeRowIndex.value;
		const selectedIndexes = sourceRows.value
			.filter((entry) => selectedKeys.value.has(entry.key))
			.map((entry) => entry.index);
		requestPrimaryAction(
			Number.isInteger(activeIndex) && activeIndex >= 0
				? activeIndex
				: selectedIndexes.length
					? Math.max(...selectedIndexes)
					: null
		);
		return;
	}

	// Action-specific shortcuts work for secondary actions too, not just the pinned action.
	if (!isInputTarget(target)) {
		const shortcutAction = resolvedActionOptions.value.find(
			(action) => action.shortcut && matchesShortcut(event, action.shortcut)
		);
		if (shortcutAction) {
			event.preventDefault();
			requestGridAction(shortcutAction);
			return;
		}
	}

	if (
		props.keyboardNavigation &&
		!isInputTarget(target) &&
		!event.altKey &&
		!event.ctrlKey &&
		!event.metaKey
	) {
		if (event.key === "ArrowDown" || event.key === "ArrowUp") {
			event.preventDefault();
			await moveRowFocus(event.key === "ArrowDown" ? 1 : -1, event);
			return;
		}
		if (event.key === "Home" || event.key === "End") {
			event.preventDefault();
			const boundaryIndex = event.key === "Home" ? 0 : displayedRows.value.length - 1;
			await focusDisplayedRow(boundaryIndex);
			keyboardSelectionAnchor.value = boundaryIndex;
			return;
		}
		if (event.key === "PageDown" || event.key === "PageUp") {
			if (props.pagination && pageCount.value > 1) {
				event.preventDefault();
				const nextPage = event.key === "PageDown" ? currentPage.value + 1 : currentPage.value - 1;
				changePage(nextPage);
				await nextTick();
				await focusDisplayedRow(event.key === "PageDown" ? 0 : displayedRows.value.length - 1);
				keyboardSelectionAnchor.value = null;
				return;
			}
		}
		if (event.key === " " && target?.closest?.(".fxr-generic-grid-row-index")) {
			event.preventDefault();
			toggleRowSelection(getCurrentPageIndex(target), event);
			return;
		}
	}
}

defineExpose({
	copySelectedRows,
	pasteRows,
	selectedRows,
	goToIndex,
});
</script>

<style scoped>
.fxr-generic-grid {
	min-width: 0;
	font-family: var(--fxr-font-family, inherit);
	color: var(--fxr-text, inherit);
}

.fxr-generic-grid-layout {
	display: grid;
	grid-template-columns: repeat(
		auto-fit,
		minmax(min(100%, var(--fxr-generic-grid-min-column-width, 240px)), 1fr)
	);
	gap: var(--fxr-generic-grid-gap, var(--fxr-space-3, 12px));
	align-items: start;
}

.fxr-generic-grid-layout > * {
	min-width: 0;
}

.fxr-generic-grid-data {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2, 8px);
	outline: none;
}

.fxr-generic-grid-footer,
.fxr-generic-grid-footer-primary,
.fxr-generic-grid-bulk-actions,
.fxr-generic-grid-footer-actions {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-2, 8px);
	min-width: 0;
}

.fxr-generic-grid-footer {
	justify-content: space-between;
	flex-wrap: wrap;
	padding-top: var(--fxr-space-2, 8px);
}

.fxr-generic-grid-footer-primary {
	display: flex;
	align-items: center;
	gap: 0;
	flex: 0 0 auto;
}

.fxr-generic-grid-bulk-actions {
	flex: 1 1 auto;
	flex-wrap: wrap;
}

.fxr-generic-grid-footer-actions {
	justify-content: flex-end;
	flex-wrap: wrap;
	margin-left: auto;
}

.fxr-grid-menu {
	position: relative;
	display: inline-flex;
	align-items: center;
	flex: 0 0 auto;
}

.fxr-grid-menu-toggle {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: var(--fxr-space-1, 4px);
	min-height: 30px;
	padding: 0 var(--fxr-space-2, 8px);
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	background: transparent;
	color: var(--fxr-text-secondary, #4b5563);
	font: inherit;
	font-size: var(--fxr-text-sm, 12px);
	font-weight: var(--fxr-weight-medium, 500);
	line-height: 1;
	cursor: pointer;
}

.fxr-generic-grid-footer-primary > .fxr-grid-button--primary {
	border-top-right-radius: 0;
	border-bottom-right-radius: 0;
}

.fxr-grid-primary-menu {
	margin-left: -1px;
}

.fxr-generic-grid-footer-primary > .fxr-grid-button--primary,
.fxr-grid-primary-menu .fxr-grid-menu-toggle {
	box-sizing: border-box;
	min-height: 30px;
}

.fxr-grid-primary-menu .fxr-grid-menu-toggle {
	min-height: 30px;
	padding: 0 var(--fxr-space-2, 8px);
	border-color: var(--fxr-border-subtle, #d1d5db);
	border-top-left-radius: 0;
	border-bottom-left-radius: 0;
	background: transparent;
	color: var(--fxr-accent, #2563eb);
}

.fxr-grid-primary-menu .fxr-grid-menu-toggle:hover {
	background: var(--fxr-accent-light, #eff6ff);
	border-color: var(--fxr-border-strong, #9ca3af);
	color: var(--fxr-accent, #2563eb);
}

.fxr-grid-menu-items {
	position: absolute;
	z-index: 100;
	bottom: calc(100% + 6px);
	min-width: 210px;
	max-width: min(300px, calc(100vw - 24px));
	padding: 5px;
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-surface, #fff);
	box-shadow: 0 8px 28px rgb(15 23 42 / 16%);
}

.fxr-grid-menu-items--left {
	left: 0;
}

.fxr-grid-menu-items--right {
	right: 0;
}

.fxr-grid-menu-heading {
	padding: 6px 8px 7px;
	color: var(--fxr-text-muted, #6b7280);
	font-size: var(--fxr-text-xs, 11px);
	font-weight: var(--fxr-weight-semibold, 600);
}

.fxr-grid-menu-item {
	display: flex;
	align-items: center;
	flex: 1 1 auto;
	gap: 8px;
	width: auto;
	min-width: 0;
	min-height: 32px;
	padding: 6px 8px;
	border: 0;
	border-radius: var(--fxr-radius-sm, 4px);
	background: transparent;
	color: var(--fxr-text, #111827);
	font: inherit;
	font-size: var(--fxr-text-sm, 12px);
	text-align: left;
	cursor: pointer;
}

.fxr-grid-menu-action-row {
	display: flex;
	align-items: stretch;
	gap: 3px;
	min-width: 0;
	border-radius: var(--fxr-radius-sm, 4px);
}

.fxr-grid-menu-action-row:hover {
	background: var(--fxr-surface-soft, #f3f4f6);
}

.fxr-grid-menu-item span {
	flex: 1;
	min-width: 0;
}

.fxr-grid-menu-pin {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex: 0 0 30px;
	width: 30px;
	min-height: 32px;
	border: 1px solid transparent;
	border-radius: var(--fxr-radius-sm, 4px);
	background: transparent;
	color: var(--fxr-text-muted, #6b7280);
	cursor: pointer;
}

.fxr-grid-menu-pin:hover,
.fxr-grid-menu-pin[aria-pressed="true"] {
	background: var(--fxr-accent-soft, #eff6ff);
	color: var(--fxr-accent, #2563eb);
}

.fxr-grid-menu-item:hover,
.fxr-grid-menu-item:focus-visible,
.fxr-grid-menu-item.is-active {
	background: var(--fxr-surface-soft, #f3f4f6);
}

.fxr-grid-menu-item.is-current {
	color: var(--fxr-accent, #2563eb);
	font-weight: var(--fxr-weight-semibold, 600);
}

.fxr-grid-button--danger {
	border-color: var(--fxr-border-danger, #dc2626);
	color: var(--fxr-text-danger, #b91c1c);
}

.fxr-grid-button--danger:hover:not(:disabled) {
	background: var(--fxr-surface-danger, #fef2f2);
	border-color: var(--fxr-border-danger, #dc2626);
	color: var(--fxr-text-danger, #b91c1c);
}

.fxr-generic-grid-search-popover {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-2, 8px);
	flex: 1 1 190px;
	min-width: 140px;
	max-width: 260px;
	padding: 0 var(--fxr-space-2, 8px);
	border: 1px solid var(--fxr-border, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-bg-input, #fff);
	color: var(--fxr-text-muted, #6b7280);
}

.fxr-generic-grid-search-popover input {
	width: 100%;
	min-width: 0;
	height: 30px;
	padding: 0;
	border: 0;
	outline: 0;
	background: transparent;
	color: var(--fxr-text, #111827);
	font: inherit;
	font-size: var(--fxr-text-sm, 12px);
}

.fxr-generic-grid-data:focus-visible {
	border-radius: var(--fxr-radius-md, 6px);
	outline: 2px solid var(--fxr-border-focus, #3b82f6);
	outline-offset: 2px;
}


.fxr-generic-grid-selection-count,
.fxr-generic-grid-page-summary,
.fxr-generic-grid-page-actions > span {
	color: var(--fxr-text-muted, #6b7280);
	font-size: var(--fxr-text-xs, 11px);
	white-space: nowrap;
}

.fxr-grid-button,
.fxr-grid-icon-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: var(--fxr-space-1, 4px);
	min-height: 28px;
	padding: 3px var(--fxr-space-2, 8px);
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-sm, 4px);
	background: var(--fxr-surface, #fff);
	color: var(--fxr-text-secondary, #4b5563);
	font: inherit;
	font-size: var(--fxr-text-xs, 11px);
	cursor: pointer;
	transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
}

.fxr-grid-button--quiet {
	background: transparent;
	border-color: transparent;
}

.fxr-grid-button--primary {
	min-height: 30px;
	border-color: var(--fxr-border-subtle, #d1d5db);
	background: transparent;
	color: var(--fxr-accent, #2563eb);
	font-weight: var(--fxr-weight-medium, 500);
	box-shadow: none;
}

.fxr-grid-icon-button--secondary {
	border-color: transparent;
	background: transparent;
	color: var(--fxr-text-muted, #6b7280);
}

.fxr-grid-button:hover:not(:disabled),
.fxr-grid-icon-button:hover:not(:disabled) {
	border-color: var(--fxr-border-strong, #9ca3af);
	background: var(--fxr-surface-soft, #f9fafb);
	color: var(--fxr-text, #111827);
}

.fxr-grid-button--primary:hover:not(:disabled) {
	border-color: var(--fxr-border-strong, #9ca3af);
	background: var(--fxr-accent-light, #eff6ff);
	color: var(--fxr-accent, #2563eb);
}

.fxr-grid-button:disabled,
.fxr-grid-icon-button:disabled {
	opacity: 0.35;
	cursor: default;
}

.fxr-grid-button:focus-visible,
.fxr-grid-icon-button:focus-visible,
.fxr-grid-menu-toggle:focus-visible,
.fxr-generic-grid-row-index:focus-visible {
	outline: 2px solid var(--fxr-border-focus, #3b82f6);
	outline-offset: 1px;
}

.fxr-generic-grid-rows {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3, 12px);
	min-width: 0;
}

.fxr-generic-grid-data.is-compact .fxr-generic-grid-rows {
	gap: var(--fxr-space-1, 4px);
}

.fxr-generic-grid-row {
	display: grid;
	grid-template-columns: 22px minmax(0, 1fr) auto;
	column-gap: var(--fxr-space-2, 8px);
	row-gap: var(--fxr-space-1, 4px);
	align-items: start;
	min-width: 0;
	padding: var(--fxr-space-1, 4px) var(--fxr-space-2, 8px);
	border: 1px solid var(--fxr-border-subtle, #e5e7eb);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-surface, #fff);
	transition: border-color 120ms ease, background-color 120ms ease, box-shadow 120ms ease;
}

.fxr-generic-grid-row-toolbar {
	display: contents;
}

.fxr-generic-grid-row-index {
	grid-column: 1;
	grid-row: 1;
	align-self: start;
	margin-top: 1px;
}

.fxr-generic-grid-row-actions {
	grid-column: 3;
	grid-row: 1;
	align-self: start;
	max-width: 100%;
}

.fxr-generic-grid-row-body {
	grid-column: 2;
	grid-row: 1;
	min-width: 0;
}

.fxr-generic-grid-row-summary {
	grid-column: 2;
	grid-row: 1;
	min-width: 0;
}

.fxr-generic-grid-row-body {
	min-width: 0;
}

.fxr-generic-grid-row.is-editing {
	grid-template-columns: 22px minmax(0, 1fr) auto;
	padding: var(--fxr-space-2, 8px);
}

.fxr-generic-grid-row.is-editing .fxr-generic-grid-row-actions {
	grid-column: 3;
	grid-row: 1;
	justify-self: end;
}

.fxr-generic-grid-row.is-editing .fxr-generic-grid-row-body {
	grid-column: 1 / -1;
	grid-row: 2;
}
.fxr-generic-grid-row.is-selected {
	border-color: var(--fxr-border-focus, #3b82f6);
	background: var(--fxr-accent-soft, #eff6ff);
	box-shadow: inset 0 0 0 1px var(--fxr-border-focus, #3b82f6);
}

.fxr-generic-grid-row.is-invalid {
	border-color: var(--fxr-border-danger, #dc2626);
	box-shadow: inset 3px 0 0 var(--fxr-border-danger, #dc2626);
}

.fxr-generic-grid-row.is-invalid .fxr-generic-grid-row-index {
	border-color: var(--fxr-border-danger, #dc2626);
	color: var(--fxr-text-danger, #b91c1c);
}

.fxr-generic-grid-row.is-editing {
	background: var(--fxr-surface-soft, #f9fafb);
}

.fxr-generic-grid-row-index {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex: 0 0 22px;
	width: 22px;
	min-height: 22px;
	padding: 0;
	border: 1px solid var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-sm, 4px);
	background: var(--fxr-surface-soft, #f9fafb);
	color: var(--fxr-text-muted, #6b7280);
	font-size: var(--fxr-text-xs, 11px);
	font-weight: var(--fxr-weight-medium, 500);
	cursor: pointer;
	user-select: none;
	-webkit-user-select: none;
	touch-action: none;
}

.fxr-generic-grid-row-index.is-selected {
	border-color: var(--fxr-border-focus, #3b82f6);
	background: var(--fxr-accent, #2563eb);
	color: #fff;
}

.fxr-generic-grid-row-actions {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 1px;
	min-width: 0;
}

.fxr-grid-icon-button {
	flex: 0 0 25px;
	width: 25px;
	height: 25px;
	min-height: 25px;
	padding: 0;
	border-color: transparent;
	background: transparent;
}

.fxr-grid-icon-button.is-danger:hover:not(:disabled) {
	border-color: var(--fxr-border-danger, #dc2626);
	color: var(--fxr-text-danger, #b91c1c);
}

.fxr-generic-grid-reorder {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 0;
	flex: 0 0 25px;
}

.fxr-generic-grid-reorder .fxr-grid-icon-button {
	width: 25px;
	height: 18px;
	min-height: 18px;
}

.fxr-generic-grid-row-fallback {
	overflow-wrap: anywhere;
	font-size: var(--fxr-text-sm, 12px);
}

.fxr-generic-grid-empty {
	padding: var(--fxr-space-3, 12px);
	border: 1px dashed var(--fxr-border-subtle, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	color: var(--fxr-text-muted, #6b7280);
	font-size: var(--fxr-text-sm, 12px);
	text-align: center;
}

.fxr-generic-grid-pagination,
.fxr-generic-grid-page-actions {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: var(--fxr-space-2, 8px);
	min-width: 0;
}

.fxr-generic-grid-pagination {
	justify-content: space-between;
	padding-top: var(--fxr-space-1, 4px);
}

.fxr-generic-grid-page-size {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-2, 8px);
	color: var(--fxr-text-muted, #6b7280);
	font-size: var(--fxr-text-xs, 11px);
}

.fxr-generic-grid-page-size select {
	min-height: 27px;
	padding: 2px 6px;
	border: 1px solid var(--fxr-border, #d1d5db);
	border-radius: var(--fxr-radius-sm, 4px);
	background: var(--fxr-bg-input, #fff);
	color: var(--fxr-text, #111827);
	font: inherit;
}

.fxr-generic-grid-page-actions {
	margin-left: auto;
}

.fxr-generic-grid-feedback {
	margin: 0;
	color: var(--fxr-text-muted, #6b7280);
	font-size: var(--fxr-text-xs, 11px);
	line-height: 1.4;
}

@media (max-width: 480px) {
	.fxr-generic-grid-row {
		grid-template-columns: 22px minmax(0, 1fr);
		column-gap: var(--fxr-space-2, 8px);
	}

	.fxr-generic-grid-row-actions {
		grid-column: 2;
		grid-row: 2;
		justify-self: start;
		flex-wrap: wrap;
	}

	.fxr-generic-grid-row-body {
		grid-column: 1 / -1;
		grid-row: 3;
	}

	.fxr-generic-grid-row-summary {
		grid-column: 2;
		grid-row: 1;
	}

	.fxr-generic-grid-row.is-editing .fxr-generic-grid-row-actions {
		grid-column: 2;
		grid-row: 2;
		justify-self: start;
	}

	.fxr-generic-grid-row.is-editing .fxr-generic-grid-row-body {
		grid-column: 1 / -1;
		grid-row: 3;
	}
}

@media (max-width: 600px) {
	.fxr-generic-grid-footer {
		align-items: flex-end;
	}
	.fxr-generic-grid-footer-actions {
		gap: 4px;
	}
	.fxr-generic-grid-row-actions {
		gap: 0;
	}
	.fxr-generic-grid-pagination {
		align-items: flex-start;
		flex-direction: column;
	}
	.fxr-generic-grid-page-actions {
		margin-left: 0;
	}
	.fxr-generic-grid-footer {
		align-items: flex-start;
	}
	.fxr-generic-grid-footer-actions {
		width: 100%;
		justify-content: flex-end;
	}
	.fxr-generic-grid-bulk-actions {
		flex-basis: 100%;
		order: 3;
	}
	.fxr-generic-grid-footer-primary {
		order: 1;
	}
	.fxr-generic-grid-footer-actions {
		order: 2;
	}
}
</style>
