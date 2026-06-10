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
								ref="fieldPickerRefs"
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

					<!-- Value / Expression -->
					<div class="filter-col value-col">
						<div class="value-input-group">
							<template v-if="row.operator === 'Between'">
								<div class="dual-value-wrapper">
									<div class="value-input-item">
										<FlexValueControl
											:modelValue="
												Array.isArray(row.value)
													? row.value[0]
													: { mode: 'static', value: '' }
											"
											:context="{
												df: getControlFactorySchema(row),
												operator: row.operator,
												referenceDoctype: row.doctype || doctype,
											}"
											:disabled="readOnly"
											:engine="store"
											:doc="store?.rule_doc"
											:variableOptions="effectiveVariableOptions"
											@update:modelValue="
												(val) => updateBetweenValue(idx, 0, val)
											"
										/>
									</div>
									<span class="between-sep">{{ __("and") }}</span>
									<div class="value-input-item">
										<FlexValueControl
											:modelValue="
												Array.isArray(row.value)
													? row.value[1]
													: { mode: 'static', value: '' }
											"
											:context="{
												df: getControlFactorySchema(row),
												operator: row.operator,
												referenceDoctype: row.doctype || doctype,
											}"
											:disabled="readOnly"
											:engine="store"
											:doc="store?.rule_doc"
											:variableOptions="effectiveVariableOptions"
											@update:modelValue="
												(val) => updateBetweenValue(idx, 1, val)
											"
										/>
									</div>
								</div>
							</template>
							<template v-else>
								<div class="control-slot w-100 min-w-0">
									<FlexValueControl
										v-model="row.value"
										:context="{
											df: getControlFactorySchema(row),
											operator: row.operator,
											referenceDoctype: row.doctype || doctype,
										}"
										:engine="store"
										:doc="store?.rule_doc"
										:variableOptions="effectiveVariableOptions"
										:disabled="readOnly"
										:readOnly="readOnly"
										@update:modelValue="() => emitUpdate()"
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
import { ref, computed, watch, onMounted, inject, nextTick } from "vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import { useStore } from "../../stores";
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
	variableOptions: {
		type: Array,
		default: null,
	},
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const fieldPickerRefs = ref([]);

// Align with the new architecture: prefer injected variableOptions if prop is not explicitly provided.
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

const filters = ref([]);

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
const isCheckField = (field) => field?.original_type === "Check" || field?.fieldtype === "Check";

const getExtraOperatorsForField = (field) => {
	if (!field?.fieldtype) return [];
	return EXTRA_FILTER_OPERATORS_BY_FIELDTYPE[field.fieldtype] || [];
};

const getNestedSetOperatorsForField = (field) => {
	if (!field || field.fieldtype !== "Link") return [];
	const nestedSetDoctypes = frappe.boot?.nested_set_doctypes || [];
	return nestedSetDoctypes.includes(field.options) ? NESTED_SET_OPERATORS : [];
};

const coerceStructuredFilterValue = (rawValue) => {
	if (Array.isArray(rawValue)) {
		return rawValue.map((item) => coerceStructuredFilterValue(item));
	}

	if (rawValue && typeof rawValue === "object" && rawValue.mode) {
		if (["formula", "format", "normalize", "normalization"].includes(rawValue.mode)) {
			const config = { ...(rawValue.config || {}) };
			if (!config.kind) {
				if (rawValue.mode === "formula") config.kind = "math_formula";
				if (rawValue.mode === "format") config.kind = "format";
				if (rawValue.mode === "normalize" || rawValue.mode === "normalization") {
					config.kind = "normalization";
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

	// Legacy tuple payload object: { value, value_type, builder }
	if (
		rawValue &&
		typeof rawValue === "object" &&
		!Array.isArray(rawValue) &&
		"value" in rawValue
	) {
		const rawType = String(rawValue.value_type || "Value").toLowerCase();
		if (rawValue.builder && typeof rawValue.builder === "object") {
			return {
				mode: "resolver",
				value: rawValue.value || "",
				config: rawValue.builder,
			};
		}
		if (rawType === "variable") {
			const path = String(rawValue.value || "")
				.trim()
				.replace(/^\{/, "")
				.replace(/\}$/, "");
			return { mode: "variable", value: path };
		}
		if (rawType === "expression") {
			return { mode: "resolver", value: rawValue.value || "" };
		}
		return { mode: "static", value: rawValue.value };
	}

	return { mode: "static", value: rawValue };
};

// Initialize local state from modelValue
const syncFromProps = () => {
	if (!props.modelValue || !Array.isArray(props.modelValue)) {
		filters.value = [];
		return;
	}

	// Consistency mapping for comparison
	const format = (list) =>
		(list || []).map((f) => {
			if (Array.isArray(f)) {
				return {
					doctype: f[0] || props.doctype,
					field: f[1],
					operator: f[2] || "=",
					value: coerceStructuredFilterValue(f[3]),
				};
			}
			return {
				doctype: f.doctype || props.doctype,
				field: f.field || f.fieldname,
				operator: f.operator || f.op || "=",
				value: coerceStructuredFilterValue(f.value),
			};
		});

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
			const structuredValue = coerceStructuredFilterValue(payload);

			row = {
				doctype: f[0],
				field: f[1],
				operator: f[2],
				value: structuredValue,
			};
		} else {
			const structuredValue = coerceStructuredFilterValue(f.value);

			row = {
				doctype: f.doctype || props.doctype,
				field: f.field || f.fieldname,
				operator: f.operator || f.op || "=",
				value: structuredValue,
			};
		}

		// Ensure operator is valid for field
		const field = getFieldDef(row.field, row.doctype);
		const allowed = getOperatorsForField(field);
		if (!allowed.includes(row.operator)) {
			const defaultCondition = getDefaultCondition(field, row.doctype || props.doctype);
			row.operator = allowed.includes(defaultCondition)
				? defaultCondition
				: allowed[0] || "=";
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

const normalizeStructuredForOperator = (row, value) => {
	if (!value || typeof value !== "object" || value.mode !== "static") return value;
	let normalized = value.value;

	if (row.operator === "like" || row.operator === "not like") {
		normalized = normalizeLikePattern(normalized);
	} else if (row.operator === "in" || row.operator === "not in") {
		normalized = normalizeInValues(normalized);
	} else if (row.operator === "is") {
		normalized = normalizeIsValue(normalized);
	} else if (normalized === "%") {
		normalized = "";
	}

	const field = getFieldDef(row.field, row.doctype || props.doctype);
	if (isCheckField(field)) {
		normalized = normalizeBooleanValue(normalized);
	}

	return { ...value, value: normalized };
};

const emitUpdate = () => {
	const serialized = filters.value
		.filter((r) => r.field)
		.map((r) => {
			if (r.operator === "Between" && Array.isArray(r.value)) {
				return [
					r.doctype || props.doctype,
					r.field,
					r.operator || "=",
					r.value.slice(0, 2).map((val) => normalizeStructuredForOperator(r, val)),
				];
			}
			return [
				r.doctype || props.doctype,
				r.field,
				r.operator || "=",
				normalizeStructuredForOperator(r, r.value),
			];
		});
	emit("update:modelValue", serialized);
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
	const parentFields = store.get_fields_for_doctype(dt, { valueMode: "fieldname" });
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
		value: { mode: "static", value: "" },
	});
	emitUpdate();

	nextTick(() => {
		const lastIndex = filters.value.length - 1;
		if (lastIndex >= 0 && fieldPickerRefs.value[lastIndex]) {
			fieldPickerRefs.value[lastIndex].focus?.();
		}
	});
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
			merged.value = [
				{ mode: "static", value: "" },
				{ mode: "static", value: "" },
			];
		} else if (row.operator === "Between" && Array.isArray(merged.value)) {
			merged.value = merged.value[0] || { mode: "static", value: "" };
		}
	}

	filters.value[idx] = merged;
	emitUpdate();
};

const updateBetweenValue = (idx, arrayIndex, val) => {
	const row = filters.value[idx];
	const merged = { ...row };
	const list = Array.isArray(merged.value)
		? [...merged.value]
		: [
				{ mode: "static", value: "" },
				{ mode: "static", value: "" },
		  ];
	list[arrayIndex] = val;
	merged.value = list;
	filters.value[idx] = merged;
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
	display: flex;
	gap: var(--fxr-space-4);
	align-items: center;
	width: 100%;
}

/* ─── Column Sizing ─── */
.doctype-col {
	flex: 0 0 160px;
}

.field-col {
	flex: 0 0 220px;
	min-width: 110px;
}

.operator-col {
	flex: 0 0 110px;
}

.value-col {
	flex: 1;
	min-width: 0;
}

.action-col {
	flex: 0 0 28px;
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

	.action-col {
		width: 100%;
		flex: 1 1 100%;
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
