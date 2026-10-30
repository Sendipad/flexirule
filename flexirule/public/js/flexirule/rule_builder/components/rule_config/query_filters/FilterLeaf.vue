<template>
	<div v-if="!doctype" class="text-muted small p-2">
		{{ __("Select a DocType to configure filters.") }}
	</div>
	<div v-else class="filter-row" :class="{ 'is-invalid': validationVisible && leafInvalid }">
		<div class="filter-row-main">
			<div class="filter-col field-col">
				<label class="filter-col-label">
					{{ __("Field") }} <span class="filter-required">*</span>
				</label>
				<ComboBoxControl
					:df="{ label: __('Field'), fieldtype: 'FieldPicker', reqd: 1 }"
					:options="navigableFields.currentFields.value"
					:doctype="doctype"
					:modelValue="leaf.field || ''"
					:placeholder="__('Select field')"
					:read_only="readOnly"
					:hideLabel="true"
					:showValidation="validationVisible"
					trigger="button"
					:navigable="true"
					:navStack="navigableFields.navStack.value"
					@navigate="navigableFields.handleNavigate"
					@back="navigableFields.handleBack"
					@update:modelValue="updateField"
				/>
			</div>
			<div class="filter-col operator-col">
				<label class="filter-col-label">
					{{ __("Operator") }} <span class="filter-required">*</span>
				</label>
				<SelectControl
					:df="operatorField"
					:modelValue="leaf.operator"
					:read_only="readOnly || !leaf.field"
					:hideLabel="true"
					:showValidation="validationVisible && operatorInvalid"
					:placeholder="__('Select operator')"
					@update:modelValue="updateOperator"
				/>
			</div>
			<div class="filter-col value-col">
				<label class="filter-col-label">
					{{ __("Value") }} <span class="filter-required">*</span>
				</label>
				<template v-if="leaf.operator === 'Between'">
					<div class="dual-value-wrapper">
						<FlexValueControl
							v-for="index in 2"
							:key="index"
							:modelValue="
								Array.isArray(leaf.value) ? leaf.value[index - 1] : emptyValue
							"
							:placeholder="index === 1 ? __('Start value') : __('End value')"
							:context="{
								df: controlSchema,
								operator: leaf.operator,
								referenceDoctype: doctype,
							}"
							:engine="store"
							:doc="store?.rule_doc"
							:variableOptions="effectiveVariableOptions"
							:disabled="readOnly"
							:showValidation="validationVisible && isMissingBetweenValue(index - 1)"
							:invalid="validationVisible && isMissingBetweenValue(index - 1)"
							@update:modelValue="(value) => updateBetween(index - 1, value)"
						/>
					</div>
				</template>
				<FlexValueControl
					v-else
					:modelValue="leaf.value"
					:placeholder="__('Enter value')"
					:context="{
						df: controlSchema,
						operator: leaf.operator,
						referenceDoctype: doctype,
					}"
					:engine="store"
					:doc="store?.rule_doc"
					:variableOptions="effectiveVariableOptions"
					:disabled="readOnly"
					:readOnly="readOnly"
					:showValidation="validationVisible && valueInvalid"
					:invalid="validationVisible && valueInvalid"
					@update:modelValue="updateValue"
				/>
			</div>
		</div>
	</div>
</template>
<script setup>
import { computed, inject, ref } from "vue";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import FlexValueControl from "../../../controls/FlexValueControl.vue";
import SelectControl from "../../../controls/SelectControl.vue";
import { useStore } from "../../../stores";
import { useNavigableFields } from "../../../composables/useNavigableFields";
import { getFieldType, getFilterOperators } from "./filter_operators.mjs";
import {
	isFilterLeafValid,
	isValueConfigured,
	isValidIsValue,
	validateFilterLeaf,
} from "./query_filter_validation.mjs";

const props = defineProps({
	modelValue: { type: Object, required: true },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: Boolean,
	variableOptions: { type: Array, default: null },
	showValidation: Boolean,
});
const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const injectedVariableOptions = inject("variableOptions", ref([]));
const effectiveVariableOptions = computed(
	() => props.variableOptions ?? injectedVariableOptions.value
);
const leaf = computed(() => props.modelValue || {});
const emptyValue = { mode: "static", value: "" };
const hasInteracted = ref(false);
const validationVisible = computed(() => props.showValidation || hasInteracted.value);
const labels = {
	"=": __("Equals"),
	"!=": __("Not Equals"),
	like: __("Like"),
	"not like": __("Not Like"),
	in: __("In"),
	"not in": __("Not In"),
	">": __("Greater Than"),
	"<": __("Less Than"),
	">=": __("Greater Than Or Equal To"),
	"<=": __("Less Than Or Equal To"),
	is: __("Is"),
	Between: __("Between"),
	Timespan: __("Timespan"),
	"starts with": __("Starts With"),
	"ends with": __("Ends With"),
	"descendants of": __("Descendants Of"),
	"descendants of (inclusive)": __("Descendants Of (inclusive)"),
	"not descendants of": __("Not Descendants Of"),
	"ancestors of": __("Ancestors Of"),
	"not ancestors of": __("Not Ancestors Of"),
};
const nestedSetOptions = () => ({
	nestedSetDoctypes: frappe.boot?.nested_set_doctypes || [],
	rootDoctype: props.doctype,
});
const field = computed(() => getFieldDef(leaf.value.field));
const operators = computed(() => getFilterOperators(field.value, nestedSetOptions()));
const operatorField = computed(() => ({
	fieldname: "operator",
	fieldtype: "Select",
	label: __("Operator"),
	reqd: 1,
	read_only: props.readOnly || !leaf.value.field,
	options: operators.value.map((operator) => ({
		label: operatorLabel(operator),
		value: operator,
	})),
}));
const operatorInvalid = computed(
	() => !leaf.value.operator || !operators.value.includes(leaf.value.operator)
);
const isConfigured = isValueConfigured;
const valueInvalid = computed(() => {
	if (!leaf.value.field) return false;
	if (operatorInvalid.value) return true;
	if (leaf.value.operator === "Between") {
		return (
			!Array.isArray(leaf.value.value) ||
			leaf.value.value.length < 2 ||
			!isValueConfigured(leaf.value.value[0]) ||
			!isValueConfigured(leaf.value.value[1])
		);
	}
	if (String(leaf.value.operator).toLowerCase() === "is")
		return !isValidIsValue(leaf.value.value);
	return !isValueConfigured(leaf.value.value);
});
function isMissingBetweenValue(index) {
	return !Array.isArray(leaf.value.value) || !isValueConfigured(leaf.value.value[index]);
}
const leafInvalid = computed(
	() => !leaf.value.field || operatorInvalid.value || valueInvalid.value
);

const operatorLabel = (op) => {
	if (["Date", "Datetime"].includes(getFieldType(field.value)))
		return (
			{
				"<": __("Before"),
				">": __("After"),
				"<=": __("On or Before"),
				">=": __("On or After"),
			}[op] ||
			labels[op] ||
			op
		);
	return labels[op] || op;
};
const navigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => leaf.value.field || ""
);
const updateValue = (value) => {
	hasInteracted.value = true;
	emit("update:modelValue", { ...leaf.value, value });
};
function updateField(value) {
	hasInteracted.value = true;
	const next = { ...leaf.value, field: value };
	const def = getFieldDef(value);
	const allowed = getOperators(def);
	if (!allowed.includes(next.operator)) next.operator = allowed[0] || "=";
	if (String(leaf.value.field || "") !== String(value || "")) {
		next.value =
			next.operator === "Between"
				? [{ ...emptyValue }, { ...emptyValue }]
				: { ...emptyValue };
	}
	// useNavigableFields watches the selected path and resolves metadata in its Link/Table
	// context. Resetting to the root here discards nested field metadata and can leave the
	// operator options and value control mapped to the wrong field type.
	emit("update:modelValue", next);
}
function getOperators(def) {
	return getFilterOperators(def, nestedSetOptions());
}
function updateOperator(operator) {
	hasInteracted.value = true;
	let value = leaf.value.value;
	if (operator === "Between" && !Array.isArray(value))
		value = [{ ...emptyValue }, { ...emptyValue }];
	if (leaf.value.operator === "Between" && operator !== "Between" && Array.isArray(value))
		value = value[0] || { ...emptyValue };
	emit("update:modelValue", { ...leaf.value, operator, value });
}
function updateBetween(index, value) {
	hasInteracted.value = true;
	const values = Array.isArray(leaf.value.value)
		? [...leaf.value.value]
		: [{ ...emptyValue }, { ...emptyValue }];
	values[index] = value;
	emit("update:modelValue", { ...leaf.value, value: values });
}
function getFieldDef(fieldname) {
	if (!fieldname) return null;
	if (fieldname === "name")
		return { fieldname, value: fieldname, fieldtype: "Data", label: "Name" };
	if (["owner", "modified_by"].includes(fieldname))
		return {
			fieldname,
			value: fieldname,
			fieldtype: "Link",
			options: "User",
			label: fieldname,
		};
	if (["creation", "modified"].includes(fieldname))
		return { fieldname, value: fieldname, fieldtype: "Datetime", label: fieldname };
	if (fieldname === "docstatus")
		return { fieldname, value: fieldname, fieldtype: "Int", label: "Docstatus" };
	// Use the picker entry first so nested Link/Table paths keep the metadata
	// for the context in which the user selected the field.
	const pickerField = navigableFields.currentFields.value.find(
		(item) => item.value === fieldname
	);
	if (pickerField) return { ...(pickerField.raw || {}), ...pickerField, value: fieldname };

	const raw = String(fieldname).replace(/^doc\./, "");
	if (frappe.meta?.has_field?.(props.doctype, raw)) {
		const df = frappe.meta.get_docfield(props.doctype, raw);
		return df ? { ...df, value: fieldname } : null;
	}
	return null;
}
const controlSchema = computed(() => {
	let schema = field.value
		? frappe.utils.deep_clone(field.value)
		: { fieldtype: "Data", fieldname: "value" };
	schema.label = __("Value");
	schema.placeholder = __("Enter value");
	schema.reqd = String(leaf.value.operator).toLowerCase() === "is" ? 0 : 1;
	schema.read_only = props.readOnly;
	schema.fieldname = String(leaf.value.field || "value").replace(/^doc\./, "");
	if (frappe.ui?.filter_utils?.set_fieldtype)
		frappe.ui.filter_utils.set_fieldtype(schema, null, leaf.value.operator);
	if (
		leaf.value.operator === "Between" &&
		["Date", "Datetime", "Time"].includes(field.value?.fieldtype)
	)
		schema.fieldtype = field.value.fieldtype;
	if (["in", "not in"].includes(String(leaf.value.operator).toLowerCase())) {
		if (getFieldType(field.value) === "Link") {
			schema.fieldtype = "MultiSelectList";
			schema.options = field.value.options;
			schema.get_data = async (txt) =>
				store.search_link_options({
					doctype: field.value.options,
					txt: txt || "",
					page_length: 40,
				});
		} else if (getFieldType(field.value) === "Select") {
			schema.fieldtype = "MultiSelectList";
			schema.options =
				typeof field.value.options === "string"
					? field.value.options.split("\n").filter(Boolean)
					: field.value.options || [];
		} else {
			schema.fieldtype = "Data";
			schema.placeholder = __("Comma-separated values");
		}
	}
	return schema;
});
function isEmpty(value) {
	return value === undefined || value === null || value === "";
}
async function validate() {
	const result = validateFilterLeaf(leaf.value, {
		doctype: props.doctype,
		fieldDef: field.value,
	});
	const errors = result.errors.map((msg) => __(msg));
	if (
		operatorInvalid.value &&
		leaf.value.field &&
		!errors.includes(__("Choose a supported operator for the selected field."))
	) {
		errors.push(__("Choose a supported operator for the selected field."));
	}
	return { valid: errors.length === 0, errors: [...new Set(errors)] };
}
defineExpose({ validate });
</script>

<style scoped>
.filter-row {
	width: 100%;
	min-width: 0;
	box-sizing: border-box;
	padding: var(--fxr-space-1) var(--fxr-space-2);
	background: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	transition:
		border-color var(--fxr-transition-fast),
		background-color var(--fxr-transition-fast);
}
.filter-row:hover {
	border-color: var(--fxr-border-strong);
}
.filter-row.is-invalid {
	border-color: var(--fxr-border-danger, var(--fxr-text-danger)) !important;
	background: var(--fxr-danger-soft);
	box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.1);
}
.filter-row-main {
	display: grid;
	grid-template-columns: minmax(170px, 1.2fr) minmax(118px, 0.8fr) minmax(180px, 1.5fr);
	gap: var(--fxr-space-2);
	align-items: start;
	width: 100%;
	min-width: 0;
}
.filter-col {
	min-width: 0;
}
.filter-col-label {
	position: absolute;
	width: 1px;
	height: 1px;
	padding: 0;
	margin: -1px;
	overflow: hidden;
	clip: rect(0, 0, 0, 0);
	white-space: nowrap;
	border: 0;
	color: var(--fxr-text-secondary);
	font-size: var(--fxr-text-xs);
	font-weight: var(--fxr-weight-semibold, 600);
	line-height: 1.25;
}
.filter-required {
	color: var(--fxr-text-danger);
}
.filter-col :deep(.fxr-control),
.filter-col :deep(.combobox-container),
.filter-col :deep(.combobox-wrapper),
.filter-col :deep(.flex-value-control),
.filter-col :deep(.flex-value-control-button) {
	display: block;
	width: 100%;
	min-width: 0;
	box-sizing: border-box;
}
.filter-col :deep(.combobox-button-trigger),
.filter-col :deep(.flex-value-control-button),
.filter-col :deep(.form-control) {
	width: 100%;
	min-width: 0;
	height: var(--fxr-input-height) !important;
	min-height: var(--fxr-input-height);
	box-sizing: border-box;
	padding: var(--fxr-input-padding-y) var(--fxr-input-padding-x) !important;
	font-size: var(--fxr-input-font-size) !important;
	border-radius: var(--fxr-radius-md) !important;
}
.filter-col :deep(.combobox-input-group) {
	width: 100%;
	min-width: 0;
}
.dual-value-wrapper {
	display: flex;
	align-items: stretch;
	gap: var(--fxr-space-1);
	width: 100%;
	min-width: 0;
}
.dual-value-wrapper > * {
	flex: 1 1 0;
	width: 0;
	min-width: 0;
}
@media (max-width: 700px) {
	.filter-row-main {
		grid-template-columns: minmax(0, 1fr) minmax(110px, 0.8fr);
	}
	.value-col {
		grid-column: 1 / -1;
	}
}
@media (max-width: 480px) {
	.filter-row-main {
		grid-template-columns: minmax(0, 1fr);
	}
	.value-col {
		grid-column: auto;
	}
}
</style>
