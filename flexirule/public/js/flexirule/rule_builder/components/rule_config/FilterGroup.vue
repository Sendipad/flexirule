<template>
	<div class="filter-group-wrapper">
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
						<LinkControl
							:df="{ label: '', fieldtype: 'Link', options: 'DocType' }"
							:modelValue="row.doctype || doctype"
							:hideLabel="true"
							:read_only="readOnly"
							@update:modelValue="(val) => updateRow(idx, { doctype: val })"
						/>
					</div>

					<!-- Field Picker -->
					<div class="filter-col field-col">
						<div class="field-picker-container">
							<FieldPickerControl
								:df="{ label: '' }"
								:fields="getFieldsForDoctype(row.doctype || doctype)"
								:documentType="row.doctype || doctype"
								:modelValue="row.field"
								:read_only="readOnly"
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
								{{ getValueTypeLabel(vt) }}
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
											<AutocompleteControl
												:df="{ fieldtype: 'Autocomplete', label: '' }"
												:modelValue="
													stripBracket(getBetweenValue(row.value, 0))
												"
												:get_options="getVariableOptions"
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
											<AutocompleteControl
												:df="{ fieldtype: 'Autocomplete', label: '' }"
												:modelValue="
													stripBracket(getBetweenValue(row.value, 1))
												"
												:get_options="getVariableOptions"
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
										<div class="dual-value-wrapper">
											<div class="value-input-item">
												<div class="builder-card">
													<div class="builder-label small text-muted">
														{{ __("From") }}
													</div>
													<select
														class="form-control input-xs"
														:value="
															getBuilderValue(row, 0).function_name
														"
														:disabled="readOnly"
														@change="
															(e) =>
																updateBuilderValue(idx, 0, {
																	function_name: e.target.value,
																})
														"
													>
														<option
															v-for="opt in builderFunctionOptions"
															:key="opt.value"
															:value="opt.value"
														>
															{{ opt.label }}
														</option>
													</select>
													<select
														v-if="
															builderNeedsBaseField(
																getBuilderValue(row, 0)
															)
														"
														class="form-control input-xs"
														:value="getBuilderValue(row, 0).base_field"
														:disabled="readOnly"
														@change="
															(e) =>
																updateBuilderValue(idx, 0, {
																	base_field: e.target.value,
																})
														"
													>
														<option
															v-for="opt in getDateFieldOptions(
																row.doctype || doctype
															)"
															:key="opt.value"
															:value="opt.value"
														>
															{{ opt.label }}
														</option>
													</select>
													<div
														v-if="
															builderNeedsOffset(
																getBuilderValue(row, 0)
															)
														"
														class="builder-offset-row"
													>
														<span class="small text-muted">{{
															__("Offset (days)")
														}}</span>
														<input
															type="number"
															class="form-control input-xs"
															:value="
																getBuilderValue(row, 0).offset_days
															"
															:disabled="readOnly"
															@input="
																(e) =>
																	updateBuilderValue(idx, 0, {
																		offset_days: toInt(
																			e.target.value
																		),
																	})
															"
														/>
													</div>
													<div class="builder-preview text-muted">
														{{
															builderPreview(getBuilderValue(row, 0))
														}}
													</div>
												</div>
											</div>
											<span class="between-sep">{{ __("and") }}</span>
											<div class="value-input-item">
												<div class="builder-card">
													<div class="builder-label small text-muted">
														{{ __("To") }}
													</div>
													<select
														class="form-control input-xs"
														:value="
															getBuilderValue(row, 1).function_name
														"
														:disabled="readOnly"
														@change="
															(e) =>
																updateBuilderValue(idx, 1, {
																	function_name: e.target.value,
																})
														"
													>
														<option
															v-for="opt in builderFunctionOptions"
															:key="opt.value"
															:value="opt.value"
														>
															{{ opt.label }}
														</option>
													</select>
													<select
														v-if="
															builderNeedsBaseField(
																getBuilderValue(row, 1)
															)
														"
														class="form-control input-xs"
														:value="getBuilderValue(row, 1).base_field"
														:disabled="readOnly"
														@change="
															(e) =>
																updateBuilderValue(idx, 1, {
																	base_field: e.target.value,
																})
														"
													>
														<option
															v-for="opt in getDateFieldOptions(
																row.doctype || doctype
															)"
															:key="opt.value"
															:value="opt.value"
														>
															{{ opt.label }}
														</option>
													</select>
													<div
														v-if="
															builderNeedsOffset(
																getBuilderValue(row, 1)
															)
														"
														class="builder-offset-row"
													>
														<span class="small text-muted">{{
															__("Offset (days)")
														}}</span>
														<input
															type="number"
															class="form-control input-xs"
															:value="
																getBuilderValue(row, 1).offset_days
															"
															:disabled="readOnly"
															@input="
																(e) =>
																	updateBuilderValue(idx, 1, {
																		offset_days: toInt(
																			e.target.value
																		),
																	})
															"
														/>
													</div>
													<div class="builder-preview text-muted">
														{{
															builderPreview(getBuilderValue(row, 1))
														}}
													</div>
												</div>
											</div>
										</div>
									</template>
									<template v-else>
										<div class="builder-card">
											<div class="builder-label small text-muted">
												{{ __("Date Formula Builder") }}
											</div>
											<select
												class="form-control input-xs"
												:value="getBuilderValue(row).function_name"
												:disabled="readOnly"
												@change="
													(e) =>
														updateBuilderValue(idx, null, {
															function_name: e.target.value,
														})
												"
											>
												<option
													v-for="opt in builderFunctionOptions"
													:key="opt.value"
													:value="opt.value"
												>
													{{ opt.label }}
												</option>
											</select>
											<select
												v-if="builderNeedsBaseField(getBuilderValue(row))"
												class="form-control input-xs"
												:value="getBuilderValue(row).base_field"
												:disabled="readOnly"
												@change="
													(e) =>
														updateBuilderValue(idx, null, {
															base_field: e.target.value,
														})
												"
											>
												<option
													v-for="opt in getDateFieldOptions(
														row.doctype || doctype
													)"
													:key="opt.value"
													:value="opt.value"
												>
													{{ opt.label }}
												</option>
											</select>
											<div
												v-if="builderNeedsOffset(getBuilderValue(row))"
												class="builder-offset-row"
											>
												<span class="small text-muted">{{
													__("Offset (days)")
												}}</span>
												<input
													type="number"
													class="form-control input-xs"
													:value="getBuilderValue(row).offset_days"
													:disabled="readOnly"
													@input="
														(e) =>
															updateBuilderValue(idx, null, {
																offset_days: toInt(e.target.value),
															})
													"
												/>
											</div>
											<div class="builder-preview text-muted">
												{{ builderPreview(getBuilderValue(row)) }}
											</div>
										</div>
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
									<AutocompleteControl
										:df="{ fieldtype: 'Autocomplete', label: '' }"
										:modelValue="stripBracket(row.value)"
										:get_options="getVariableOptions"
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
								<div v-else style="width: 100%; min-width: 150px">
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
import FieldPickerControl from "../../controls/FieldPickerControl.vue";
import AutocompleteControl from "../../controls/AutocompleteControl.vue";
import LinkControl from "../../controls/LinkControl.vue";
import ControlFactory from "../../controls/ControlFactory.vue";
import { useStore } from "../../stores";

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

const filters = ref([]);
const BASE_VALUE_TYPES = ["Value", "Number", "Boolean", "Variable", "Expression"];
const BUILDER_VALUE_TYPE = "Builder";
const VALUE_TYPE_LABELS = {
	Value: __("Literal"),
	Number: __("Number"),
	Boolean: __("Yes / No"),
	Variable: __("Variable"),
	Expression: __("Formula (Advanced)"),
	Builder: __("Date Formula Builder"),
};

const timespanOptions = [
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

const ALL_CONDITIONS = [
	["=", __("Equals")],
	["!=", __("Not Equals")],
	["like", __("Like")],
	["not like", __("Not Like")],
	["in", __("In")],
	["not in", __("Not In")],
	["is", __("Is")],
	[">", __("Greater Than")],
	["<", __("Less Than")],
	[">=", __("Greater Than Or Equal To")],
	["<=", __("Less Than Or Equal To")],
	["Between", __("Between")],
	["Timespan", __("Timespan")],
	["starts with", __("Starts With")],
	["ends with", __("Ends With")],
];

const operatorLabelMap = Object.fromEntries(ALL_CONDITIONS.map(([op, label]) => [op, label]));
const DATE_OPERATOR_LABELS = {
	"<": __("Before"),
	">": __("After"),
	"<=": __("On or Before"),
	">=": __("On or After"),
};

const INVALID_CONDITION_MAP = {
	Date: ["like", "not like", "starts with", "ends with"],
	Datetime: ["like", "not like", "in", "not in", "=", "!=", "starts with", "ends with"],
	Data: ["Between", "Timespan"],
	Time: ["Between", "Timespan", "starts with", "ends with"],
	Select: ["like", "not like", "Between", "Timespan", "starts with", "ends with"],
	Link: ["Between", "Timespan", ">", "<", ">=", "<=", "starts with", "ends with"],
	Currency: ["Between", "Timespan", "starts with", "ends with"],
	Color: ["Between", "Timespan", "starts with", "ends with"],
	Check: ALL_CONDITIONS.map((c) => c[0]).filter((c) => c !== "="),
	Code: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"HTML Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Markdown Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Password: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Rating: ["like", "not like", "Between", "in", "not in", "Timespan", "starts with", "ends with"],
	Float: ["like", "not like", "Between", "in", "not in", "Timespan", "starts with", "ends with"],
	Int: ["like", "not like", "Between", "in", "not in", "Timespan", "starts with", "ends with"],
};
const DATE_FIELDTYPES = new Set(["Date", "Datetime"]);
const BUILDER_SUPPORTED_FIELDTYPES = new Set(["Date", "Datetime"]);
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

// Initialize local state from modelValue
const syncFromProps = () => {
	if (!props.modelValue || !Array.isArray(props.modelValue)) {
		filters.value = [];
		return;
	}

	// Stability check: If our cleaned local state is already same as incoming prop,
	// do nothing. This preserves local empty rows being edited.
	const clean_local = filters.value
		.filter((f) => f.field || f.fieldname)
		.map((f) => ({
			doctype: f.doctype || props.doctype,
			field: f.field || f.fieldname,
			operator: f.operator || f.op || "=",
			value: f.value,
			value_type: f.value_type || "Value",
		}));

	// deep compare strings
	if (JSON.stringify(clean_local) === JSON.stringify(props.modelValue)) {
		return;
	}

	// Normalize if coming from frappe format [dt, field, op, val]
	filters.value = props.modelValue.map((f) => {
		let row = {};
		if (Array.isArray(f)) {
			row = {
				doctype: f[0],
				field: f[1],
				operator: f[2],
				value: f[3],
				value_type: guessValueType(f[3]),
				builder: null,
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
			const out = {
				doctype: n.doctype || props.doctype,
				field: n.field,
				operator: n.operator || "=",
				value: n.value,
				value_type: n.value_type || "Value",
			};
			if (n.value_type === BUILDER_VALUE_TYPE && n.builder) {
				out.builder = n.builder;
			}
			return out;
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

const getFieldsForDoctype = (dt) => {
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) {
		return [];
	}
	return fields.map((f) => {
		// Extract raw label from format "doc.fieldname (Real Label)"
		let realLabel = f.label;
		const match = f.label.match(/\((.*?)\)/);
		if (match && match[1]) {
			realLabel = match[1];
		}

		return {
			...f,
			label: `${realLabel} (${f.fieldname})`,
			value: f.value,
		};
	});
};

const getFieldDef = (fieldname, doctype) => {
	if (!fieldname) return null;
	const dt = doctype || props.doctype;

	// Standard field fallbacks
	if (["name"].includes(fieldname)) {
		return { fieldname, value: fieldname, fieldtype: "Data", label: "Name" };
	}
	if (["owner", "modified_by"].includes(fieldname)) {
		return {
			fieldname,
			value: fieldname,
			fieldtype: "Link",
			options: "User",
			label: fieldname === "owner" ? "Owner" : "Modified By",
		};
	}
	if (["creation", "modified"].includes(fieldname)) {
		return {
			fieldname,
			value: fieldname,
			fieldtype: "Datetime",
			label: fieldname === "creation" ? "Creation" : "Modified",
		};
	}
	if (fieldname === "docstatus") {
		return { fieldname, value: fieldname, fieldtype: "Int", label: "Docstatus" };
	}

	// Try Frappe's native meta cache first
	const raw_fieldname = fieldname.startsWith("doc.") ? fieldname.substring(4) : fieldname;
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
	if (!field) return ALL_CONDITIONS.map((c) => c[0]);
	const fieldtype = field.fieldtype || "Data";
	const invalid = INVALID_CONDITION_MAP[fieldtype] || [];
	return ALL_CONDITIONS.filter((c) => !invalid.includes(c[0])).map((c) => c[0]);
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

const getValueTypeLabel = (valueType) => VALUE_TYPE_LABELS[valueType] || __(valueType);

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
	const raw_fieldname =
		field?.fieldname ||
		(row.field?.startsWith("doc.") ? row.field.substring(4) : row.field) ||
		"value";
	schema.label = "";
	schema.read_only = props.readOnly;
	schema.fieldname = raw_fieldname; // Ensure valid fieldname for frappe controls (no doc. prefix)

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
			schema.get_data = async (txt) => {
				if (!field.options) return [];
				try {
					const rows = await frappe.db.get_link_options(field.options, txt || "");
					return (rows || []).map((row) => ({
						value: row.value || row,
						description: row.description || "",
					}));
				} catch (e) {
					return [];
				}
			};
		} else if (field && field.fieldtype === "Select") {
			schema.fieldtype = "MultiCheck";
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

const normalizeBuilderItem = (item, fallbackField = "") => ({
	kind: "date_formula",
	function_name: item?.function_name || "add_days_doc",
	base_field: item?.base_field || fallbackField || "posting_date",
	offset_days: toInt(item?.offset_days ?? 0, 0),
});

const getDefaultBuilderItem = (row) => {
	const dateField =
		getDateFieldOptions(row.doctype || props.doctype)[0]?.value || row.field || "posting_date";
	return normalizeBuilderItem({}, dateField);
};

const compileBuilderExpression = (builder) => {
	const item = normalizeBuilderItem(builder);
	const offset = toInt(item.offset_days, 0);
	if (item.function_name === "doc_field") {
		return `{doc.${item.base_field}}`;
	}
	if (item.function_name === "today") {
		return "{frappe.utils.nowdate()}";
	}
	if (item.function_name === "add_days_today") {
		return `{frappe.utils.add_days(frappe.utils.nowdate(), ${offset})}`;
	}
	return `{frappe.utils.add_days(doc.${item.base_field}, ${offset})}`;
};

const builderNeedsOffset = (builder) => {
	const fn = normalizeBuilderItem(builder).function_name;
	return fn === "add_days_doc" || fn === "add_days_today";
};

const builderNeedsBaseField = (builder) => {
	const fn = normalizeBuilderItem(builder).function_name;
	return fn === "add_days_doc" || fn === "doc_field";
};

const builderPreview = (builder) => {
	const item = normalizeBuilderItem(builder);
	if (item.function_name === "doc_field") {
		return __("Uses current document field: doc.{0}").replace("{0}", item.base_field);
	}
	if (item.function_name === "today") {
		return __("Uses current date");
	}
	if (item.function_name === "add_days_today") {
		return __("Uses today with offset {0} day(s)").replace("{0}", item.offset_days);
	}
	return __("Uses doc.{0} with offset {1} day(s)")
		.replace("{0}", item.base_field)
		.replace("{1}", item.offset_days);
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
	const normalized = normalizeBuilderState({ ...row });
	if (idx === null || idx === undefined) {
		return Array.isArray(normalized.builder) ? normalized.builder[0] : normalized.builder;
	}
	return Array.isArray(normalized.builder) ? normalized.builder[idx] : normalized.builder;
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

	// FlexiRule: Wrap Link fields in [DocType, Value] tuple for equality operators
	if (
		["=", "!="].includes(merged.operator) &&
		field?.fieldtype === "Link" &&
		merged.value_type === "Value"
	) {
		const val = data.value !== undefined ? data.value : merged.value;
		if (val && !Array.isArray(val)) {
			merged.value = [field.options, val];
		}
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
		if (!row.value || !row.value.startsWith("{")) {
			row.value = `{${row.value || ""}}`;
		}
	} else if (row.value && row.value.startsWith("{")) {
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

onMounted(syncFromProps);
</script>

<style scoped>
.filter-group-wrapper {
	width: 100%;
}

.filter-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.filter-row {
	display: flex;
	flex-direction: column;
	background: #f8f9fa;
	border: 1px solid #e9ecef;
	border-radius: 4px;
	padding: 6px;
}

.filter-row-main {
	display: grid;
	grid-template-columns: 1.5fr 0.8fr 1fr 2fr auto;
	gap: 8px;
	align-items: center;
}

/* Specific columns */
.doctype-col {
	grid-column: span 1;
}
.field-col {
	min-width: 120px;
}
.operator-col {
	min-width: 80px;
}
.value-col {
	min-width: 220px;
}
.type-col {
	min-width: 140px;
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
}

:deep(.border-warning .form-control) {
	border-color: var(--orange-500, #ff9800) !important;
	background-color: #fff8f1 !important;
}

.value-input-group {
	display: flex;
	width: 100%;
}

.expression-wrapper {
	display: flex;
	align-items: center;
	background: #fff8e1;
	border: 1px solid #ffe082;
	border-radius: 4px;
	padding: 0 4px;
	width: 100%;
}

.expr-bracket {
	color: #ffa000;
	font-weight: bold;
	padding: 0 4px;
}

.type-select {
	font-size: 10px;
	height: 24px;
	padding: 2px 4px;
	background: #f1f3f5;
}

.dual-value-wrapper {
	display: flex;
	align-items: center;
	gap: 6px;
	width: 100%;
}

.value-input-item {
	flex: 1;
	min-width: 0;
}

.builder-wrapper {
	width: 100%;
}

.builder-card {
	display: flex;
	flex-direction: column;
	gap: 6px;
	border: 1px solid #e5e7eb;
	border-radius: 6px;
	padding: 6px;
	background: #f8fafc;
}

.builder-offset-row {
	display: grid;
	grid-template-columns: 1fr 110px;
	gap: 8px;
	align-items: center;
}

.builder-preview {
	font-size: 11px;
	line-height: 1.3;
	background: #ffffff;
	border: 1px dashed #d1d5db;
	border-radius: 4px;
	padding: 4px 6px;
}

.between-sep {
	font-size: 11px;
	color: #6c757d;
	font-weight: 500;
}

.expression-wrapper.variable-mode {
	background: #f3f0ff;
	border-color: #d1c4e9;
}

.expression-wrapper.variable-mode .expr-bracket {
	color: #673ab7;
}

.border-dashed {
	border: 1px dashed #dee2e6;
}

:deep(.field-picker-control) {
	margin-bottom: 0 !important;
}

:deep(.control.frappe-control) {
	margin-bottom: 0 !important;
}

.filter-row-main :deep(.form-control) {
	height: 28px;
	padding: 2px 8px;
	font-size: 12px;
}
</style>
