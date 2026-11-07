<template>
	<div class="inline-operator-token-wrap">
		<button
			ref="buttonRef"
			type="button"
			class="inline-operator-token"
			:class="{ 'is-empty': !modelValue, 'is-open': isOpen }"
			:disabled="disabled || readOnly"
			@click="toggleDropdown"
		>
			<span>{{ currentLabel }}</span>
			<i v-if="!readOnly" class="fa fa-angle-down ml-1"></i>
		</button>

		<!-- Operator Selection Popover -->
		<Teleport to="body">
			<div
				v-if="isOpen"
				ref="dropdownRef"
				class="operator-dropdown-menu"
				:style="dropdownStyle"
			>
				<div class="operator-dropdown-header">
					{{ __("Select Comparison") }}
				</div>
				<div class="operator-dropdown-list">
					<div
						v-for="op in compatibleOperators"
						:key="op.id"
						class="operator-dropdown-item"
						:class="{ 'is-selected': op.id === modelValue }"
						@click="selectOperator(op.id)"
					>
						<span class="operator-item-label">{{ op.label || op.id }}</span>
						<span v-if="op.arity === 1" class="operator-item-unary">{{
							__("unary")
						}}</span>
					</div>
					<div v-if="compatibleOperators.length === 0" class="operator-empty-state">
						{{ __("No compatible comparisons") }}
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from "vue";

const props = defineProps({
	modelValue: { type: String, default: "" },
	contract: { type: Object, default: () => ({}) },
	leftFieldtype: { type: String, default: "Data" },
	leftValueType: { type: String, default: "string" },
	leftValueTypes: { type: Array, default: () => ["string"] },
	readOnly: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change"]);

const isOpen = ref(false);
const buttonRef = ref(null);
const dropdownRef = ref(null);
const dropdownStyle = ref({});

const allContractOperators = computed(() => {
	const ops = props.contract?.operators;
	if (Array.isArray(ops)) return ops;
	if (ops && typeof ops === "object") return Object.values(ops);
	return [];
});

const compatibleOperators = computed(() => {
	const ft = props.leftFieldtype;
	const vts = props.leftValueTypes.length > 0 ? props.leftValueTypes : [props.leftValueType];

	return allContractOperators.value.filter((opSpec) => {
		if (opSpec.fieldtypes && Array.isArray(opSpec.fieldtypes)) {
			if (!opSpec.fieldtypes.includes(ft)) return false;
		}
		if (opSpec.accepted_left_types && Array.isArray(opSpec.accepted_left_types)) {
			if (!vts.some((v) => opSpec.accepted_left_types.includes(v))) return false;
		}
		return true;
	});
});

const currentLabel = computed(() => {
	if (!props.modelValue) return __("Choose operator...");
	const match = allContractOperators.value.find((op) => op.id === props.modelValue);
	return match?.label || props.modelValue;
});

function toggleDropdown() {
	if (props.disabled || props.readOnly) return;
	isOpen.value = !isOpen.value;
	if (isOpen.value) {
		nextTick(updatePosition);
	}
}

function selectOperator(opId) {
	emit("update:modelValue", opId);
	emit("change", opId);
	isOpen.value = false;
}

function updatePosition() {
	if (!buttonRef.value) return;
	const rect = buttonRef.value.getBoundingClientRect();
	dropdownStyle.value = {
		position: "fixed",
		top: `${rect.bottom + 4}px`,
		left: `${Math.max(12, Math.min(rect.left, window.innerWidth - 220))}px`,
		zIndex: 9999,
	};
}

function handleClickOutside(event) {
	if (!isOpen.value) return;
	if (
		dropdownRef.value &&
		!dropdownRef.value.contains(event.target) &&
		buttonRef.value &&
		!buttonRef.value.contains(event.target)
	) {
		isOpen.value = false;
	}
}

onMounted(() => {
	document.addEventListener("mousedown", handleClickOutside);
	window.addEventListener("resize", updatePosition);
	window.addEventListener("scroll", updatePosition, true);
});

onBeforeUnmount(() => {
	document.removeEventListener("mousedown", handleClickOutside);
	window.removeEventListener("resize", updatePosition);
	window.removeEventListener("scroll", updatePosition, true);
});
</script>

<style scoped>
.inline-operator-token-wrap {
	display: inline-flex;
	align-items: center;
}

.inline-operator-token {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 4px 10px;
	border-radius: 6px;
	font-size: 13px;
	font-weight: 600;
	color: #1e293b;
	background: #f1f5f9;
	border: 1px solid #cbd5e1;
	cursor: pointer;
	transition: all 0.15s ease;
	outline: none;
	white-space: nowrap;
}

.inline-operator-token:hover:not(:disabled) {
	background: #e2e8f0;
	border-color: #94a3b8;
}

.inline-operator-token.is-empty {
	color: #64748b;
	font-weight: 500;
	border-style: dashed;
}

.inline-operator-token:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

.operator-dropdown-menu {
	width: 220px;
	max-height: 280px;
	background: #ffffff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
	overflow: hidden;
	display: flex;
	flex-direction: column;
	font-family: inherit;
}

.operator-dropdown-header {
	padding: 6px 10px;
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: #64748b;
	background: #f8fafc;
	border-bottom: 1px solid #f1f5f9;
}

.operator-dropdown-list {
	overflow-y: auto;
	padding: 4px 0;
	max-height: 240px;
}

.operator-dropdown-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 6px 10px;
	font-size: 12px;
	color: #1e293b;
	cursor: pointer;
	transition: background-color 0.1s ease;
}

.operator-dropdown-item:hover {
	background-color: #f1f5f9;
}

.operator-dropdown-item.is-selected {
	background-color: #eef2ff;
	color: #4f46e5;
	font-weight: 600;
}

.operator-item-unary {
	font-size: 10px;
	font-family: monospace;
	padding: 1px 4px;
	background: #e2e8f0;
	color: #64748b;
	border-radius: 3px;
}

.operator-empty-state {
	padding: 12px;
	font-size: 12px;
	color: #94a3b8;
	text-align: center;
}
</style>
