<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { getOperationOptions, isTerminalAction } from "../../core/contracts";
import { useStore } from "../stores";
import { mapActionTypeToNodeType } from "../composables/useActionTypeMapper";
import { useActionSearch } from "../composables/useActionSearch";

const props = defineProps({
	// discovery props
	placeholder: {
		type: String,
		default: () =>
			window.__
				? __("Search actions or type Action: operation")
				: "Search actions or type Action: operation",
	},
	showPaste: {
		type: Boolean,
		default: true,
	},
	autoFocus: {
		type: Boolean,
		default: true,
	},
	// context props
	mode: {
		type: String,
		default: "popover", // 'popover' | 'node' | 'inline'
	},
	// node-mode specific props
	id: String,
	data: Object,
	selected: Boolean,
	sourcePosition: String,
	targetPosition: String,
	// popover-mode specific props
	position: Object, // { x, y }
});

const emit = defineEmits(["select", "paste", "close"]);
const store = useStore();

const {
	searchQuery,
	filteredResults,
	canPaste,
	loadProcessOperations,
	checkClipboard,
	isSearchingRemote,
} = useActionSearch();

const selectedIndex = ref(-1);
const searchInputRef = ref(null);
const zoneRef = ref(null);
const popoverRef = ref(null);

// Node mode state
const customLabel = ref("");
const selectedPreset = ref({
	action_type: "Process",
	operation: null,
	process_name: null,
	selected_label: "Process",
});

const isHorizontal = computed(() => store.settings?.layout_direction !== "Top to Bottom");
const targetPos = computed(
	() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
);
const sourcePos = computed(
	() => props.sourcePosition || (isHorizontal.value ? Position.Right : Position.Bottom)
);

function selectItem(item) {
	if (item.type === "header") return;
	if (item.type === "scope_action") {
		searchQuery.value = `${item.value}: `;
		selectedIndex.value = -1;
		nextTick(() => searchInputRef.value?.focus());
		return;
	}
	if (item.type === "paste_discovery") {
		onPasteClick();
		return;
	}

	const selection = {
		action_type: item.value || item.action_type || "Process",
		operation: item.operation || null,
		process_name: item.process_name || null,
		label: item.label || item.value || "Process",
	};

	if (props.mode === "node") {
		selectedPreset.value = {
			action_type: selection.action_type,
			operation: selection.operation,
			process_name: selection.process_name,
			selected_label: selection.label,
		};
		// in node mode, we often don't want to auto-create, but we can if ENTER is pressed
	} else {
		emit("select", selection);
	}
}

function nextSelectableIndex(startIndex, direction) {
	const total = filteredResults.value.length;
	if (!total) return -1;
	let index = startIndex;
	for (let step = 0; step < total; step++) {
		index = (index + direction + total) % total;
		if (filteredResults.value[index]?.type !== "header") return index;
	}
	return -1;
}

function onKeydown(e) {
	if (e.key === "Escape") emit("close");

	if (e.key === "ArrowDown") {
		if (!filteredResults.value.length) return;
		e.preventDefault();
		selectedIndex.value = nextSelectableIndex(selectedIndex.value, 1);
		scrollToActive();
	} else if (e.key === "ArrowUp") {
		if (!filteredResults.value.length) return;
		e.preventDefault();
		selectedIndex.value = nextSelectableIndex(selectedIndex.value, -1);
		scrollToActive();
	} else if (e.key === "Enter") {
		if (selectedIndex.value !== -1) {
			e.preventDefault();
			selectItem(filteredResults.value[selectedIndex.value]);
			if (props.mode === "node") {
				// in node mode, Enter on a result selects it.
				// Enter on the "Create" button (below) triggers creation.
			}
		} else if (props.mode === "node" && customLabel.value) {
			onCreate();
		}
	}
}

function scrollToActive() {
	nextTick(() => {
		const activeItem = zoneRef.value?.querySelector(".result-item.active");
		if (activeItem) {
			activeItem.scrollIntoView({ block: "nearest" });
		}
	});
}

function onPasteClick() {
	emit("paste");
}

function onCreate() {
	if (props.mode !== "node") return;
	const nodeIndex = store.nodes.findIndex((n) => n.id === props.id);
	if (nodeIndex === -1) return;

	const action_type = selectedPreset.value.action_type || "Process";
	const label =
		customLabel.value ||
		selectedPreset.value.operation ||
		selectedPreset.value.selected_label ||
		action_type;
	const nodeType = mapActionTypeToNodeType(action_type);
	const node = store.nodes[nodeIndex];
	if (!node) return;

	const nodeData = store.get_default_node_data(action_type.toLowerCase(), label);
	const suggestedParentId = node.data?.suggested_parent_id;
	const suggestedSourceHandle = node.data?.suggested_source_handle || "default";

	if (selectedPreset.value.operation) nodeData.operation = selectedPreset.value.operation;
	if (selectedPreset.value.process_name)
		nodeData.process_name = selectedPreset.value.process_name;

	if (action_type === "Process" && nodeData.operation && !nodeData.process_name) {
		const matches = getOperationOptions("Process", {})
			.filter((op) => op.value === nodeData.operation && op.process_name)
			.map((op) => op.process_name);
		const unique = [...new Set(matches)];
		if (unique.length === 1) nodeData.process_name = unique[0];
	}

	store.nodes[nodeIndex].type = nodeType;
	store.nodes[nodeIndex].label = label;
	store.nodes[nodeIndex].data = {
		...nodeData,
		action_id: props.id,
		action_label: label,
		next_step_if_true: node.data?.next_step_if_true || nodeData.next_step_if_true,
		next_step_if_false: node.data?.next_step_if_false || nodeData.next_step_if_false,
	};

	if (suggestedParentId) {
		const edgeId = `e-${suggestedParentId}-${props.id}-${suggestedSourceHandle}`;
		const hasIncoming = store.edges.some((edge) => edge.target === props.id);
		if (!hasIncoming) {
			store.edges.push({
				id: edgeId,
				source: suggestedParentId,
				target: props.id,
				sourceHandle: suggestedSourceHandle,
				animated: suggestedParentId === "root",
			});
		}
	}

	if (isTerminalAction(action_type)) {
		store.edges = store.edges.filter((edge) => edge.source !== props.id);
		store.nodes[nodeIndex].data.next_step_if_true = null;
		store.nodes[nodeIndex].data.next_step_if_false = null;
	}

	store.select(props.id);
	store.show_sidebar = true;
	store.touch_node(props.id);
	store.mark_dirty();
}

function deleteNode() {
	if (props.mode === "node") {
		frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
	}
}

function onClickOutside(e) {
	if (props.mode === "popover" && popoverRef.value && !popoverRef.value.contains(e.target)) {
		emit("close");
	}
}

onMounted(() => {
	loadProcessOperations();
	checkClipboard();
	if (props.mode === "popover") {
		document.addEventListener("mousedown", onClickOutside);
	}
	if (props.autoFocus) {
		setTimeout(() => searchInputRef.value?.focus(), 100);
	}
});

onUnmounted(() => {
	if (props.mode === "popover") {
		document.removeEventListener("mousedown", onClickOutside);
	}
});

defineExpose({
	focus: () => searchInputRef.value?.focus(),
	clear: () => (searchQuery.value = ""),
});
</script>

<template>
	<!-- Popover Mode Wrapper -->
	<div
		v-if="mode === 'popover'"
		ref="popoverRef"
		class="action-popover"
		:style="{
			left: position.x + 'px',
			top: position.y + 'px',
		}"
	>
		<div class="popover-header">
			<i class="fa fa-plus-circle"></i>
			<span>{{ __("Add Action") }}</span>
		</div>
		<div ref="zoneRef" class="action-zone" @keydown="onKeydown">
			<div class="popover-search">
				<i :class="['fa', isSearchingRemote ? 'fa-spinner fa-spin' : 'fa-search']"></i>
				<input
					ref="searchInputRef"
					type="text"
					v-model="searchQuery"
					:placeholder="placeholder"
					class="form-control"
					autocomplete="off"
				/>
			</div>
			<div class="popover-body" @wheel.stop>
				<div
					v-if="showPaste && canPaste"
					class="result-item is-option paste-option"
					@mousedown.prevent="onPasteClick"
				>
					<div class="item-icon" style="color: var(--blue-500, #3b82f6)">
						<i class="fa fa-paste"></i>
					</div>
					<div class="item-content">
						<div class="item-label">{{ __("Paste Action") }}</div>
						<div class="item-desc">{{ __("Insert from clipboard") }}</div>
					</div>
				</div>

				<div v-if="!filteredResults.length && !canPaste" class="no-results">
					{{ __("No matching actions found") }}
				</div>

				<div
					v-for="(item, idx) in filteredResults"
					:key="idx"
					:class="[
						'result-item',
						item.type === 'header' ? 'is-header' : 'is-option',
						{ active: idx === selectedIndex },
					]"
					@mousedown.prevent="selectItem(item)"
					@mouseover="selectedIndex = idx"
				>
					<template v-if="item.type === 'header'">
						{{ item.label }}
					</template>
					<template v-else>
						<div class="item-icon" :style="{ color: item.color }">
							<i :class="['fa', item.icon?.replace('fa ', '') || 'fa-cog']"></i>
						</div>
						<div class="item-content">
							<div class="item-label">{{ item.label }}</div>
							<div v-if="item.description" class="item-desc">
								{{ item.description }}
							</div>
						</div>
					</template>
				</div>
			</div>
		</div>
	</div>

	<!-- Node Mode Wrapper (VueFlow ActionSelectorNode) -->
	<div
		v-else-if="mode === 'node'"
		class="action-selector-card"
		:class="{ selected: selected, 'is-vertical': !isHorizontal }"
	>
		<Handle type="target" :position="targetPos" class="handle-target" />
		<div class="node-header">
			<i class="fa fa-plus-circle"></i>
			<span class="header-text">{{ __("New Action") }}</span>
			<button class="delete-btn" @click.stop="deleteNode" v-if="selected">
				<i class="fa fa-trash"></i>
			</button>
		</div>
		<div class="node-body">
			<div class="form-group search-group">
				<label class="small text-muted">{{ __("Action Type") }}</label>
				<div ref="zoneRef" class="search-wrapper action-zone" @keydown="onKeydown">
					<div class="popover-search">
						<i
							:class="['fa', isSearchingRemote ? 'fa-spinner fa-spin' : 'fa-search']"
						></i>
						<input
							ref="searchInputRef"
							type="text"
							v-model="searchQuery"
							class="form-control input-xs"
							:placeholder="placeholder"
							autocomplete="off"
						/>
					</div>
					<div class="popover-body" @wheel.stop>
						<div
							v-for="(item, idx) in filteredResults"
							:key="idx"
							:class="[
								'result-item',
								item.type === 'header' ? 'is-header' : 'is-option',
								{ active: idx === selectedIndex },
							]"
							@mousedown.prevent="selectItem(item)"
							@mouseover="selectedIndex = idx"
						>
							<template v-if="item.type === 'header'">
								{{ item.label }}
							</template>
							<template v-else>
								<div class="item-icon" :style="{ color: item.color }">
									<i
										:class="['fa', item.icon?.replace('fa ', '') || 'fa-cog']"
									></i>
								</div>
								<div class="item-content">
									<div class="item-label">{{ item.label }}</div>
									<div v-if="item.description" class="item-desc">
										{{ item.description }}
									</div>
								</div>
							</template>
						</div>
					</div>
					<div v-if="selectedPreset.operation" class="selected-operation-preview">
						<span class="badge-chip">{{ selectedPreset.action_type }}</span>
						<span class="selected-operation-text">{{ selectedPreset.operation }}</span>
						<span v-if="selectedPreset.process_name" class="selected-process-name">
							({{ selectedPreset.process_name }})
						</span>
					</div>
				</div>
			</div>
			<div class="form-group">
				<label class="small text-muted">{{ __("Label") }}</label>
				<input
					type="text"
					v-model="customLabel"
					class="form-control input-xs"
					:placeholder="__('Enter label...')"
					@keyup.enter="onCreate"
				/>
			</div>
			<button class="btn btn-primary btn-xs btn-block mt-2" @click="onCreate">
				{{ __("Create") }}
			</button>
		</div>
		<div class="node-footer">
			<span class="text-muted small">{{ __("Configure to proceed") }}</span>
		</div>
		<Handle type="source" :position="sourcePos" id="default" class="handle-source" />
	</div>

	<!-- Inline / Other Mode -->
	<div v-else ref="zoneRef" class="action-zone" @keydown="onKeydown">
		<!-- simple generic implementation -->
		<slot></slot>
	</div>
</template>

<style scoped>
/* Consolidated styles from ActionPopover and ActionSelectorNode */

.action-zone {
	display: flex;
	flex-direction: column;
	background: inherit;
	max-height: inherit;
}

.action-popover {
	position: fixed;
	width: 280px;
	max-height: 400px;
	background: #fff;
	background-color: var(--fxr-surface, #ffffff);
	border: 1px solid var(--border-color, #dfe3e8);
	border-radius: 8px;
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
	z-index: 2147483647;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.popover-header {
	padding: 10px 12px;
	background: #f8f9fa;
	border-bottom: 1px solid #f0f4f7;
	display: flex;
	align-items: center;
	gap: 8px;
	font-weight: 700;
	font-size: 11px;
	color: var(--primary, #3b82f6);
}

.popover-search {
	padding: 8px;
	position: relative;
	border-bottom: 1px solid #f0f4f7;
}

.popover-search i {
	position: absolute;
	left: 16px;
	top: 50%;
	transform: translateY(-50%);
	color: #adb5bd;
	font-size: 10px;
}

.popover-search input {
	padding-left: 28px !important;
	height: 32px;
	font-size: 12px;
	border-radius: 4px;
	border: 1px solid var(--border-color, #dfe3e8);
}

.popover-body {
	flex: 1;
	overflow-y: auto;
	padding: 4px 0;
}

.result-item {
	padding: 8px 12px;
	cursor: pointer;
}

.is-header {
	font-size: 10px;
	font-weight: 700;
	color: #94a3b8;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	padding: 12px 12px 4px;
	cursor: default;
	background: #fff;
	background-color: var(--fxr-surface, #ffffff);
	position: sticky;
	top: 0;
	z-index: 1;
}

.is-option {
	display: flex;
	align-items: center;
	gap: 10px;
	transition: background 0.1s;
}

.is-option:hover,
.is-option.active {
	background: #f1f5f9;
}

.item-icon {
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
}

.item-content {
	flex: 1;
	min-width: 0;
}

.item-label {
	font-size: 12px;
	font-weight: 500;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-desc {
	font-size: 10px;
	color: #64748b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.no-results {
	padding: 20px;
	text-align: center;
	color: #94a3b8;
	font-size: 12px;
}

.paste-option {
	border-bottom: 1px solid #f1f5f9;
	background: #f8fafc;
}

.paste-option:hover {
	background: #f1f5f9;
}

/* Node mode styles */

.action-selector-card {
	width: 260px;
	background: #fff;
	border: 2px dashed #d1d8dd;
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	transition: all 0.2s ease;
}

.action-selector-card.selected {
	border-color: var(--primary);
	border-style: solid;
	box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2);
}

.node-header {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid #f0f4f7;
	gap: 8px;
	background: #f8f9fa;
	border-radius: 8px 8px 0 0;
}

.node-header i {
	color: var(--primary);
	font-size: 14px;
}

.header-text {
	font-size: 11px;
	font-weight: 700;
	color: #6c757d;
	flex: 1;
}

.delete-btn {
	background: none;
	border: none;
	padding: 2px;
	cursor: pointer;
	color: #adb5bd;
}

.delete-btn:hover {
	color: #dc3545;
}

.node-body {
	padding: 12px;
	display: flex;
	flex-direction: column;
}

.search-wrapper {
	max-height: 280px;
	display: flex;
	flex-direction: column;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	padding-bottom: 4px;
	overflow: hidden;
}

.search-wrapper :deep(.popover-search) {
	border-bottom: 1px solid #f0f4f7;
}

.search-wrapper :deep(.popover-body) {
	max-height: 180px;
}

.form-group {
	margin-bottom: 8px;
}

.form-group label {
	display: block;
	margin-bottom: 2px;
}

.selected-operation-preview {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 6px 8px 0;
	flex-wrap: wrap;
}

.badge-chip {
	background: #eef2ff;
	color: #4338ca;
	border: 1px solid #c7d2fe;
	border-radius: 10px;
	padding: 1px 6px;
	font-size: 10px;
	font-weight: 700;
}

.selected-operation-text {
	font-size: 10px;
	font-weight: 600;
	color: #1f2937;
}

.selected-process-name {
	font-size: 10px;
	color: #6b7280;
}

.node-footer {
	padding: 6px 12px;
	background-color: #f8fcfd;
	border-bottom-left-radius: 8px;
	border-bottom-right-radius: 8px;
	border-top: 1px solid #f0f4f7;
	text-align: center;
}

.handle-target,
.handle-source {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid #d1d8dd !important;
	z-index: 10 !important;
}

/* Custom Scrollbar */
.popover-body::-webkit-scrollbar {
	width: 6px;
}
.popover-body::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 3px;
}
</style>
