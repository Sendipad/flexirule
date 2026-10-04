<template>
	<div class="query-filter-node">
		<!-- Nested Group Node -->
		<div v-if="node.conditions" class="nested-group-card">
			<div class="group-header">
				<div class="logic-toggle small">
					<button
						type="button"
						class="logic-btn"
						:class="{ active: node.op === 'and' }"
						@click="
							node.op = 'and';
							emitUpdate();
						"
						:disabled="readOnly"
					>
						{{ __("AND") }}
					</button>
					<button
						type="button"
						class="logic-btn"
						:class="{ active: node.op === 'or' }"
						@click="
							node.op = 'or';
							emitUpdate();
						"
						:disabled="readOnly"
					>
						{{ __("OR") }}
					</button>
				</div>

				<div class="group-actions" v-if="!readOnly">
					<button
						class="btn btn-xs btn-outline-secondary"
						@click="addCondition(node)"
						:title="__('Add Condition')"
					>
						<i class="fa fa-plus mr-1"></i> {{ __("Condition") }}
					</button>
					<button
						class="btn btn-xs btn-outline-secondary ml-1"
						@click="addGroup(node)"
						:title="__('Add Group')"
					>
						<i class="fa fa-folder-open-o mr-1"></i> {{ __("Group") }}
					</button>
					<button
						class="btn btn-xs btn-link text-danger ml-2"
						@click="removeSelf"
						:title="__('Remove Group')"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
			</div>

			<div class="group-body">
				<div v-if="!node.conditions.length" class="empty-group-text">
					{{ __("Empty group. Click 'Condition' or 'Group' to add rules.") }}
				</div>
				<div
					v-for="(child, cIdx) in node.conditions"
					:key="child.id || cIdx"
					class="child-node-wrapper"
				>
					<QueryFilterNode
						:node="child"
						:index="cIdx"
						:parentGroup="node"
						:doctype="doctype"
						:readOnly="readOnly"
						:allowAnyDoctype="allowAnyDoctype"
						:showValidation="showValidation"
						:effectiveVariableOptions="effectiveVariableOptions"
						@update="emitUpdate"
					/>
				</div>
			</div>
		</div>

		<!-- Condition Row Node -->
		<div v-else class="filter-row">
			<div class="filter-row-main">
				<!-- Doctype Picker (if allowAnyDoctype) -->
				<div v-if="allowAnyDoctype" class="filter-col doctype-col">
					<ComboBoxControl
						:df="{ label: '', fieldtype: 'Link', options: 'DocType' }"
						:modelValue="node.doctype || doctype"
						:doctype="'DocType'"
						:hideLabel="true"
						:read_only="readOnly"
						@update:modelValue="
							(val) => {
								node.doctype = val;
								emitUpdate();
							}
						"
					/>
				</div>

				<!-- Field Picker -->
				<div class="filter-col field-col">
					<NavigableFieldBrowser
						v-if="node.doctype || doctype"
						:df="{ label: '', fieldtype: 'FieldPicker', reqd: 1 }"
						:doctype="node.doctype || doctype"
						:modelValue="node.field"
						:readOnly="readOnly"
						:showValidation="showValidation"
						:hideLabel="true"
						@update:modelValue="(val) => onFieldChange(val)"
					/>
				</div>

				<!-- Operator -->
				<div class="filter-col operator-col">
					<select
						class="form-control input-xs"
						:value="node.operator"
						:disabled="readOnly"
						@change="(e) => onOperatorChange(e.target.value)"
					>
						<option
							v-for="op in getOperatorsForField(
								getFieldDef(node.field, node.doctype)
							)"
							:key="op"
							:value="op"
						>
							{{ getOperatorLabel(op, node) }}
						</option>
					</select>
				</div>

				<!-- Value / Expression -->
				<div class="filter-col value-col">
					<div class="value-input-group">
						<template v-if="node.operator === 'Between'">
							<div class="dual-value-wrapper">
								<div class="value-input-item">
									<FlexValueControl
										:modelValue="
											Array.isArray(node.value)
												? node.value[0]
												: { mode: 'static', value: '' }
										"
										:context="{
											df: { ...getControlFactorySchema(node), reqd: 1 },
											operator: node.operator,
											referenceDoctype: node.doctype || doctype,
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
										:modelValue="
											Array.isArray(node.value)
												? node.value[1]
												: { mode: 'static', value: '' }
										"
										:context="{
											df: { ...getControlFactorySchema(node), reqd: 1 },
											operator: node.operator,
											referenceDoctype: node.doctype || doctype,
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
									v-model="node.value"
									:context="{
										df: { ...getControlFactorySchema(node), reqd: 1 },
										operator: node.operator,
										referenceDoctype: node.doctype || doctype,
									}"
									:engine="store"
									:doc="store?.rule_doc"
									:variableOptions="effectiveVariableOptions"
									:disabled="readOnly"
									:readOnly="readOnly"
									:showValidation="showValidation"
									@update:modelValue="emitUpdate"
								/>
							</div>
						</template>
					</div>
				</div>

				<!-- Delete -->
				<div v-if="!readOnly" class="filter-col action-col">
					<button class="btn btn-xs btn-link text-danger" @click="removeSelf">
						<i class="fa fa-trash"></i>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import NavigableFieldBrowser from "../../controls/NavigableFieldBrowser.vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import { useStore } from "../../stores";

const props = defineProps({
	node: { type: Object, required: true },
	index: { type: Number, required: true },
	parentGroup: { type: Object, required: true },
	doctype: { type: String, required: true },
	readOnly: { type: Boolean, default: false },
	allowAnyDoctype: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
	effectiveVariableOptions: { type: Array, default: () => [] },
});

const emit = defineEmits(["update"]);
const store = useStore();

function emitUpdate() {
	emit("update");
}

function uuid() {
	return "f_" + Math.random().toString(36).substr(2, 9);
}

function addCondition(targetGroup) {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		doctype: props.doctype,
		field: "name",
		operator: "=",
		value: { mode: "static", value: "" },
	});
	emitUpdate();
}

function addGroup(targetGroup) {
	if (!targetGroup.conditions) targetGroup.conditions = [];
	targetGroup.conditions.push({
		id: uuid(),
		op: "and",
		conditions: [],
	});
	emitUpdate();
}

function removeSelf() {
	if (props.parentGroup && Array.isArray(props.parentGroup.conditions)) {
		props.parentGroup.conditions.splice(props.index, 1);
		emitUpdate();
	}
}

function onFieldChange(val) {
	props.node.field = val;
	const fieldDef = getFieldDef(val, props.node.doctype || props.doctype);
	const allowedOps = getOperatorsForField(fieldDef);
	if (!allowedOps.includes(props.node.operator)) {
		props.node.operator = allowedOps[0] || "=";
	}
	emitUpdate();
}

function onOperatorChange(op) {
	const prevOp = props.node.operator;
	props.node.operator = op;
	if (op === "Between" && !Array.isArray(props.node.value)) {
		props.node.value = [
			{ mode: "static", value: "" },
			{ mode: "static", value: "" },
		];
	} else if (prevOp === "Between" && Array.isArray(props.node.value)) {
		props.node.value = props.node.value[0] || { mode: "static", value: "" };
	}
	emitUpdate();
}

function updateBetweenValue(idx, val) {
	if (!Array.isArray(props.node.value)) {
		props.node.value = [
			{ mode: "static", value: "" },
			{ mode: "static", value: "" },
		];
	}
	props.node.value[idx] = val;
	emitUpdate();
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

const EXTRA_FILTER_OPERATORS_BY_FIELDTYPE = {
	Data: ["starts with", "ends with"],
	Text: ["starts with", "ends with"],
	"Small Text": ["starts with", "ends with"],
	"Long Text": ["starts with", "ends with"],
	"Text Editor": ["starts with", "ends with"],
};

const isCheckField = (field) => field?.original_type === "Check" || field?.fieldtype === "Check";

function getFieldDef(fieldname, dtName) {
	if (!fieldname) return null;
	const dt = dtName || props.doctype;
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

	if (isDotted && dt && window.frappe && frappe.meta) {
		const [parentFieldname, childFieldname] = fieldname.split(".", 2);
		const parentDf = frappe.meta.get_docfield(dt, parentFieldname);
		if (parentDf && parentDf.options) {
			const childDf = frappe.meta.get_docfield(parentDf.options, childFieldname);
			if (childDf) {
				return {
					...childDf,
					value: fieldname,
					fieldname,
					parentfield: parentFieldname,
					parenttype: dt,
					parent: parentDf.options,
				};
			}
		}
	}

	if (dt && window.frappe && frappe.meta && frappe.meta.has_field(dt, fieldname)) {
		const df = frappe.meta.get_docfield(dt, fieldname);
		if (df) {
			return { ...df, value: fieldname };
		}
	}

	const storeFields = store.get_fields_for_doctype(dt);
	const match = (storeFields || []).find(
		(f) => f.value === fieldname || f.fieldname === fieldname
	);
	if (match) return match;

	return { fieldname, value: fieldname, fieldtype: "Data", label: fieldname };
}

function getOperatorsForField(field) {
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

	if (
		field.fieldtype === "Link" &&
		window.frappe &&
		frappe.boot?.nested_set_doctypes?.includes(field.options)
	) {
		for (const op of NESTED_SET_OPERATORS) {
			if (!allowed.includes(op)) allowed.push(op);
		}
	}

	if (isCheckField(field)) return allowed.filter((op) => op === "=" || op === "!=");
	return allowed.length ? allowed : ["="];
}

function getOperatorLabel(op, node) {
	const map = {
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
	return map[op] || op;
}

function getControlFactorySchema(node) {
	const field = getFieldDef(node.field, node.doctype || props.doctype);
	let schema = field ? frappe.utils.deep_clone(field) : { fieldtype: "Data", fieldname: "value" };
	const rawField =
		typeof node.field === "string" && node.field.startsWith("doc.")
			? node.field.substring(4)
			: node.field;
	schema.label = "";
	schema.read_only = props.readOnly;
	schema.fieldname = rawField;

	if (window.frappe && frappe.ui && frappe.ui.filter_utils) {
		frappe.ui.filter_utils.set_fieldtype(schema, null, node.operator);
		if (
			node.operator === "Between" &&
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

	const opLower = (node.operator || "").toLowerCase();
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
	} else if (["=", "!="].includes(node.operator) && field?.fieldtype === "Link") {
		schema.fieldtype = "Link";
		schema.options = field.options;
	} else if (node.operator === "Between") {
		schema.placeholder = __("Value1, Value2");
	}

	return schema;
}
</script>

<style scoped>
.query-filter-node {
	width: 100%;
}

.nested-group-card {
	background-color: var(--fxr-surface-soft, #f8fafc);
	border: 1px solid var(--fxr-border-subtle, #e2e8f0);
	border-radius: var(--fxr-radius-md, 6px);
	padding: 8px 12px;
	margin: 4px 0;
}

.group-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 8px;
}

.logic-toggle.small {
	display: flex;
	background: var(--fxr-surface-2, #e2e8f0);
	padding: 2px;
	border-radius: 4px;
}

.logic-btn {
	border: none;
	background: transparent;
	padding: 2px 10px;
	border-radius: 3px;
	font-size: 10px;
	font-weight: 800;
	color: var(--fxr-text-soft, #64748b);
	cursor: pointer;
}

.logic-btn.active {
	background-color: var(--fxr-accent, #2563eb);
	color: #ffffff;
}

.group-body {
	padding-left: 12px;
	border-left: 2px solid var(--fxr-accent-border, #cbd5e1);
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.empty-group-text {
	font-size: 11px;
	color: var(--fxr-text-muted, #94a3b8);
	font-style: italic;
	padding: 4px 0;
}

.filter-row {
	display: flex;
	flex-direction: column;
	background-color: var(--fxr-bg-input, #ffffff);
	border: 1px solid var(--fxr-border-subtle, #e2e8f0);
	border-radius: var(--fxr-radius-sm, 4px);
	padding: 4px 8px;
	margin-bottom: 2px;
}

.filter-row-main {
	display: flex;
	gap: 8px;
	align-items: center;
	width: 100%;
}

.doctype-col {
	flex: 0 0 130px;
}

.field-col {
	flex: 1;
	min-width: 150px;
}

.operator-col {
	flex: 0 0 110px;
}

.value-col {
	flex: 1.2;
	min-width: 160px;
}

.action-col {
	flex: 0 0 28px;
	display: flex;
	justify-content: center;
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

.between-sep {
	font-size: 11px;
	color: var(--fxr-text-muted);
	font-weight: 600;
	text-transform: uppercase;
}
</style>
