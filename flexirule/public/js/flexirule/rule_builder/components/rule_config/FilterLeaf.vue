<template>
	<div class="filter-leaf-wrapper fxr-accent-scope">
		<div class="filter-row-main">
			<!-- Field Picker -->
			<div class="filter-col field-col">
				<div class="field-picker-container">
					<ComboBoxControl
						ref="fieldPickerRef"
						:df="{ label: '', fieldtype: 'FieldPicker', reqd: 1 }"
						:options="currentFieldsOptions"
						:doctype="leafDoctype"
						:modelValue="modelValue.field"
						:read_only="readOnly"
						:showValidation="showValidation"
						:trigger="'button'"
						:hideLabel="true"
						:navigable="true"
						:navStack="navStack"
						@navigate="handleNavigate"
						@back="handleBack"
						:class="{
							'border-warning':
								modelValue.field && !isFieldValid(modelValue.field, leafDoctype),
						}"
						@update:modelValue="onFieldSelect"
					/>
					<i
						v-if="modelValue.field && !isFieldValid(modelValue.field, leafDoctype)"
						class="fa fa-warning text-warning field-warning-icon"
						:title="__('Field not found in DocType')"
					></i>
				</div>
			</div>

			<!-- Operator -->
			<div class="filter-col operator-col">
				<select
					class="form-control input-xs"
					:value="modelValue.operator || '='"
					:disabled="readOnly"
					@change="onOperatorChange"
				>
					<option v-for="op in allowedOperators" :key="op" :value="op">
						{{ getOperatorLabel(op) }}
					</option>
				</select>
			</div>

			<!-- Value / Expression -->
			<div class="filter-col value-col">
				<div class="value-input-group">
					<template v-if="modelValue.operator === 'Between'">
						<div class="dual-value-wrapper">
							<div class="value-input-item">
								<FlexValueControl
									:modelValue="betweenVal0"
									:context="{
										df: { ...controlSchema, reqd: 1 },
										operator: modelValue.operator,
										referenceDoctype: leafDoctype,
									}"
									:disabled="readOnly"
									:readOnly="readOnly"
									:showValidation="showValidation"
									:engine="store"
									:doc="store?.rule_doc"
									:variableOptions="effectiveVariableOptions"
									@update:modelValue="(val) => updateBetweenValue(0, val)"
								/>
							</div>
							<span class="between-sep">{{ __("and") }}</span>
							<div class="value-input-item">
								<FlexValueControl
									:modelValue="betweenVal1"
									:context="{
										df: { ...controlSchema, reqd: 1 },
										operator: modelValue.operator,
										referenceDoctype: leafDoctype,
									}"
									:disabled="readOnly"
									:readOnly="readOnly"
									:showValidation="showValidation"
									:engine="store"
									:doc="store?.rule_doc"
									:variableOptions="effectiveVariableOptions"
									@update:modelValue="(val) => updateBetweenValue(1, val)"
								/>
							</div>
						</div>
					</template>
					<template v-else>
						<div class="control-slot w-100 min-w-0">
							<FlexValueControl
								:modelValue="singleVal"
								:context="{
									df: { ...controlSchema, reqd: 1 },
									operator: modelValue.operator,
									referenceDoctype: leafDoctype,
								}"
								:engine="store"
								:doc="store?.rule_doc"
								:variableOptions="effectiveVariableOptions"
								:disabled="readOnly"
								:readOnly="readOnly"
								:showValidation="showValidation"
								@update:modelValue="onValueChange"
							/>
						</div>
					</template>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import { useStore } from "../../stores";
import { useNavigableFields } from "../../composables/useNavigableFields";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			doctype: "",
			field: "",
			operator: "=",
			value: { mode: "static", value: "" },
		}),
	},
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const fieldPickerRef = ref(null);

const injectedVariableOptions = inject("variableOptions", ref([]));
const effectiveVariableOptions = computed(
	() => props.variableOptions ?? injectedVariableOptions.value
);

const leafDoctype = computed(() => props.modelValue.doctype || props.doctype);

// Dedicated, independent useNavigableFields instance per leaf
const nav = useNavigableFields(
	() => leafDoctype.value,
	() => props.modelValue.field
);

const currentFieldsOptions = computed(() => {
	const fields = nav.currentFields.value;
	if (fields && fields.length > 0) return fields;
	return getFieldsForDoctype(leafDoctype.value);
});

const navStack = computed(() => nav.navStack.value);

function handleNavigate(option) {
	nav.handleNavigate(option);
}

function handleBack(stackIdx) {
	nav.handleBack(stackIdx);
}

const BASE_QUERY_OPERATORS = [
	"=",
	"!=",
	"like",
	"not like",
	"in",
	"not in",
	">",
	"<",
	">=",
	"<=",
	"is",
];
const QUERY_EXTENSION_OPERATORS = ["Between", "Timespan", "starts with", "ends with"];
const NESTED_SET_OPERATORS = [
	"descendants of",
	"descendants of (inclusive)",
	"not descendants of",
	"ancestors of",
	"not ancestors of",
];

const operatorLabelMap = {
	"=": __("Equals"),
	"!=": __("Not Equals"),
	like: __("Like"),
	"not like": __("Not Like"),
	in: __("In"),
	"not in": __("Not In"),
	is: __("Is"),
	">": __("Greater Than"),
	"<": __("Less Than"),
	">=": __("Greater Than Or Equal To"),
	"<=": __("Less Than Or Equal To"),
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

const DATE_OPERATOR_LABELS = {
	"<": __("Before"),
	">": __("After"),
	"<=": __("On or Before"),
	">=": __("On or After"),
};

const EXTRA_FILTER_OPERATORS_BY_FIELDTYPE = {
	Data: ["starts with", "ends with"],
	Text: ["starts with", "ends with"],
	"Small Text": ["starts with", "ends with"],
	"Long Text": ["starts with", "ends with"],
	"Text Editor": ["starts with", "ends with"],
};

const FRAPPE_INVALID_CONDITION_MAP = {
	Date: ["like", "not like"],
	Datetime: ["like", "not like", "in", "not in", "=", "!="],
	Data: ["Between", "Timespan"],
	Time: ["Between", "Timespan"],
	Select: ["like", "not like", "Between", "Timespan"],
	Link: ["Between", "Timespan", ">", "<", ">=", "<="],
	Currency: ["Between", "Timespan"],
	Color: ["Between", "Timespan"],
	Code: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"HTML Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Markdown Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Password: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Rating: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Float: ["like", "not like", "Between", "in", "not in", "Timespan"],
};

const isCheckField = (field) => field?.original_type === "Check" || field?.fieldtype === "Check";

function shouldIncludeFilterField(df, baseDoctype) {
	if (!df || !df.fieldname) return false;
	const layoutTypes = [
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Button",
		"Image",
		"Fold",
		"Heading",
		"Spacer",
	];
	if (layoutTypes.includes(df.fieldtype)) return false;
	if (frappe.model?.no_value_type?.includes(df.fieldtype)) return false;
	if (df.fieldname === "docstatus" && !frappe.model?.is_submittable?.(baseDoctype)) return false;
	return true;
}

function getFieldsForDoctype(dt) {
	if (!dt) return [];
	const parentFields = store.get_fields_for_doctype(dt, { valueMode: "fieldname" }) || [];
	const mapped = [];
	for (const df of parentFields) {
		if (!shouldIncludeFilterField(df, dt)) continue;
		if (frappe.model?.table_fields?.includes(df.fieldtype)) continue;
		mapped.push({ ...df, parent: dt });
	}

	const meta = frappe.get_meta?.(dt);
	if (meta?.fields) {
		for (const tableDf of meta.fields) {
			if (!frappe.model?.table_fields?.includes(tableDf.fieldtype) || !tableDf.options)
				continue;
			const childMeta = frappe.get_meta?.(tableDf.options);
			if (!childMeta) continue;
			let childFields = [...(childMeta.fields || [])];
			if (tableDf.fieldtype === "Table MultiSelect") {
				const linkField = childFields.find((f) => f.fieldtype === "Link");
				childFields = linkField ? [linkField] : [];
			}
			for (const childDf of childFields) {
				if (!shouldIncludeFilterField(childDf, dt)) continue;
				const value = `${tableDf.fieldname}.${childDf.fieldname}`;
				mapped.push({
					...childDf,
					parent: tableDf.options,
					parentfield: tableDf.fieldname,
					parenttype: dt,
					label: `${tableDf.label || tableDf.fieldname}: ${
						childDf.label || childDf.fieldname
					} (${value})`,
					value,
				});
			}
		}
	}
	return mapped;
}

function getFieldDef(fieldname, dt) {
	if (!fieldname) return null;
	const docType = dt || leafDoctype.value;
	const isDotted = typeof fieldname === "string" && fieldname.includes(".");

	if (!isDotted && ["name"].includes(fieldname)) {
		return { fieldname, value: fieldname, fieldtype: "Data", label: "Name" };
	}
	if (!isDotted && ["owner", "modified_by"].includes(fieldname)) {
		return {
			fieldname,
			value: fieldname,
			fieldtype: "Link",
			options: "User",
			label: fieldname === "owner" ? "Owner" : "Modified By",
		};
	}
	if (!isDotted && ["creation", "modified"].includes(fieldname)) {
		return {
			fieldname,
			value: fieldname,
			fieldtype: "Datetime",
			label: fieldname === "creation" ? "Creation" : "Modified",
		};
	}
	if (!isDotted && fieldname === "docstatus") {
		return { fieldname, value: fieldname, fieldtype: "Int", label: "Docstatus" };
	}

	if (isDotted && docType) {
		const [tableFieldname, childFieldname] = fieldname.split(".", 2);
		const tableDf = frappe.meta?.get_docfield?.(docType, tableFieldname);
		if (tableDf?.options) {
			const childDf = frappe.meta?.get_docfield?.(tableDf.options, childFieldname);
			if (childDf) {
				return {
					...childDf,
					value: fieldname,
					fieldname,
					parentfield: tableFieldname,
					parenttype: docType,
					parent: tableDf.options,
				};
			}
		}
	}

	const rawFieldname =
		typeof fieldname === "string" && fieldname.startsWith("doc.")
			? fieldname.substring(4)
			: fieldname;
	if (docType && window.frappe && frappe.meta?.has_field?.(docType, rawFieldname)) {
		const df = frappe.meta.get_docfield(docType, rawFieldname);
		if (df) return { ...df, value: fieldname };
	}

	const fields = getFieldsForDoctype(docType);
	return fields.find((f) => f.value === fieldname) || null;
}

const currentFieldDef = computed(() => getFieldDef(props.modelValue.field, leafDoctype.value));

const allowedOperators = computed(() => {
	const field = currentFieldDef.value;
	if (!field) return [...BASE_QUERY_OPERATORS, ...QUERY_EXTENSION_OPERATORS];
	const all = [...BASE_QUERY_OPERATORS, ...QUERY_EXTENSION_OPERATORS];
	const invalid =
		FRAPPE_INVALID_CONDITION_MAP[field.original_type] ||
		FRAPPE_INVALID_CONDITION_MAP[field.fieldtype] ||
		[];
	const allowed = all.filter((op) => !invalid.includes(op));
	const extra = EXTRA_FILTER_OPERATORS_BY_FIELDTYPE[field.fieldtype] || [];
	for (const op of extra) {
		if (!allowed.includes(op)) allowed.push(op);
	}
	if (field.fieldtype === "Link" && frappe.boot?.nested_set_doctypes?.includes(field.options)) {
		for (const op of NESTED_SET_OPERATORS) {
			if (!allowed.includes(op)) allowed.push(op);
		}
	}
	if (isCheckField(field)) return allowed.filter((op) => op === "=" || op === "!=");
	return allowed.length ? allowed : ["="];
});

function getDefaultCondition(field, dt) {
	if (!field) return "=";
	if (field.fieldtype === "Data") {
		try {
			const meta = dt ? frappe.get_meta?.(dt) : null;
			if (!meta?.is_large_table) return "like";
		} catch (e) {
			return "like";
		}
		return "=";
	}
	if (field.fieldtype === "Date" || field.fieldtype === "Datetime") {
		return "Between";
	}
	return "=";
}

function getOperatorLabel(op) {
	const field = currentFieldDef.value;
	if (field && (field.fieldtype === "Date" || field.fieldtype === "Datetime")) {
		return DATE_OPERATOR_LABELS[op] || operatorLabelMap[op] || op;
	}
	return operatorLabelMap[op] || op;
}

const controlSchema = computed(() => {
	const field = currentFieldDef.value;
	let schema = field
		? frappe.utils?.deep_clone?.(field) || { ...field }
		: { fieldtype: "Data", fieldname: "value" };
	const rawField =
		typeof props.modelValue.field === "string" && props.modelValue.field.startsWith("doc.")
			? props.modelValue.field.substring(4)
			: props.modelValue.field;
	schema.label = "";
	schema.read_only = props.readOnly;
	schema.fieldname = rawField;

	if (window.frappe && frappe.ui?.filter_utils) {
		frappe.ui.filter_utils.set_fieldtype(schema, null, props.modelValue.operator);
		if (
			props.modelValue.operator === "Between" &&
			["Date", "Datetime", "Time"].includes(field?.fieldtype)
		) {
			schema.fieldtype = field.fieldtype;
		}
	} else {
		if (schema.fieldname === "docstatus") {
			schema.fieldtype = "Select";
			schema.options = [
				{ value: "0", label: __("Draft") },
				{ value: "1", label: __("Submitted") },
				{ value: "2", label: __("Cancelled") },
			];
		} else if (isCheckField(field)) {
			schema.fieldtype = "Select";
			schema.options = [
				{ label: __("Yes"), value: "1" },
				{ label: __("No"), value: "0" },
			];
		}
	}

	const opLower = (props.modelValue.operator || "").toLowerCase();
	if (["in", "not in"].includes(opLower)) {
		if (field && field.fieldtype === "Link") {
			schema.fieldtype = "MultiSelectList";
			schema.displayMode = "compact";
			schema.get_data = async (txt) => {
				if (!field.options) return [];
				return await store.search_link_options({
					doctype: field.options,
					txt: txt || "",
					page_length: 40,
				});
			};
		} else if (field && field.fieldtype === "Select") {
			schema.fieldtype = "MultiSelectList";
			schema.displayMode = "compact";
			if (typeof field.options === "string") {
				schema.options = field.options
					.split("\n")
					.map((opt) => opt.trim())
					.filter(Boolean);
			} else if (Array.isArray(field.options)) {
				schema.options = field.options;
			} else {
				schema.options = [];
			}
		} else {
			schema.fieldtype = "Data";
			schema.placeholder = __("Comma-separated values");
		}
	} else if (["=", "!="].includes(props.modelValue.operator) && field?.fieldtype === "Link") {
		schema.fieldtype = "Link";
		schema.options = field.options;
	} else if (props.modelValue.operator === "Between") {
		schema.placeholder = __("Value1, Value2");
	}

	return schema;
});

const betweenVal0 = computed(() => {
	const val = props.modelValue.value;
	if (Array.isArray(val)) return val[0] || { mode: "static", value: "" };
	return { mode: "static", value: "" };
});

const betweenVal1 = computed(() => {
	const val = props.modelValue.value;
	if (Array.isArray(val)) return val[1] || { mode: "static", value: "" };
	return { mode: "static", value: "" };
});

const singleVal = computed(() => {
	const val = props.modelValue.value;
	if (Array.isArray(val)) return val[0] || { mode: "static", value: "" };
	if (val && typeof val === "object") return val;
	return { mode: "static", value: val ?? "" };
});

function isFieldValid(fieldname, dt) {
	if (!fieldname) return true;
	if (typeof fieldname === "string" && (fieldname.startsWith("{") || fieldname.includes(".")))
		return true;
	const fields = getFieldsForDoctype(dt || leafDoctype.value);
	if (!fields || !fields.length) return true;
	return fields.some((f) => f.value === fieldname);
}

function onFieldSelect(newField) {
	const fieldDef = getFieldDef(newField, leafDoctype.value);
	let op = props.modelValue.operator || "=";
	const operators = allowedOperators.value;
	if (!operators.includes(op)) {
		const defaultOp = getDefaultCondition(fieldDef, leafDoctype.value);
		op = operators.includes(defaultOp) ? defaultOp : operators[0] || "=";
	}

	nav.resetStack();

	emit("update:modelValue", {
		...props.modelValue,
		doctype: leafDoctype.value,
		field: newField,
		operator: op,
	});
}

function onOperatorChange(e) {
	const newOp = e.target.value;
	let newVal = props.modelValue.value;

	if (newOp === "Between" && !Array.isArray(newVal)) {
		newVal = [singleVal.value, { mode: "static", value: "" }];
	} else if (props.modelValue.operator === "Between" && Array.isArray(newVal)) {
		newVal = newVal[0] || { mode: "static", value: "" };
	}

	emit("update:modelValue", {
		...props.modelValue,
		operator: newOp,
		value: newVal,
	});
}

function onValueChange(val) {
	emit("update:modelValue", {
		...props.modelValue,
		value: val,
	});
}

function updateBetweenValue(index, val) {
	const list = [betweenVal0.value, betweenVal1.value];
	list[index] = val;
	emit("update:modelValue", {
		...props.modelValue,
		value: list,
	});
}

function isValueEmpty(val) {
	return val === undefined || val === null || val === "";
}

function validate() {
	const errors = [];
	const field = props.modelValue.field;
	const operator = props.modelValue.operator;
	const value = props.modelValue.value;

	if (!field) {
		errors.push(__("Filter field is required"));
	}
	if (!operator) {
		errors.push(__("Filter operator is required"));
	}
	if (operator === "Between") {
		if (
			!Array.isArray(value) ||
			value.length < 2 ||
			isValueEmpty(value[0]?.value) ||
			isValueEmpty(value[1]?.value)
		) {
			errors.push(__("Both values are required for Between"));
		}
	} else if (operator !== "is") {
		const isEmpty = value?.mode === "static" ? isValueEmpty(value.value) : !value;
		if (isEmpty) {
			errors.push(__("Filter value is required"));
		}
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate, focus: () => fieldPickerRef.value?.focus?.() });
</script>

<style scoped>
.filter-leaf-wrapper {
	width: 100%;
	font-family: var(--fxr-font-family);
}

.filter-row-main {
	display: flex;
	gap: var(--fxr-space-3);
	align-items: center;
	width: 100%;
	background-color: var(--fxr-bg-input);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	padding: 4px var(--fxr-space-3);
}

.field-col {
	flex: 0 0 200px;
	min-width: 120px;
}

.operator-col {
	flex: 0 0 110px;
}

.value-col {
	flex: 1;
	min-width: 0;
}

.field-picker-container {
	position: relative;
	display: flex;
	align-items: center;
	width: 100%;
}

.field-warning-icon {
	position: absolute;
	right: 18px;
	z-index: 5;
	pointer-events: all;
	cursor: help;
	font-size: 11px;
}

.value-input-group {
	display: flex;
	width: 100%;
}

.dual-value-wrapper {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-2);
	width: 100%;
}

.value-input-item {
	flex: 1;
	min-width: 0;
}

.between-sep {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
	font-weight: 600;
	text-transform: uppercase;
}

@media (max-width: 768px) {
	.filter-row-main {
		flex-direction: column;
		align-items: stretch;
	}
	.field-col,
	.operator-col,
	.value-col {
		flex: 1 1 100%;
		width: 100%;
	}
}
</style>
