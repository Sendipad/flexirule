<template>
	<div class="value-resolver-control" ref="controlRef">
		<!-- Token UI -->
		<div class="resolver-token" :class="{ 'is-active': showPopover }" @click="togglePopover">
			<div class="token-content">
				<i :class="categoryIcon" class="text-muted mr-1"></i>
				<span class="token-text">{{ previewText }}</span>
			</div>
			<i class="fa fa-chevron-down token-caret"></i>
		</div>

		<!-- Popover -->
		<div v-if="showPopover" class="resolver-popover shadow-sm">
			<div class="popover-header">
				<span class="font-weight-bold extra-small text-uppercase text-muted">{{
					__(popoverTitle)
				}}</span>
				<button class="btn btn-xs btn-link p-0 text-muted" @click="closePopover">
					<i class="fa fa-times"></i>
				</button>
			</div>
			<div class="popover-body">
				<!-- Category Selector -->
				<div class="config-row mb-3">
					<label class="control-label small">{{ __("Formula Type") }}</label>
					<select
						class="form-control input-xs"
						v-model="localState.kind"
						:disabled="readOnly"
					>
						<option
							v-for="cat in availableCategories"
							:key="cat.value"
							:value="cat.value"
						>
							{{ cat.label }}
						</option>
					</select>
				</div>

				<hr class="my-2 border-top" />

				<!-- ═══════════ Date Formula ═══════════ -->
				<template v-if="localState.kind === 'date_formula'">
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
				</template>

				<!-- ═══════════ Math Formula ═══════════ -->
				<template v-else-if="localState.kind === 'math_formula'">
					<div class="config-row">
						<label class="control-label small">{{ __("Field A") }}</label>
						<select
							class="form-control input-xs"
							v-model="localState.field_a"
							:disabled="readOnly"
						>
							<option value="">{{ __("Select field...") }}</option>
							<option
								v-for="opt in numericFieldOptions"
								:key="opt.value"
								:value="opt.value"
							>
								{{ opt.label }}
							</option>
						</select>
					</div>
					<div class="config-row mt-2">
						<label class="control-label small">{{ __("Operator") }}</label>
						<div class="d-flex gap-2">
							<select
								class="form-control input-xs"
								v-model="localState.math_op"
								:disabled="readOnly"
							>
								<option value="+">{{ __("Add (+)") }}</option>
								<option value="-">{{ __("Subtract (-)") }}</option>
								<option value="*">{{ __("Multiply (×)") }}</option>
								<option value="/">{{ __("Divide (÷)") }}</option>
							</select>
						</div>
					</div>
					<div class="config-row mt-2">
						<label class="control-label small">{{ __("Field B / Value") }}</label>
						<div class="d-flex gap-2">
							<select
								class="form-control input-xs flex-1"
								v-model="localState.field_b_type"
								:disabled="readOnly"
							>
								<option value="field">{{ __("Document Field") }}</option>
								<option value="constant">{{ __("Fixed Value") }}</option>
							</select>
							<select
								v-if="localState.field_b_type === 'field'"
								class="form-control input-xs flex-1"
								v-model="localState.field_b"
								:disabled="readOnly"
							>
								<option value="">{{ __("Select field...") }}</option>
								<option
									v-for="opt in numericFieldOptions"
									:key="opt.value"
									:value="opt.value"
								>
									{{ opt.label }}
								</option>
							</select>
							<input
								v-else
								type="number"
								step="any"
								class="form-control input-xs flex-1"
								v-model.number="localState.constant_b"
								:disabled="readOnly"
								:placeholder="__('Enter value')"
							/>
						</div>
					</div>
					<div class="config-row mt-2">
						<label class="control-label small">{{ __("Round To") }}</label>
						<div class="d-flex align-items-center gap-2">
							<input
								type="number"
								class="form-control input-xs"
								style="width: 60px"
								v-model.number="localState.precision"
								min="0"
								max="9"
								:disabled="readOnly"
							/>
							<span class="text-muted small">{{ __("decimal places") }}</span>
						</div>
					</div>
				</template>

				<!-- ═══════════ Date Difference ═══════════ -->
				<template v-else-if="localState.kind === 'date_diff'">
					<div class="config-row">
						<label class="control-label small">{{ __("Start Date") }}</label>
						<div class="d-flex gap-2">
							<select
								class="form-control input-xs flex-1"
								v-model="localState.diff_start_type"
								:disabled="readOnly"
							>
								<option value="today">{{ __("Today") }}</option>
								<option value="doc_field">{{ __("Document Field") }}</option>
							</select>
							<select
								v-if="localState.diff_start_type === 'doc_field'"
								class="form-control input-xs flex-1"
								v-model="localState.diff_start_field"
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
					<div class="config-row mt-2">
						<label class="control-label small">{{ __("End Date") }}</label>
						<div class="d-flex gap-2">
							<select
								class="form-control input-xs flex-1"
								v-model="localState.diff_end_type"
								:disabled="readOnly"
							>
								<option value="today">{{ __("Today") }}</option>
								<option value="doc_field">{{ __("Document Field") }}</option>
							</select>
							<select
								v-if="localState.diff_end_type === 'doc_field'"
								class="form-control input-xs flex-1"
								v-model="localState.diff_end_field"
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
					<div class="config-row mt-2">
						<label class="control-label small">{{ __("Result Unit") }}</label>
						<select
							class="form-control input-xs"
							v-model="localState.diff_unit"
							:disabled="readOnly"
						>
							<option value="days">{{ __("Days") }}</option>
							<option value="months">{{ __("Months") }}</option>
							<option value="years">{{ __("Years") }}</option>
						</select>
					</div>
				</template>
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
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
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
	/** Restrict which formula categories are available */
	allowedKinds: {
		type: Array,
		default: null, // null = all categories
	},
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const controlRef = ref(null);
const showPopover = ref(false);
let _syncing = false;

// ─── Category Definitions ───
const ALL_CATEGORIES = [
	{ value: "date_formula", label: __("Date Formula"), icon: "fa fa-calendar" },
	{ value: "math_formula", label: __("Math Formula"), icon: "fa fa-calculator" },
	{ value: "date_diff", label: __("Date Difference"), icon: "fa fa-calendar-minus-o" },
];

const availableCategories = computed(() => {
	if (props.allowedKinds && props.allowedKinds.length > 0) {
		return ALL_CATEGORIES.filter((c) => props.allowedKinds.includes(c.value));
	}
	return ALL_CATEGORIES;
});

// ─── Default State Factory ───
function getDefaultState(kind = "date_formula") {
	return {
		kind,
		// Date Formula fields
		base_type: "today",
		base_field: "",
		offset_sign: "+",
		offset_value: 0,
		offset_unit: "days",
		// Math Formula fields
		field_a: "",
		math_op: "+",
		field_b_type: "field",
		field_b: "",
		constant_b: 0,
		precision: 2,
		// Date Diff fields
		diff_start_type: "today",
		diff_start_field: "",
		diff_end_type: "doc_field",
		diff_end_field: "",
		diff_unit: "days",
	};
}

const localState = ref(getDefaultState());

// ─── Field Options ───
const dateFieldOptions = computed(() => {
	const dt = props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Date", "Datetime"].includes(f.fieldtype))
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

const numericFieldOptions = computed(() => {
	const dt = props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

// ─── Sync from Props (Hydration) ───
const syncFromProps = () => {
	const val = props.modelValue || {};
	const kind = val.kind || "date_formula";
	const next = { ...getDefaultState(kind) };

	if (kind === "date_formula") {
		// Backward compat: support old `function_name` schema
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

		next.base_type = baseType;
		next.base_field = baseField;
		next.offset_sign = offsetValue < 0 ? "-" : "+";
		next.offset_value = Math.abs(offsetValue);
		next.offset_unit = offsetUnit;
	} else if (kind === "math_formula") {
		next.field_a = val.field_a || "";
		next.math_op = val.math_op || "+";
		next.field_b_type = val.field_b_type || "field";
		next.field_b = val.field_b || "";
		next.constant_b = val.constant_b ?? 0;
		next.precision = val.precision ?? 2;
	} else if (kind === "date_diff") {
		next.diff_start_type = val.diff_start_type || "today";
		next.diff_start_field = val.diff_start_field || "";
		next.diff_end_type = val.diff_end_type || "doc_field";
		next.diff_end_field = val.diff_end_field || "";
		next.diff_unit = val.diff_unit || "days";
	}

	// Shallow equality guard to prevent loops
	const cur = localState.value;
	const keys = Object.keys(next);
	let changed = false;
	for (const key of keys) {
		if (cur[key] !== next[key]) {
			changed = true;
			break;
		}
	}
	if (!changed) return;

	_syncing = true;
	localState.value = next;
	_syncing = false;
};

watch(() => props.modelValue, syncFromProps, { deep: true });
watch(() => props.doctype, syncFromProps);

// ─── Sync to Parent ───
watch(
	() => localState.value,
	(newVal) => {
		if (_syncing) return;

		const emitted = { kind: newVal.kind };

		if (newVal.kind === "date_formula") {
			const offset =
				newVal.offset_sign === "-"
					? -Math.abs(newVal.offset_value)
					: Math.abs(newVal.offset_value);
			Object.assign(emitted, {
				base_type: newVal.base_type,
				base_field: newVal.base_field,
				offset_value: offset,
				offset_unit: newVal.offset_unit,
			});
		} else if (newVal.kind === "math_formula") {
			Object.assign(emitted, {
				field_a: newVal.field_a,
				math_op: newVal.math_op,
				field_b_type: newVal.field_b_type,
				field_b: newVal.field_b,
				constant_b: newVal.constant_b,
				precision: newVal.precision,
			});
		} else if (newVal.kind === "date_diff") {
			Object.assign(emitted, {
				diff_start_type: newVal.diff_start_type,
				diff_start_field: newVal.diff_start_field,
				diff_end_type: newVal.diff_end_type,
				diff_end_field: newVal.diff_end_field,
				diff_unit: newVal.diff_unit,
			});
		}

		emit("update:modelValue", emitted);
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

// ─── Computed UI Properties ───
const categoryIcon = computed(() => {
	const cat = ALL_CATEGORIES.find((c) => c.value === localState.value.kind);
	return cat?.icon || "fa fa-calculator";
});

const popoverTitle = computed(() => {
	const cat = ALL_CATEGORIES.find((c) => c.value === localState.value.kind);
	return cat?.label || __("Configure Formula");
});

const previewText = computed(() => {
	const s = localState.value;

	if (s.kind === "date_formula") {
		const base = s.base_type === "today" ? __("Today") : s.base_field || __("Doc Field");
		if (s.offset_value === 0) return base;
		return `${base} ${s.offset_sign} ${s.offset_value} ${s.offset_unit}`;
	}

	if (s.kind === "math_formula") {
		const a = s.field_a || "?";
		const b = s.field_b_type === "field" ? s.field_b || "?" : s.constant_b;
		return `${a} ${s.math_op} ${b}`;
	}

	if (s.kind === "date_diff") {
		const start = s.diff_start_type === "today" ? __("Today") : s.diff_start_field || "?";
		const end = s.diff_end_type === "today" ? __("Today") : s.diff_end_field || "?";
		return `${end} − ${start} (${s.diff_unit})`;
	}

	return __("Configure");
});

const expressionSnippet = computed(() => {
	const s = localState.value;

	if (s.kind === "date_formula") {
		const baseExpr = s.base_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.base_field}`;
		const offset = s.offset_sign === "-" ? -Math.abs(s.offset_value) : Math.abs(s.offset_value);
		if (offset === 0) return `{${baseExpr}}`;
		if (s.offset_unit === "days") {
			return `{frappe.utils.add_days(${baseExpr}, ${offset})}`;
		}
		return `{frappe.utils.add_to_date(${baseExpr}, ${s.offset_unit}=${offset})}`;
	}

	if (s.kind === "math_formula") {
		const a = s.field_a ? `frappe.utils.flt(doc.${s.field_a})` : "0";
		const b =
			s.field_b_type === "field"
				? s.field_b
					? `frappe.utils.flt(doc.${s.field_b})`
					: "0"
				: String(s.constant_b ?? 0);
		const prec = s.precision ?? 2;
		return `{frappe.utils.flt(${a} ${s.math_op} ${b}, ${prec})}`;
	}

	if (s.kind === "date_diff") {
		const start =
			s.diff_start_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.diff_start_field}`;
		const end =
			s.diff_end_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.diff_end_field}`;

		if (s.diff_unit === "days") {
			return `{frappe.utils.date_diff(${end}, ${start})}`;
		}
		if (s.diff_unit === "months") {
			return `{frappe.utils.month_diff(${end}, ${start})}`;
		}
		// Years — month_diff / 12 rounded
		return `{int(frappe.utils.month_diff(${end}, ${start}) / 12)}`;
	}

	return "";
});
</script>

<style scoped>
/* ─── ValueResolverControl – Unified Design ─── */
.value-resolver-control {
	position: relative;
	display: block;
	width: 100%;
	min-width: 0;
}

.resolver-token {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--fr-space-2, 4px) var(--fr-space-4, 8px);
	background: var(--fr-bg-muted, #f8fafc);
	border: 1px solid var(--fr-border, #e2e8f0);
	border-radius: var(--fr-radius-md, 6px);
	cursor: pointer;
	transition: all var(--fr-transition-fast, 0.15s);
	height: var(--fr-input-height, 30px);
	user-select: none;
}

.resolver-token:hover,
.resolver-token.is-active {
	border-color: var(--fr-accent, var(--primary));
	background: var(--fr-bg-card, #fff);
	box-shadow: var(--fr-shadow-focus, 0 0 0 2px rgba(59, 130, 246, 0.08));
}

.token-content {
	display: flex;
	align-items: center;
	gap: var(--fr-space-3, 6px);
	overflow: hidden;
	min-width: 0;
}

.token-text {
	font-size: var(--fr-text-base, 12px);
	color: var(--fr-text, #1e293b);
	font-weight: var(--fr-weight-medium, 500);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.token-caret {
	font-size: 10px;
	color: var(--fr-text-muted, #94a3b8);
	flex-shrink: 0;
	margin-left: var(--fr-space-2, 4px);
}

.resolver-popover {
	position: absolute;
	top: calc(100% + 4px);
	left: 0;
	z-index: var(--fr-z-popover, 100020);
	width: 320px;
	background: var(--fr-bg-card, #fff);
	border: 1px solid var(--fr-border, #e2e8f0);
	border-radius: var(--fr-radius-lg, 8px);
	box-shadow: var(--fr-shadow-lg, 0 10px 40px rgba(0, 0, 0, 0.12));
	display: flex;
	flex-direction: column;
}

.popover-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--fr-space-4, 8px) var(--fr-space-6, 12px);
	border-bottom: 1px solid var(--fr-bg-muted, #f1f5f9);
	background: var(--fr-bg-muted, #f1f5f9);
	border-radius: var(--fr-radius-lg, 8px) var(--fr-radius-lg, 8px) 0 0;
}

.popover-body {
	padding: var(--fr-space-6, 12px);
}

.popover-body .form-control {
	height: var(--fr-input-height, 30px) !important;
	font-size: var(--fr-input-font-size, 12px) !important;
	border: 1px solid var(--fr-border, #e2e8f0) !important;
	border-radius: var(--fr-radius-md, 6px) !important;
	padding: var(--fr-input-padding-y, 4px) var(--fr-input-padding-x, 8px) !important;
	transition: border-color var(--fr-transition-fast, 0.15s),
		box-shadow var(--fr-transition-fast, 0.15s) !important;
}

.popover-body .form-control:focus {
	border-color: var(--fr-border-focus, var(--primary)) !important;
	box-shadow: var(--fr-shadow-focus, 0 0 0 2px rgba(59, 130, 246, 0.08)) !important;
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
	padding: var(--fr-space-4, 8px) var(--fr-space-6, 12px);
	border-top: 1px solid var(--fr-bg-muted, #f1f5f9);
	background: var(--fr-bg-muted, #f1f5f9);
	border-radius: 0 0 var(--fr-radius-lg, 8px) var(--fr-radius-lg, 8px);
}

.preview-snippet {
	font-family: var(--fr-font-mono, monospace);
	word-break: break-all;
	text-align: center;
	font-size: var(--fr-text-xs, 10px);
}

.preview-snippet code {
	background: transparent;
	color: var(--fr-text-secondary, #64748b);
	font-size: inherit;
}

.config-row {
	display: flex;
	flex-direction: column;
	gap: var(--fr-space-2, 4px);
}

.config-row label {
	font-size: var(--fr-text-sm, 11px);
	font-weight: var(--fr-weight-medium, 500);
	color: var(--fr-text-secondary, #64748b);
}

.gap-2 {
	gap: var(--fr-space-4, 8px);
}

hr.border-top {
	border-color: var(--fr-border, #e2e8f0);
	opacity: 0.5;
}
</style>
