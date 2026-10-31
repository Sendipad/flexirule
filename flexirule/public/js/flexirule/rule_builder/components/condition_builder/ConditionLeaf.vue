<template>
	<div class="condition-leaf" :class="{ 'has-error': hasError }">
		<!-- Left Operand -->
		<div class="operand-col left-operand">
			<FlexValueControl
				:modelValue="localDomain.left"
				:docFields="docFields"
				:variableOptions="variableOptions"
				:readOnly="readOnly"
				:placeholder="__('Select left operand...')"
				@update:modelValue="onUpdateLeft"
			/>
		</div>

		<!-- Operator Selector -->
		<div class="operator-col">
			<select
				class="form-control form-control-sm operator-select"
				:value="localDomain.op"
				:disabled="readOnly"
				@change="onUpdateOp($event.target.value)"
			>
				<option v-for="op in operatorOptions" :key="op.id" :value="op.id">
					{{ op.label }}
				</option>
			</select>
		</div>

		<!-- Right Operand (when operator arity is 2) -->
		<div v-if="requiresRightOperand" class="operand-col right-operand">
			<FlexValueControl
				:modelValue="localDomain.right"
				:docFields="docFields"
				:variableOptions="variableOptions"
				:readOnly="readOnly"
				:placeholder="__('Select right operand...')"
				@update:modelValue="onUpdateRight"
			/>
		</div>

		<!-- Errors Display -->
		<div v-if="validationErrors.length" class="leaf-errors text-danger small w-100 mt-1">
			<div v-for="(err, idx) in validationErrors" :key="idx">
				<i class="fa fa-exclamation-circle mr-1"></i> {{ err }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import { validateComparisonDomain } from "./canonical_condition_validator.mjs";

const props = defineProps({
	domain: {
		type: Object,
		required: true,
	},
	operators: {
		type: Array,
		default: () => [],
	},
	docFields: {
		type: Array,
		default: () => [],
	},
	variableOptions: {
		type: Array,
		default: () => [],
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
	showValidation: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:domain"]);

const localDomain = computed(
	() => props.domain || { type: "comparison", op: "eq", left: null, right: null }
);

const operatorOptions = computed(() => props.operators || []);

const currentOperatorMeta = computed(() => {
	return operatorOptions.value.find((op) => op.id === localDomain.value.op);
});

const requiresRightOperand = computed(() => {
	const meta = currentOperatorMeta.value;
	return meta ? meta.arity !== 1 : true;
});

const validationErrors = computed(() => {
	if (!props.showValidation) return [];
	return validateComparisonDomain(localDomain.value, operatorOptions.value);
});

const hasError = computed(() => validationErrors.value.length > 0);

function onUpdateLeft(val) {
	const updated = { ...localDomain.value, left: val };
	emit("update:domain", updated);
}

function onUpdateOp(newOp) {
	const meta = operatorOptions.value.find((op) => op.id === newOp);
	const updated = { ...localDomain.value, op: newOp };

	// If switching to unary operator, remove right operand
	if (meta && meta.arity === 1) {
		delete updated.right;
	} else if (updated.right === undefined) {
		updated.right = { mode: "static", value: "" };
	}

	emit("update:domain", updated);
}

function onUpdateRight(val) {
	const updated = { ...localDomain.value, right: val };
	emit("update:domain", updated);
}
</script>

<style scoped>
.condition-leaf {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: var(--fxr-space-2, 8px);
	width: 100%;
}

.operand-col {
	flex: 1 1 200px;
	min-width: 160px;
}

.operator-col {
	flex: 0 0 160px;
}

.operator-select {
	font-weight: 500;
	background-color: var(--fxr-bg-surface, #ffffff);
	border-color: var(--fxr-border, #d1d5db);
}

.condition-leaf.has-error {
	padding: 4px;
	border: 1px solid var(--fxr-danger-border, #fca5a5);
	border-radius: 4px;
	background-color: var(--fxr-danger-bg-subtle, #fef2f2);
}
</style>
