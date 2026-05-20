<template>
	<div class="filter-group-wrapper fxr-accent-scope" :style="panelStyleVars">
		<div
			v-if="!doctype && !allowAnyDoctype"
			class="text-muted small p-2 text-center border-dashed rounded"
		>
			{{ __("Select a DocType to configure filters.") }}
		</div>
		<div v-else class="filter-list">
			<div v-for="(row, idx) in filters" :key="idx" class="filter-row">
				<div class="filter-row-main">
					<!-- Doctype Picker (if allowAnyDoctype) -->
					<div v-if="allowAnyDoctype" class="filter-col doctype-col">
						<ComboBoxControl
							:df="{ label: '', fieldtype: 'Link', options: 'DocType' }"
							:modelValue="row.doctype || doctype"
							:doctype="'DocType'"
							:hideLabel="true"
							:read_only="readOnly"
							@update:modelValue="(val) => updateRow(idx, { doctype: val })"
						/>
					</div>

					<!-- Field Picker -->
					<div class="filter-col field-col">
						<div class="field-picker-container">
							<ComboBoxControl
								:df="{ label: '', fieldtype: 'FieldPicker' }"
								:options="getFieldsForDoctype(row.doctype || doctype)"
								:doctype="row.doctype || doctype"
								:modelValue="row.field"
								:read_only="readOnly"
								:trigger="'button'"
								:hideLabel="true"
								:class="{
									'border-warning':
										row.field &&
										!isFieldValid(row.field, row.doctype || doctype),
								}"
								@update:modelValue="(val) => updateRow(idx, { field: val })"
							/>
							<i
								v-if="row.field && !isFieldValid(row.field, row.doctype || doctype)"
								class="fa fa-warning text-warning field-warning-icon"
								:title="__('Field not found in DocType')"
							></i>
						</div>
					</div>

					<!-- Operator -->
					<div class="filter-col operator-col">
						<select
							class="form-control input-xs"
							:value="row.operator"
							:disabled="readOnly"
							@change="(e) => updateRow(idx, { operator: e.target.value })"
						>
							<option
								v-for="op in getOperatorsForField(
									getFieldDef(row.field, row.doctype)
								)"
								:key="op"
								:value="op"
							>
								{{ getOperatorLabel(op, row) }}
							</option>
						</select>
					</div>

					<!-- Value Type -->
					<div class="filter-col type-col">
						<select
							class="form-control input-xs type-select"
							:value="row.value_type"
							:disabled="readOnly"
							@change="(e) => toggleValueType(idx, e.target.value)"
						>
							<option v-for="vt in getValueTypeOptions(row)" :key="vt" :value="vt">
								{{ getValueTypeLabel(vt, row) }}
							</option>
						</select>
					</div>

					<!-- Value / Expression -->
					<div class="filter-col value-col">
						<div class="value-input-group">
							<template
								v-if="row.operator === 'Between' && row.value_type !== 'Builder'"
							>
								<div class="dual-value-wrapper">
									<div class="value-input-item">
										<template
											v-if="
												row.value_type === 'Variable' ||
												row.value_type === 'Expression'
											"
										>
											<ComboBoxControl
												:df="{ fieldtype: 'Autocomplete', label: '' }"
												:modelValue="
													stripBracket(getBetweenValue(row.value, 0))
												"
												:get_query="getVariableOptions"
												:hideLabel="true"
												:read_only="readOnly"
												@update:modelValue="
													(val) =>
														setBetweenValue(
															idx,
															0,
															row.value_type === 'Value'
																? val
																: `{${val}}`
														)
												"
											/>
										</template>
										<template v-else>
											<ControlFactory
												:df="getControlFactorySchema(row)"
												:modelValue="getBetweenValue(row.value, 0)"
												:read_only="readOnly"
												:hideLabel="true"
												@update:modelValue="
													(val) => setBetweenValue(idx, 0, val)
												"
											/>
										</template>
									</div>
									<span class="between-sep">{{ __("and") }}</span>
									<div class="value-input-item">
										<template
											v-if="
												row.value_type === 'Variable' ||
												row.value_type === 'Expression'
											"
										>
											<ComboBoxControl
												:df="{ fieldtype: 'Autocomplete', label: '' }"
												:modelValue="
													stripBracket(getBetweenValue(row.value, 1))
												"
												:get_query="getVariableOptions"
												:hideLabel="true"
												:read_only="readOnly"
												@update:modelValue="
													(val) =>
														setBetweenValue(
															idx,
															1,
															row.value_type === 'Value'
																? val
																: `{${val}}`
														)
												"
											/>
										</template>
										<template v-else>
											<ControlFactory
												:df="getControlFactorySchema(row)"
												:modelValue="getBetweenValue(row.value, 1)"
												:read_only="readOnly"
												:hideLabel="true"
												@update:modelValue="
													(val) => setBetweenValue(idx, 1, val)
												"
											/>
										</template>
									</div>
								</div>
							</template>
							<template v-else-if="row.value_type === 'Builder'">
								<div class="builder-wrapper">
									<template v-if="row.operator === 'Between'">
										<div class="dual-value-wrapper align-items-center">
											<div class="value-input-item">
												<ValueResolverControl
													:modelValue="getBuilderValue(row, 0)"
													:doctype="row.doctype || doctype"
													:readOnly="readOnly"
													:allowedKinds="getAllowedBuilderKinds(row)"
													@update:modelValue="
														(val) => updateBuilderValue(idx, 0, val)
													"
												/>
											</div>
											<span class="between-sep">{{ __("and") }}</span>
											<div class="value-input-item">
												<ValueResolverControl
													:modelValue="getBuilderValue(row, 1)"
													:doctype="row.doctype || doctype"
													:readOnly="readOnly"
													:allowedKinds="getAllowedBuilderKinds(row)"
													@update:modelValue="
														(val) => updateBuilderValue(idx, 1, val)
													"
												/>
											</div>
										</div>
									</template>
									<template v-else>
										<ValueResolverControl
											:modelValue="getBuilderValue(row)"
											:doctype="row.doctype || doctype"
											:readOnly="readOnly"
											:allowedKinds="getAllowedBuilderKinds(row)"
											@update:modelValue="
												(val) => updateBuilderValue(idx, null, val)
											"
										/>
									</template>
								</div>
							</template>
							<template
								v-else-if="
									row.value_type === 'Expression' || row.value_type === 'Variable'
								"
							>
								<div
									class="expression-wrapper"
									:class="{ 'variable-mode': row.value_type === 'Variable' }"
								>
									<span
										class="expr-bracket"
										v-if="row.value_type === 'Expression'"
										>{</span
									>
									<ComboBoxControl
										:df="{ fieldtype: 'Autocomplete', label: '' }"
										:modelValue="stripBracket(row.value)"
										:get_query="getVariableOptions"
										:hideLabel="true"
										:read_only="readOnly"
										@update:modelValue="
											(val) => updateRow(idx, { value: `{${val}}` })
										"
									/>
									<span
										class="expr-bracket"
										v-if="row.value_type === 'Expression'"
										>}</span
									>
								</div>
							</template>
							<template v-else>
								<select
									v-if="row.operator === 'is'"
									class="form-control input-xs"
									:value="row.value"
									:disabled="readOnly"
									@change="
										(e) =>
											updateRow(idx, {
												value: e.target.value,
												value_type: 'Value',
											})
									"
								>
									<option value="set">{{ __("Set") }}</option>
									<option value="not set">{{ __("Not Set") }}</option>
								</select>
								<select
									v-else-if="row.operator === 'Timespan'"
									class="form-control input-xs"
									:value="row.value"
									:disabled="readOnly"
									@change="
										(e) =>
											updateRow(idx, {
												value: e.target.value,
												value_type: 'Value',
											})
									"
								>
									<option
										v-for="opt in timespanOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
								<div v-else class="control-slot">
									<ControlFactory
										:df="getControlFactorySchema(row)"
										:modelValue="getDisplayValue(row)"
										:read_only="readOnly"
										:hideLabel="true"
										@update:modelValue="(val) => updateRow(idx, { value: val })"
									/>
								</div>
							</template>
						</div>
					</div>

					<!-- Delete -->
					<div v-if="!readOnly" class="filter-col action-col">
						<button class="btn btn-xs btn-link text-danger" @click="removeFilter(idx)">
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>

			<div v-if="!readOnly" class="filter-actions mt-2">
				<button class="btn btn-xs btn-link p-0 text-primary" @click="addFilter">
					<i class="fa fa-plus mr-1"></i> {{ __("Add Filter") }}
				</button>
				<button
					v-if="filters.length > 0"
					class="btn btn-xs btn-link p-0 text-muted ml-3"
					@click="clearFilters"
				>
					{{ __("Clear All") }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import ControlFactory from "../../controls/ControlFactory.vue";
import ValueResolverControl from "../../controls/ValueResolverControl.vue";
import { useStore } from "../../stores";
import { compileToCode } from "../../../core/builder_utils.js";
import { getContract } from "../../../core/contracts.js";

const props = defineProps({
	modelValue: {
		type: Array,
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
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();

const panelStyleVars = computed(() => {
	const node = (store.nodes || []).find((n) => n.id === props.nodeId);
	const actionType = node?.data?.action_type || node?.type;
	const accent = getContract(actionType)?.css?.color || "var(--fxr-accent)";
	return {
		"--fxr-node-accent": accent,
		"--fxr-node-accent-light": `color-mix(in srgb, ${accent} 12%, white)`,
	};
});

const filters = ref([]);
const BASE_VALUE_TYPES = ["Value", "Number", "Boolean", "Variable", "Expression"];
const BUILDER_VALUE_TYPE = "Builder";
const VALUE_TYPE_LABELS = {
	Value: __("Literal"),
	Number: __("Number"),
	Boolean: __("Yes / No"),
	Variable: __("Variable"),
	Expression: __("Formula (Advanced)"),
	Builder: __("Formula Builder"),
};

const timespanOptions = frappe.ui?.filter_utils?.get_timespan_options
	? frappe.ui.filter_utils.get_timespan_options([
			"Last",
			"Yesterday",
			"Today",
			"Tomorrow",
			"This",
			"Next",
	  ])
	: [
			{ label: __("Last 7 Days"), value: "last 7 days" },
			{ label: __("Last 14 Days"), value: "last 14 days" },
			{ label: __("Last 30 Days"), value: "last 30 days" },
			{ label: __("Last 90 Days"), value: "last 90 days" },
			{ label: __("Last Week"), value: "last week" },
			{ label: __("Last Month"), value: "last month" },
			{ label: __("Last Quarter"), value: "last quarter" },
			{ label: __("Last 6 Months"), value: "last 6 months" },
			{ label: __("Last Year"), value: "last year" },
			{ label: __("Yesterday"), value: "yesterday" },
			{ label: __("Today"), value: "today" },
			{ label: __("Tomorrow"), value: "tomorrow" },
			{ label: __("This Week"), value: "this week" },
			{ label: __("This Month"), value: "this month" },
			{ label: __("This Quarter"), value: "this quarter" },
			{ label: __("This Year"), value: "this year" },
			{ label: __("Next 7 Days"), value: "next 7 days" },
			{ label: __("Next 14 Days"), value: "next 14 days" },
			{ label: __("Next 30 Days"), value: "next 30 days" },
			{ label: __("Next Week"), value: "next week" },
			{ label: __("Next Month"), value: "next month" },
			{ label: __("Next Quarter"), value: "next quarter" },
			{ label: __("Next 6 Months"), value: "next 6 months" },
			{ label: __("Next Year"), value: "next year" },
	  ];

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
	Data: ["starts with", "ends with"], // FlexiRule enhancement (not in core Frappe)
	Text: ["starts with", "ends with"], // FlexiRule enhancement
	"Small Text": ["starts with", "ends with"], // FlexiRule enhancement
	"Long Text": ["starts with", "ends with"], // FlexiRule enhancement
	"Text Editor": ["starts with", "ends with"], // FlexiRule enhancement
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
const DATE_FIELDTYPES = new Set(["Date", "Datetime"]);
const BUILDER_SUPPORTED_FIELDTYPES = new Set([
	"Date",
	"Datetime",
	"Int",
	"Float",
	"Currency",
	"Percent",
	"Data",
	"Small Text",
	"Text",
	"Long Text",
	"Select",
]);
const builderFunctionOptions = [
	{ value: "add_days_doc", label: __("Document Date +/- Days") },
	{ value: "doc_field", label: __("Document Date (No Offset)") },
	{ value: "today", label: __("Today") },
	{ value: "add_days_today", label: __("Today +/- Days") },
];

const CHECK_VALUE_TYPES = ["Boolean", "Variable", "Expression"];
const isCheckField = (field) => field?.original_type === "Check" || field?.fieldtype === "Check";
const getDefaultValueTypeForField = (field) => (isCheckField(field) ? "Boolean" : "Value");
const formatBooleanValueForDisplay = (value) => {
	if (value === true || value === 1 || value === "1" || value === "Yes") return "Yes";
	if (value === false || value === 0 || value === "0" || value === "No") return "No";
	return value;
};

const getExtraOperatorsForField = (field) => {
	if (!field?.fieldtype) return [];
	return EXTRA_FILTER_OPERATORS_BY_FIELDTYPE[field.fieldtype] || [];
};

const getNestedSetOperatorsForField = (field) => {
	if (!field || field.fieldtype !== "Link") return [];
	const nestedSetDoctypes = frappe.boot?.nested_set_doctypes || [];
	return nestedSetDoctypes.includes(field.options) ? NESTED_SET_OPERATORS : [];
};

// Initialize local state from modelValue
const syncFromProps = () => {
	if (!props.modelValue || !Array.isArray(props.modelValue)) {
		filters.value = [];
		return;
	}

	// Consistency mapping for comparison
	const format = (list) =>
		(list || []).map((f) => ({
			doctype: f.doctype || props.doctype,
			field: f.field || f.fieldname,
			operator: f.operator || f.op || "=",
			value: f.value,
			value_type: f.value_type || "Value",
			builder: f.builder || null,
		}));

	const current_cleaned = format(filters.value.filter((f) => f.field || f.fieldname));
	const incoming_cleaned = format(
		(props.modelValue || []).filter((f) => f.field || f.fieldname || (Array.isArray(f) && f[1]))
	);

	// Stability check: If our cleaned local state is already same as incoming prop,
	// do nothing. This preserves local state while ensuring we stay synced.
	if (JSON.stringify(current_cleaned) === JSON.stringify(incoming_cleaned)) {
		return;
	}

	// Normalize if coming from frappe format [dt, field, op, val]
	filters.value = props.modelValue.map((f) => {
		let row = {};
		if (Array.isArray(f)) {
			const payload = f[3];
			const payloadValue =
				payload && typeof payload === "object" && !Array.isArray(payload)
					? payload.value
					: payload;
			row = {
				doctype: f[0],
				field: f[1],
				operator: f[2],
				value: payloadValue,
				value_type:
					payload && typeof payload === "object" && !Array.isArray(payload)
						? payload.value_type || guessValueType(payloadValue)
						: guessValueType(payloadValue),
				builder:
					payload && typeof payload === "object" && !Array.isArray(payload)
						? payload.builder || null
						: null,
			};
		} else {
			row = {
				doctype: f.doctype || props.doctype,
				field: f.field || f.fieldname,
				operator: f.operator || f.op || "=",
				value: f.value,
				value_type: f.value_type || guessValueType(f.value),
				builder: f.builder || null,
			};
		}
		row = normalizeBuilderState(row);
		// Ensure operator is valid for field
		const field = getFieldDef(row.field, row.doctype);
		const allowed = getOperatorsForField(field);
		if (!allowed.includes(row.operator)) {
			const defaultCondition = getDefaultCondition(field, row.doctype || props.doctype);
			row.operator = allowed.includes(defaultCondition)
				? defaultCondition
				: allowed[0] || "=";
		}
		const allowedValueTypes = getValueTypeOptions(row);
		if (!allowedValueTypes.includes(row.value_type)) {
			row.value_type = getDefaultValueTypeForField(field);
			row.builder = null;
		}
		if (isCheckField(field)) {
			row.operator = "=";
			if (!CHECK_VALUE_TYPES.includes(row.value_type)) {
				row.value_type = "Boolean";
			}
			if (row.value_type === "Boolean") {
				row.value = formatBooleanValueForDisplay(row.value);
				if (row.value !== "Yes" && row.value !== "No") {
					row.value = "No";
				}
			}
		}
		return row;
	});
};

const normalizeLikePattern = (value) => {
	if (typeof value !== "string") return value;
	const trimmed = value.trim();
	if (!trimmed) return "";
	if (trimmed.startsWith("%") || trimmed.endsWith("%")) return trimmed;
	return `%${trimmed}%`;
};

const normalizeInValues = (value) => {
	if (Array.isArray(value)) {
		return value.map((v) => String(v).trim()).filter(Boolean);
	}
	if (typeof value !== "string") {
		return value ? [String(value)] : [];
	}
	const raw = value.trim();
	if (!raw) return [];
	try {
		const parsed = JSON.parse(raw);
		if (Array.isArray(parsed)) return parsed.map((v) => String(v).trim()).filter(Boolean);
		return [String(parsed).trim()].filter(Boolean);
	} catch (e) {
		return raw
			.split(",")
			.map((v) => v.trim())
			.filter(Boolean);
	}
};

const normalizeIsValue = (value) => {
	const raw = (value || "").toString().trim().toLowerCase();
	return raw === "not set" ? "not set" : "set";
};

const normalizeBooleanValue = (value) => {
	if (value === true || value === 1 || value === "1" || value === "Yes") return 1;
	if (value === false || value === 0 || value === "0" || value === "No") return 0;
	return value;
};

const normalizeFilterValueForOperator = (row, value) => {
	if (row.value_type === BUILDER_VALUE_TYPE) return value;
	if (row.operator === "like" || row.operator === "not like") {
		return normalizeLikePattern(value);
	}
	if (row.operator === "in" || row.operator === "not in") {
		return normalizeInValues(value);
	}
	if (row.operator === "is") {
		return normalizeIsValue(value);
	}
	return value === "%" ? "" : value;
};

const getDisplayValue = (row) => {
	if (
		["=", "!="].includes(row.operator) &&
		Array.isArray(row.value) &&
		row.value.length === 2 &&
		typeof row.value[0] === "string"
	) {
		return row.value[1];
	}
	return row.value;
};

const normalizeRowForEmit = (row) => {
	const normalized = { ...row };
	const field = getFieldDef(normalized.field, normalized.doctype || props.doctype);
	if (field?.original_type === "Check" || field?.fieldtype === "Check") {
		normalized.value = normalizeBooleanValue(normalized.value);
	}
	if (
		normalized.operator === "Between" &&
		Array.isArray(normalized.value) &&
		normalized.value.length >= 2
	) {
		normalized.value = [normalized.value[0], normalized.value[1]];
	} else {
		normalized.value = normalizeFilterValueForOperator(normalized, normalized.value);
	}
	return normalized;
};

const emitUpdate = () => {
	const serialized = filters.value
		.filter((r) => r.field)
		.map((r) => {
			const n = normalizeRowForEmit(r);
			const payload = {
				value: n.value,
				value_type: n.value_type || "Value",
			};
			if (n.value_type === BUILDER_VALUE_TYPE && n.builder) {
				payload.builder = n.builder;
			}
			return [n.doctype || props.doctype, n.field, n.operator || "=", payload];
		});
	emit("update:modelValue", serialized);
};

const guessValueType = (val) => {
	if (typeof val === "number") return "Number";
	if (typeof val === "boolean") return "Boolean";
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
		return "Expression";
	}
	return "Value";
};

const stripBracket = (val) => {
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
		return val.slice(1, -1);
	}
	return val;
};

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
	if (!meta) {
		return [];
	}

	const mapped = [];

	// Fetch unified fields (including standard ones like modified_by) from the meta store
	const parentFields = store.get_fields_for_doctype(dt, "");
	for (const df of parentFields) {
		if (!shouldIncludeFilterField(df, dt)) continue;
		if (frappe.model.table_fields.includes(df.fieldtype)) continue;
		mapped.push({
			...df,
			parent: dt,
		});
	}

	// Child table fields in parent context (Frappe-style)
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
				label: `${tableDf.label || tableDf.fieldname}: ${
					childDf.label || childDf.fieldname
				} (${value})`,
				value,
			});
		}
	}

	doctypeFieldsCache.set(dt, mapped);
	return mapped;
};

// Clear cache if metadata changes
watch(
	() => store.doc_meta,
	() => doctypeFieldsCache.clear(),
	{ deep: true }
);

const getFieldDef = (fieldname, doctype) => {
	if (!fieldname) return null;
	const dt = doctype || props.doctype;
	const isDotted = typeof fieldname === "string" && fieldname.includes(".");

	// Standard field fallbacks
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

	// Child table field: table_field.child_field
	if (isDotted && dt) {
		const [tableFieldname, childFieldname] = fieldname.split(".", 2);
		const tableDf = frappe.meta.get_docfield(dt, tableFieldname);
		if (tableDf && tableDf.options) {
			const childDf = frappe.meta.get_docfield(tableDf.options, childFieldname);
			if (childDf) {
				return {
					...childDf,
					value: fieldname,
					fieldname,
					parentfield: tableFieldname,
					parenttype: dt,
					parent: tableDf.options,
				};
			}
		}
	}

	// Try Frappe's native meta cache
	const raw_fieldname =
		typeof fieldname === "string" && fieldname.startsWith("doc.")
			? fieldname.substring(4)
			: fieldname;
	if (dt && window.frappe && frappe.meta && frappe.meta.has_field(dt, raw_fieldname)) {
		const df = frappe.meta.get_docfield(dt, raw_fieldname);
		if (df) {
			return { ...df, value: fieldname }; // ensure value alias is there
		}
	}

	// Fallback to locally extracted list
	const fields = getFieldsForDoctype(dt);
	return fields.find((f) => f.value === fieldname) || null;
};

const getOperatorsForField = (field) => {
	if (!field) return [...BASE_QUERY_OPERATORS, ...QUERY_EXTENSION_OPERATORS];
	const all = [...BASE_QUERY_OPERATORS, ...QUERY_EXTENSION_OPERATORS];
	const invalid =
		FRAPPE_INVALID_CONDITION_MAP[field.original_type] ||
		FRAPPE_INVALID_CONDITION_MAP[field.fieldtype] ||
		[];
	const allowed = all.filter((op) => !invalid.includes(op));
	const extra = getExtraOperatorsForField(field);
	for (const op of extra) {
		if (!allowed.includes(op)) allowed.push(op);
	}
	const nestedSetOps = getNestedSetOperatorsForField(field);
	for (const op of nestedSetOps) {
		if (!allowed.includes(op)) allowed.push(op);
	}
	if (isCheckField(field)) return allowed.filter((op) => op === "=" || op === "!=");
	return allowed.length ? allowed : ["="];
};

const getDefaultCondition = (field, doctype) => {
	if (!field) return "=";
	if (field.fieldtype === "Data") {
		try {
			const meta = doctype ? frappe.get_meta(doctype) : null;
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
};

const getOperatorLabel = (operator, row) => {
	const field = getFieldDef(row?.field, row?.doctype || props.doctype);
	if (field && (field.fieldtype === "Date" || field.fieldtype === "Datetime")) {
		return DATE_OPERATOR_LABELS[operator] || operatorLabelMap[operator] || operator;
	}
	return operatorLabelMap[operator] || operator;
};

const getValueTypeLabel = (valueType, row) => {
	if (valueType === BUILDER_VALUE_TYPE) {
		const field = getFieldDef(row?.field, row?.doctype || props.doctype);
		if (field && DATE_FIELDTYPES.has(field.fieldtype)) return __("Date Formula");
		if (
			field &&
			BUILDER_SUPPORTED_FIELDTYPES.has(field.fieldtype) &&
			!DATE_FIELDTYPES.has(field.fieldtype)
		)
			return __("Math Formula");
		return __("Formula Builder");
	}
	return VALUE_TYPE_LABELS[valueType] || __(valueType);
};

const getValueTypeOptions = (row) => {
	const field = getFieldDef(row.field, row.doctype || props.doctype);
	if (!field || !field.fieldtype) {
		return [...BASE_VALUE_TYPES];
	}
	if (isCheckField(field)) {
		return [...CHECK_VALUE_TYPES];
	}
	const options = [...BASE_VALUE_TYPES];
	if (BUILDER_SUPPORTED_FIELDTYPES.has(field.fieldtype)) {
		options.push(BUILDER_VALUE_TYPE);
	}
	return options;
};

const isBooleanValue = (row) => {
	if (row.value_type === "Boolean") return true;
	const field = getFieldDef(row.field, row.doctype || props.doctype);
	return field && field.fieldtype === "Check";
};

const getVariableOptions = async () => {
	if (!props.nodeId) return [];
	return await store.getAvailableVariables(props.nodeId);
};

const getControlFactorySchema = (row) => {
	const field = getFieldDef(row.field, row.doctype || props.doctype);
	let schema = field ? frappe.utils.deep_clone(field) : { fieldtype: "Data", fieldname: "value" };
	const rawField =
		typeof row.field === "string" && row.field.startsWith("doc.")
			? row.field.substring(4)
			: row.field;
	schema.label = "";
	schema.read_only = props.readOnly;
	schema.fieldname = rawField; // Ensure valid fieldname for frappe controls (no doc. prefix)

	// Native Frappe Filter Manipulation (perfect parity)
	if (window.frappe && frappe.ui && frappe.ui.filter_utils) {
		frappe.ui.filter_utils.set_fieldtype(schema, null, row.operator);
		// Force restore fieldtype for Between if it's a date/time field,
		// as set_fieldtype might sometimes generalize it to Data for multiple values
		if (row.operator === "Between" && ["Date", "Datetime", "Time"].includes(field?.fieldtype)) {
			schema.fieldtype = field.fieldtype;
		}
	} else {
		// Fallback if filter_utils is somehow missing
		if (schema.fieldname === "docstatus") {
			schema.fieldtype = "Select";
			schema.options = [
				{ value: "0", label: __("Draft") },
				{ value: "1", label: __("Submitted") },
				{ value: "2", label: __("Cancelled") },
			];
		} else if (schema.fieldtype === "Check") {
			schema.fieldtype = "Select";
			schema.options = [
				{ label: __("Yes"), value: "1" },
				{ label: __("No"), value: "0" },
			];
		}
	}

	// FlexiRule Specific overrides for multi-value operators
	if (["in", "not in"].includes(row.operator)) {
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
	} else if (["=", "!="].includes(row.operator) && field?.fieldtype === "Link") {
		// Ensure Link dropdown is preserved for equality operators
		schema.fieldtype = "Link";
		schema.options = field.options;
	} else if (row.operator === "Between") {
		schema.placeholder = __("Value1, Value2");
	}

	return schema;
};

const addFilter = () => {
	const defaultField = "name";
	const defaultFieldDef = getFieldDef(defaultField, props.doctype);
	const defaultOperator = getDefaultCondition(defaultFieldDef, props.doctype);
	filters.value.push({
		doctype: props.doctype,
		field: defaultField,
		operator: defaultOperator,
		value: "",
		value_type: "Value",
	});
	emitUpdate();
};

const toInt = (value, fallback = 0) => {
	const parsed = Number.parseInt(value, 10);
	return Number.isFinite(parsed) ? parsed : fallback;
};

const NUMERIC_FIELDTYPES = new Set(["Int", "Float", "Currency", "Percent"]);

const STRING_FIELDTYPES = new Set(["Data", "Small Text", "Text", "Long Text", "Select"]);

const getAllowedBuilderKinds = (row) => {
	const field = getFieldDef(row.field, row.doctype || props.doctype);
	if (!field || !field.fieldtype) return null; // all kinds
	if (DATE_FIELDTYPES.has(field.fieldtype)) {
		return ["date_formula", "date_diff", "format"];
	}
	if (NUMERIC_FIELDTYPES.has(field.fieldtype)) {
		return ["math_formula", "format"];
	}
	if (STRING_FIELDTYPES.has(field.fieldtype)) {
		return ["normalization", "format", "string_formula"];
	}
	return null; // all kinds
};

const normalizeBuilderItem = (item, fallbackField = "") => {
	const kind = item?.kind || "date_formula";

	// For non-date kinds, pass through the item structure
	if (kind === "math_formula") {
		return {
			kind: "math_formula",
			field_a: item?.field_a || "",
			math_op: item?.math_op || "+",
			field_b_type: item?.field_b_type || "field",
			field_b: item?.field_b || "",
			constant_b: item?.constant_b ?? 0,
			precision: item?.precision ?? 2,
		};
	}

	if (kind === "date_diff") {
		return {
			kind: "date_diff",
			diff_start_type: item?.diff_start_type || "today",
			diff_start_field: item?.diff_start_field || "",
			diff_end_type: item?.diff_end_type || "doc_field",
			diff_end_field: item?.diff_end_field || fallbackField || "",
			diff_unit: item?.diff_unit || "days",
		};
	}

	// Default: date_formula (backward compatible)
	const base_type =
		item?.base_type || (item?.function_name?.includes("today") ? "today" : "doc_field");
	return {
		kind: "date_formula",
		base_type: base_type,
		base_field: item?.base_field || fallbackField || "posting_date",
		offset_value: toInt(item?.offset_value ?? item?.offset_days ?? 0, 0),
		offset_unit: item?.offset_unit || "days",
	};
};

const getDefaultBuilderItem = (row) => {
	const field = getFieldDef(row.field, row.doctype || props.doctype);
	if (field && NUMERIC_FIELDTYPES.has(field.fieldtype)) {
		return normalizeBuilderItem({ kind: "math_formula", field_a: row.field || "" });
	}
	const dateField =
		getDateFieldOptions(row.doctype || props.doctype)[0]?.value || row.field || "posting_date";
	return normalizeBuilderItem({}, dateField);
};

const compileBuilderExpression = (builder) => {
	const item = normalizeBuilderItem(builder);
	return compileToCode(item);
};

const syncBuilderToValue = (row) => {
	if (row.value_type !== "Builder") return row;
	if (row.operator === "Between") {
		const list = Array.isArray(row.builder)
			? row.builder
			: [getDefaultBuilderItem(row), getDefaultBuilderItem(row)];
		const normalized = [
			normalizeBuilderItem(list[0], row.field || props.doctype),
			normalizeBuilderItem(list[1], row.field || props.doctype),
		];
		row.builder = normalized;
		row.value = normalized.map((item) => compileBuilderExpression(item));
		return row;
	}

	const single = Array.isArray(row.builder) ? row.builder[0] : row.builder;
	const normalized = normalizeBuilderItem(single, row.field || props.doctype);
	row.builder = normalized;
	row.value = compileBuilderExpression(normalized);
	return row;
};

const normalizeBuilderState = (row) => {
	if (row.value_type !== "Builder") return row;

	if (row.operator === "Between") {
		let builder = row.builder;
		if (!Array.isArray(builder)) {
			builder = [{}, {}];
		}
		row.builder = [
			normalizeBuilderItem(builder[0], row.field),
			normalizeBuilderItem(builder[1], row.field),
		];
	} else {
		const builder = Array.isArray(row.builder) ? row.builder[0] : row.builder;
		row.builder = normalizeBuilderItem(builder, row.field);
	}
	return syncBuilderToValue(row);
};

const getDateFieldOptions = (dt) => {
	return getFieldsForDoctype(dt).filter((f) => DATE_FIELDTYPES.has(f.fieldtype));
};

const getBuilderValue = (row, idx = null) => {
	// Read existing builder without re-normalizing to avoid creating new objects on every render.
	// Builder is already normalized during mutations (syncFromProps, updateRow, toggleValueType).
	const builder = row.builder;
	if (!builder) {
		return getDefaultBuilderItem(row);
	}
	if (idx === null || idx === undefined) {
		return Array.isArray(builder) ? builder[0] : builder;
	}
	return Array.isArray(builder) ? builder[idx] || getDefaultBuilderItem(row) : builder;
};

const updateBuilderValue = (idx, builderIndex, partial) => {
	const row = filters.value[idx];
	const merged = normalizeBuilderState({ ...row });
	if (merged.operator === "Between") {
		const list = Array.isArray(merged.builder)
			? [...merged.builder]
			: [getDefaultBuilderItem(merged), getDefaultBuilderItem(merged)];
		const i = builderIndex ?? 0;
		list[i] = normalizeBuilderItem({ ...(list[i] || {}), ...partial }, merged.field);
		merged.builder = list;
	} else {
		const single = Array.isArray(merged.builder) ? merged.builder[0] : merged.builder;
		merged.builder = normalizeBuilderItem({ ...(single || {}), ...partial }, merged.field);
	}
	syncBuilderToValue(merged);
	filters.value[idx] = merged;
	emitUpdate();
};

const removeFilter = (idx) => {
	filters.value.splice(idx, 1);
	emitUpdate();
};

const clearFilters = () => {
	filters.value = [];
	emitUpdate();
};

const updateRow = (idx, data) => {
	const row = filters.value[idx];
	const merged = { ...row, ...data };
	const field = getFieldDef(merged.field, merged.doctype || props.doctype);

	// If field changed, update operator and reset value if needed
	if (data.field && data.field !== row.field) {
		const operators = getOperatorsForField(field);
		if (!operators.includes(merged.operator)) {
			const defaultCondition = getDefaultCondition(field, merged.doctype || props.doctype);
			merged.operator = operators.includes(defaultCondition)
				? defaultCondition
				: operators[0] || "=";
		}
	}

	// Handle operator change to/from Between
	if (data.operator && data.operator !== row.operator) {
		if (data.operator === "Between" && !Array.isArray(merged.value)) {
			merged.value = [merged.value || "", ""];
		} else if (row.operator === "Between" && Array.isArray(merged.value)) {
			merged.value = merged.value[0] || "";
		}
	}

	if (merged.value_type === "Builder") {
		normalizeBuilderState(merged);
	}

	if (isCheckField(field)) {
		merged.operator = "=";
		if (!CHECK_VALUE_TYPES.includes(merged.value_type)) {
			merged.value_type = "Boolean";
			merged.builder = null;
		}
		if (merged.value_type === "Boolean") {
			merged.value = formatBooleanValueForDisplay(merged.value);
			if (merged.value !== "Yes" && merged.value !== "No") {
				merged.value = formatBooleanValueForDisplay(row.value);
			}
			if (merged.value !== "Yes" && merged.value !== "No") {
				merged.value = "No";
			}
		}
	}
	const allowedValueTypes = getValueTypeOptions(merged);
	if (!allowedValueTypes.includes(merged.value_type)) {
		merged.value_type = getDefaultValueTypeForField(field);
		merged.builder = null;
	}

	filters.value[idx] = merged;
	emitUpdate();
};

const getBetweenValue = (value, idx) => {
	if (Array.isArray(value)) return value[idx] || "";
	if (typeof value === "string" && value.includes(",")) {
		return value.split(",")[idx]?.trim() || "";
	}
	return idx === 0 ? value : "";
};

const setBetweenValue = (idx, valIdx, newVal) => {
	const row = filters.value[idx];
	let currentVal = row.value;
	if (!Array.isArray(currentVal)) {
		currentVal = [getBetweenValue(currentVal, 0), getBetweenValue(currentVal, 1)];
	}
	currentVal[valIdx] = newVal;
	updateRow(idx, { value: [...currentVal] });
};

const toggleValueType = (idx, type) => {
	const row = filters.value[idx];
	row.value_type = type;
	const field = getFieldDef(row.field, row.doctype || props.doctype);

	if (type === BUILDER_VALUE_TYPE) {
		row.builder =
			row.operator === "Between"
				? [getDefaultBuilderItem(row), getDefaultBuilderItem(row)]
				: getDefaultBuilderItem(row);
		syncBuilderToValue(row);
	} else if (type === "Boolean") {
		row.builder = null;
		row.value = formatBooleanValueForDisplay(row.value);
		if (row.value !== "Yes" && row.value !== "No") {
			row.value = "No";
		}
	} else if (type === "Expression" || type === "Variable") {
		row.builder = null;
		if (!row.value || typeof row.value !== "string" || !row.value.startsWith("{")) {
			row.value = `{${row.value || ""}}`;
		}
	} else if (row.value && typeof row.value === "string" && row.value.startsWith("{")) {
		row.builder = null;
		row.value = stripBracket(row.value);
	} else {
		row.builder = null;
	}
	if (isCheckField(field) && !CHECK_VALUE_TYPES.includes(row.value_type)) {
		row.value_type = "Boolean";
	}

	emitUpdate();
};

const isFieldValid = (fieldname, dt) => {
	const fields = getFieldsForDoctype(dt || props.doctype);
	if (!fields || !fields.length) return true;
	if (!fieldname) return true;
	if (typeof fieldname === "string" && fieldname.startsWith("{")) return true;
	return fields.some((f) => f.value === fieldname);
};

watch(() => props.modelValue, syncFromProps, { deep: true });
watch(
	() => props.doctype,
	() => {
		// Optional: Clear filters if doctype changes and not allowing any doctype
		// if (!props.allowAnyDoctype) clearFilters();
	}
);

onMounted(async () => {
	syncFromProps();
});
</script>

<style scoped>
/* ─── FilterGroup – Unified Design ─── */
.filter-group-wrapper {
	width: 100%;
	font-family: var(--fxr-font-family);
}

.filter-list {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

/* ─── Filter Row ─── */
.filter-row {
	display: flex;
	flex-direction: column;
	background: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-lg);
	padding: var(--fxr-space-4) var(--fxr-space-5);
	transition: border-color var(--fxr-transition-fast), box-shadow var(--fxr-transition-fast);
}

.filter-row:hover {
	border-color: var(--fxr-border-strong);
	box-shadow: var(--fxr-shadow-sm);
}

.filter-row-main {
	display: grid;
	grid-template-columns: 1.6fr 0.9fr 0.85fr 2.2fr auto;
	gap: var(--fxr-space-4);
	align-items: center;
}

/* ─── Column Sizing ─── */
.doctype-col {
	grid-column: span 1;
}

.field-col {
	min-width: 110px;
}

.operator-col {
	min-width: 80px;
}

.value-col {
	min-width: 180px;
}

.type-col {
	min-width: 120px;
}

.action-col {
	width: 28px;
	display: flex;
	justify-content: center;
}

/* ─── Field Picker ─── */
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
	border-color: #f59e0b !important;
	background-color: #fffbeb !important;
}

/* ─── Value Area ─── */
.value-input-group {
	display: flex;
	width: 100%;
}

.control-slot {
	width: 100%;
	min-width: 0;
}

/* ─── Expression Wrapper ─── */
.expression-wrapper {
	display: flex;
	align-items: center;
	background: var(--fxr-badge-expr);
	border: 1px solid #fed7aa;
	border-radius: var(--fxr-radius-md);
	padding: 0 var(--fxr-space-2);
	width: 100%;
	transition: border-color var(--fxr-transition-fast);
}

.expression-wrapper:focus-within {
	border-color: #fb923c;
	box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.1);
}

.expr-bracket {
	color: #ea580c;
	font-weight: var(--fxr-weight-bold);
	padding: 0 var(--fxr-space-2);
	font-size: var(--fxr-text-md);
	user-select: none;
}

.expression-wrapper.variable-mode {
	background: var(--fxr-badge-var);
	border-color: #c4b5fd;
}

.expression-wrapper.variable-mode:focus-within {
	border-color: #a78bfa;
	box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.1);
}

.expression-wrapper.variable-mode .expr-bracket {
	color: var(--fxr-badge-var-text);
}

/* ─── Value Type Select ─── */
.type-select {
	font-size: var(--fxr-text-xs) !important;
	height: var(--fxr-input-height-sm) !important;
	padding: 1px 20px 1px 6px !important;
	background-color: var(--fxr-bg-muted) !important;
	border: 1px solid transparent !important;
	border-radius: var(--fxr-radius-pill) !important;
	color: var(--fxr-text-secondary);
	font-weight: var(--fxr-weight-semibold);
	appearance: none;
	-webkit-appearance: none;
	cursor: pointer;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2.5'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
	background-repeat: no-repeat;
	background-position: right 5px center;
	background-size: 10px;
	transition: all var(--fxr-transition-fast);
	letter-spacing: 0.01em;
}

.type-select:hover:not(:disabled) {
	background-color: #e2e8f0 !important;
	border-color: var(--fxr-border-strong) !important;
}

.type-select:focus {
	border-color: var(--fxr-border-focus) !important;
	box-shadow: var(--fxr-shadow-focus) !important;
	background-color: var(--fxr-bg-card) !important;
}

/* ─── Between / Dual Value ─── */
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

.builder-wrapper {
	width: 100%;
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

/* ─── Actions Bar ─── */
.filter-actions {
	display: flex;
	align-items: center;
	padding-top: var(--fxr-space-4);
}

.filter-actions .btn {
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-medium);
	border-radius: var(--fxr-radius-md);
	transition: all var(--fxr-transition-fast);
}

.filter-actions .btn:hover {
	text-decoration: none;
}

/* ─── Delete Button ─── */
.filter-col.action-col .btn {
	width: 26px;
	height: 26px;
	padding: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: var(--fxr-radius-sm);
	opacity: 0.4;
	transition: all var(--fxr-transition-fast);
}

.filter-row:hover .filter-col.action-col .btn {
	opacity: 0.7;
}

.filter-col.action-col .btn:hover {
	opacity: 1;
	background: var(--fxr-bg-danger);
}

/* ─── Empty State ─── */
.border-dashed {
	border: 1px dashed var(--fxr-border);
	border-radius: var(--fxr-radius-lg);
}

/* ─── Deep Overrides for Nested Controls ─── */
:deep(.field-picker-control) {
	margin-bottom: 0 !important;
}

:deep(.control.frappe-control) {
	margin-bottom: 0 !important;
}

/* Unified input sizing inside filter rows */
.filter-row-main :deep(.form-control),
.filter-row-main :deep(input.form-control),
.filter-row-main :deep(select.form-control) {
	height: var(--fxr-input-height) !important;
	padding: var(--fxr-input-padding-y) var(--fxr-input-padding-x) !important;
	font-size: var(--fxr-input-font-size) !important;
	border: 1px solid var(--fxr-border) !important;
	border-radius: var(--fxr-radius-md) !important;
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

.filter-row-main :deep(.form-control:hover:not(:disabled):not(:focus)) {
	border-color: var(--fxr-border-strong) !important;
}

/* Select dropdown arrow consistency */
.filter-row-main :deep(select.form-control) {
	appearance: none !important;
	-webkit-appearance: none !important;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E") !important;
	background-repeat: no-repeat !important;
	background-position: right 6px center !important;
	background-size: 12px !important;
	padding-right: 24px !important;
	cursor: pointer;
}

/* Link control consistency */
.filter-row-main :deep(.link-field .form-control),
.filter-row-main :deep(.awesomplete input) {
	height: var(--fxr-input-height) !important;
	font-size: var(--fxr-input-font-size) !important;
}

@media (max-width: 920px) {
	.filter-row-main {
		grid-template-columns: 1fr;
		gap: var(--fxr-space-3);
	}

	.action-col {
		width: 100%;
		justify-content: flex-end;
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

	.filter-actions {
		flex-wrap: wrap;
		gap: var(--fxr-space-3);
	}
}
</style>
