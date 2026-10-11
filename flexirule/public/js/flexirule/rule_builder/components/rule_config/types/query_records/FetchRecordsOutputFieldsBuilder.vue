<template>
	<div class="output-fields-builder">
		<div class="builder-header">
			<div>
				<h6 class="mb-0">{{ __("Output Fields") }}</h6>
				<p class="section-description">{{ __("Configure ordered Frappe-style field expressions. Use aliases for readable output keys; embedded child tables remain nested.") }}</p>
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
					<input v-model="row.argument" class="form-control form-control-sm source-select" :placeholder="__('Field name or *')" :disabled="readOnly" @input="emitUpdate" />
					<input v-model="row.alias" class="form-control form-control-sm alias-input" :placeholder="__('Output alias (required)')" :disabled="readOnly" @input="emitUpdate" />
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
			<div v-if="row.kind === 'child' && row.child_field" class="child-fields">
				<label class="small text-muted">{{ __("Child fields") }}</label>
				<MultiSelectList :df="{ label: '', fieldname: 'fields', placeholder: __('Select fields from child table…') }" :options="getChildFieldOptions(row.child_field)" :modelValue="row.fields" :read_only="readOnly" :hideLabel="true" @update:modelValue="updateChildFields(row, $event)" />
			</div>
			<small v-if="row.kind === 'function'" class="expression-preview text-muted">{{ expressionFor(row) || __("Complete the function fields to preview its serialized expression.") }}</small>
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
function splitExpression(value) {
	const expression = String(value || "").trim();
	const functionMatch = expression.match(/^([A-Z]+)\((.*)\)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$/i);
	if (functionMatch && FUNCTION_OPTIONS.includes(functionMatch[1].toUpperCase())) {
		return { kind: "function", function: functionMatch[1].toUpperCase(), argument: functionMatch[2].trim(), alias: functionMatch[3] };
	}
	const match = expression.match(/^(.+?)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$/i);
	return { kind: "field", source: match ? match[1].trim() : expression, alias: match ? match[2] : "" };
}
function normalizeRows() {
	const fieldRows = props.fields.map((value) => ({ id: makeId(), ...splitExpression(value) }));
	const functionRows = props.functions.map((fn) => {
		const args = Array.isArray(fn.args) ? fn.args : [];
		return {
			id: makeId(), kind: "function", function: String(fn.function || "COUNT").toUpperCase(),
			argument: args.map((arg) => {
				if (arg && typeof arg === "object") return arg.type === "literal" ? String(arg.value ?? "") : String(arg.value ?? "");
				return String(arg ?? "");
			}).join(", "), alias: fn.alias || "",
		};
	});
	const childRows = props.embeddedChildren.map((child) => ({ id: makeId(), kind: "child", child_field: child.child_field || "", fields: [...(child.fields || [])] }));
	return [...fieldRows, ...functionRows, ...(props.resultMode === "embedded_child" ? childRows : [])];
}
const rows = ref(normalizeRows());
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function expressionFor(row) {
	if (row.kind !== "function") return "";
	if (row.function === "NOW") return row.alias ? `NOW() as ${row.alias}` : "";
	const argument = (row.argument || "").trim();
	if (!argument || !row.alias?.trim()) return "";
	return `${row.function}(${argument}) as ${row.alias.trim()}`;
}
function serialize() {
	const fields = [];
	const children = [];
	for (const row of rows.value) {
		if (row.kind === "field" && row.source?.trim()) {
			fields.push(row.alias?.trim() ? `${row.source.trim()} as ${row.alias.trim()}` : row.source.trim());
		} else if (row.kind === "function") {
			const expression = expressionFor(row);
			if (expression) fields.push(expression);
		} else if (row.kind === "child" && row.child_field) {
			children.push({ child_field: row.child_field, fields: [...(row.fields || [])] });
		}
	}
	emit("update:fields", fields);
	emit("update:functions", []);
	emit("update:embeddedChildren", children);
}
function emitUpdate() { serialize(); }
function changeKind(row) {
	if (row.kind === "field") Object.assign(row, { source: "", alias: "" });
	if (row.kind === "function") Object.assign(row, { function: "COUNT", argument: "*", alias: "" });
	if (row.kind === "child") Object.assign(row, { child_field: "", fields: ["name"] });
	emitUpdate();
}
function changeFunction(row) {
	row.argument = row.function === "NOW" ? "" : row.function === "COUNT" ? "*" : "";
	emitUpdate();
}
function changeChild(row) { row.fields = ["name"]; emitUpdate(); }
function removeRow(index) { if (props.readOnly) return; rows.value.splice(index, 1); emitUpdate(); }
function getChildFieldOptions(childFieldName) {
	const table = props.childTableOptions.find((item) => item.value === childFieldName);
	if (!table?.child_doctype) return [];
	return metaStore.get_fields_for_doctype(table.child_doctype, { alias: "", valueMode: "fieldname" });
}
function updateChildFields(row, value) { row.fields = Array.isArray(value) ? [...value] : []; emitUpdate(); }
watch(() => [props.fields, props.functions, props.embeddedChildren, props.resultMode], () => {
	const normalized = normalizeRows();
	// Avoid replacing local rows on every parent echo; that would interrupt active edits.
	if (JSON.stringify(normalized.map(({ id, ...row }) => row)) !== JSON.stringify(rows.value.map(({ id, ...row }) => row))) {
		rows.value = normalized;
	}
}, { deep: true });
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
.child-fields { display: flex; flex-direction: column; gap: var(--spacing-xs); padding-left: 155px; }
.expression-preview { padding-left: 155px; overflow-wrap: anywhere; }
@media (max-width: 640px) {
	.row-top { flex-wrap: wrap; }
	.kind-select, .source-select, .function-select, .alias-input { flex: 1 1 100%; }
	.child-fields, .expression-preview { padding-left: 0; }
}
</style>
