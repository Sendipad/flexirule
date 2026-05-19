<template>
	<div class="condition-builder fxr-accent-scope">
		<!-- Main Header -->
		<div class="builder-header">
			<div class="logic-toggle">
				<button
					type="button"
					class="logic-btn"
					:class="{ active: rootGroup.op === 'and' }"
					@click="rootGroup.op = 'and'"
					:disabled="readOnly"
				>
					{{ __("AND") }}
				</button>
				<button
					type="button"
					class="logic-btn"
					:class="{ active: rootGroup.op === 'or' }"
					@click="rootGroup.op = 'or'"
					:disabled="readOnly"
				>
					{{ __("OR") }}
				</button>
			</div>

			<div class="builder-actions" v-if="!readOnly">
				<button class="fxr-btn" @click="addCondition(rootGroup)">
					<i class="fa fa-plus"></i>
					<span>{{ __("Condition") }}</span>
				</button>
				<button class="fxr-btn" @click="addGroup(rootGroup)">
					<i class="fa fa-folder-open-o"></i>
					<span>{{ __("Group") }}</span>
				</button>
				<button class="fxr-btn" @click="addCollection(rootGroup)">
					<i class="fa fa-table"></i>
					<span>{{ __("Collection") }}</span>
				</button>
			</div>
		</div>

		<!-- Conditions List -->
		<div
			class="conditions-container"
			:class="{ 'drag-over': isDragOver }"
			@dragover.prevent.stop="isDragOver = true"
			@dragleave="isDragOver = false"
			@drop.stop="handleRootDrop"
		>
			<div v-if="!rootGroup.conditions?.length" class="empty-state">
				<div class="empty-icon">
					<i class="fa fa-filter"></i>
				</div>
				<p class="empty-text">
					{{ __("No conditions defined yet. Click 'Condition' or 'Group' to start.") }}
				</p>
			</div>
			<div
				v-for="(node, idx) in rootGroup.conditions"
				:key="node.id || idx"
				class="node-wrapper"
			>
				<ConditionNode
					:node="node"
					:index="idx"
					:parentGroup="rootGroup"
					:docFields="docFields"
					:readOnly="readOnly"
				/>
			</div>
			<!-- Spacer to make dropping at the end easier -->
			<div
				class="drop-spacer"
				v-if="rootGroup.conditions?.length > 0 && !readOnly"
				:class="{ active: isDragOver }"
			>
				<span v-if="isDragOver">{{ __("Drop here to move to top level") }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
/**
 * ConditionBuilder - Main container for condition editing
 * Owns the root condition group state and provides methods via inject
 */
import { ref, reactive, watch, nextTick, provide, computed, onMounted } from "vue";
import { useStore } from "../../stores";

import ConditionNode from "./ConditionNode.vue";

const props = defineProps({
	modelValue: { type: Object, default: () => ({ op: "and", conditions: [] }) },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const store = useStore();

// Create a reactive copy of the model
const rootGroup = reactive(JSON.parse(JSON.stringify(props.modelValue)));

let isUpdating = false;

// Sync with parent when rootGroup changes
watch(
	rootGroup,
	(newVal) => {
		if (isUpdating) return;
		emit("update:modelValue", JSON.parse(JSON.stringify(newVal)));
	},
	{ deep: true }
);

// Sync from parent when modelValue changes externally
watch(
	() => props.modelValue,
	(newVal) => {
		if (!newVal || isUpdating) return;

		const currentJSON = JSON.stringify(rootGroup);
		const newJSON = JSON.stringify(newVal);

		if (newJSON !== currentJSON) {
			isUpdating = true;
			Object.assign(rootGroup, JSON.parse(newJSON));
			nextTick(() => {
				isUpdating = false;
			});
		}
	},
	{ deep: true }
);

// UUID generator
function uuid() {
	return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
		const r = (Math.random() * 16) | 0;
		return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
	});
}

// Action methods - provided to children via inject
function addCondition(targetGroup, fieldPrefix = "doc") {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		left: { ref: fieldPrefix + "." },
		op: "==",
		right: { value: "" },
	});
}

function addGroup(targetGroup) {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		op: "and",
		conditions: [],
	});
}

function addCollection(targetGroup) {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		op: "any",
		collection: "",
		alias: "row",
		where: { op: "and", conditions: [] },
	});
}

function removeNode(targetGroup, index) {
	if (targetGroup.conditions && targetGroup.conditions[index] !== undefined) {
		targetGroup.conditions.splice(index, 1);
	}
}

function isDescendantOf(parent, targetId) {
	if (parent.id === targetId) return true;
	if (parent.conditions) {
		for (const cond of parent.conditions) {
			if (cond.id === targetId) return true;
			if (cond.conditions && isDescendantOf(cond, targetId)) return true;
			if (cond.where && isDescendantOf(cond.where, targetId)) return true;
		}
	}
	return false;
}

function moveNode(fromGroup, fromIndex, toGroup, toIndex) {
	if (!fromGroup.conditions || fromGroup.conditions[fromIndex] === undefined) return;
	if (!toGroup.conditions) toGroup.conditions = [];

	const node = fromGroup.conditions[fromIndex];

	// Guard: Cannot drop a group into itself or its descendants
	if (node.conditions || node.where) {
		if (isDescendantOf(node, toGroup.id)) {
			console.warn(
				"FlexiRule: Illegal move - cannot drop a group into itself or its descendants."
			);
			return;
		}
	}

	fromGroup.conditions.splice(fromIndex, 1);

	if (toIndex === -1) {
		toGroup.conditions.push(node);
	} else {
		toGroup.conditions.splice(toIndex, 0, node);
	}
}

// Drag and Drop state
const dragInfo = reactive({
	fromGroup: null,
	fromIndex: -1,
});

function onDragStart(node, group, index) {
	dragInfo.fromGroup = group;
	dragInfo.fromIndex = index;
}

function onDrop(toGroup, toIndex = -1) {
	if (!dragInfo.fromGroup) return;
	moveNode(dragInfo.fromGroup, dragInfo.fromIndex, toGroup, toIndex);
	dragInfo.fromGroup = null;
	dragInfo.fromIndex = -1;
}

// Operator config from backend
const operatorConfig = ref({
	fieldtype_operators: {},
	operator_labels: {},
});

async function loadOperatorConfig() {
	try {
		const result = await frappe.call({
			method: "flexirule.ruleflow.api.get_operator_config",
		});
		if (result.message) {
			operatorConfig.value = result.message;
		}
	} catch (e) {
		console.error("Failed to load operator config:", e);
	}
}

onMounted(loadOperatorConfig);

const isDragOver = ref(false);

function handleRootDrop() {
	isDragOver.value = false;
	onDrop(rootGroup);
}

// Provide actions and config to all descendant components
provide("conditionActions", {
	addCondition,
	addGroup,
	addCollection,
	removeNode,
	moveNode,
	onDragStart,
	onDrop,
});
provide(
	"docFields",
	computed(() => props.docFields)
);
provide("conditionContext", reactive({ alias: "doc" }));
provide("operatorConfig", operatorConfig);
provide("store", store);
provide(
	"readOnly",
	computed(() => props.readOnly)
);
</script>

<style scoped>
.condition-builder {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-4);
	background: var(--fxr-bg-page);
	border-radius: var(--fxr-radius-lg);
	padding: var(--fxr-space-4);
	min-height: 180px;
}

.builder-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding-bottom: var(--fxr-space-3);
	border-bottom: 1px solid var(--fxr-border);
}

.logic-toggle {
	display: flex;
	background: var(--fxr-border);
	padding: var(--fxr-space-1);
	border-radius: var(--fxr-radius-md);
}

.logic-btn {
	border: none;
	background: transparent;
	padding: var(--fxr-space-2) var(--fxr-space-6);
	border-radius: var(--fxr-radius-sm);
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-bold);
	color: var(--fxr-text-muted);
	transition: all var(--fxr-transition-fast);
	cursor: pointer;
}

.logic-btn.active {
	background: var(--fxr-bg-card);
	color: var(--fxr-node-accent, var(--fxr-accent));
	box-shadow: var(--fxr-shadow-sm);
}

.builder-actions {
	display: flex;
	gap: var(--fxr-space-3);
}

.builder-actions .fxr-btn {
	background: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	color: var(--fxr-text-secondary);
}

.builder-actions .fxr-btn:hover {
	background: var(--fxr-bg-muted);
	border-color: var(--fxr-border-strong);
	transform: translateY(-1px);
}

.builder-actions .fxr-btn i {
	font-size: 11px;
	color: var(--fxr-node-accent, var(--fxr-accent));
}

.conditions-container {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
	min-height: 100px;
	padding: var(--fxr-space-1);
	border-radius: var(--fxr-radius-lg);
	transition: all var(--fxr-transition-fast);
}

.conditions-container.drag-over {
	background: var(--fxr-node-accent-light, var(--fxr-accent-light));
	box-shadow: inset 0 0 0 2px var(--fxr-node-accent, var(--fxr-accent));
}

.drop-spacer {
	height: 32px;
	margin-top: var(--fxr-space-2);
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: var(--fxr-radius-md);
	border: 1px dashed transparent;
	color: var(--fxr-node-accent, var(--fxr-accent));
	font-size: var(--fxr-text-xs);
	font-weight: var(--fxr-weight-semibold);
	transition: all var(--fxr-transition-fast);
}

.drop-spacer.active {
	border-color: var(--fxr-node-accent, var(--fxr-accent));
	background: var(--fxr-node-accent-light, var(--fxr-accent-light));
}

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 40px;
	background: var(--fxr-bg-card);
	border: 2px dashed var(--fxr-border);
	border-radius: var(--fxr-radius-lg);
	text-align: center;
}

.empty-icon {
	width: 48px;
	height: 48px;
	background: var(--fxr-bg-muted);
	color: var(--fxr-text-muted);
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
	font-size: 20px;
	margin-bottom: var(--fxr-space-4);
}

.empty-text {
	font-size: var(--fxr-text-md);
	color: var(--fxr-text-secondary);
	margin: 0;
}

.node-wrapper {
	transition: all var(--fxr-transition-slow) ease;
}

@media (max-width: 768px) {
	.condition-builder {
		padding: var(--fxr-space-4);
		gap: var(--fxr-space-5);
	}

	.builder-header {
		flex-direction: column;
		align-items: stretch;
		gap: var(--fxr-space-3);
	}

	.builder-actions {
		flex-wrap: wrap;
	}
}
</style>
