<template>
	<div class="resource-mapper-control">
		<div v-if="df?.label && !hideLabel" class="control-label label" :class="{ reqd: df?.reqd }">
			{{ __(df.label) }}
		</div>

		<!-- Mode & Options Bar -->
		<div class="rm-options-bar">
			<div class="rm-option-group">
				<label class="rm-check">
					<input type="checkbox" v-model="ui.copy_same_fields" :disabled="readOnly" />
					<span>{{ __("Auto-copy matching fields") }}</span>
				</label>
			</div>
			<div class="rm-option-group">
				<label class="rm-label-sm">{{ __("Source") }}</label>
				<AutocompleteControl
					:df="{ fieldtype: 'Autocomplete', label: '' }"
					:options="sourceOptionsNormalized"
					:modelValue="ui.source_path"
					:read_only="readOnly"
					:hideLabel="true"
					@update:modelValue="(val) => (ui.source_path = val || 'doc')"
				/>
			</div>
			<button v-if="!readOnly" class="rm-btn rm-btn-magic" @click="previewScalarAutoMap">
				<i class="fa fa-magic"></i> {{ __("Auto-map") }}
			</button>
		</div>

		<!-- Exclude Fields (when copy_same_fields) -->
		<div v-if="ui.copy_same_fields" class="rm-exclude-section">
			<label class="rm-label-sm">{{ __("Exclude Fields") }}</label>
			<div class="rm-exclude-row">
				<select
					class="form-control input-xs"
					v-model="pendingExcludeField"
					:disabled="readOnly"
				>
					<option value="">{{ __("Select field…") }}</option>
					<option
						v-for="f in scalarTargetOptions"
						:key="`exclude-${f.value}`"
						:value="f.value"
					>
						{{ f.label || f.value }}
					</option>
				</select>
				<button v-if="!readOnly" class="rm-btn rm-btn-sm" @click="addExcludedField">
					{{ __("Add") }}
				</button>
			</div>
			<div v-if="ui.field_no_map?.length" class="rm-chip-list">
				<span v-for="(f, idx) in ui.field_no_map" :key="`chip-${f}-${idx}`" class="rm-chip">
					{{ f }}
					<button v-if="!readOnly" class="rm-chip-x" @click="removeExcludedField(idx)">
						×
					</button>
				</span>
			</div>
		</div>

		<!-- Auto-map Preview -->
		<div v-if="scalarAutoMapPreview.length" class="rm-preview-box">
			<div class="rm-preview-title">
				{{ __("Auto-map Preview") }}
				<span class="rm-badge">{{ scalarAutoMapPreview.length }}</span>
			</div>
			<div class="rm-preview-list">
				<div
					v-for="(row, idx) in scalarAutoMapPreview"
					:key="`preview-${idx}`"
					class="rm-preview-row"
				>
					<code class="rm-target">{{ row.target }}</code>
					<i class="fa fa-long-arrow-left rm-arrow"></i>
					<code class="rm-source">{{ row.path }}</code>
				</div>
			</div>
			<div class="rm-preview-actions">
				<button class="rm-btn rm-btn-primary" @click="applyScalarAutoMap">
					{{ __("Apply") }}
				</button>
				<button class="rm-btn rm-btn-default" @click="cancelScalarAutoMap">
					{{ __("Cancel") }}
				</button>
			</div>
		</div>

		<!-- ═══ Scalar Field Mappings ═══ -->
		<div class="rm-section">
			<div class="rm-section-header">
				<h6><i class="fa fa-columns"></i> {{ __("Field Mappings") }}</h6>
				<button v-if="!readOnly" class="rm-btn rm-btn-sm" @click="addScalarRow">
					<i class="fa fa-plus"></i> {{ __("Add") }}
				</button>
			</div>

			<div v-if="!ui.scalars.length" class="rm-empty">
				{{ __("No field mappings. Click + Add or use Auto-map.") }}
			</div>

			<div v-for="(row, idx) in ui.scalars" :key="`scalar-${idx}`" class="rm-mapping-row">
				<!-- Target -->
				<div class="rm-cell rm-cell-target">
					<FieldPickerControl
						:df="{ label: '' }"
						:fields="scalarTargetOptions"
						:documentType="targetDoctype"
						:modelValue="row.target"
						:read_only="readOnly"
						@update:modelValue="(val) => (row.target = val || '')"
					/>
				</div>

				<!-- Arrow -->
				<div class="rm-cell rm-cell-arrow">
					<i class="fa fa-long-arrow-left"></i>
				</div>

				<!-- Source Type -->
				<div class="rm-cell rm-cell-type">
					<select
						class="form-control input-xs"
						v-model="row.source_type"
						:disabled="readOnly"
					>
						<option value="path">{{ __("Path") }}</option>
						<option value="expr">{{ __("Expr") }}</option>
						<option value="literal">{{ __("Static") }}</option>
					</select>
				</div>

				<!-- Source Value -->
				<div class="rm-cell rm-cell-source">
					<AutocompleteControl
						v-if="row.source_type === 'path'"
						:df="{ fieldtype: 'Autocomplete', label: '' }"
						:options="scalarSourceOptions"
						:modelValue="row.path"
						:read_only="readOnly"
						:hideLabel="true"
						@update:modelValue="(val) => (row.path = val || '')"
					/>
					<input
						v-else-if="row.source_type === 'expr'"
						class="form-control input-xs"
						v-model="row.expr"
						:placeholder="__('Expression')"
						:disabled="readOnly"
					/>
					<input
						v-else
						class="form-control input-xs"
						v-model="row.literal"
						:placeholder="__('Static value')"
						:disabled="readOnly"
					/>
				</div>

				<!-- Delete -->
				<div class="rm-cell rm-cell-action">
					<button
						v-if="!readOnly"
						class="rm-btn rm-btn-danger"
						@click="removeScalarRow(idx)"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
			</div>
		</div>

		<!-- ═══ Child Table Mappings ═══ -->
		<div class="rm-section">
			<div class="rm-section-header">
				<h6><i class="fa fa-table"></i> {{ __("Child Table Mappings") }}</h6>
				<button v-if="!readOnly" class="rm-btn rm-btn-sm" @click="addTableMap">
					<i class="fa fa-plus"></i> {{ __("Add Table") }}
				</button>
			</div>

			<div v-if="!ui.tables.length" class="rm-empty">
				{{ __("No child table mappings configured.") }}
			</div>

			<div v-for="(table, tIdx) in ui.tables" :key="`tbl-${tIdx}`" class="rm-table-card">
				<div class="rm-table-header">
					<div class="rm-table-header-fields">
						<select
							class="form-control input-xs"
							v-model="table.target_table"
							:disabled="readOnly"
						>
							<option value="">{{ __("Target Table") }}</option>
							<option
								v-for="tbl in tableTargetOptions"
								:key="tbl.value"
								:value="tbl.value"
							>
								{{ tbl.label }}
							</option>
						</select>

						<input
							class="form-control input-xs"
							v-model="table.source_path"
							:placeholder="__('Source path (e.g. doc.items)')"
							:disabled="readOnly"
						/>

						<input
							class="form-control input-xs rm-alias-input"
							v-model="table.item_alias"
							:placeholder="__('Alias')"
							:disabled="readOnly"
						/>
					</div>

					<div class="rm-table-header-actions">
						<button
							v-if="!readOnly"
							class="rm-btn rm-btn-sm"
							@click="previewTableAutoMap(table, tIdx)"
						>
							{{ __("Auto-map") }}
						</button>
						<button
							v-if="!readOnly"
							class="rm-btn rm-btn-danger"
							@click="removeTableMap(tIdx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>

				<!-- Table Auto-map Preview -->
				<div v-if="tableAutoMapPreview[tIdx]?.length" class="rm-preview-box">
					<div class="rm-preview-title">
						{{ __("Table Auto-map Preview") }}
						<span class="rm-badge">{{ tableAutoMapPreview[tIdx].length }}</span>
					</div>
					<div class="rm-preview-list">
						<div
							v-for="(row, pIdx) in tableAutoMapPreview[tIdx]"
							:key="`table-preview-${tIdx}-${pIdx}`"
							class="rm-preview-row"
						>
							<code class="rm-target">{{ row.target }}</code>
							<i class="fa fa-long-arrow-left rm-arrow"></i>
							<code class="rm-source">{{ row.path }}</code>
						</div>
					</div>
					<div class="rm-preview-actions">
						<button
							class="rm-btn rm-btn-primary"
							@click="applyTableAutoMap(table, tIdx)"
						>
							{{ __("Apply") }}
						</button>
						<button class="rm-btn rm-btn-default" @click="cancelTableAutoMap(tIdx)">
							{{ __("Cancel") }}
						</button>
					</div>
				</div>

				<!-- Table Options -->
				<div class="rm-table-options">
					<label class="rm-check">
						<input type="checkbox" v-model="table.reset_value" :disabled="readOnly" />
						<span>{{ __("Replace existing rows") }}</span>
					</label>
					<label class="rm-check">
						<input type="checkbox" v-model="table.add_if_empty" :disabled="readOnly" />
						<span>{{ __("Only if empty") }}</span>
					</label>
					<input
						class="form-control input-xs"
						v-model="table.condition"
						:placeholder="__('Include condition (e.g. item.qty > 0)')"
						:disabled="readOnly"
					/>
					<input
						class="form-control input-xs"
						v-model="table.filter"
						:placeholder="__('Skip filter (e.g. item.disabled == 1)')"
						:disabled="readOnly"
					/>
				</div>

				<!-- Row Mappings -->
				<div class="rm-table-rows">
					<div class="rm-section-header rm-section-header-sm">
						<span class="rm-label-sm">{{ __("Row Field Mapping") }}</span>
						<button
							v-if="!readOnly"
							class="rm-btn rm-btn-sm"
							@click="addTableRow(table)"
						>
							<i class="fa fa-plus"></i>
						</button>
					</div>

					<div v-if="!table.mappings?.length" class="rm-empty rm-empty-sm">
						{{ __("No row mappings.") }}
					</div>

					<div
						v-for="(row, rIdx) in table.mappings"
						:key="`tbl-row-${tIdx}-${rIdx}`"
						class="rm-mapping-row"
					>
						<div class="rm-cell rm-cell-target">
							<select
								class="form-control input-xs"
								v-model="row.target"
								:disabled="readOnly"
							>
								<option value="">{{ __("Target Field") }}</option>
								<option
									v-for="cf in getChildFieldOptions(table.target_table)"
									:key="cf.value"
									:value="cf.value"
								>
									{{ cf.label }}
								</option>
							</select>
						</div>

						<div class="rm-cell rm-cell-arrow">
							<i class="fa fa-long-arrow-left"></i>
						</div>

						<div class="rm-cell rm-cell-type">
							<select
								class="form-control input-xs"
								v-model="row.source_type"
								:disabled="readOnly"
							>
								<option value="path">{{ __("Path") }}</option>
								<option value="expr">{{ __("Expr") }}</option>
								<option value="literal">{{ __("Static") }}</option>
							</select>
						</div>

						<div class="rm-cell rm-cell-source">
							<AutocompleteControl
								v-if="row.source_type === 'path'"
								:df="{ fieldtype: 'Autocomplete', label: '' }"
								:options="getTableRowSourceOptions(table)"
								:modelValue="row.path"
								:read_only="readOnly"
								:hideLabel="true"
								@update:modelValue="(val) => (row.path = val || '')"
							/>
							<input
								v-else-if="row.source_type === 'expr'"
								class="form-control input-xs"
								v-model="row.expr"
								:placeholder="__('Expression')"
								:disabled="readOnly"
							/>
							<input
								v-else
								class="form-control input-xs"
								v-model="row.literal"
								:placeholder="__('Static value')"
								:disabled="readOnly"
							/>
						</div>

						<div class="rm-cell rm-cell-action">
							<button
								v-if="!readOnly"
								class="rm-btn rm-btn-danger"
								@click="removeTableRow(table, rIdx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>

		<div v-if="df?.description && !hideDescription" class="description text-muted mt-2">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import AutocompleteControl from "./AutocompleteControl.vue";
import FieldPickerControl from "./FieldPickerControl.vue";

const props = defineProps({
	df: { type: Object, default: null },
	modelValue: { type: [Object, String], default: null },
	targetDoctype: { type: String, default: "" },
	targetFields: { type: Array, default: () => [] },
	sourceOptions: { type: Array, default: () => [] },
	read_only: { type: Boolean, default: false },
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const readOnly = computed(() => !!props.read_only || !!props.df?.read_only);
const targetDoctype = computed(() => props.targetDoctype || props.df?.targetDoctype || "");

const ui = ref({
	version: 2,
	mode: "field_mappings",
	source_path: "doc",
	copy_same_fields: false,
	field_no_map: [],
	scalars: [],
	tables: [],
});
const tableTargetOptions = ref([]);
const childFieldMap = ref({});
const pendingExcludeField = ref("");
const scalarAutoMapPreview = ref([]);
const tableAutoMapPreview = ref({});
let emitting = false;

function makeScalar() {
	return {
		target: "",
		source_type: "path",
		path: "",
		expr: "",
		literal: "",
	};
}

function makeTable() {
	return {
		target_table: "",
		source_path: "",
		item_alias: "item",
		reset_value: true,
		add_if_empty: false,
		condition: "",
		filter: "",
		mappings: [],
	};
}

function normalizeModel(val) {
	if (val && typeof val === "object") {
		return {
			version: val.version || 2,
			mode: val.mode || "field_mappings",
			source_path: val.source_path || "doc",
			copy_same_fields: !!val.copy_same_fields,
			field_no_map: Array.isArray(val.field_no_map) ? val.field_no_map.filter(Boolean) : [],
			scalars: Array.isArray(val.scalars)
				? val.scalars.filter((s) => s && s.target && !String(s.target).includes("."))
				: [],
			tables: Array.isArray(val.tables)
				? val.tables.map((table) => ({
						target_table: table?.target_table || "",
						source_path: table?.source_path || "",
						item_alias: table?.item_alias || "item",
						reset_value: table?.reset_value !== undefined ? !!table.reset_value : true,
						add_if_empty: !!table?.add_if_empty,
						condition: table?.condition || "",
						filter: table?.filter || "",
						mappings: Array.isArray(table?.mappings) ? table.mappings : [],
				  }))
				: [],
		};
	}

	if (typeof val === "string" && val.trim()) {
		try {
			const parsed = JSON.parse(val);
			return normalizeModel(parsed);
		} catch (e) {
			return {
				version: 2,
				mode: "field_mappings",
				source_path: "doc",
				copy_same_fields: false,
				field_no_map: [],
				scalars: [],
				tables: [],
			};
		}
	}

	return {
		version: 2,
		mode: "field_mappings",
		source_path: "doc",
		copy_same_fields: false,
		field_no_map: [],
		scalars: [],
		tables: [],
	};
}

const scalarTargetOptions = computed(() => {
	if (props.targetFields && props.targetFields.length) {
		return props.targetFields.filter(
			(f) => f && f.value && !String(f.value).includes(".") && f.fieldtype !== "Table"
		);
	}

	if (tableTargetOptions.value.length && childFieldMap.value.__parent_fields) {
		return childFieldMap.value.__parent_fields;
	}
	return [];
});

function uniqueOptions(options) {
	const seen = new Set();
	return (options || []).filter((opt) => {
		const value = String(opt?.value || "").trim();
		if (!value || seen.has(value)) return false;
		seen.add(value);
		return true;
	});
}

const sourceOptionsNormalized = computed(() => {
	const baseRoots = [
		{ label: "doc", value: "doc" },
		{ label: "old_doc", value: "old_doc" },
		{ label: "vars", value: "vars" },
		{ label: "item", value: "item" },
		{ label: "loop", value: "loop" },
	];
	const incoming = (props.sourceOptions || []).map((opt) => {
		if (typeof opt === "string") return { label: opt, value: opt };
		return {
			label: opt?.label || opt?.value,
			value: opt?.value,
		};
	});
	return uniqueOptions([...baseRoots, ...incoming]);
});

const scalarSourceOptions = computed(() => {
	// Source options come only from real upstream context (variable_options),
	// NOT generated from target fields. This prevents invalid mappings
	// like doc.grand_total when the source doctype doesn't have that field.
	return uniqueOptions([...sourceOptionsNormalized.value]);
});

function addScalarRow() {
	ui.value.scalars.push(makeScalar());
}

function removeScalarRow(idx) {
	ui.value.scalars.splice(idx, 1);
}

function addTableMap() {
	ui.value.tables.push(makeTable());
}

function removeTableMap(idx) {
	ui.value.tables.splice(idx, 1);
	tableAutoMapPreview.value = {};
}

function addTableRow(table) {
	table.mappings = table.mappings || [];
	table.mappings.push(makeScalar());
}

function removeTableRow(table, idx) {
	table.mappings.splice(idx, 1);
}

function addExcludedField() {
	const fieldname = (pendingExcludeField.value || "").trim();
	if (!fieldname) return;
	const list = Array.isArray(ui.value.field_no_map) ? ui.value.field_no_map : [];
	if (!list.includes(fieldname)) {
		ui.value.field_no_map = [...list, fieldname];
	}
	pendingExcludeField.value = "";
}

function removeExcludedField(idx) {
	if (!Array.isArray(ui.value.field_no_map)) return;
	ui.value.field_no_map.splice(idx, 1);
}

function getLeaf(path) {
	if (!path) return "";
	const parts = String(path).trim().split(".");
	return parts[parts.length - 1] || "";
}

function buildPath(base, fieldname) {
	const cleanBase = String(base || "")
		.trim()
		.replace(/\.$/, "");
	if (!cleanBase) return fieldname || "";
	if (!fieldname) return cleanBase;
	return `${cleanBase}.${fieldname}`;
}

function preferredSource(targetField, options, prefix = "") {
	const candidates = (options || []).filter((opt) => {
		if (!opt?.value) return false;
		const value = String(opt.value);
		if (prefix && !value.startsWith(prefix)) return false;
		return getLeaf(value) === targetField;
	});
	if (!candidates.length) return null;
	return candidates.find((c) => String(c.value).startsWith("doc.")) || candidates[0];
}

// System / internal fields that should never be auto-mapped
const AUTOMAP_EXCLUDE_FIELDS = new Set([
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
	"parent",
	"parentfield",
	"parenttype",
	"lft",
	"rgt",
	"old_parent",
	"naming_series",
	"_user_tags",
	"_comments",
	"_assign",
	"_liked_by",
	"_seen",
	"doctype",
	"amended_from",
]);

function collectScalarAutoMapRows() {
	const existing = new Set(ui.value.scalars.map((row) => row.target).filter(Boolean));
	const suggestions = [];

	scalarTargetOptions.value.forEach((field) => {
		const target = field.value || field.fieldname;
		if (!target || existing.has(target)) return;
		// Skip system / internal fields
		if (AUTOMAP_EXCLUDE_FIELDS.has(target)) return;
		// Only suggest a mapping when a real source match exists in the context
		const source = preferredSource(target, scalarSourceOptions.value);
		if (!source) return;
		suggestions.push({
			target,
			source_type: "path",
			path: source.value,
			expr: "",
			literal: "",
		});
		existing.add(target);
	});

	return suggestions;
}

function previewScalarAutoMap() {
	scalarAutoMapPreview.value = collectScalarAutoMapRows();
}

function applyScalarAutoMap() {
	if (!scalarAutoMapPreview.value.length) return;
	ui.value.scalars = [...ui.value.scalars, ...scalarAutoMapPreview.value];
	scalarAutoMapPreview.value = [];
}

function cancelScalarAutoMap() {
	scalarAutoMapPreview.value = [];
}

function collectTableAutoMapRows(table) {
	if (!table || !table.target_table) return [];
	const childFields = getChildFieldOptions(table.target_table);
	if (!childFields.length) return [];
	const existing = new Set((table.mappings || []).map((row) => row.target).filter(Boolean));
	const rowAlias = (table.item_alias || "item").trim() || "item";
	const rowSourceOptions = getTableRowSourceOptions(table);
	const suggestions = [];

	childFields.forEach((cf) => {
		const target = cf.value;
		if (!target || existing.has(target)) return;
		// Skip system / internal fields
		if (AUTOMAP_EXCLUDE_FIELDS.has(target)) return;
		// Try to find a match in context variables, fallback to speculative mapping based on rowAlias
		const source = preferredSource(target, rowSourceOptions, `${rowAlias}.`);
		const sourcePath = source ? source.value : `${rowAlias}.${target}`;

		suggestions.push({
			target,
			source_type: "path",
			path: sourcePath,
			expr: "",
			literal: "",
		});
		existing.add(target);
	});

	return suggestions;
}

function previewTableAutoMap(table, tableIndex) {
	const rows = collectTableAutoMapRows(table);
	tableAutoMapPreview.value = {
		...tableAutoMapPreview.value,
		[tableIndex]: rows,
	};
}

function applyTableAutoMap(table, tableIndex) {
	const rows = tableAutoMapPreview.value?.[tableIndex] || [];
	if (!rows.length) return;
	table.mappings = Array.isArray(table.mappings) ? table.mappings : [];
	table.mappings.push(...rows);
	cancelTableAutoMap(tableIndex);
}

function cancelTableAutoMap(tableIndex) {
	const next = { ...(tableAutoMapPreview.value || {}) };
	delete next[tableIndex];
	tableAutoMapPreview.value = next;
}

function getChildFieldOptions(tableField) {
	return childFieldMap.value[tableField] || [];
}

function getTableRowSourceOptions(table) {
	// Derive from upstream context variables only, as requested.
	// Removed rowFieldHints which were speculative guesses based on target fields.
	return uniqueOptions([...sourceOptionsNormalized.value]);
}

async function loadTargetMeta(doctype) {
	tableTargetOptions.value = [];
	childFieldMap.value = {};
	if (!doctype) return;

	await frappe.model.with_doctype(doctype);
	const meta = frappe.get_meta(doctype);
	if (!meta) return;

	const parentFields = [];
	const tableFields = [];

	for (const df of meta.fields || []) {
		if (
			["Section Break", "Column Break", "Tab Break", "HTML", "Fold", "Heading"].includes(
				df.fieldtype
			)
		) {
			continue;
		}
		if (df.fieldtype === "Table" || df.fieldtype === "Table MultiSelect") {
			if (df.options) {
				tableFields.push({
					value: df.fieldname,
					label: df.label || df.fieldname,
					child_doctype: df.options,
				});
			}
			continue;
		}
		parentFields.push({
			value: df.fieldname,
			label: df.label || df.fieldname,
			fieldtype: df.fieldtype,
		});
	}

	childFieldMap.value.__parent_fields = parentFields;
	tableTargetOptions.value = tableFields;

	for (const table of tableFields) {
		await frappe.model.with_doctype(table.child_doctype);
		const childMeta = frappe.get_meta(table.child_doctype);
		const childOptions = [];
		for (const cf of childMeta?.fields || []) {
			if (
				["Section Break", "Column Break", "Tab Break", "HTML", "Fold", "Heading"].includes(
					cf.fieldtype
				)
			) {
				continue;
			}
			childOptions.push({
				value: cf.fieldname,
				label: cf.label || cf.fieldname,
				fieldtype: cf.fieldtype,
			});
		}
		childFieldMap.value[table.value] = childOptions;
	}
}

watch(
	() => props.modelValue,
	(val) => {
		if (emitting) return;
		ui.value = normalizeModel(val);
		scalarAutoMapPreview.value = [];
		tableAutoMapPreview.value = {};
	},
	{ immediate: true, deep: true }
);

watch(
	ui,
	() => {
		emitting = true;
		emit("update:modelValue", JSON.parse(JSON.stringify(ui.value)));
		setTimeout(() => {
			emitting = false;
		}, 0);
	},
	{ deep: true }
);

watch(
	targetDoctype,
	(val) => {
		loadTargetMeta(val);
	},
	{ immediate: true }
);
</script>

<style scoped>
.resource-mapper-control {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

/* ─── Options Bar ─── */
.rm-options-bar {
	display: flex;
	align-items: center;
	gap: 12px;
	flex-wrap: wrap;
	padding: 8px 12px;
	background: var(--bg-light, #fff);
	border: 1px solid var(--border-color);
	border-radius: 8px;
}

.rm-option-group {
	display: flex;
	align-items: center;
	gap: 6px;
}

.rm-label-sm {
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted);
	white-space: nowrap;
}

.rm-check {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	font-size: 12px;
	cursor: pointer;
	color: var(--text-color);
}

/* ─── Exclude Section ─── */
.rm-exclude-section {
	padding: 8px 12px;
	background: #f8fafc;
	border: 1px solid var(--border-color);
	border-radius: 8px;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.rm-exclude-row {
	display: grid;
	grid-template-columns: 1fr auto;
	gap: 6px;
}

.rm-chip-list {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
}

.rm-chip {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 2px 8px;
	border-radius: 999px;
	background: linear-gradient(135deg, #e8f0fe, #d4e4fd);
	border: 1px solid rgba(36, 144, 239, 0.2);
	font-size: 11px;
	color: var(--primary, #2490ef);
	font-weight: 500;
}

.rm-chip-x {
	background: transparent;
	border: 0;
	padding: 0;
	line-height: 1;
	font-size: 13px;
	color: var(--text-muted);
	cursor: pointer;
}

/* ─── Section ─── */
.rm-section {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 10px 12px;
	background: var(--bg-light, #fff);
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.rm-section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
}

.rm-section-header h6 {
	margin: 0;
	font-size: 12px;
	font-weight: 600;
	display: flex;
	align-items: center;
	gap: 6px;
}

.rm-section-header-sm {
	padding-top: 4px;
	border-top: 1px dashed var(--border-color);
}

/* ─── Mapping Row ─── */
.rm-mapping-row {
	display: grid;
	grid-template-columns: 1.4fr auto 0.7fr 1.6fr auto;
	gap: 6px;
	align-items: center;
}

.rm-cell-arrow {
	color: var(--text-muted);
	font-size: 12px;
	text-align: center;
}

/* ─── Table Card ─── */
.rm-table-card {
	border: 1px dashed var(--border-color);
	border-radius: 8px;
	padding: 10px;
	display: flex;
	flex-direction: column;
	gap: 8px;
	background: #fafbfc;
}

.rm-table-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
}

.rm-table-header-fields {
	display: flex;
	gap: 6px;
	flex: 1;
}

.rm-table-header-actions {
	display: flex;
	gap: 4px;
	flex-shrink: 0;
}

.rm-alias-input {
	max-width: 80px;
}

.rm-table-options {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 6px;
	align-items: center;
}

.rm-table-rows {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

/* ─── Preview Box ─── */
.rm-preview-box {
	border: 1px solid var(--primary, #2490ef);
	border-radius: 8px;
	padding: 10px;
	background: #f0f7ff;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.rm-preview-title {
	font-size: 12px;
	font-weight: 600;
	color: var(--primary, #2490ef);
	display: flex;
	align-items: center;
	gap: 6px;
}

.rm-badge {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 18px;
	height: 18px;
	padding: 0 5px;
	border-radius: 999px;
	background: var(--primary, #2490ef);
	color: #fff;
	font-size: 10px;
	font-weight: 700;
}

.rm-preview-list {
	max-height: 120px;
	overflow: auto;
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.rm-preview-row {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 12px;
}

.rm-preview-row .rm-target {
	color: var(--text-color);
	font-weight: 500;
}

.rm-preview-row .rm-source {
	color: var(--primary, #2490ef);
}

.rm-preview-row .rm-arrow {
	color: var(--text-muted);
	font-size: 11px;
}

.rm-preview-actions {
	display: flex;
	gap: 6px;
}

/* ─── Buttons ─── */
.rm-btn {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 4px 10px;
	font-size: 11px;
	font-weight: 500;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	background: var(--bg-light, #fff);
	color: var(--text-color);
	cursor: pointer;
	transition: all 0.15s;
	white-space: nowrap;
}

.rm-btn:hover {
	background: var(--bg-blue, #e8f0fe);
	border-color: var(--primary, #2490ef);
}

.rm-btn-sm {
	padding: 3px 8px;
	font-size: 11px;
}

.rm-btn-magic {
	color: var(--primary, #2490ef);
	border-color: var(--primary, #2490ef);
}

.rm-btn-primary {
	background: var(--primary, #2490ef);
	color: #fff;
	border-color: var(--primary, #2490ef);
}

.rm-btn-primary:hover {
	opacity: 0.9;
	color: #fff;
}

.rm-btn-default {
	background: var(--bg-light, #fff);
}

.rm-btn-danger {
	color: var(--red-500, #e53e3e);
	border-color: transparent;
	background: transparent;
	padding: 3px 6px;
}

.rm-btn-danger:hover {
	background: var(--red-50, #fff5f5);
}

/* ─── Empty ─── */
.rm-empty {
	font-size: 12px;
	color: var(--text-muted);
	text-align: center;
	padding: 12px;
}

.rm-empty-sm {
	padding: 6px;
	font-size: 11px;
}
</style>
