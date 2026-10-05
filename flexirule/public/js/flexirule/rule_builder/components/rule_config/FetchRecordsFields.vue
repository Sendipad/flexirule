<template>
	<div class="fetch-fields-editor">
		<div class="fields-toolbar">
			<MultiSelectList
				:df="{ fieldname: 'fields', placeholder: __('Select fields to fetch...') }"
				:options="fieldOptions"
				:modelValue="selectableValues"
				:read_only="readOnly"
				:hideLabel="true"
				@update:modelValue="syncSelectedFields"
			/>
		</div>
		<div v-if="entries.length" class="field-entries">
			<div v-for="(entry, index) in entries" :key="entry.id" class="field-entry">
				<div class="field-entry-main">
					<div class="field-entry-picker">
						<ComboBoxControl
							:df="{ label: '', fieldtype: 'FieldPicker', reqd: 1 }"
							:options="fieldOptions"
							:doctype="doctype"
							:modelValue="entry.field"
							:read_only="readOnly"
							:trigger="'button'"
							:hideLabel="true"
							:navigable="true"
							:navStack="navigableFields.navStack.value"
							@mousedown="activateEntry(index)"
							@navigate="navigableFields.handleNavigate"
							@back="navigableFields.handleBack"
							@update:modelValue="(value) => updateField(index, value)"
						/>
					</div>
					<select
						v-if="!entry.child"
						class="form-control field-function"
						:value="entry.function"
						:disabled="readOnly"
						@change="updateFunction(index, $event.target.value)"
					>
						<option value="">{{ __("Field") }}</option>
						<option v-for="fn in functionOptions" :key="fn" :value="fn">{{ fn }}</option>
					</select>
					<input
						v-if="!entry.child"
						class="form-control field-alias"
						:value="entry.alias"
						:disabled="readOnly"
						:placeholder="__('Alias')"
						@input="updateAlias(index, $event.target.value)"
					/>
					<button
						v-if="!readOnly"
						type="button"
						class="btn btn-xs btn-link text-danger remove-field"
						:title="__('Remove field')"
						@click="removeEntry(index)"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
				<div v-if="entry.child" class="child-field-editor">
					<div class="child-field-label"><i class="fa fa-table mr-1"></i>{{ __("Child fields") }}</div>
					<MultiSelectList
						:df="{ fieldname: 'child_fields', placeholder: __('Select child fields...') }"
						:options="entry.childOptions"
						:modelValue="entry.childFields"
						:read_only="readOnly"
						:hideLabel="true"
						@update:modelValue="(value) => updateChildFields(index, value)"
					/>
				</div>
				<div v-if="entry.expression" class="field-expression">{{ entry.expression }}</div>
			</div>
		</div>
		<div class="field-actions" v-if="!readOnly">
			<button type="button" class="btn btn-xs btn-link p-0 text-primary" @click="addField">
				<i class="fa fa-plus mr-1"></i>{{ __("Add Field") }}
			</button>
			<button type="button" class="btn btn-xs btn-link p-0 text-primary" @click="addChildField">
				<i class="fa fa-table mr-1"></i>{{ __("Add Child Table") }}
			</button>
			<button type="button" class="btn btn-xs btn-link p-0 text-muted" @click="clearFields">
				{{ __("Clear All") }}
			</button>
		</div>
		<div class="field-help text-muted small">
			{{ __("Field references use native Query Builder paths. Aliases and supported SQL functions are serialized into the backend fields contract.") }}
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import MultiSelectList from "../../../controls/MultiSelectList.vue";
import { useMetaStore } from "../../../stores/useMetaStore";
import { useNavigableFields } from "../../../composables/useNavigableFields";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	doctype: { type: String, required: true },
	readOnly: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);
const metaStore = useMetaStore();
const activeEntry = ref(0);
const entries = reactive([]);
const functionOptions = ["COUNT", "SUM", "AVG", "MIN", "MAX"];

const navigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => entries[activeEntry.value]?.field || ""
);
const fieldOptions = computed(() => navigableFields.currentFields.value || []);
const selectableValues = computed(() =>
	entries.filter((entry) => !entry.child && typeof entry.serialized === "string").map((entry) => entry.serialized)
);

function clone(value) {
	return value === undefined ? value : JSON.parse(JSON.stringify(value));
}
function createEntry(field = "name") {
	return {
		id: "field-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8),
		field, function: "", alias: "", child: false, childFields: [], childOptions: [],
		serialized: field, expression: "",
	};
}
function parseField(value) {
	if (value && typeof value === "object" && !Array.isArray(value)) {
		const keys = Object.keys(value);
		if (keys.length === 1 && Array.isArray(value[keys[0]])) {
			const tableField = keys[0];
			return {
				...createEntry(tableField), child: true, childFields: value[tableField].map(String),
				serialized: clone(value), expression: JSON.stringify(value),
			};
		}
	}
	const raw = String(value || "").trim();
	if (!raw) return createEntry("name");
	const aliasMatch = raw.match(/^(.+?)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$/i);
	const expression = aliasMatch ? aliasMatch[1].trim() : raw;
	const alias = aliasMatch ? aliasMatch[2] : "";
	const fnMatch = expression.match(/^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$/);
	return {
		...createEntry(fnMatch ? fnMatch[2].trim() : expression),
		function: fnMatch ? fnMatch[1].toUpperCase() : "",
		alias, serialized: raw, expression: raw,
	};
}
function serializeEntry(entry) {
	if (entry.child) return { [entry.field]: clone(entry.childFields) };
	let expression = entry.field || "";
	if (entry.function) expression = entry.function === "NOW" ? "NOW()" : entry.function + "(" + expression + ")";
	if (entry.alias) expression += " as " + entry.alias.trim();
	return expression;
}
function rebuild(values) {
	entries.splice(0, entries.length, ...(Array.isArray(values) ? values.map(parseField) : []));
	for (const entry of entries) {
		entry.serialized = serializeEntry(entry);
		entry.expression = typeof entry.serialized === "string" ? entry.serialized : JSON.stringify(entry.serialized);
	}
	if (!entries.length && !props.readOnly) entries.push(createEntry("name"));
}
function emitFields() {
	const value = entries.map(serializeEntry).filter((item) => {
		if (typeof item === "string") return item.trim();
		return Object.keys(item).length > 0 && Object.values(item)[0]?.length;
	});
	emit("update:modelValue", value);
}
function syncSelectedFields(values) {
	const selected = new Set((values || []).map(String));
	for (let i = entries.length - 1; i >= 0; i--) {
		if (!entries[i].child && !selected.has(entries[i].serialized)) entries.splice(i, 1);
	}
	for (const value of selected) {
		if (!entries.some((entry) => !entry.child && entry.serialized === value)) entries.push(parseField(value));
	}
	emitFields();
}
function activateEntry(index) {
	activeEntry.value = index;
	navigableFields.syncStackToValue(entries[index]?.field || "");
}
function updateField(index, value) {
	const entry = entries[index];
	if (!entry || entry.child) return;
	entry.field = value;
	entry.serialized = serializeEntry(entry);
	entry.expression = entry.serialized;
	activeEntry.value = index;
	emitFields();
}
function updateFunction(index, value) {
	const entry = entries[index];
	if (!entry) return;
	entry.function = value;
	entry.serialized = serializeEntry(entry);
	entry.expression = entry.serialized;
	emitFields();
}
function updateAlias(index, value) {
	const entry = entries[index];
	if (!entry) return;
	entry.alias = value;
	entry.serialized = serializeEntry(entry);
	entry.expression = entry.serialized;
	emitFields();
}
async function addChildField() {
	if (!props.doctype) return;
	await metaStore.fetch_metadata(props.doctype);
	const fields = metaStore.doc_meta[props.doctype] || [];
	const table = fields.find((field) => ["Table", "Table MultiSelect"].includes(field.fieldtype) && field.options);
	if (!table) return;
	await metaStore.fetch_metadata(table.options);
	const childFields = (metaStore.doc_meta[table.options] || [])
		.filter((field) => field.fieldname && !["Section Break", "Column Break", "Tab Break", "HTML"].includes(field.fieldtype))
		.map((field) => ({ value: field.fieldname, label: (field.label || field.fieldname) + " (" + field.fieldname + ")", description: field.fieldtype }));
	const entry = {
		...createEntry(table.fieldname), child: true,
		childFields: childFields.slice(0, 1).map((field) => field.value),
		childOptions: childFields,
	};
	entries.push(entry);
	emitFields();
}
function addField() {
	entries.push(createEntry("name"));
	activeEntry.value = entries.length - 1;
	navigableFields.resetStack();
	emitFields();
}
function removeEntry(index) {
	entries.splice(index, 1);
	if (activeEntry.value >= entries.length) activeEntry.value = Math.max(0, entries.length - 1);
	emitFields();
}
function updateChildFields(index, value) {
	const entry = entries[index];
	if (!entry || !entry.child) return;
	entry.childFields = (value || []).map(String);
	entry.serialized = serializeEntry(entry);
	entry.expression = JSON.stringify(entry.serialized);
	emitFields();
}
function clearFields() {
	entries.splice(0, entries.length);
	emitFields();
}
watch(() => props.modelValue, (value) => {
	const incoming = JSON.stringify(value || []);
	const current = JSON.stringify(entries.map(serializeEntry));
	if (incoming !== current) rebuild(value || []);
}, { deep: true, immediate: true });
</script>

<style scoped>
.fetch-fields-editor { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.fields-toolbar { min-width: 0; }
.field-entries { display: flex; flex-direction: column; gap: var(--fxr-space-2); margin-top: var(--fxr-space-2); }
.field-entry { padding: var(--fxr-space-2); border: 1px solid var(--fxr-border-subtle); border-radius: var(--fxr-radius-md); background: var(--fxr-bg-input); }
.field-entry-main { display: flex; align-items: center; gap: var(--spacing-sm); min-width: 0; }
.field-entry-picker { flex: 1 1 280px; min-width: 0; }
.field-function { flex: 0 0 110px; }
.field-alias { flex: 0 1 180px; min-width: 120px; }
.remove-field { flex: 0 0 28px; }
.child-field-editor { display: grid; grid-template-columns: 130px minmax(0, 1fr); gap: var(--spacing-sm); align-items: center; margin-top: var(--fxr-space-2); }
.child-field-label { color: var(--fxr-text-muted); font-size: var(--fxr-text-sm); }
.field-expression { margin-top: 4px; font-family: var(--fxr-font-mono, monospace); font-size: 11px; color: var(--fxr-text-muted); overflow-wrap: anywhere; }
.field-actions { display: flex; gap: var(--spacing-md); align-items: center; }
.field-help { line-height: 1.4; }
@media (max-width: 800px) { .field-entry-main { flex-wrap: wrap; } .field-entry-picker { flex-basis: 100%; } .child-field-editor { grid-template-columns: 1fr; } }
</style>
