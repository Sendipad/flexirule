<template>
	<div class="output-fields-builder">
		<div class="builder-header">
			<div>
				<h6 class="mb-0">{{ __("Output Fields") }}</h6>
				<p class="section-description">
					{{ __("Define each output value in one place: fields, SQL functions, or embedded child tables.") }}
				</p>
			</div>
			<button v-if="!readOnly" type="button" class="btn btn-xs btn-outline-primary" @click="addRow">
				<i class="fa fa-plus mr-1"></i>{{ __("Add Output Field") }}
			</button>
		</div>

		<div v-if="rows.length === 0" class="empty-state text-muted py-3 text-center">
			<small>{{ __("No output fields configured. Add a field, function, or child table.") }}</small>
		</div>

		<div v-for="(row, index) in rows" :key="row.id" class="output-row">
			<div class="row-top">
				<select v-model="row.kind" class="form-control form-control-sm kind-select" :disabled="readOnly" @change="changeKind(row)">
					<option value="field">{{ __("Field") }}</option>
					<option value="function">{{ __("SQL Function") }}</option>
					<option v-if="resultMode === 'embedded_child'" value="child">{{ __("Embedded Child Table") }}</option>
				</select>

				<template v-if="row.kind === 'field'">
					<select v-model="row.source" class="form-control form-control-sm source-select" :disabled="readOnly" @change="emitUpdate">
						<option value="">{{ __("Select field…") }}</option>
						<option v-for="field in fieldsOptions" :key="field.value" :value="field.value">{{ field.label }}</option>
					</select>
					<input v-model="row.alias" class="form-control form-control-sm alias-input" :placeholder="__('Alias (optional)')" :disabled="readOnly" @input="emitUpdate" />
				</template>

				<template v-else-if="row.kind === 'function'">
					<select v-model="row.function" class="form-control form-control-sm function-select" :disabled="readOnly" @change="changeFunction(row)">
						<option v-for="fn in FUNCTION_OPTIONS" :key="fn" :value="fn">{{ fn }}</option>
					</select>
					<input v-model="row.alias" class="form-control form-control-sm alias-input" :placeholder="__('Output alias')" :disabled="readOnly" @input="emitUpdate" />
				</template>

				<template v-else-if="row.kind === 'child'">
					<select v-model="row.child_field" class="form-control form-control-sm source-select" :disabled="readOnly" @change="changeChild(row)">
						<option value="">{{ __("Select child table…") }}</option>
						<option v-for="table in childTableOptions" :key="table.value" :value="table.value">{{ table.label }} ({{ table.value }})</option>
					</select>
				</template>

				<button v-if="!readOnly" type="button" class="btn btn-xs btn-link text-danger remove-row" :title="__('Remove output field')" @click="removeRow(index)">
					<i class="fa fa-trash"></i>
				</button>
			</div>

			<div v-if="row.kind === 'function' && row.function !== 'NOW'" class="function-arguments">
				<div v-for="(arg, argIndex) in row.args" :key="argIndex" class="argument-row">
					<select v-model="arg.type" class="form-control form-control-sm arg-kind" :disabled="readOnly" @change="emitUpdate">
						<option value="field">{{ __("Field") }}</option>
						<option value="literal">{{ __("Literal") }}</option>
					</select>
					<select v-if="arg.type === 'field'" v-model="arg.value" class="form-control form-control-sm arg-value" :disabled="readOnly" @change="emitUpdate">
						<option value="*">{{ __("All rows (*)") }}</option>
						<option v-for="field in fieldsOptions" :key="field.value" :value="field.value">{{ field.label }}</option>
					</select>
					<input v-else v-model="arg.value" class="form-control form-control-sm arg-value" :placeholder="__('Literal value')" :disabled="readOnly" @input="emitUpdate" />
					<button v-if="!readOnly && row.function === 'CONCAT' && row.args.length > 2" type="button" class="btn btn-xs btn-link text-danger" @click="removeArgument(row, argIndex)">
						<i class="fa fa-times"></i>
					</button>
				</div>
				<button v-if="!readOnly && row.function === 'CONCAT'" type="button" class="btn btn-xs btn-link p-0" @click="addArgument(row)">
					<i class="fa fa-plus mr-1"></i>{{ __("Add argument") }}
				</button>
				<small v-if="row.function === 'EXTRACT'" class="text-muted">{{ __("Use a date unit literal (year, month, day, hour, minute, second) as the first argument.") }}</small>
			</div>

			<div v-if="row.kind === 'child' && row.child_field" class="child-fields">
				<label class="small text-muted">{{ __("Child fields") }}</label>
				<MultiSelectList
					:df="{ label: '', fieldname: 'fields', placeholder: __('Select fields from child table…') }"
					:options="getChildFieldOptions(row.child_field)"
					:modelValue="row.fields"
					:read_only="readOnly"
					:hideLabel="true"
					@update:modelValue="updateChildFields(row, $event)"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import MultiSelectList from "../../../../controls/MultiSelectList.vue";
import { useMetaStore } from "../../../../stores/useMetaStore";

const props = defineProps({
	fields: { type: Array, default: () => [] },
	functions: { type: Array, default: () => [] },
	embeddedChildren: { type: Array, default: () => [] },
	fieldsOptions: { type: Array, default: () => [] },
	childTableOptions: { type: Array, default: () => [] },
	resultMode: { type: String, required: true },
	readOnly: { type: Boolean, default: false },
});
const emit = defineEmits(["update:fields", "update:functions", "update:embeddedChildren"]);
const metaStore = useMetaStore();
const FUNCTION_OPTIONS = ["COUNT", "SUM", "AVG", "MIN", "MAX", "ABS", "IFNULL", "CONCAT", "EXTRACT", "NOW"];

function makeId() {
	return "output-" + Math.random().toString(36).slice(2, 10);
}
function splitField(value) {
	const match = String(value || "").match(/^(.+?)\s+as\s+(.+)$/i);
	return match ? { source: match[1].trim(), alias: match[2].trim() } : { source: value || "", alias: "" };
}
function normalizeRows() {
	const fieldRows = props.fields.map((value) => ({ id: makeId(), kind: "field", ...splitField(value) }));
	const functionRows = props.functions.map((fn) => ({ id: makeId(), kind: "function", ...clone(fn), args: (fn.args || []).map(normalizeArg) }));
	const childRows = props.embeddedChildren.map((child) => ({ id: makeId(), kind: "child", child_field: child.child_field || "", fields: [...(child.fields || [])] }));
	return [...fieldRows, ...functionRows, ...(props.resultMode === "embedded_child" ? childRows : [])];
}
function normalizeArg(arg) {
	if (arg && typeof arg === "object") return { type: arg.type || "field", value: arg.value ?? "" };
	return { type: "field", value: String(arg ?? "") };
}
function clone(value) {
	return JSON.parse(JSON.stringify(value));
}
const rows = ref(normalizeRows());
function serialize() {
	emit("update:fields", rows.value.filter((row) => row.kind === "field" && row.source).map((row) => row.alias ? row.source + " as " + row.alias : row.source));
	emit("update:functions", rows.value.filter((row) => row.kind === "function").map(({ id, kind, ...fn }) => fn));
	emit("update:embeddedChildren", rows.value.filter((row) => row.kind === "child" && row.child_field).map(({ id, kind, ...child }) => child));
}
function emitUpdate() {
	serialize();
}
function defaultArgs(fn) {
	if (fn === "NOW") return [];
	if (fn === "COUNT") return [{ type: "field", value: "*" }];
	if (fn === "CONCAT") return [{ type: "field", value: "" }, { type: "literal", value: " " }];
	if (fn === "IFNULL") return [{ type: "field", value: "" }, { type: "literal", value: "N/A" }];
	if (fn === "EXTRACT") return [{ type: "literal", value: "year" }, { type: "field", value: "" }];
	return [{ type: "field", value: "" }];
}
function addRow() {
	if (props.readOnly) return;
	rows.value.push({ id: makeId(), kind: "field", source: "", alias: "" });
}
function changeKind(row) {
	if (row.kind === "field") Object.assign(row, { source: "", alias: "" });
	if (row.kind === "function") Object.assign(row, { function: "COUNT", args: defaultArgs("COUNT"), alias: "" });
	if (row.kind === "child") Object.assign(row, { child_field: "", fields: ["name"] });
	emitUpdate();
}
function changeFunction(row) {
	row.args = defaultArgs(row.function);
	emitUpdate();
}
function changeChild(row) {
	row.fields = ["name"];
	emitUpdate();
}
function removeRow(index) {
	if (props.readOnly) return;
	rows.value.splice(index, 1);
	emitUpdate();
}
function addArgument(row) {
	row.args.push({ type: "literal", value: " " });
	emitUpdate();
}
function removeArgument(row, index) {
	row.args.splice(index, 1);
	emitUpdate();
}
function getChildFieldOptions(childFieldName) {
	const table = props.childTableOptions.find((item) => item.value === childFieldName);
	if (!table?.child_doctype) return [];
	return metaStore.get_fields_for_doctype(table.child_doctype, { alias: "", valueMode: "fieldname" });
}
function updateChildFields(row, value) {
	row.fields = Array.isArray(value) ? [...value] : [];
	emitUpdate();
}
watch(
	() => [props.fields, props.functions, props.embeddedChildren, props.resultMode],
	() => { rows.value = normalizeRows(); },
	{ deep: true }
);
</script>

<style scoped>
.output-fields-builder { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.builder-header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--spacing-md); }
.section-description { margin: 2px 0 0; color: var(--fxr-text-muted); font-size: var(--fxr-text-sm); }
.output-row { border: 1px solid var(--fxr-border-color, #e2e8f0); border-radius: 6px; padding: var(--spacing-sm); display: flex; flex-direction: column; gap: var(--spacing-sm); }
.row-top { display: flex; align-items: center; gap: var(--spacing-xs); min-width: 0; }
.kind-select { flex: 0 0 155px; }
.source-select, .function-select, .alias-input { flex: 1; min-width: 0; }
.remove-row { flex: 0 0 28px; padding: 0; }
.function-arguments, .child-fields { display: flex; flex-direction: column; gap: var(--spacing-xs); padding-left: 155px; }
.argument-row { display: flex; gap: var(--spacing-xs); min-width: 0; }
.arg-kind { flex: 0 0 100px; }
.arg-value { flex: 1; min-width: 0; }
@media (max-width: 640px) {
	.row-top { flex-wrap: wrap; }
	.kind-select, .source-select, .function-select, .alias-input { flex: 1 1 100%; }
	.function-arguments, .child-fields { padding-left: 0; }
}
</style>
