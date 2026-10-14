<template>
	<div class="output-fields-editor">
		<GenericGrid
			ref="outputGridRef"
			class="output-fields-list"
			:gridLabel="__('Output fields')"
			:rows="rows"
			rowKey="id"
			:rowInvalid="isRowInvalid"
			:searchableFields="searchableFields"
			:actionOptions="gridActions"
			defaultPrimaryAction="add-field"
			:preferenceKey="'flexirule:fetch-records-output-primary:' + doctype + ':' + shape"
			:cloneRow="cloneGridRow"
			:readOnly="readOnly"
			:compact="true"
			:pagination="true"
			:pageSize="10"
			:pageSizeOptions="[5, 10, 20, 50]"
			@row-action="handleGridRowAction"
			@primary-action="handleGridPrimaryAction"
			@grid-action="handleGridSecondaryAction"
			@bulk-delete="handleBulkDelete"
			@update:rows="handlePastedRows"
		>
			<template #empty>{{ __("No output fields yet. Add a field or child selection to get started.") }}</template>
			<template #row-summary="{ row }">
				<div class="output-field-row-copy">
					<strong :title="rowTitle(row)">{{ rowTitle(row) }}</strong>
					<p :title="rowDescription(row)">{{ rowDescription(row) }}</p>
				</div>
			</template>
			<template #row="{ row }">
				<div v-if="row.isEditing" class="output-field-edit">
					<div v-if="row.kind === 'field'" class="output-field-controls">
						<OutputFieldPicker
							:doctype="doctype"
							:modelValue="row.field"
							:readOnly="readOnly"
							:label="__('Field')"
							@update:modelValue="updateRowValue(row, 'field', $event)"
						/>
						<input
							class="form-control output-field-alias"
							:value="row.alias"
							:disabled="readOnly"
							:placeholder="__('Output alias (optional)')"
							:aria-label="__('Output alias (optional)')"
							@input="updateRowValue(row, 'alias', $event.target.value)"
						/>
					</div>

					<div
						v-else-if="row.kind === 'function'"
						class="output-field-controls output-function-controls"
					>
						<SelectControl
							class="output-function-select"
							:df="{
								fieldtype: 'Select',
								label: '',
								options: aggregateFunctions,
								reqd: 1,
							}"
							:modelValue="row.functionName"
							:read_only="readOnly"
							:hideLabel="true"
							:aria-label="__('Aggregate function')"
							@update:modelValue="
								(value) => updateRowValue(row, 'functionName', value)
							"
						/>
						<OutputFieldPicker
							:doctype="doctype"
							:modelValue="row.field"
							:readOnly="readOnly"
							:rootOnly="true"
							:label="__('Source field')"
							@update:modelValue="updateRowValue(row, 'field', $event)"
						/>
						<input
							class="form-control output-field-alias"
							:value="row.alias"
							:disabled="readOnly"
							:placeholder="__('Required output alias')"
							:aria-label="__('Required output alias')"
							@input="updateRowValue(row, 'alias', $event.target.value)"
						/>
					</div>

					<div v-else-if="row.kind === 'literal'" class="output-literal-controls">
						<div class="output-field-controls">
							<div class="output-field-control">
								<label class="output-field-label">{{
									__("Output field name")
								}}</label>
								<input
									class="form-control"
									:value="row.fieldname"
									:disabled="readOnly"
									:placeholder="__('document_type')"
									@input="updateRowValue(row, 'fieldname', $event.target.value)"
								/>
							</div>
							<div class="output-field-control">
								<label class="output-field-label">{{ __("Label") }}</label>
								<input
									class="form-control"
									:value="row.label"
									:disabled="readOnly"
									:placeholder="__('Document Type')"
									@input="updateRowValue(row, 'label', $event.target.value)"
								/>
							</div>
							<div class="output-field-control">
								<label class="output-field-label">{{ __("Value type") }}</label>
								<select
									class="form-control"
									:value="row.fieldtype || 'Data'"
									:disabled="readOnly"
									@change="updateRowValue(row, 'fieldtype', $event.target.value)"
								>
									<option
										v-for="type in literalFieldTypes"
										:key="type.value"
										:value="type.value"
									>
										{{ type.label }}
									</option>
								</select>
							</div>
						</div>
						<div
							v-if="['Link', 'Select'].includes(row.fieldtype)"
							class="output-field-control"
						>
							<label class="output-field-label">{{ __("Options") }}</label>
							<input
								class="form-control"
								:value="row.options || ''"
								:disabled="readOnly"
								:placeholder="
									row.fieldtype === 'Link'
										? __('Customer')
										: __('Option A / Option B')
								"
								@input="updateRowValue(row, 'options', $event.target.value)"
							/>
						</div>
						<div class="output-field-control">
							<label class="output-field-label">{{ __("Value") }}</label>
							<FlexValueControl
								:modelValue="row.value_spec"
								:variableOptions="variableOptions"
								:readOnly="readOnly"
								:showValidation="showValidation"
								:context="{
									df: {
										fieldname: row.fieldname || 'literal_value',
										label: row.label || __('Literal value'),
										fieldtype: row.fieldtype || 'Data',
										reqd: 0,
										options: row.options,
									},
								}"
								@update:modelValue="updateRowValue(row, 'value_spec', $event)"
							/>
						</div>
					</div>

					<div v-else-if="row.kind === 'child'" class="output-child-controls">
						<div class="output-child-table">
							<label class="output-field-label">{{ __("Child table") }}</label>
							<SelectControl
								class="output-child-select"
								:df="{ fieldtype: 'Select', label: '', options: childTableOptions }"
								:modelValue="row.tableField"
								:read_only="readOnly"
								:hideLabel="true"
								@update:modelValue="(value) => changeChildTable(row, value)"
							/>
						</div>
						<div class="output-child-fields">
							<label class="output-field-label">{{ __("Child fields") }}</label>
							<MultiSelectList
								:df="{
									label: '',
									fieldname: 'child_fields',
									placeholder: __('Select child fields...'),
								}"
								:options="row.childFieldOptions || []"
								:modelValue="row.fields || []"
								:read_only="readOnly || !row.tableField"
								:hideLabel="true"
								@update:modelValue="updateRowValue(row, 'fields', $event)"
							/>
						</div>
					</div>

					<div v-else class="output-field-controls">
						<textarea
							class="form-control output-field-raw"
							:value="row.expression"
							:disabled="readOnly"
							:placeholder="
								__('Advanced native field expression or JSON field descriptor')
							"
							:aria-label="
								__('Advanced native field expression or JSON field descriptor')
							"
							rows="2"
							@input="updateRaw(row, $event.target.value)"
						></textarea>
					</div>
				</div>
			</template>

		</GenericGrid>

		<p v-if="requiresGroupBy" class="output-fields-warning">
			<i class="fa fa-info-circle mr-1"></i>
			{{
				__(
					"When aggregates and regular fields are combined, set Group By in Result limit and grouping. Otherwise, use aggregate-only output fields."
				)
			}}
		</p>

		<p v-if="shape === 'embedded_children'" class="output-fields-hint">
			{{
				__(
					"Child selections return nested arrays for each parent record. Use dotted paths only when you want flat joined rows."
				)
			}}
		</p>
		<p class="output-fields-hint">
			{{
				__(
					"Functions use Frappe-style field syntax. Aggregate functions currently support fields on the selected DocType, not linked or child-table paths."
				)
			}}
		</p>

		<div v-if="showValidation && validationErrors.length" class="output-fields-errors">
			<div v-for="error in validationErrors" :key="error">
				<i class="fa fa-exclamation-circle mr-1"></i>{{ error }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import MultiSelectList from "../../../../controls/MultiSelectList.vue";
import FlexValueControl from "../../../../controls/FlexValueControl.vue";
import SelectControl from "../../../../controls/SelectControl.vue";
import GenericGrid from "../../../../controls/GenericGrid.vue";
import { useMetaStore } from "../../../../stores/useMetaStore";
import {
	AGGREGATE_FUNCTIONS,
	humanizeAlias,
	parseOutputFields,
	serializeOutputFields,
	validateOutputFields,
} from "./output_fields_model.js";
import { resolveFieldInfo } from "./output_field_info.mjs";
import OutputFieldPicker from "./OutputFieldPicker.vue";

const props = defineProps({
	modelValue: { type: [Array, String], default: () => [] },
	doctype: { type: String, required: true },
	shape: { type: String, required: true },
	groupBy: { type: String, default: "" },
	variableOptions: { type: Array, default: null },
	readOnly: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);
const metaStore = useMetaStore();
const outputGridRef = ref(null);
const rows = ref(
	parseOutputFields(props.modelValue).map((row) => ({
		...row,
		isEditing: false,
		childFieldOptions: [],
	}))
);
const validationErrors = ref([]);
const searchableFields = [
	"kind",
	"field",
	"alias",
	"functionName",
	"fieldname",
	"label",
	"tableField",
	"expression",
];
const gridActions = computed(() => {
	const actions = [
		{ id: "add-field", label: __("Add field"), icon: "fa fa-plus", shortcut: "Alt+Shift+F" },
		{ id: "add-function", label: __("Add function"), icon: "fa fa-calculator", shortcut: "Alt+Shift+G" },
		{ id: "add-literal", label: __("Add literal value"), icon: "fa fa-tag", shortcut: "Alt+Shift+L" },
	];
	if (props.shape === "embedded_children") {
		actions.push({
			id: "add-child",
			label: __("Add child selection"),
			icon: "fa fa-sitemap",
			shortcut: "Alt+Shift+C",
		});
	}
	return actions;
});
const requiresGroupBy = computed(
	() =>
		rows.value.some((row) => row.kind === "function") &&
		rows.value.some((row) => ["field", "raw"].includes(row.kind)) &&
		!String(props.groupBy || "").trim()
);
const aggregateFunctions = AGGREGATE_FUNCTIONS.map((value) => ({
	value,
	label: value.toUpperCase(),
}));
const literalFieldTypes = [
	{ value: "Data", label: __("Text (Data)") },
	{ value: "Int", label: __("Integer (Int)") },
	{ value: "Float", label: __("Number (Float)") },
	{ value: "Currency", label: __("Currency") },
	{ value: "Check", label: __("Checkbox (Check)") },
	{ value: "Date", label: __("Date") },
	{ value: "Datetime", label: __("Datetime") },
	{ value: "Time", label: __("Time") },
	{ value: "Link", label: __("Link") },
	{ value: "Select", label: __("Select") },
];

const parentFields = computed(() => metaStore.doc_meta?.[props.doctype] || []);
const childTableOptions = computed(() =>
	parentFields.value
		.filter(
			(field) => ["Table", "Table MultiSelect"].includes(field.fieldtype) && field.options
		)
		.map((field) => ({
			value: field.fieldname,
			label:
				(field.original_label || field.label || field.fieldname) +
				" (" +
				field.fieldname +
				")",
			doctype: field.options,
		}))
);

function fieldInfo(fieldname) {
	return resolveFieldInfo(metaStore.doc_meta, props.doctype, fieldname);
}
function revealRow(index) {
	if (!Number.isInteger(index)) return;
	nextTick(() => outputGridRef.value?.goToIndex(index));
}

function newId() {
	return "output-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
}

function rowTitle(row) {
	if (row.kind === "field") return row.alias || row.field || __("Output field");
	if (row.kind === "function") {
		const fn = (row.functionName || "count").toUpperCase();
		return row.alias
			? humanizeAlias(row.alias) + " (" + fn + ")"
			: fn + "(" + (fieldInfo(row.field).label || row.field || "?") + ")";
	}
	if (row.kind === "child") {
		return fieldInfo(row.tableField).label || __("Embedded child selection");
	}
	if (row.kind === "literal") {
		return row.label || humanizeAlias(row.fieldname) || __("Literal value");
	}
	return row.expression || __("Advanced field expression");
}

function rowDescription(row) {
	if (row.kind === "field") {
		const source = row.field
			? (row.field.includes(".") ? __("Related field") : __("Parent field")) +
			  " · " +
			  row.field
			: __("Choose a field");
		return row.alias ? source + " · " + __("Output alias") + ": " + row.alias : source;
	}
	if (row.kind === "function") {
		const expression =
			(row.functionName || "count").toUpperCase() + "(" + (row.field || "?") + ")";
		return (
			__("Function") +
			" · " +
			expression +
			(row.alias ? " · " + __("Output alias") + ": " + row.alias : "")
		);
	}
	if (row.kind === "child") {
		const fields = Array.isArray(row.fields) ? row.fields.join(", ") : "";
		return fields ? __("Child fields") + " · " + fields : __("Select child fields");
	}
	if (row.kind === "literal") {
		const mode = row.value_spec?.mode || "static";
		return __("Literal column") + " · " + (row.fieldname || "—") + " · " + __(mode);
	}
	return __("Advanced native field expression");
}

function emitRows() {
	validationErrors.value = [];
	emit("update:modelValue", serializeOutputFields(rows.value));
}

function updateRowValue(row, key, value) {
	if (props.readOnly) return;
	row[key] = value;
	emitRows();
}

function updateRaw(row, value) {
	if (props.readOnly) return;
	row.expression = value;
	row.dirty = true;
	emitRows();
}

function addField(afterIndex = null) {
	if (props.readOnly) return;
	insertNewRow(
		{
			id: newId(),
			kind: "field",
			field: "",
			alias: "",
			fields: [],
			isEditing: true,
			childFieldOptions: [],
		},
		afterIndex
	);
}

function addFunction(afterIndex = null) {
	if (props.readOnly) return;
	insertNewRow(
		{
			id: newId(),
			kind: "function",
			functionName: "count",
			field: "",
			alias: "",
			fields: [],
			isEditing: true,
			childFieldOptions: [],
		},
		afterIndex
	);
}

function addChild(afterIndex = null) {
	if (props.readOnly) return;
	insertNewRow(
		{
			id: newId(),
			kind: "child",
			tableField: "",
			fields: [],
			isEditing: true,
			childFieldOptions: [],
		},
		afterIndex
	);
}

function insertNewRow(row, afterIndex = null) {
	const insertIndex =
		Number.isInteger(afterIndex) && afterIndex >= 0
			? Math.min(afterIndex + 1, rows.value.length)
			: rows.value.length;
	rows.value.splice(insertIndex, 0, row);
	emitRows();
	revealRow(insertIndex);
}

function addLiteral(afterIndex = null) {
	if (props.readOnly) return;
	const usedNames = new Set(
		rows.value
			.map((row) =>
				row.kind === "literal"
					? row.fieldname
					: row.alias || (row.kind === "field" ? row.field : "")
			)
			.filter(Boolean)
	);
	let fieldname = "literal_value";
	let suffix = 2;
	while (usedNames.has(fieldname)) fieldname = "literal_value_" + suffix++;
	insertNewRow(
		{
			id: newId(),
			kind: "literal",
			fieldname,
			label: humanizeAlias(fieldname),
			fieldtype: "Data",
			reqd: 0,
			value_spec: { mode: "static", value: "" },
			isEditing: true,
			childFieldOptions: [],
		},
		afterIndex
	);
}

function cloneGridRow(row) {
	const allowedKinds = new Set(["field", "function", "child", "literal", "raw"]);
	if (!row || typeof row !== "object" || !allowedKinds.has(row.kind)) return null;
	const copy = JSON.parse(JSON.stringify(row));
	copy.id = newId();
	copy.isEditing = false;
	copy.childFieldOptions = [];
	return copy;
}

function handlePastedRows(nextRows) {
	if (props.readOnly || !Array.isArray(nextRows)) return;
	rows.value = nextRows.map((row) => ({
		...row,
		isEditing: Boolean(row.isEditing),
		childFieldOptions: Array.isArray(row.childFieldOptions) ? row.childFieldOptions : [],
	}));
	emitRows();
	refreshMetadata();
}

function handleGridPrimaryAction({ action = "add-field", afterIndex = null } = {}) {
	handleGridAction(action, afterIndex);
}

function handleGridSecondaryAction({ action } = {}) {
	handleGridAction(action);
}

function handleGridAction(action, afterIndex = null) {
	if (props.readOnly) return;
	switch (action) {
		case "add-function":
			addFunction(afterIndex);
			break;
		case "add-literal":
			addLiteral(afterIndex);
			break;
		case "add-child":
			if (props.shape === "embedded_children") addChild(afterIndex);
			break;
		case "add-field":
		default:
			addField(afterIndex);
			break;
	}
}

function handleBulkDelete(selectedRows = []) {
	if (props.readOnly || !Array.isArray(selectedRows) || !selectedRows.length) return;
	const selectedIds = new Set(selectedRows.map((row) => row?.id).filter(Boolean));
	rows.value = rows.value.filter((row) => !selectedIds.has(row.id));
	emitRows();
	refreshMetadata();
}

function handleGridRowAction({ action, row, index }) {
	if (props.readOnly) return;
	switch (action) {
		case "add-after":
			addField(index);
			break;
		case "edit":
			row.isEditing = true;
			break;
		case "view":
			row.isEditing = false;
			break;
		case "move-up":
			moveRow(index, -1);
			revealRow(index - 1);
			break;
		case "move-down":
			moveRow(index, 1);
			revealRow(index + 1);
			break;
		case "remove":
			removeRow(index);
			break;
	}
}

function isRowInvalid(row, index) {
	const prefix = "Output field " + (index + 1) + ":";
	if (validationErrors.value.some((error) => error.startsWith(prefix))) return true;
	if (row?.kind !== "child") return false;
	if (
		row.tableField &&
		!childTableOptions.value.some((option) => option.value === row.tableField)
	) {
		return true;
	}
	return (
		Array.isArray(row.fields) &&
		row.fields.some(
			(field) => !row.childFieldOptions.some((option) => option.value === field)
		)
	);
}

function removeRow(index) {
	if (props.readOnly) return;
	rows.value.splice(index, 1);
	emitRows();
}

function moveRow(index, direction) {
	if (props.readOnly) return;
	const nextIndex = index + direction;
	if (nextIndex < 0 || nextIndex >= rows.value.length) return;
	const [row] = rows.value.splice(index, 1);
	rows.value.splice(nextIndex, 0, row);
	emitRows();
}

async function loadChildFieldOptions(row, filterExisting = false) {
	const option = childTableOptions.value.find((item) => item.value === row.tableField);
	if (!option) {
		row.childFieldOptions = [];
		return;
	}
	try {
		await metaStore.fetch_metadata(option.doctype);
		const fields = metaStore.doc_meta[option.doctype] || [];
		row.childFieldOptions = fields
			.filter((field) => field.fieldname && !field.hidden)
			.map((field) => ({
				value: field.fieldname,
				label:
					(field.original_label || field.label || field.fieldname) +
					" (" +
					field.fieldname +
					")",
			}));
		if (filterExisting) {
			const allowed = new Set(row.childFieldOptions.map((field) => field.value));
			row.fields = (row.fields || []).filter((field) => allowed.has(field));
		}
	} catch (error) {
		console.warn("OutputFieldsEditor: failed to load child DocType fields", error);
		row.childFieldOptions = [];
	}
}

async function refreshMetadata() {
	if (!props.doctype) return;
	try {
		await metaStore.fetch_metadata(props.doctype);
		for (const row of rows.value) {
			if (row.kind === "child") await loadChildFieldOptions(row);
		}
	} catch (error) {
		console.warn("OutputFieldsEditor: failed to load DocType fields", error);
	}
}

async function changeChildTable(row, tableField) {
	if (props.readOnly) return;
	row.tableField = tableField;
	row.fields = [];
	await loadChildFieldOptions(row);
	emitRows();
}

async function validate() {
	const errors = validateOutputFields(rows.value, props.shape, props.groupBy);
	for (const row of rows.value) {
		if (row.kind !== "child" || !row.tableField) continue;
		if (!childTableOptions.value.some((option) => option.value === row.tableField)) {
			errors.push("Child selection references a field that is not a child table.");
			continue;
		}
		if (
			row.fields.some(
				(field) => !row.childFieldOptions.some((option) => option.value === field)
			)
		) {
			errors.push(
				"Child selection contains a field that is not available in the selected child DocType."
			);
		}
	}
	validationErrors.value = errors;
	return { valid: errors.length === 0, errors };
}

watch(
	() => props.modelValue,
	(value) => {
		if (JSON.stringify(serializeOutputFields(rows.value)) === JSON.stringify(value)) return;
		rows.value = parseOutputFields(value).map((row) => ({
			...row,
			isEditing: false,
			childFieldOptions: [],
		}));
		refreshMetadata();
	},
	{ deep: true }
);
watch(() => props.doctype, refreshMetadata);
onMounted(refreshMetadata);
defineExpose({ validate });
</script>

<style scoped>
.output-fields-editor {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2, var(--spacing-xs));
	color: var(--fxr-text);
}

.output-fields-list {
	min-width: 0;
	container-type: inline-size;
	container-name: output-fields-grid;
}

.output-fields-list :deep(.fxr-generic-grid-row) {
	align-items: start;
}

.output-fields-list :deep(.fxr-generic-grid-row-summary) {
	align-self: center;
}

.output-fields-list :deep(.fxr-generic-grid-row.is-editing) {
	border-color: var(--fxr-border-focus);
	background: var(--fxr-surface-soft, #f9fafb);
}

.output-field-row-copy {
	display: flex;
	flex-direction: column;
	justify-content: center;
	min-width: 0;
	flex: 1;
	user-select: text;
}

.output-field-row-copy strong {
	display: block;
	overflow: hidden;
	color: var(--fxr-text);
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-medium);
	text-overflow: ellipsis;
	white-space: nowrap;
}

.output-field-row-copy p {
	margin: 1px 0 0;
	overflow: hidden;
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-xs);
	line-height: 1.35;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.output-field-edit {
	padding: var(--fxr-space-2, var(--spacing-xs)) 0 0;
}

.output-field-controls {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: var(--fxr-space-2, var(--spacing-xs));
	align-items: start;
}

.output-function-controls {
	grid-template-columns: minmax(76px, 0.45fr) minmax(0, 1.2fr) minmax(0, 1fr);
}

.output-function-select,
.output-field-alias {
	min-width: 0;
}

.output-child-controls {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: var(--fxr-space-3, var(--spacing-sm));
	align-items: start;
}

.output-child-table,
.output-child-fields {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-1, 4px);
	min-width: 0;
}

.output-field-label {
	margin: 0;
	color: var(--fxr-text-secondary);
	font-size: var(--fxr-text-xs);
	font-weight: var(--fxr-weight-medium);
}

.output-field-raw {
	min-width: 0;
	font-family: var(--font-mono);
	font-size: var(--fxr-text-sm);
}

.output-fields-empty {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-2, var(--spacing-xs));
	padding: var(--fxr-space-3, var(--spacing-sm));
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
}

.output-fields-hint,
.output-fields-warning {
	margin: 0;
	font-size: var(--fxr-text-xs);
	line-height: 1.4;
}

.output-fields-hint {
	color: var(--fxr-text-muted);
}

.output-fields-warning {
	color: var(--fxr-text-warning, #b45309);
}

.output-fields-errors {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-1, 4px);
	color: var(--fxr-text-danger, #ef4444);
	font-size: var(--fxr-text-xs);
}

:deep(.field-picker-control),
:deep(.control.frappe-control),
:deep(.control-input-wrapper) {
	min-width: 0;
	max-width: 100%;
	width: 100%;
	margin-bottom: 0 !important;
}

:deep(.output-function-select),
:deep(.output-child-select) {
	display: block;
	width: 100%;
	min-width: 0;
	max-width: 100%;
	margin-bottom: 0 !important;
}

:deep(.output-function-select .fxr-input-group),
:deep(.output-child-select .fxr-input-group) {
	min-width: 0;
	margin-bottom: 0 !important;
}

:deep(.output-function-select .combobox-container),
:deep(.output-child-select .combobox-container),
:deep(.output-function-select .combobox-wrapper),
:deep(.output-child-select .combobox-wrapper) {
	width: 100%;
	min-width: 0;
	max-width: 100%;
	box-sizing: border-box;
}

:deep(.output-function-select .combobox-wrapper),
:deep(.output-child-select .combobox-wrapper) {
	min-height: var(--fxr-input-height, 32px);
	border-radius: var(--fxr-radius-md, 6px);
	box-shadow: none;
}

:deep(.output-function-select .combobox-input-group),
:deep(.output-child-select .combobox-input-group) {
	height: var(--fxr-input-height, 32px);
	padding: 0 var(--fxr-input-padding-x, 8px);
}

:deep(.output-function-select .combobox-button-trigger),
:deep(.output-child-select .combobox-button-trigger) {
	min-width: 0;
	font-size: var(--fxr-input-font-size, var(--fxr-text-sm));
}

:deep(.form-control),
:deep(input.form-control),
:deep(select.form-control) {
	height: var(--fxr-input-height, 32px) !important;
	padding: var(--fxr-input-padding-y, 5px) var(--fxr-input-padding-x, 8px) !important;
	border: 1px solid var(--fxr-border) !important;
	border-radius: var(--fxr-radius-md) !important;
	background-color: var(--fxr-bg-input) !important;
	color: var(--fxr-text) !important;
	font-size: var(--fxr-input-font-size, var(--fxr-text-sm)) !important;
	transition: border-color var(--fxr-transition-fast), box-shadow var(--fxr-transition-fast);
}

:deep(.form-control:focus) {
	border-color: var(--fxr-border-focus) !important;
	box-shadow: var(--fxr-shadow-focus) !important;
}

@container output-fields-grid (max-width: 560px) {
	.output-field-controls,
	.output-function-controls,
	.output-child-controls {
		grid-template-columns: minmax(0, 1fr);
	}

	.output-field-controls > *,
	.output-child-controls > *,
	.output-literal-controls,
	.output-field-control {
		min-width: 0;
		width: 100%;
	}
}

@media (max-width: 700px) {
	.output-field-edit {
		padding-left: 0;
	}
}
</style>
