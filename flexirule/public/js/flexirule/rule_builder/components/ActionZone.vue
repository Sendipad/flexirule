<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from "vue";
import { Handle, Position } from "@vue-flow/core";
import {
	getOperationOptions,
	isTerminalAction,
	getContract,
	getEffectiveActionPolicy,
	getFieldLabel,
} from "../../core/contracts";
import { useStore } from "../stores";
import { mapActionTypeToNodeType } from "../composables/useActionTypeMapper";
import { useActionSearch } from "../composables/useActionSearch";
import { useFloatingDropdown } from "../composables/useFloatingDropdown";
import ComboBoxControl from "../controls/ComboBoxControl.vue";
import NodeToolbar from "./nodes/NodeToolbar.vue";

const props = defineProps({
	// discovery props
	placeholder: {
		type: String,
		default: () =>
			window.__
				? __("Search actions or type Action: operation")
				: "Search actions or type Action: operation",
	},
	maxWidth: {
		type: Number,
		default: 320,
	},
	maxHeight: {
		type: Number,
		default: 450,
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
	trigger: Object, // HTMLElement
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
const labelInputRef = ref(null);
const zoneRef = ref(null);

const {
	triggerRef: popoverTriggerRef,
	dropdownRef: popoverDropdownRef,
	isOpen: isPopoverOpen,
	dropdownStyle: popoverStyle,
	openDropdown: openPopover,
	closeDropdown: closePopover,
	updatePosition: updatePopoverPosition,
} = useFloatingDropdown({
	minWidth: 320,
	maxWidth: 400,
	maxHeight: 500,
	matchTriggerWidth: false,
	offset: 0,
});

const step = ref("discovery"); // 'discovery' | 'labeling'
const customLabel = ref("");
const selectedItemData = ref(null);

const isHorizontal = computed(() => {
	const settings = store.settings?.value || store.settings;
	return settings?.layout_direction !== "Top to Bottom";
});
const targetPos = computed(
	() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
);
const sourcePos = computed(
	() => props.sourcePosition || (isHorizontal.value ? Position.Right : Position.Bottom)
);

function selectItem(item) {
	if (!item || item.type === "header") return;

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

	const action_type = item.action_type || item.value || "Process";
	const selection = {
		action_type,
		operation: item.operation || null,
		process_name: item.process_name || null,
		label: (item.label || item.value || action_type)
			.replace(`${action_type}: `, "")
			.replace("Process: ", ""),
		icon: item.icon || "fa-cog",
		color: item.color || "#6b7280",
	};

	selectedItemData.value = selection;
	customLabel.value = selection.label;
	step.value = "labeling";

	nextTick(() => {
		updatePopoverPosition();
		setTimeout(() => {
			if (labelInputRef.value) {
				labelInputRef.value.focus();
				labelInputRef.value.select();
			}
		}, 50);
	});
}

function nextSelectableIndex(startIndex, direction) {
	const total = filteredResults.value.length;
	if (!total) return -1;
	let index = startIndex;
	for (let stepCount = 0; stepCount < total; stepCount++) {
		index = (index + direction + total) % total;
		if (filteredResults.value[index]?.type !== "header") return index;
	}
	return -1;
}

function onKeydown(e) {
	if (e.key === "Escape") {
		if (step.value === "labeling") {
			goBack();
			e.stopPropagation();
		} else {
			emit("close");
		}
		return;
	}

	if (step.value === "discovery") {
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
		} else if (e.key === "Enter" && selectedIndex.value !== -1) {
			e.preventDefault();
			selectItem(filteredResults.value[selectedIndex.value]);
		}
	} else if (step.value === "labeling") {
		if (e.key === "Enter") {
			e.preventDefault();
			confirmSelection();
		}
	}
}

function goBack() {
	step.value = "discovery";
	selectedItemData.value = null;
	nextTick(() => searchInputRef.value?.focus());
}

function confirmSelection() {
	if (!selectedItemData.value) return;

	const payload = {
		...selectedItemData.value,
		label: (customLabel.value || selectedItemData.value.label).trim(),
	};

	if (props.mode === "node") {
		onCreate(payload);
	} else {
		emit("select", payload);
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

function onCreate(finalPayload = null) {
	if (props.mode !== "node") return;

	const nodes = store.nodes.value || store.nodes;
	const edges = store.edges.value || store.edges;

	const nodeIndex = nodes.findIndex((n) => n.id === props.id);
	if (nodeIndex === -1) {
		console.warn("[ActionZone] Node not found for upgrade:", props.id);
		return;
	}

	const selection =
		finalPayload ||
		(selectedItemData.value
			? {
					...selectedItemData.value,
					label: (customLabel.value || selectedItemData.value.label).trim(),
			  }
			: null);

	if (!selection) return;

	const action_type = selection.action_type;
	const label = selection.label;
	const nodeType = mapActionTypeToNodeType(action_type);
	const node = nodes[nodeIndex];

	console.log("[ActionZone] Upgrading node:", props.id, "to type:", action_type);

	const nodeData = store.get_default_node_data(action_type.toLowerCase(), label);
	const suggestedParentId = node.data?.suggested_parent_id;
	const suggestedSourceHandle = node.data?.suggested_source_handle || "default";

	if (selection.operation) nodeData.operation = selection.operation;
	if (selection.process_name) nodeData.process_name = selection.process_name;

	if (action_type === "Process" && nodeData.operation && !nodeData.process_name) {
		const matches = getOperationOptions("Process", {})
			.filter((op) => op.value === nodeData.operation && op.process_name)
			.map((op) => op.process_name);
		const unique = [...new Set(matches)];
		if (unique.length === 1) nodeData.process_name = unique[0];
	}

	// Preservation logic: upgrading a node should keep its current outputs unless it's becoming terminal
	const nextTrue = isTerminalAction(action_type)
		? null
		: node.data?.next_step_if_true || nodeData.next_step_if_true;
	const nextFalse = isTerminalAction(action_type)
		? null
		: node.data?.next_step_if_false || nodeData.next_step_if_false;

	const updatedNode = {
		...node,
		type: nodeType,
		label: label,
		data: {
			...nodeData,
			action_id: props.id,
			action_label: label,
			next_step_if_true: nextTrue,
			next_step_if_false: nextFalse,
			suggested_parent_id: null,
			suggested_source_handle: null,
		},
	};

	let newNodes = [...nodes];
	newNodes[nodeIndex] = updatedNode;

	let newEdges = [...edges];

	// Handle Scaffolding for complex types
	if (action_type === "Loop") {
		const bodyNodeId = frappe.utils.get_random(8);
		const bodyData = store.get_default_node_data("selector", __("Loop Body"));
		bodyData.action_id = bodyNodeId;

		const bodyNode = {
			id: bodyNodeId,
			type: "selector",
			position: { x: node.position.x + 100, y: node.position.y + 150 },
			label: __("Loop Body"),
			data: {
				...bodyData,
				next_step_if_true: props.id,
				suggested_parent_id: props.id,
				suggested_source_handle: "default",
			},
		};

		updatedNode.data.next_step_if_true = bodyNodeId;
		updatedNode.data.next_step_if_false = nextTrue; // After Last continues to original next step

		newNodes.push(bodyNode);
		newEdges.push(
			{
				id: `e-${props.id}-${bodyNodeId}-default`,
				source: props.id,
				target: bodyNodeId,
				sourceHandle: "default",
				type: "add",
				data: { loopBody: true },
			},
			{
				id: `e-${bodyNodeId}-${props.id}-return`,
				source: bodyNodeId,
				target: props.id,
				targetHandle: "return",
				type: "add",
				data: { isReturn: true },
			}
		);

		// If there was an existing output, reconnect it to the 'false' (After Last) handle
		if (nextTrue) {
			newEdges = newEdges.map((e) => {
				if (e.source === props.id && e.sourceHandle === "default") {
					return { ...e, sourceHandle: "false", data: { ...e.data, afterLast: true } };
				}
				return e;
			});
		}
	} else if (action_type === "Condition" || action_type === "Switch") {
		const stopNodeId = frappe.utils.get_random(8);
		const stopData = store.get_default_node_data("stop");
		stopData.operation = "Success";
		stopData.action_id = stopNodeId;

		const stopNode = {
			id: stopNodeId,
			type: "stop",
			position: { x: node.position.x + 100, y: node.position.y + 150 },
			label: __("End"),
			data: stopData,
		};

		updatedNode.data.next_step_if_true = nextTrue;
		updatedNode.data.next_step_if_false = stopNodeId;

		newNodes.push(stopNode);
		newEdges.push({
			id: `e-${props.id}-${stopNodeId}-false`,
			source: props.id,
			target: stopNodeId,
			sourceHandle: "false",
			type: "add",
		});

		// Fix handle for existing true path
		newEdges = newEdges.map((e) => {
			if (e.source === props.id && e.sourceHandle === "default") {
				return { ...e, sourceHandle: "true" };
			}
			return e;
		});
	}

	if (suggestedParentId) {
		const edgeId = `e-${suggestedParentId}-${props.id}-${suggestedSourceHandle}`;
		const hasIncoming = newEdges.some((edge) => edge.target === props.id);
		if (!hasIncoming) {
			newEdges.push({
				id: edgeId,
				source: suggestedParentId,
				target: props.id,
				sourceHandle: suggestedSourceHandle,
				type: "add",
				animated: suggestedParentId === "root",
			});
		}
	}

	if (isTerminalAction(action_type)) {
		newEdges = newEdges.filter((edge) => edge.source !== props.id);
	}

	// Apply immutable updates to store
	if (store.nodes.value) {
		store.nodes.value = newNodes;
		store.edges.value = newEdges;
	} else {
		store.nodes = newNodes;
		store.edges = newEdges;
	}

	store.select(props.id);
	store.show_sidebar = true;
	store.touch_node(props.id);
	store.mark_dirty();
}

const showProcessSelector = computed(() => {
	return selectedItemData.value?.action_type === "Process";
});

const showOperationSelector = computed(() => {
	if (!selectedItemData.value) return false;
	const actionType = selectedItemData.value.action_type;
	const contract = getContract(actionType);
	return (
		contract.operation_options ||
		["Process", "Query Records", "Document Action", "Stop", "Notify"].includes(actionType)
	);
});

const operationLabel = computed(() => {
	if (!selectedItemData.value) return __("Operation");
	const actionType = selectedItemData.value.action_type;
	const contract = getContract(actionType);
	return (
		getFieldLabel(actionType, "operation", {
			operation: selectedItemData.value.operation,
			processName: selectedItemData.value.process_name,
		}) ||
		contract.operation_label ||
		__("Operation")
	);
});

const processOptions = computed(() => {
	const processes = store.processes?.value || store.processes || [];
	return processes.map((p) => ({
		value: p.name,
		label: p.process_name || p.name,
		description: p.module,
	}));
});

const operationOptions = computed(() => {
	if (!selectedItemData.value) return [];
	const actionType = selectedItemData.value.action_type;
	const processName = selectedItemData.value.process_name;

	return getOperationOptions(actionType, { processName }).map((op) => ({
		value: op.value,
		label: op.label || op.value,
		description: op.description || "",
	}));
});

function onProcessChange() {
	if (selectedItemData.value) {
		selectedItemData.value.operation = null;
	}
}

function onOperationChange(val) {
	if (!selectedItemData.value) return;

	// Update label if it was matching the old operation or is empty
	const actionType = selectedItemData.value.action_type;
	if (!customLabel.value || customLabel.value === actionType) {
		const option = operationOptions.value.find((o) => o.value === val);
		if (option) {
			customLabel.value = option.label;
		}
	}
}

const debouncedRemoteSearch = frappe.utils.debounce(async (query) => {
	if (!query || query.length < 2) {
		// remoteResults handled by hook
		return;
	}
	// remoteResults handled by hook
}, 300);

function deleteNode() {
	if (props.mode === "node") {
		frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
	}
}

function onClickOutside(e) {
	if (props.mode !== "popover" || !popoverDropdownRef.value) return;
	const target = e.target;
	if (!document.body.contains(target)) return;

	const isInside = popoverDropdownRef.value.contains(target) || target.closest(".action-popover");

	if (!isInside) {
		emit("close");
	}
}

function handleGlobalKeydown(e) {
	if (e.key === "Escape") {
		if (props.mode === "popover") {
			emit("close");
		}
	}
}

function updateTriggerMock() {
	if (!props.position) return;
	popoverTriggerRef.value = {
		getBoundingClientRect: () => ({
			top: props.position.y,
			bottom: props.position.y,
			left: props.position.x,
			right: props.position.x,
			width: 0,
			height: 0,
		}),
	};
}

watch(
	() => props.position,
	() => {
		if (props.mode === "popover") {
			updateTriggerMock();
			updatePopoverPosition();
		}
	},
	{ deep: true }
);

watch(searchQuery, () => {
	selectedIndex.value = -1;
});

watch(filteredResults, () => {
	if (selectedIndex.value >= filteredResults.value.length) {
		selectedIndex.value = -1;
	}
});

onMounted(() => {
	loadProcessOperations();
	checkClipboard();
	if (props.mode === "popover") {
		if (props.trigger) {
			popoverTriggerRef.value = props.trigger;
		} else {
			updateTriggerMock();
		}
		openPopover();
		document.addEventListener("mousedown", onClickOutside, true);
		window.addEventListener("keydown", handleGlobalKeydown, true);
	}
	if (props.autoFocus) {
		setTimeout(() => searchInputRef.value?.focus(), 100);
	}
});

onUnmounted(() => {
	if (props.mode === "popover") {
		closePopover();
		document.removeEventListener("mousedown", onClickOutside, true);
		window.removeEventListener("keydown", handleGlobalKeydown, true);
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
		ref="popoverDropdownRef"
		class="action-popover"
		:style="popoverStyle"
	>
		<div class="popover-header">
			<i class="fa fa-plus-circle"></i>
			<span>{{ __("Add Action") }}</span>
		</div>
		<div ref="zoneRef" class="action-zone" @keydown="onKeydown">
			<template v-if="step === 'discovery'">
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
						:key="item.key || idx"
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
			</template>

			<template v-else-if="step === 'labeling'">
				<div class="labeling-container">
					<div class="selected-item-preview">
						<div class="item-icon" :style="{ color: selectedItemData.color }">
							<i
								:class="[
									'fa',
									selectedItemData.icon?.replace('fa ', '') || 'fa-cog',
								]"
							></i>
						</div>
						<div class="item-content">
							<div class="item-label">{{ selectedItemData.label }}</div>
							<div class="item-type-badge">{{ selectedItemData.action_type }}</div>
						</div>
					</div>
					<div v-if="showProcessSelector" class="form-group labeling-form">
						<label class="fxr-label-sm">{{ __("Process") }}</label>
						<ComboBoxControl
							v-model="selectedItemData.process_name"
							:options="processOptions"
							:placeholder="__('Select Process...')"
							@change="onProcessChange"
						/>
					</div>
					<div v-if="showOperationSelector" class="form-group labeling-form">
						<label class="fxr-label-sm">{{ operationLabel }}</label>
						<ComboBoxControl
							v-model="selectedItemData.operation"
							:options="operationOptions"
							:placeholder="__('Select Operation...')"
							@change="onOperationChange"
						/>
					</div>
					<div class="form-group labeling-form">
						<label class="fxr-label-sm">{{ __("Label") }}</label>
						<input
							ref="labelInputRef"
							type="text"
							v-model="customLabel"
							class="form-control"
							:placeholder="__('Name this action...')"
						/>
					</div>
					<div class="labeling-footer">
						<button class="btn btn-default btn-sm" @click="goBack">
							<i class="fa fa-chevron-left mr-1"></i> {{ __("Back") }}
						</button>
						<button class="btn btn-primary btn-sm" @click="confirmSelection">
							{{ __("Create Action") }}
						</button>
					</div>
				</div>
			</template>
		</div>
	</div>

	<!-- Node Mode Wrapper (VueFlow ActionSelectorNode) -->
	<div
		v-else-if="mode === 'node'"
		class="action-selector-card"
		:class="{ selected: selected, 'is-vertical': !isHorizontal }"
	>
		<Handle type="target" :position="targetPos" class="handle-target" />
		<NodeToolbar
			:node-id="id"
			:selected="selected"
			:is-read-only="false"
			@delete="deleteNode"
			@configure="() => {}"
		/>
		<div class="node-header">
			<i class="fa fa-plus-circle"></i>
			<span class="header-text">{{ __("New Action") }}</span>
		</div>
		<div class="node-body">
			<div ref="zoneRef" class="action-zone" @keydown="onKeydown">
				<template v-if="step === 'discovery'">
					<div class="form-group search-group">
						<label class="small text-muted">{{ __("Action Type") }}</label>
						<div class="search-wrapper">
							<div class="popover-search">
								<i
									:class="[
										'fa',
										isSearchingRemote ? 'fa-spinner fa-spin' : 'fa-search',
									]"
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
									:key="item.key || idx"
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
												:class="[
													'fa',
													item.icon?.replace('fa ', '') || 'fa-cog',
												]"
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
						</div>
					</div>
				</template>

				<template v-else-if="step === 'labeling'">
					<div class="labeling-container in-node">
						<div v-if="showProcessSelector" class="form-group labeling-form">
							<label class="small text-muted">{{ __("Process") }}</label>
							<ComboBoxControl
								v-model="selectedItemData.process_name"
								:options="processOptions"
								:placeholder="__('Select Process...')"
								@change="onProcessChange"
							/>
						</div>
						<div v-if="showOperationSelector" class="form-group labeling-form">
							<label class="small text-muted">{{ operationLabel }}</label>
							<ComboBoxControl
								v-model="selectedItemData.operation"
								:options="operationOptions"
								:placeholder="__('Select Operation...')"
								@change="onOperationChange"
							/>
						</div>
						<div class="form-group labeling-form">
							<label class="small text-muted">{{ __("Label") }}</label>
							<input
								ref="labelInputRef"
								type="text"
								v-model="customLabel"
								class="form-control input-xs"
								:placeholder="__('Enter label...')"
							/>
						</div>
						<div class="labeling-footer mt-2">
							<button class="btn btn-default btn-xs" @click="goBack">
								{{ __("Back") }}
							</button>
							<button class="btn btn-primary btn-xs flex-1" @click="confirmSelection">
								{{ __("Create") }}
							</button>
						</div>
					</div>
				</template>
			</div>
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
	flex: 1;
	min-height: 0; /* Important for flex child scrolling */
}

.action-popover {
	position: fixed;
	background-color: var(--fxr-surface-elevated);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	box-shadow: var(--fxr-shadow-lg);
	z-index: 2147483647;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.popover-header {
	padding: 10px 12px;
	background: var(--fxr-surface-2);
	border-bottom: 1px solid var(--fxr-border-subtle);
	display: flex;
	align-items: center;
	gap: 8px;
	font-weight: 700;
	font-size: 11px;
	color: var(--fxr-accent);
}

.popover-search {
	padding: 8px;
	position: relative;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.popover-search i {
	position: absolute;
	left: 16px;
	top: 50%;
	transform: translateY(-50%);
	color: var(--fxr-text-faint);
	font-size: 10px;
}

.popover-search input {
	padding-left: 28px !important;
	height: 32px;
	font-size: 12px;
	border-radius: var(--fxr-radius-sm);
	border: 1px solid var(--fxr-border);
	background-color: var(--fxr-bg-input);
	color: var(--fxr-text);
}

.popover-body {
	flex: 1;
	overflow-y: auto;
	padding: 4px 0;
	min-height: 0; /* Important for flex */
}

.result-item {
	padding: 8px 12px;
	cursor: pointer;
}

.is-header {
	font-size: 10px;
	font-weight: 700;
	color: var(--fxr-text-muted);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	padding: 12px 12px 4px;
	cursor: default;
	background-color: var(--fxr-surface-elevated);
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
	background-color: var(--fxr-bg-hover);
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
	color: var(--fxr-text-strong);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-desc {
	font-size: 10px;
	color: var(--fxr-text-soft);
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
	border-bottom: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-surface-soft);
}

.paste-option:hover {
	background-color: var(--fxr-bg-hover);
}

/* Node mode styles */

.action-selector-card {
	width: 260px;
	background-color: var(--fxr-surface-elevated);
	border: 2px dashed var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	box-shadow: var(--fxr-shadow-md);
	position: relative;
	transition: all 0.2s ease;
}

.action-selector-card.selected {
	border-color: var(--fxr-accent);
	border-style: solid;
	box-shadow: 0 0 0 2px var(--fxr-accent-soft);
}

.node-header {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	gap: 8px;
	background: var(--fxr-surface-2);
	border-radius: var(--fxr-radius-md) var(--fxr-radius-md) 0 0;
}

.node-header i {
	color: var(--fxr-accent);
	font-size: 14px;
}

.header-text {
	font-size: 11px;
	font-weight: 700;
	color: var(--fxr-text-soft);
	flex: 1;
}

.node-body {
	padding: 12px;
	display: flex;
	flex-direction: column;
}

.search-wrapper {
	max-height: 400px;
	display: flex;
	flex-direction: column;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	overflow: hidden;
}

.search-wrapper :deep(.popover-search) {
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.search-wrapper :deep(.popover-body) {
	/* Let flex handle it */
	flex: 1;
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
	background-color: var(--fxr-accent-soft);
	color: var(--fxr-accent);
	border: 1px solid var(--fxr-accent-border);
	border-radius: 10px;
	padding: 1px 6px;
	font-size: 10px;
	font-weight: 700;
}

.selected-operation-text {
	font-size: 10px;
	font-weight: 600;
	color: var(--fxr-text-strong);
}

.selected-process-name {
	font-size: 10px;
	color: var(--fxr-text-soft);
}

.node-footer {
	padding: 6px 12px;
	background-color: var(--fxr-surface-soft);
	border-bottom-left-radius: var(--fxr-radius-md);
	border-bottom-right-radius: var(--fxr-radius-md);
	border-top: 1px solid var(--fxr-border-subtle);
	text-align: center;
}

.handle-target,
.handle-source {
	width: 10px !important;
	height: 10px !important;
	background-color: var(--fxr-bg-card) !important;
	border: 2px solid var(--fxr-border) !important;
	z-index: 10 !important;
}

/* Labeling step styles */

.labeling-container {
	padding: 16px;
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.labeling-container.in-node {
	padding: 4px;
	gap: 8px;
}

.selected-item-preview {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 8px;
	background-color: var(--fxr-surface-soft);
	border-radius: var(--fxr-radius-sm);
}

.item-type-badge {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	color: #64748b;
	margin-top: 2px;
}

.labeling-footer {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 8px;
	margin-top: 4px;
}

/* Custom Scrollbar */
.popover-body::-webkit-scrollbar {
	width: 6px;
}
.popover-body::-webkit-scrollbar-thumb {
	background-color: var(--fxr-border-strong);
	border-radius: 3px;
}
</style>
