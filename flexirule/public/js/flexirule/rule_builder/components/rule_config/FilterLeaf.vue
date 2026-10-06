<template>
	<div class="filter-leaf fxr-accent-scope" :style="panelStyleVars">
		<div class="filter-row">
			<div class="filter-row-main">
				<!-- Doctype Picker (if allowAnyDoctype) -->
				<div v-if="allowAnyDoctype" class="filter-col doctype-col">
					<ComboBoxControl
						:df="{ label: '', fieldtype: 'Link', options: 'DocType' }"
						:modelValue="currentDoctype"
						:doctype="'DocType'"
						:hideLabel="true"
						:read_only="readOnly"
						@update:modelValue="onDoctypeSelect"
					/>
				</div>

				<!-- Field Picker -->
				<div class="filter-col field-col">
					<div class="field-picker-container">
						<ComboBoxControl
							ref="fieldPickerRef"
							:df="{ label: '', fieldtype: 'FieldPicker', reqd: 1 }"
							:options="availableFields"
							:doctype="currentDoctype"
							:modelValue="currentField"
							:read_only="readOnly"
							:showValidation="showValidation"
							:trigger="'button'"
							:hideLabel="true"
							:navigable="true"
							:navStack="nav.navStack.value"
							@navigate="nav.handleNavigate"
							@back="nav.handleBack"
							:class="{
								'border-warning': currentField && !isFieldValid(currentField, currentDoctype),
							}"
							@update:modelValue="onFieldSelect"
						/>
						<i
							v-if="currentField && !isFieldValid(currentField, currentDoctype)"
							class="fa fa-warning text-warning field-warning-icon"
							:title="__('Field not found in DocType')"
						></i>
					</div>
				</div>

				<!-- Operator -->
				<div class="filter-col operator-col">
					<select
						class="form-control input-xs"
						:value="currentOperator"
						:disabled="readOnly"
						@change="onOperatorChange"
					>
						<option
							v-for="op in allowedOperators"
							:key="op"
							:value="op"
						>
							{{ getOperatorLabel(op) }}
						</option>
					</select>
				</div>

				<!-- Value / Expression -->
				<div class="filter-col value-col">
					<div class="value-input-group">
						<template v-if="currentOperator === 'Between'">
							<div class="dual-value-wrapper">
								<div class="value-input-item">
									<FlexValueControl
										:modelValue="betweenVal1"
										:context="{
											df: { ...controlSchema, reqd: 1 },
											operator: currentOperator,
											referenceDoctype: currentDoctype,
										}"
										:disabled="readOnly"
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
										:modelValue="betweenVal2"
										:context="{
											df: { ...controlSchema, reqd: 1 },
											operator: currentOperator,
											referenceDoctype: currentDoctype,
										}"
										:disabled="readOnly"
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
									:modelValue="currentValue"
									:context="{
										df: { ...controlSchema, reqd: 1 },
										operator: currentOperator,
										referenceDoctype: currentDoctype,
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
	</div>
</template>

<script setup>
import { ref, computed, watch, inject } from "vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import { useStore } from "../../stores";
import { getContract } from "../../../core/contracts.js";
import { useNavigableFields } from "../../composables/useNavigableFields";

const props = defineProps({
	modelValue: {
		type: [Object, Array],
		default: () => ({ doctype: "", field: "", operator: "=", value: { mode: "static", value: "" } }),
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
const fieldPickerRef = ref(null);

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

const coerceStructuredValue = (rawValue) => {
	if (Array.isArray(rawValue)) {
		return rawValue.map((item) => coerceStructuredValue(item));
	}
	if (rawValue && typeof rawValue === "object" && rawValue.mode) {
		if (["formula", "format", "normalize", "normalization"].includes(rawValue.mode)) {
			const config = { ...(rawValue.config || {}) };
			if (!config.kind) {
				if (rawValue.mode === "formula") config.kind = "math_formula";
				if (["format", "normalize", "normalization"].includes(rawValue.mode)) {
					config.kind = "text";
				}
			}
			return {
				mode: "resolver",
				value: rawValue.value || rawValue.expression || "",
				config,
			};
		}
		if (rawValue.mode === "variable") {
			return { mode: "variable", value: rawValue.value || rawValue.path || "" };
		}
		return rawValue;
	}
	if (rawValue && typeof rawValue === "object" && "value" in rawValue) {
		const rawType = String(rawValue.value_type || "Value").toLowerCase();
		if (rawValue.builder && typeof rawValue.builder === "object") {
			return {
				mode: "resolver",
				value: rawValue.value || "",
				config: rawValue.builder,
			};
		}
		if (rawType === "variable") {
			const path = String(rawValue.value || "").trim().replace(/^\{/, "").replace(/\}$/, "");
			return { mode: "variable", value: path };
		}
		if (rawType === "expression") {
			return { mode: "resolver", value: rawValue.value || "" };
		}
		return { mode: "static", value: rawValue.value };
	}
	return { mode: "static", value: rawValue ?? "" };
};

const extractRow = (val) => {
	let target = val;
	if (Array.isArray(val) && val.length === 1 && typeof val[0] === "object" && !Array.isArray(val[0])) {
		target = val[0];
	}

	if (Array.isArray(target)) {
		if (target.length === 4) {
			return {
				doctype: target[0] || props.doctype,
				field: target[1] || "",
				operator: target[2] || "=",
				value: coerceStructuredValue(target[3]),
			};
		}
		if (target.length === 3) {
			return {
				doctype: props.doctype,
				field: target[0] || "",
				operator: target[1] || "=",
				value: coerceStructuredValue(target[2]),
			};
		}
	}

	if (target && typeof target === "object") {
		return {
			doctype: target.doctype || props.doctype,
			field: target.field || target.fieldname || "",
			operator: target.operator || target.op || "=",
			value: coerceStructuredValue(target.value),
		};
	}

	return {
		doctype: props.doctype,
		field: "",
		operator: "=",
		value: { mode: "static", value: "" },
	};
};

const localRow = ref(extractRow(props.modelValue));

watch(
	() => props.modelValue,
	(val) => {
		const extracted = extractRow(val);
		if (JSON.stringify(extracted) !== JSON.stringify(localRow.value)) {
			localRow.value = extracted;
		}
	},
	{ deep: true }
);

const currentDoctype = computed(() => localRow.value.doctype || props.doctype);
const currentField = computed(() => localRow.value.field || "");
const currentOperator = computed(() => localRow.value.operator || "=");
const currentValue = computed(() => localRow.value.value);

const betweenVal1 = computed(() => {
	if (Array.isArray(currentValue.value)) return currentValue.value[0] || { mode: "static", value: "" };
	return { mode: "static", value: "" };
});

const betweenVal2 = computed(() => {
	if (Array.isArray(currentValue.value)) return currentValue.value[1] || { mode: "static", value: "" };
	return { mode: "static", value: "" };
});

// Single stable useNavigableFields composable instance
const nav = useNavigableFields(
	() => currentDoctype.value,
	() => currentField.value
);

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

const doctypeFieldsCache = new Map();

const isLayoutFieldtype = (fieldtype) =>
	[
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Button",
		"Image",
		"Fold",
		"Heading",
		"Spacer",
	].includes(fieldtype);

const shouldIncludeFilterField = (df, baseDoctype) => {
	if (!df || !df.fieldname || isLayoutFieldtype(df.fieldtype)) return false;
	if (frappe.model.no_value_type.includes(df.fieldtype)) return false;
	if (df.fieldname === "docstatus" && !frappe.model.is_submittable(baseDoctype)) return false;
	return true;
};

const getFieldsForDoctype = (dt) => {
	if (!dt) return [];
	if (doctypeFieldsCache.has(dt)) return doctypeFieldsCache.get(dt);

	const meta = frappe.get_meta(dt);
	if (!meta) return [];

	const mapped = [];
	const parentFields = store.get_fields_for_doctype(dt, { valueMode: "fieldname" });
	for (const df of parentFields) {
		if (!shouldIncludeFilterField(df, dt)) continue;
		if (frappe.model.table_fields.includes(df.fieldtype)) continue;
		mapped.push({ ...df, parent: dt });
	}

	for (const tableDf of meta.fields || []) {
		if (!frappe.model.table_fields.includes(tableDf.fieldtype) || !tableDf.options) continue;
		const childMeta = frappe.get_meta(tableDf.options);
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
				label: `${tableDf.label || tableDf.fieldname}: ${childDf.label || childDf.fieldname} (${value})`,
				value,
			});
		}
	}

	doctypeFieldsCache.set(dt, mapped);
	return mapped;
};

const getFieldDef = (fieldname, dt) => {
	if (!fieldname) return null;
	const doctype = dt || currentDoctype.value;
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

	if (isDotted && doctype) {
		const [tableFieldname, childFieldname] = fieldname.split(".", 2);
		const tableDf = frappe.meta.get_docfield(doctype, tableFieldname);
		if (tableDf && tableDf.options) {
			const childDf = frappe.meta.get_docfield(tableDf.options, childFieldname);
			if (childDf) {
				return {
					...childDf,
					value: fieldname,
					fieldname,
					parentfield: tableFieldname,
					parenttype: doctype,
					parent: tableDf.options,
				};
			}
		}
	}

	const raw_fieldname =
		typeof fieldname === "string" && fieldname.startsWith("doc.")
			? fieldname.substring(4)
			: fieldname;
	if (doctype && window.frappe && frappe.meta && frappe.meta.has_field(doctype, raw_fieldname)) {
		const df = frappe.meta.get_docfield(doctype, raw_fieldname);
		if (df) return { ...df, value: fieldname };
	}

	const fields = getFieldsForDoctype(doctype);
	return fields.find((f) => f.value === fieldname) || null;
};

const currentFieldDef = computed(() => getFieldDef(currentField.value, currentDoctype.value));

const availableFields = computed(() => {
	const navFields = nav.currentFields.value;
	if (navFields && navFields.length > 0) return navFields;
	return getFieldsForDoctype(currentDoctype.value);
});

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

	if (field.fieldtype === "Link") {
		const nestedSetDoctypes = frappe.boot?.nested_set_doctypes || [];
		if (nestedSetDoctypes.includes(field.options)) {
			for (const op of NESTED_SET_OPERATORS) {
				if (!allowed.includes(op)) allowed.push(op);
			}
		}
	}

	if (isCheckField(field)) return allowed.filter((op) => op === "=" || op === "!=");
	return allowed.length ? allowed : ["="];
});

const getDefaultCondition = (field, dt) => {
	if (!field) return "=";
	if (field.fieldtype === "Data") {
		try {
			const meta = dt ? frappe.get_meta(dt) : null;
			if (!meta?.is_large_table) return "like";
		} catch (e) {
			return "like";
		}
		return "=";
	}
	if (field.fieldtype === "Date" || field.fieldtype === "Datetime") return "Between";
	return "=";
};

const getOperatorLabel = (operator) => {
	const field = currentFieldDef.value;
	if (field && (field.fieldtype === "Date" || field.fieldtype === "Datetime")) {
		return DATE_OPERATOR_LABELS[operator] || operatorLabelMap[operator] || operator;
	}
	return operatorLabelMap[operator] || operator;
};

const controlSchema = computed(() => {
	const field = currentFieldDef.value;
	let schema = field ? frappe.utils.deep_clone(field) : { fieldtype: "Data", fieldname: "value" };
	const rawField =
		typeof currentField.value === "string" && currentField.value.startsWith("doc.")
			? currentField.value.substring(4)
			: currentField.value;
	schema.label = "";
	schema.read_only = props.readOnly;
	schema.fieldname = rawField;

	if (window.frappe && frappe.ui && frappe.ui.filter_utils) {
		frappe.ui.filter_utils.set_fieldtype(schema, null, currentOperator.value);
		if (currentOperator.value === "Between" && ["Date", "Datetime", "Time"].includes(field?.fieldtype)) {
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

	const opLower = (currentOperator.value || "").toLowerCase();
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
	} else if (["=", "!="].includes(currentOperator.value) && field?.fieldtype === "Link") {
		schema.fieldtype = "Link";
		schema.options = field.options;
	} else if (currentOperator.value === "Between") {
		schema.placeholder = __("Value1, Value2");
	}

	return schema;
});

const isFieldValid = (fieldname, dt) => {
	if (!fieldname) return true;
	if (typeof fieldname === "string" && (fieldname.startsWith("{") || fieldname.includes("."))) {
		return true;
	}
	const fields = getFieldsForDoctype(dt || currentDoctype.value);
	if (!fields || !fields.length) return true;
	return fields.some((f) => f.value === fieldname);
};

function emitUpdate(updatedRow) {
	localRow.value = updatedRow;
	if (Array.isArray(props.modelValue)) {
		emit("update:modelValue", [updatedRow]);
	} else {
		emit("update:modelValue", updatedRow);
	}
}

function onDoctypeSelect(val) {
	const nextRow = { ...localRow.value, doctype: val, field: "" };
	nav.resetStack();
	emitUpdate(nextRow);
}

function onFieldSelect(val) {
	const fieldDef = getFieldDef(val, currentDoctype.value);
	const allowed = allowedOperators.value;
	let nextOp = currentOperator.value;
	if (!allowed.includes(nextOp)) {
		const defaultCond = getDefaultCondition(fieldDef, currentDoctype.value);
		nextOp = allowed.includes(defaultCond) ? defaultCond : allowed[0] || "=";
	}
	nav.resetStack();
	emitUpdate({ ...localRow.value, field: val, operator: nextOp });
}

function onOperatorChange(e) {
	const newOp = e.target.value;
	let nextVal = currentValue.value;
	if (newOp === "Between" && !Array.isArray(nextVal)) {
		nextVal = [
			{ mode: "static", value: "" },
			{ mode: "static", value: "" },
		];
	} else if (currentOperator.value === "Between" && Array.isArray(nextVal)) {
		nextVal = nextVal[0] || { mode: "static", value: "" };
	}
	emitUpdate({ ...localRow.value, operator: newOp, value: nextVal });
}

function onValueChange(val) {
	emitUpdate({ ...localRow.value, value: val });
}

function updateBetweenValue(index, val) {
	const list = Array.isArray(currentValue.value)
		? [...currentValue.value]
		: [
				{ mode: "static", value: "" },
				{ mode: "static", value: "" },
		  ];
	list[index] = val;
	emitUpdate({ ...localRow.value, value: list });
}

function isValueEmpty(val) {
	return val === undefined || val === null || val === "";
}

function validate() {
	const errors = [];
	if (!currentField.value) {
		errors.push(__("Filter: Field is required"));
	}
	if (!currentOperator.value) {
		errors.push(__("Filter: Operator is required"));
	}
	if (currentOperator.value === "Between") {
		if (
			!Array.isArray(currentValue.value) ||
			currentValue.value.length < 2 ||
			isValueEmpty(currentValue.value[0]?.value) ||
			isValueEmpty(currentValue.value[1]?.value)
		) {
			errors.push(__("Filter: Both values are required for Between"));
		}
	} else if (currentOperator.value !== "is") {
		const structVal = currentValue.value;
		const isEmpty = structVal?.mode === "static" ? isValueEmpty(structVal.value) : !structVal;
		if (isEmpty) {
			errors.push(__("Filter: Value is required"));
		}
	}
	return { valid: errors.length === 0, errors };
}

function focus() {
	fieldPickerRef.value?.focus?.();
}

defineExpose({ validate, focus });
</script>

<style scoped>
.filter-leaf {
	width: 100%;
	font-family: var(--fxr-font-family);
}

.filter-row {
	display: flex;
	flex-direction: column;
	background-color: var(--fxr-bg-input);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	padding: 4px var(--spacing-md);
	transition: all var(--fxr-transition-fast);
}

.filter-row:hover {
	border-color: var(--fxr-accent);
	background-color: var(--fxr-surface-soft);
}

.filter-row-main {
	display: flex;
	gap: var(--spacing-md);
	align-items: center;
	width: 100%;
}

.doctype-col {
	flex: 0 0 140px;
}

.field-col {
	flex: 0 0 180px;
	min-width: 100px;
}

.operator-col {
	flex: 0 0 100px;
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

:deep(.border-warning .form-control) {
	border-color: var(--fxr-border-focus) !important;
	background-color: var(--fxr-badge-resolver) !important;
}

.value-input-group {
	display: flex;
	width: 100%;
}

.control-slot {
	width: 100%;
	min-width: 0;
}

.dual-value-wrapper {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-3);
	width: 100%;
}

.value-input-item {
	flex: 1;
	min-width: 0;
}

.between-sep {
	font-size: var(--fxr-text-sm);
	color: var(--fxr-text-muted);
	font-weight: var(--fxr-weight-semibold);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	flex-shrink: 0;
	padding: 0 2px;
}

.filter-row-main :deep(.form-control),
.filter-row-main :deep(input.form-control),
.filter-row-main :deep(select.form-control) {
	height: var(--fxr-input-height) !important;
	padding: var(--fxr-input-padding-y) var(--fxr-input-padding-x) !important;
	font-size: var(--fxr-input-font-size) !important;
	border: 1px solid var(--fxr-border) !important;
	border-radius: var(--fxr-radius-md) !important;
	background-color: var(--fxr-bg-input) !important;
	color: var(--fxr-text) !important;
	transition: border-color var(--fxr-transition-fast), box-shadow var(--fxr-transition-fast) !important;
}

.filter-row-main :deep(.fxr-control),
.filter-row-main :deep(.combobox-container),
.filter-row-main :deep(.multi-select-list) {
	width: 100%;
	min-width: 0;
}

.filter-row-main :deep(.form-control:focus) {
	border-color: var(--fxr-node-accent, var(--fxr-border-focus)) !important;
	box-shadow: 0 0 0 2px var(--fxr-node-accent-light, var(--fxr-accent-light)) !important;
}

.filter-row-main :deep(select.form-control) {
	appearance: none !important;
	-webkit-appearance: none !important;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E") !important;
	background-repeat: no-repeat !important;
	background-position: right 6px center !important;
	background-size: 12px !important;
	padding-right: 24px !important;
	cursor: pointer;
}

@media (max-width: 920px) {
	.filter-row-main {
		flex-wrap: wrap;
		gap: var(--fxr-space-3);
	}
	.doctype-col,
	.field-col,
	.operator-col {
		flex: 1 1 200px;
	}
	.value-col {
		flex: 1 1 100%;
	}
}

@media (max-width: 640px) {
	.filter-row {
		padding: var(--fxr-space-4);
	}
	.dual-value-wrapper {
		flex-direction: column;
		align-items: stretch;
	}
	.between-sep {
		text-align: center;
	}
}
</style>
