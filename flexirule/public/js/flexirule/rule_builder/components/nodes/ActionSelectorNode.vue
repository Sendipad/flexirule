<script setup>
import { ref, computed, onMounted } from "vue";
import { Handle, Position } from "@vue-flow/core";
import {
	ACTION_TYPE_CONTRACT,
	PROCESS_REGISTRY,
	getActionTypeOptions,
	getOperationOptions,
	loadContractsFromBackend,
	isTerminalAction,
} from "../../../core/contracts";
import { useStore } from "../../store";
import { mapActionTypeToNodeType } from "../../composables/useActionTypeMapper";

const props = defineProps(["data", "label", "id", "selected", "sourcePosition", "targetPosition"]);
const store = useStore();

const isHorizontal = computed(() => store.settings?.layout_direction !== "Top to Bottom");

const targetPos = computed(
	() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
);
const sourcePos = computed(
	() => props.sourcePosition || (isHorizontal.value ? Position.Right : Position.Bottom)
);

const selectedPreset = ref({
	action_type: "Process",
	operation: null,
	process_name: null,
	selected_label: "Process",
});
const customLabel = ref("");
const searchQuery = ref("");
const showResults = ref(false);
const processOperations = ref([]);
const selectedIndex = ref(-1);

// ... (rest of the script)
// Fuzzy match helper — matches each query word independently against the text
// Fuzzy match helper — supports acronyms and word-start matching
function fuzzyMatch(text, query) {
	if (!query) return true;
	const lowerText = text.toLowerCase();
	const q = query.toLowerCase().trim();

	// 1. Simple substring match
	if (lowerText.includes(q)) return true;

	// 2. Acronym match (e.g. "dq" -> "Document Query")
	const words = lowerText.split(/[\s_-]+/).filter(Boolean);
	const acronym = words.map((w) => w[0]).join("");
	if (acronym.includes(q)) return true;

	// 3. Multi-word match (e.g. "doc query" -> "Document Query Records")
	const qWords = q.split(/\s+/).filter(Boolean);
	return qWords.every((qw) => words.some((w) => w.startsWith(qw) || w.includes(qw)));
}

// Categorize action types into groups for display
const ACTION_CATEGORIES = {
	"Control Flow": ["Condition", "Stop", "Wait", "Loop", "Sub-Rule"],
	"Data Actions": ["Set Value", "Query Records", "Document Action"],
	Notifications: ["Notify"],
	Processes: ["Process"],
};

const actionTypes = computed(() => {
	const meta = frappe.get_meta("Rule Action");
	if (!meta || !meta.fields) return [];

	const typeField = meta.fields.find((f) => f.fieldname === "action_type");
	if (!typeField || !typeField.options) return [];

	return typeField.options
		.split("\n")
		.filter(
			(t) => t && t !== "Entry Action" && t !== "Start" && getActionTypeOptions().includes(t)
		)
		.map((t) => {
			const contract = ACTION_TYPE_CONTRACT[t] || {};
			return {
				label: __(t),
				value: t,
				actionType: t,
				icon: contract.css?.icon || "fa fa-cog",
				color: contract.css?.color || "#6b7280",
				description: contract.description || "",
				category:
					Object.entries(ACTION_CATEGORIES).find(([, types]) => types.includes(t))?.[0] ||
					__("Other"),
			};
		});
});

// Filtered results for fuzzy search
const filteredResults = computed(() => {
	const q = searchQuery.value;
	const results = [];

	// 1. Filter action types and their native operations
	actionTypes.value.forEach((t) => {
		const contract = ACTION_TYPE_CONTRACT[t.value] || {};
		const ops = getOperationOptions(t.value);

		// Match the action type itself
		const matchAction =
			fuzzyMatch(t.label, q) || fuzzyMatch(t.description, q) || fuzzyMatch(t.value, q);
		if (matchAction) {
			results.push({ type: "header", label: t.label });
			results.push({ type: "action", ...t });
		}

		// Match operations within this action type
		const matchingOps = ops.filter(
			(op) => fuzzyMatch(op.label || op.value, q) || fuzzyMatch(op.value, q)
		);
		if (matchingOps.length) {
			if (!matchAction) {
				results.push({ type: "header", label: t.label });
			}
			matchingOps.forEach((op) => {
				results.push({
					type: "op",
					label: `${t.label} → ${__(op.label || op.value)}`,
					value: t.value,
					operation: op.value,
					process_name: t.value === "Process" ? op.process_name || null : null,
					icon: t.icon,
					color: t.color,
					description: t.description,
				});
			});
		}
	});

	// 2. Filter process operations (backend processes)
	const matchingProcessOps = processOperations.value.filter(
		(op) =>
			fuzzyMatch(op.label, q) ||
			fuzzyMatch(op.process, q) ||
			fuzzyMatch(op.description || "", q)
	);

	if (matchingProcessOps.length) {
		results.push({ type: "header", label: __("Process Operations") });
		matchingProcessOps.forEach((op) =>
			results.push({
				type: "process_op",
				label: `${op.process} → ${op.label}`,
				value: "Process",
				process_name: op.process,
				operation: op.operation,
				icon: "fa fa-cog",
				color: "#8b5cf6",
				description: op.description || "",
			})
		);
	}

	return results;
});

async function loadProcessOperations() {
	await loadContractsFromBackend();
	if (Array.isArray(PROCESS_REGISTRY) && PROCESS_REGISTRY.length) {
		processOperations.value = PROCESS_REGISTRY.flatMap((proc) =>
			(proc.operations || [])
				.filter((op) => op.enabled !== 0 && op.visible_in_builder !== 0 && op.func_name)
				.map((op) => ({
					process: proc.name,
					module: proc.module,
					operation: op.func_name,
					label: op.label || op.func_name,
					description: op.description || "",
				}))
		);
		return;
	}
	try {
		const res = await frappe.call({
			method: "flexirule.ruleflow.api.get_all_process_operations",
		});
		processOperations.value = res.message || [];
	} catch (e) {
		processOperations.value = [];
	}
}

function selectItem(item) {
	if (item.type === "header") return;
	if (item.type === "process_op") {
		selectedPreset.value = {
			action_type: "Process",
			operation: item.operation,
			process_name: item.process_name,
			selected_label: item.label || item.operation || "Process",
		};
	} else if (item.type === "op") {
		selectedPreset.value = {
			action_type: item.value || "Process",
			operation: item.operation || null,
			process_name: item.process_name || null,
			selected_label: item.label || item.operation || item.value || "Process",
		};
	} else {
		selectedPreset.value = {
			action_type: item.value || "Process",
			operation: null,
			process_name: null,
			selected_label: item.label || item.value || "Process",
		};
	}

	searchQuery.value = item.label;
	showResults.value = false;
}

function onSearchFocus() {
	showResults.value = true;
}

function onSearchKeydown(e) {
	if (!showResults.value || !filteredResults.value.length) return;

	if (e.key === "ArrowDown") {
		e.preventDefault();
		selectedIndex.value = (selectedIndex.value + 1) % filteredResults.value.length;
		// Skip headers
		if (filteredResults.value[selectedIndex.value]?.type === "header") {
			onSearchKeydown(e);
		}
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		selectedIndex.value =
			(selectedIndex.value - 1 + filteredResults.value.length) % filteredResults.value.length;
		// Skip headers
		if (filteredResults.value[selectedIndex.value]?.type === "header") {
			onSearchKeydown(e);
		}
	} else if (e.key === "Enter" && selectedIndex.value !== -1) {
		e.preventDefault();
		selectItem(filteredResults.value[selectedIndex.value]);
	}
}

function onSearchBlur() {
	// Delay to allow click on results
	setTimeout(() => {
		showResults.value = false;
		selectedIndex.value = -1;
	}, 200);
}

function onCreate() {
	const nodeIndex = store.nodes.findIndex((n) => n.id === props.id);

	if (nodeIndex === -1) return;

	const action_type = selectedPreset.value.action_type || "Process";
	const label =
		customLabel.value ||
		selectedPreset.value.operation ||
		selectedPreset.value.selected_label ||
		action_type;
	// Map Action Type to VueFlow node type using the same logic as App.vue
	const nodeType = mapActionTypeToNodeType(action_type);

	const nodeData = store.get_default_node_data(action_type.toLowerCase(), label);
	const suggestedParentId = store.nodes[nodeIndex].data?.suggested_parent_id;
	const suggestedSourceHandle = store.nodes[nodeIndex].data?.suggested_source_handle || "default";

	// Pre-fill process/operation data from selected preset
	if (selectedPreset.value.operation) {
		nodeData.operation = selectedPreset.value.operation;
	}
	if (selectedPreset.value.process_name) {
		nodeData.process_name = selectedPreset.value.process_name;
	}
	if (action_type === "Process" && nodeData.operation && !nodeData.process_name) {
		const matches = getOperationOptions("Process", {})
			.filter((op) => op.value === nodeData.operation && op.process_name)
			.map((op) => op.process_name);
		const unique = [...new Set(matches)];
		if (unique.length === 1) {
			nodeData.process_name = unique[0];
		}
	}

	// Upgrade the node
	store.nodes[nodeIndex].type = nodeType;
	store.nodes[nodeIndex].label = label;
	store.nodes[nodeIndex].data = {
		...nodeData,
		action_id: props.id,
		action_label: label,
		suggested_parent_id: null,
		suggested_source_handle: null,
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

	// If the chosen node is terminal, remove any outgoing edges that might have existed
	// (Selector nodes often have an outgoing edge if inserted on a connection)
	if (isTerminalAction(action_type)) {
		store.edges = store.edges.filter((edge) => edge.source !== props.id);
		store.nodes[nodeIndex].data.next_step_if_true = null;
		store.nodes[nodeIndex].data.next_step_if_false = null;
	}

	store.open_config(props.id);
	store.touch_node(props.id);
	store.mark_dirty();
}

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}

onMounted(() => {
	loadProcessOperations();
});
</script>

<template>
	<div
		class="action-selector-card"
		:class="{
			selected: selected,
			'is-vertical': !isHorizontal,
		}"
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
				<div class="search-wrapper">
					<div class="search-input-group">
						<i class="fa fa-search search-icon"></i>
						<input
							type="text"
							v-model="searchQuery"
							class="form-control input-xs"
							:placeholder="__('Search actions...')"
							@focus="onSearchFocus"
							@blur="onSearchBlur"
							@keydown="onSearchKeydown"
							@keyup.enter="onCreate"
						/>
					</div>
					<div v-if="selectedPreset.operation" class="selected-operation-preview">
						<span class="badge-chip">{{ selectedPreset.action_type }}</span>
						<span class="selected-operation-text">
							{{ selectedPreset.operation }}
						</span>
						<span v-if="selectedPreset.process_name" class="selected-process-name">
							({{ selectedPreset.process_name }})
						</span>
					</div>
					<div
						v-if="showResults && filteredResults.length"
						class="search-results"
						@wheel.stop
					>
						<div
							v-for="(item, idx) in filteredResults"
							:key="idx"
							:class="[
								'search-result-item',
								item.type === 'header' ? 'result-header' : 'result-option',
								{ active: idx === selectedIndex },
							]"
							@mousedown.prevent="selectItem(item)"
							@mouseover="selectedIndex = idx"
						>
							<template v-if="item.type === 'header'">
								<span class="header-label">{{ item.label }}</span>
							</template>
							<template v-else>
								<i
									:class="['fa', item.icon?.replace('fa ', '')]"
									:style="{ color: item.color }"
								></i>
								<div class="result-text">
									<span class="result-label">{{ item.label }}</span>
									<span v-if="item.description" class="result-desc">{{
										item.description
									}}</span>
								</div>
							</template>
						</div>
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
</template>

<style scoped>
.action-selector-card {
	width: 220px;
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
}

.form-group {
	margin-bottom: 8px;
}

.form-group label {
	display: block;
	margin-bottom: 2px;
}

.search-wrapper {
	position: relative;
}

.search-input-group {
	position: relative;
	display: flex;
	align-items: center;
}

.search-icon {
	position: absolute;
	left: 8px;
	color: #adb5bd;
	font-size: 10px;
	z-index: 1;
	pointer-events: none;
}

.search-input-group input {
	padding-left: 24px !important;
}

.search-results {
	position: absolute;
	top: 100%;
	left: 0;
	right: 0;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
	z-index: 100;
	max-height: 240px;
	overflow-y: auto;
	overscroll-behavior: contain;
	margin-top: 2px;
}

.search-results :deep(*) {
	user-select: none;
}

.selected-operation-preview {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-top: 6px;
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

.search-result-item {
	cursor: pointer;
	padding: 6px 10px;
	font-size: 11px;
	transition: background 0.15s;
}

.result-header {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	color: var(--text-muted);
	padding: 8px 12px 4px;
	cursor: default;
	letter-spacing: 0.8px;
	border-top: 1px solid #f1f5f9;
	background: #fcfcfc;
}

.result-header:first-child {
	border-top: none;
}

.result-option {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	gap: 10px;
	transition: all 0.2s;
}

.result-option:hover,
.result-option.active {
	background: #f3f4f6;
}

.result-option i {
	font-size: 14px;
	width: 16px;
	text-align: center;
}

.result-text {
	display: flex;
	flex-direction: column;
	min-width: 0;
}

.result-label {
	font-weight: 500;
	color: #111827;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	line-height: 1.2;
}

.result-desc {
	font-size: 10px;
	color: #6b7280;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	margin-top: 1px;
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

.action-selector-card:not(.is-vertical) .handle-target {
	left: -5px !important;
	top: 50% !important;
	transform: translateY(-50%) !important;
}

.action-selector-card:not(.is-vertical) .handle-source {
	right: -5px !important;
	top: 50% !important;
	transform: translateY(-50%) !important;
}

.is-vertical .handle-target {
	top: -5px !important;
	left: 50% !important;
	transform: translateX(-50%) !important;
}

.is-vertical .handle-source {
	bottom: -5px !important;
	left: 50% !important;
	transform: translateX(-50%) !important;
}

.action-selector-card.selected .handle-target,
.action-selector-card.selected .handle-source {
	border-color: var(--primary) !important;
}
/* RTL Support */
[dir="rtl"] .node-header {
	flex-direction: row;
}

[dir="rtl"] .header-text {
	text-align: right;
}

[dir="rtl"] .delete-btn {
	margin-left: 0;
	margin-right: auto;
}

[dir="rtl"] .search-icon {
	left: auto;
	right: 8px;
}

[dir="rtl"] .search-input-group input {
	padding-left: 10px !important;
	padding-right: 24px !important;
}

[dir="rtl"] .result-option i {
	margin-right: 0;
	margin-left: 10px;
}
</style>
