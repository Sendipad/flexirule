<template>
	<div class="condition-builder">
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
				<button class="fr-btn" @click="addCondition(rootGroup)">
					<i class="fa fa-plus"></i>
					<span>{{ __("Condition") }}</span>
				</button>
				<button class="fr-btn" @click="addGroup(rootGroup)">
					<i class="fa fa-folder-open-o"></i>
					<span>{{ __("Group") }}</span>
				</button>
				<button class="fr-btn" @click="addCollection(rootGroup)">
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
	gap: var(--fr-space-10);
	background: var(--fr-bg-page);
	border-radius: var(--fr-radius-lg);
	padding: var(--fr-space-8);
	min-height: 200px;
}

.builder-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding-bottom: var(--fr-space-6);
	border-bottom: 1px solid var(--fr-border);
}

.logic-toggle {
	display: flex;
	background: var(--fr-border);
	padding: var(--fr-space-1);
	border-radius: var(--fr-radius-md);
}

.logic-btn {
	border: none;
	background: transparent;
	padding: var(--fr-space-2) var(--fr-space-6);
	border-radius: var(--fr-radius-sm);
	font-size: var(--fr-text-sm);
	font-weight: var(--fr-weight-bold);
	color: var(--fr-text-muted);
	transition: all var(--fr-transition-fast);
	cursor: pointer;
}

.logic-btn.active {
	background: var(--fr-bg-card);
	color: var(--fr-accent);
	box-shadow: var(--fr-shadow-sm);
}

.builder-actions {
	display: flex;
	gap: var(--fr-space-3);
}

.builder-actions .fr-btn {
	background: var(--fr-bg-card);
	border: 1px solid var(--fr-border);
	color: var(--fr-text-secondary);
}

.builder-actions .fr-btn:hover {
	background: var(--fr-bg-muted);
	border-color: var(--fr-border-strong);
	transform: translateY(-1px);
}

.builder-actions .fr-btn i {
	font-size: 11px;
	color: var(--fr-accent);
}

.conditions-container {
	display: flex;
	flex-direction: column;
	gap: var(--fr-space-5);
	min-height: 100px;
	padding: var(--fr-space-2);
	border-radius: var(--fr-radius-lg);
	transition: all var(--fr-transition-fast);
}

.conditions-container.drag-over {
	background: var(--fr-accent-light);
	box-shadow: inset 0 0 0 2px var(--fr-accent);
}

.drop-spacer {
	height: 40px;
	margin-top: var(--fr-space-4);
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: var(--fr-radius-md);
	border: 1px dashed transparent;
	color: var(--fr-accent);
	font-size: var(--fr-text-sm);
	font-weight: var(--fr-weight-semibold);
	transition: all var(--fr-transition-fast);
}

.drop-spacer.active {
	border-color: var(--fr-accent);
	background: var(--fr-accent-light);
}

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 40px;
	background: var(--fr-bg-card);
	border: 2px dashed var(--fr-border);
	border-radius: var(--fr-radius-lg);
	text-align: center;
}

.empty-icon {
	width: 48px;
	height: 48px;
	background: var(--fr-bg-muted);
	color: var(--fr-text-muted);
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
	font-size: 20px;
	margin-bottom: var(--fr-space-4);
}

.empty-text {
	font-size: var(--fr-text-md);
	color: var(--fr-text-secondary);
	margin: 0;
}

.node-wrapper {
	transition: all var(--fr-transition-slow) ease;
}
</style>
