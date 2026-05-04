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
				<button class="action-btn" @click="addCondition(rootGroup)">
					<i class="fa fa-plus"></i>
					<span>{{ __("Condition") }}</span>
				</button>
				<button class="action-btn" @click="addGroup(rootGroup)">
					<i class="fa fa-folder-open-o"></i>
					<span>{{ __("Group") }}</span>
				</button>
				<button class="action-btn" @click="addCollection(rootGroup)">
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
	gap: 20px;
	background: #f8fafc;
	border-radius: 12px;
	padding: 20px;
	min-height: 200px;
}

.builder-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding-bottom: 16px;
	border-bottom: 1px solid #e2e8f0;
}

.logic-toggle {
	display: flex;
	background: #e2e8f0;
	padding: 3px;
	border-radius: 8px;
}

.logic-btn {
	border: none;
	background: transparent;
	padding: 6px 16px;
	border-radius: 6px;
	font-size: 12px;
	font-weight: 700;
	color: #64748b;
	transition: all 0.2s;
	cursor: pointer;
}

.logic-btn.active {
	background: white;
	color: var(--primary);
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.builder-actions {
	display: flex;
	gap: 8px;
}

.action-btn {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 6px 12px;
	background: white;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	font-size: 12px;
	font-weight: 600;
	color: #475569;
	cursor: pointer;
	transition: all 0.2s;
}

.action-btn:hover {
	background: #f1f5f9;
	border-color: #cbd5e1;
	transform: translateY(-1px);
}

.action-btn i {
	font-size: 11px;
	color: var(--primary);
}

.conditions-container {
	display: flex;
	flex-direction: column;
	gap: 12px;
	min-height: 100px;
	padding: 10px;
	border-radius: 12px;
	transition: all 0.2s;
}

.conditions-container.drag-over {
	background: rgba(var(--primary-rgb, 36, 144, 239), 0.08);
	box-shadow: inset 0 0 0 2px var(--primary);
	border-radius: 12px;
}

.drop-spacer {
	height: 40px;
	margin-top: 8px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 8px;
	border: 1px dashed transparent;
	color: var(--primary);
	font-size: 11px;
	font-weight: 600;
	transition: all 0.2s;
}

.drop-spacer.active {
	border-color: var(--primary);
	background: rgba(var(--primary-rgb, 36, 144, 239), 0.05);
}

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 40px;
	background: white;
	border: 2px dashed #e2e8f0;
	border-radius: 12px;
	text-align: center;
}

.empty-icon {
	width: 48px;
	height: 48px;
	background: #f1f5f9;
	color: #94a3b8;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
	font-size: 20px;
	margin-bottom: 12px;
}

.empty-text {
	font-size: 13px;
	color: #64748b;
	margin: 0;
}

.node-wrapper {
	transition: all 0.3s ease;
}
</style>
