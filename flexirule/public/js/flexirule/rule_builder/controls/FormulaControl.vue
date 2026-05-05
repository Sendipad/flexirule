<template>
	<div class="formula-control" ref="controlRef">
		<!-- Token UI -->
		<div class="formula-token" :class="{ 'is-active': showPopover }" @click="togglePopover">
			<div class="token-content">
				<i class="fa fa-calculator text-muted mr-1"></i>
				<span class="token-text">{{ previewText }}</span>
			</div>
			<i class="fa fa-chevron-down token-caret"></i>
		</div>

		<!-- Popover -->
		<div v-if="showPopover" class="formula-popover shadow-sm">
			<div class="popover-header">
				<span class="font-weight-bold extra-small text-uppercase text-muted">{{
					__("Configure Date Formula")
				}}</span>
				<button class="btn btn-xs btn-link p-0 text-muted" @click="closePopover">
					<i class="fa fa-times"></i>
				</button>
			</div>
			<div class="popover-body">
				<!-- Base Date Row -->
				<div class="config-row">
					<label class="control-label small">{{ __("Base Date") }}</label>
					<div class="d-flex gap-2">
						<select
							class="form-control input-xs flex-1"
							v-model="localState.base_type"
							:disabled="readOnly"
						>
							<option value="today">{{ __("Today") }}</option>
							<option value="doc_field">{{ __("Document Field") }}</option>
						</select>
						<select
							v-if="localState.base_type === 'doc_field'"
							class="form-control input-xs flex-1"
							v-model="localState.base_field"
							:disabled="readOnly"
						>
							<option
								v-for="opt in dateFieldOptions"
								:key="opt.value"
								:value="opt.value"
							>
								{{ opt.label }}
							</option>
						</select>
					</div>
				</div>

				<!-- Modifier Row -->
				<div class="config-row mt-2">
					<label class="control-label small">{{ __("Offset") }}</label>
					<div class="d-flex align-items-center gap-2">
						<select
							class="form-control input-xs"
							v-model="localState.offset_sign"
							style="width: 60px"
							:disabled="readOnly"
						>
							<option value="+">+</option>
							<option value="-">-</option>
						</select>
						<input
							type="number"
							class="form-control input-xs"
							style="width: 60px"
							v-model.number="localState.offset_value"
							min="0"
							:disabled="readOnly"
						/>
						<select
							class="form-control input-xs flex-1"
							v-model="localState.offset_unit"
							:disabled="readOnly"
						>
							<option value="days">{{ __("Days") }}</option>
							<option value="weeks">{{ __("Weeks") }}</option>
							<option value="months">{{ __("Months") }}</option>
							<option value="years">{{ __("Years") }}</option>
							<option value="hours">{{ __("Hours") }}</option>
						</select>
					</div>
				</div>
			</div>
			<div class="popover-footer">
				<div class="preview-snippet text-muted extra-small">
					<code>{{ expressionSnippet }}</code>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useStore } from "../stores";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({}),
	},
	doctype: {
		type: String,
		default: "",
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const controlRef = ref(null);
const showPopover = ref(false);
let _syncing = false;

const localState = ref({
	base_type: "today",
	base_field: "",
	offset_sign: "+",
	offset_value: 0,
	offset_unit: "days",
});

const dateFieldOptions = computed(() => {
	const dt = props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];

	const allowedTypes = new Set(["Date", "Datetime"]);
	return fields
		.filter((f) => allowedTypes.has(f.fieldtype))
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) {
				realLabel = match[1];
			}
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

// Sync from props
const syncFromProps = () => {
	const val = props.modelValue || {};

	// Backward compatibility mapping from old `function_name` schema
	let baseType = val.base_type || "today";
	let baseField = val.base_field || "";
	let offsetValue = val.offset_value || 0;
	let offsetUnit = val.offset_unit || "days";

	if (val.function_name) {
		if (val.function_name.includes("doc")) baseType = "doc_field";
		else baseType = "today";

		if (val.offset_days) {
			offsetValue = val.offset_days;
			offsetUnit = "days";
		}
	}

	if (!baseField && dateFieldOptions.value.length > 0) {
		baseField = dateFieldOptions.value[0].value;
	}

	const next = {
		base_type: baseType,
		base_field: baseField,
		offset_sign: offsetValue < 0 ? "-" : "+",
		offset_value: Math.abs(offsetValue),
		offset_unit: offsetUnit,
	};

	// Deep equality check – skip if already in sync to prevent loops
	const cur = localState.value;
	if (
		cur.base_type === next.base_type &&
		cur.base_field === next.base_field &&
		cur.offset_sign === next.offset_sign &&
		cur.offset_value === next.offset_value &&
		cur.offset_unit === next.offset_unit
	) {
		return;
	}

	_syncing = true;
	localState.value = next;
	_syncing = false;
};

watch(() => props.modelValue, syncFromProps, { deep: true });
watch(() => props.doctype, syncFromProps);

// Sync to parent – guarded to avoid emitting during prop-sync
watch(
	() => localState.value,
	(newVal) => {
		if (_syncing) return;
		const offset =
			newVal.offset_sign === "-"
				? -Math.abs(newVal.offset_value)
				: Math.abs(newVal.offset_value);
		const emittedValue = {
			kind: "date_formula",
			base_type: newVal.base_type,
			base_field: newVal.base_field,
			offset_value: offset,
			offset_unit: newVal.offset_unit,
		};
		emit("update:modelValue", emittedValue);
	},
	{ deep: true }
);

onMounted(() => {
	syncFromProps();
	document.addEventListener("click", handleClickOutside);
});

onBeforeUnmount(() => {
	document.removeEventListener("click", handleClickOutside);
});

const handleClickOutside = (e) => {
	if (controlRef.value && !controlRef.value.contains(e.target)) {
		showPopover.value = false;
	}
};

const togglePopover = () => {
	if (props.readOnly) return;
	showPopover.value = !showPopover.value;
};

const closePopover = () => {
	showPopover.value = false;
};

const previewText = computed(() => {
	const base =
		localState.value.base_type === "today"
			? __("Today")
			: localState.value.base_field || __("Doc Field");
	const val = localState.value.offset_value;
	if (val === 0) return base;
	const sign = localState.value.offset_sign;
	const unit = localState.value.offset_unit;
	return `${base} ${sign} ${val} ${unit}`;
});

const expressionSnippet = computed(() => {
	const baseExpr =
		localState.value.base_type === "today"
			? "frappe.utils.nowdate()"
			: `doc.${localState.value.base_field}`;
	const offset =
		localState.value.offset_sign === "-"
			? -Math.abs(localState.value.offset_value)
			: Math.abs(localState.value.offset_value);
	if (offset === 0) return `{${baseExpr}}`;
	return `{frappe.utils.add_to_date(${baseExpr}, ${localState.value.offset_unit}=${offset})}`;
});
</script>

<style scoped>
/* ─── FormulaControl – Unified Design ─── */
.formula-control {
	position: relative;
	display: inline-block;
	min-width: 140px;
}

.formula-token {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--fr-space-2) var(--fr-space-4);
	background: var(--fr-bg-muted);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-md);
	cursor: pointer;
	transition: all var(--fr-transition-fast);
	height: var(--fr-input-height);
	user-select: none;
}

.formula-token:hover,
.formula-token.is-active {
	border-color: var(--fr-accent);
	background: var(--fr-bg-card);
	box-shadow: var(--fr-shadow-focus);
}

.token-content {
	display: flex;
	align-items: center;
	gap: var(--fr-space-3);
	overflow: hidden;
}

.token-text {
	font-size: var(--fr-text-base);
	color: var(--fr-text);
	font-weight: var(--fr-weight-medium);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.token-caret {
	font-size: 10px;
	color: var(--fr-text-muted);
	flex-shrink: 0;
}

.formula-popover {
	position: absolute;
	top: calc(100% + 4px);
	left: 0;
	z-index: var(--fr-z-popover, 100020);
	width: 280px;
	background: var(--fr-bg-card);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	box-shadow: var(--fr-shadow-lg);
	display: flex;
	flex-direction: column;
}

.popover-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--fr-space-4) var(--fr-space-6);
	border-bottom: 1px solid var(--fr-bg-muted);
	background: var(--fr-bg-muted);
	border-radius: var(--fr-radius-lg) var(--fr-radius-lg) 0 0;
}

.popover-body {
	padding: var(--fr-space-6);
}

.popover-body .form-control {
	height: var(--fr-input-height) !important;
	font-size: var(--fr-input-font-size) !important;
	border: 1px solid var(--fr-border) !important;
	border-radius: var(--fr-radius-md) !important;
	padding: var(--fr-input-padding-y) var(--fr-input-padding-x) !important;
	transition: border-color var(--fr-transition-fast), box-shadow var(--fr-transition-fast) !important;
}

.popover-body .form-control:focus {
	border-color: var(--fr-border-focus) !important;
	box-shadow: var(--fr-shadow-focus) !important;
}

.popover-body select.form-control {
	appearance: none !important;
	-webkit-appearance: none !important;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E") !important;
	background-repeat: no-repeat !important;
	background-position: right 6px center !important;
	background-size: 12px !important;
	padding-right: 24px !important;
	cursor: pointer;
}

.popover-body input[type="number"] {
	-moz-appearance: textfield;
}

.popover-body input[type="number"]::-webkit-inner-spin-button,
.popover-body input[type="number"]::-webkit-outer-spin-button {
	-webkit-appearance: none;
	margin: 0;
}

.popover-footer {
	padding: var(--fr-space-4) var(--fr-space-6);
	border-top: 1px solid var(--fr-bg-muted);
	background: var(--fr-bg-muted);
	border-radius: 0 0 var(--fr-radius-lg) var(--fr-radius-lg);
}

.preview-snippet {
	font-family: var(--fr-font-mono);
	word-break: break-all;
	text-align: center;
	font-size: var(--fr-text-xs);
}

.preview-snippet code {
	background: transparent;
	color: var(--fr-text-secondary);
	font-size: inherit;
}

.config-row {
	display: flex;
	flex-direction: column;
	gap: var(--fr-space-2);
}

.config-row label {
	font-size: var(--fr-text-sm);
	font-weight: var(--fr-weight-medium);
	color: var(--fr-text-secondary);
}

.gap-2 {
	gap: var(--fr-space-4);
}
</style>
