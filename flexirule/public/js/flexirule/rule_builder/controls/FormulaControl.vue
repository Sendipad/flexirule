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
		<div v-if="showPopover" class="formula-popover">
			<div class="popover-header">
				<span class="popover-title">{{ __("Configure Date Formula") }}</span>
				<button class="fr-btn fr-btn--icon fr-btn--sm" @click="closePopover">
					<i class="fa fa-times"></i>
				</button>
			</div>
			<div class="popover-body">
				<!-- Base Date Row -->
				<div class="config-row">
					<label class="fr-label-sm">{{ __("Base Date") }}</label>
					<div class="d-flex fr-gap-2">
						<select
							class="fr-select flex-1"
							v-model="localState.base_type"
							:disabled="readOnly"
						>
							<option value="today">{{ __("Today") }}</option>
							<option value="doc_field">{{ __("Document Field") }}</option>
						</select>
						<select
							v-if="localState.base_type === 'doc_field'"
							class="fr-select flex-1"
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
				<div class="config-row mt-4">
					<label class="fr-label-sm">{{ __("Offset") }}</label>
					<div class="d-flex align-items-center fr-gap-2">
						<select
							class="fr-select"
							v-model="localState.offset_sign"
							style="width: 70px"
							:disabled="readOnly"
						>
							<option value="+">+</option>
							<option value="-">-</option>
						</select>
						<input
							type="number"
							class="fr-input"
							style="width: 80px"
							v-model.number="localState.offset_value"
							min="0"
							:disabled="readOnly"
						/>
						<select
							class="fr-select flex-1"
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
				<div class="preview-snippet">
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
.formula-control {
	position: relative;
	display: block;
	width: 100%;
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
}

.formula-popover {
	position: absolute;
	top: calc(100% + var(--fr-space-2));
	left: 0;
	z-index: var(--fr-z-popover);
	width: 320px;
	background: var(--fr-bg-card);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	box-shadow: var(--fr-shadow-lg);
}

.popover-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--fr-space-4) var(--fr-space-6);
	background: var(--fr-bg-muted);
	border-radius: var(--fr-radius-lg) var(--fr-radius-lg) 0 0;
	border-bottom: 1px solid var(--fr-border);
}

.popover-title {
	font-size: var(--fr-text-sm);
	font-weight: var(--fr-weight-semibold);
	color: var(--fr-text-secondary);
	text-transform: uppercase;
	letter-spacing: 0.05em;
}

.popover-body {
	padding: var(--fr-space-6);
	display: flex;
	flex-direction: column;
	gap: var(--fr-space-5);
}

.popover-footer {
	padding: var(--fr-space-4) var(--fr-space-6);
	background: var(--fr-bg-muted);
	border-radius: 0 0 var(--fr-radius-lg) var(--fr-radius-lg);
	border-top: 1px solid var(--fr-border);
}

.preview-snippet {
	font-family: var(--fr-font-mono);
	font-size: var(--fr-text-xs);
	color: var(--fr-text-muted);
	text-align: center;
}

.preview-snippet code {
	background: transparent;
	color: var(--fr-accent);
}

.config-row {
	display: flex;
	flex-direction: column;
	gap: var(--fr-space-2);
}

.fr-gap-2 {
	gap: var(--fr-space-3);
}
</style>
