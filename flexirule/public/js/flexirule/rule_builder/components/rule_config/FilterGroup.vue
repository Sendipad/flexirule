<template>
	<div class="filter-group-wrapper fxr-accent-scope" :style="panelStyleVars">
		<div
			v-if="!doctype && !allowAnyDoctype"
			class="text-muted small p-2 text-center border-dashed rounded"
		>
			{{ __("Select a DocType to configure filters.") }}
		</div>

		<div v-else class="root-filter-container">
			<!-- Root Group Logic Header -->
			<div class="root-group-header">
				<div class="logic-toggle">
					<button
						type="button"
						class="logic-btn"
						:class="{ active: rootGroup.op === 'and' }"
						@click="rootGroup.op = 'and'; emitUpdate()"
						:disabled="readOnly"
					>
						{{ __("AND") }}
					</button>
					<button
						type="button"
						class="logic-btn"
						:class="{ active: rootGroup.op === 'or' }"
						@click="rootGroup.op = 'or'; emitUpdate()"
						:disabled="readOnly"
					>
						{{ __("OR") }}
					</button>
				</div>

				<div class="root-actions" v-if="!readOnly">
					<button class="btn btn-xs btn-outline-primary" @click="addCondition(rootGroup)">
						<i class="fa fa-plus mr-1"></i> {{ __("Add Condition") }}
					</button>
					<button class="btn btn-xs btn-outline-secondary ml-2" @click="addGroup(rootGroup)">
						<i class="fa fa-folder-open-o mr-1"></i> {{ __("Add Group") }}
					</button>
					<button
						v-if="rootGroup.conditions?.length"
						class="btn btn-xs btn-link text-muted ml-3"
						@click="clearFilters"
					>
						{{ __("Clear All") }}
					</button>
				</div>
			</div>

			<!-- Filter List Body -->
			<div class="root-group-body">
				<div v-if="!rootGroup.conditions?.length" class="empty-state p-3 text-center border-dashed rounded text-muted">
					<i class="fa fa-filter fa-2x mb-2 opacity-30"></i>
					<p class="m-0 small">{{ __("No filters defined. Click 'Add Condition' or 'Add Group' to start.") }}</p>
				</div>

				<div v-for="(node, idx) in rootGroup.conditions" :key="node.id || idx" class="node-item-wrapper">
					<QueryFilterNode
						:node="node"
						:index="idx"
						:parentGroup="rootGroup"
						:doctype="doctype"
						:readOnly="readOnly"
						:allowAnyDoctype="allowAnyDoctype"
						:showValidation="showValidation"
						:effectiveVariableOptions="effectiveVariableOptions"
						@update="emitUpdate"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject, reactive } from "vue";
import QueryFilterNode from "./QueryFilterNode.vue";
import { useStore } from "../../stores";
import { getContract } from "../../../core/contracts.js";

const props = defineProps({
	modelValue: {
		type: [Array, Object],
		default: () => [],
	},
	doctype: {
		type: String,
		required: true,
	},
	nodeId: {
		type: String,
		default: null,
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
	allowAnyDoctype: {
		type: Boolean,
		default: false,
	},
	variableOptions: {
		type: Array,
		default: null,
	},
	showValidation: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();

const injectedVariableOptions = inject("variableOptions", ref([]));
const effectiveVariableOptions = computed(
	() => props.variableOptions ?? injectedVariableOptions.value
);

const panelStyleVars = computed(() => {
	const node = (store.nodes || []).find((n) => n.id === props.nodeId);
	const actionType = node?.data?.action_type || node?.type;
	const accent = getContract(actionType)?.css?.color || "var(--fxr-accent)";
	return {
		"--fxr-node-accent": accent,
		"--fxr-node-accent-light": `color-mix(in srgb, ${accent} 12%, var(--fxr-surface))`,
	};
});

function uuid() {
	return "f_" + Math.random().toString(36).substr(2, 9);
}

const rootGroup = reactive({
	id: "root",
	op: "and",
	conditions: [],
});

function coerceStructuredValue(val) {
	if (Array.isArray(val)) {
		return val.map(coerceStructuredValue);
	}
	if (val && typeof val === "object" && val.mode) {
		return val;
	}
	return { mode: "static", value: val !== undefined && val !== null ? val : "" };
}

function syncFromProps() {
	const val = props.modelValue;
	if (!val) {
		rootGroup.op = "and";
		rootGroup.conditions = [];
		return;
	}

	if (typeof val === "object" && !Array.isArray(val) && val.conditions) {
		rootGroup.op = val.op || "and";
		rootGroup.conditions = JSON.parse(JSON.stringify(val.conditions));
		return;
	}

	if (Array.isArray(val)) {
		rootGroup.op = "and";
		rootGroup.conditions = val.map((row) => {
			if (Array.isArray(row)) {
				return {
					id: uuid(),
					doctype: row[0] || props.doctype,
					field: row[1],
					operator: row[2] || "=",
					value: coerceStructuredValue(row[3]),
				};
			}
			if (typeof row === "object" && row !== null) {
				if (row.conditions) return row; // already a sub group
				return {
					id: uuid(),
					doctype: row.doctype || props.doctype,
					field: row.field || row.fieldname,
					operator: row.operator || "=",
					value: coerceStructuredValue(row.value),
				};
			}
			return {
				id: uuid(),
				doctype: props.doctype,
				field: "name",
				operator: "=",
				value: { mode: "static", value: "" },
			};
		});
	}
}

function emitUpdate() {
	// Check if simple flat AND structure without sub groups
	const isFlatAnd = rootGroup.op === "and" && rootGroup.conditions.every((c) => !c.conditions);

	if (isFlatAnd) {
		const serialized = rootGroup.conditions
			.filter((r) => r.field)
			.map((r) => [
				r.doctype || props.doctype,
				r.field,
				r.operator || "=",
				r.value,
			]);
		emit("update:modelValue", serialized);
	} else {
		// Emit full recursive group structure
		emit("update:modelValue", {
			op: rootGroup.op,
			conditions: JSON.parse(JSON.stringify(rootGroup.conditions)),
		});
	}
}

function addCondition(targetGroup) {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		doctype: props.doctype,
		field: "name",
		operator: "=",
		value: { mode: "static", value: "" },
	});
	emitUpdate();
}

function addGroup(targetGroup) {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		op: "and",
		conditions: [],
	});
	emitUpdate();
}

function clearFilters() {
	rootGroup.conditions = [];
	emitUpdate();
}

function validateNode(node) {
	const errors = [];
	if (node.conditions) {
		node.conditions.forEach((child) => {
			errors.push(...validateNode(child));
		});
	} else {
		if (!node.field) errors.push(__("Field is required for filter row"));
		if (!node.operator) errors.push(__("Operator is required for filter row"));
	}
	return errors;
}

function validate() {
	const errors = validateNode(rootGroup);
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

watch(() => props.modelValue, syncFromProps, { deep: true, immediate: true });
</script>

<style scoped>
.filter-group-wrapper {
	width: 100%;
	font-family: var(--fxr-font-family);
}

.root-filter-container {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.root-group-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	border-bottom: 1px solid var(--fxr-border-subtle, #e2e8f0);
	padding-bottom: 6px;
}

.logic-toggle {
	display: flex;
	background-color: var(--fxr-surface-2, #e2e8f0);
	padding: 2px;
	border-radius: 4px;
}

.logic-btn {
	border: none;
	background: transparent;
	padding: 2px 12px;
	border-radius: 3px;
	font-size: 11px;
	font-weight: 800;
	color: var(--fxr-text-soft, #64748b);
	cursor: pointer;
}

.logic-btn.active {
	background-color: var(--fxr-accent, #2563eb);
	color: #ffffff;
}

.root-group-body {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.border-dashed {
	border: 1px dashed var(--fxr-border, #cbd5e1);
}
</style>
