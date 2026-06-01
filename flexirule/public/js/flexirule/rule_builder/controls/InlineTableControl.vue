<script setup>
import { computed, ref, watch } from "vue";
import ComboBoxControl from "./ComboBoxControl.vue";
/**
 * InlineTableControl - Repeatable rows with columns
 * Supports per-field hooks: get_options, onchange
 */

const props = defineProps({
	df: Object,
	modelValue: [Array, String],
	documentType: String,
	read_only: Boolean,
});

const emit = defineEmits(["update:modelValue"]);

// Dynamic options cache per row/field
const dynamicOptions = ref({});

const rows = computed({
	get() {
		if (Array.isArray(props.modelValue)) return props.modelValue;
		if (typeof props.modelValue === "string" && props.modelValue) {
			try {
				return JSON.parse(props.modelValue);
			} catch {
				return [];
			}
		}
		return [];
	},
	set(val) {
		emit("update:modelValue", val);
	},
});

const tableFields = computed(() => {
	return props.df?.table_fields || [];
});

const visibleTableFields = computed(() => {
	// If none have in_list_view set, show all. Otherwise filter.
	const hasInListView = tableFields.value.some((f) => f.in_list_view === true);
	if (!hasInListView) return tableFields.value;
	return tableFields.value.filter((f) => f.in_list_view !== false);
});

// Initialize options for all rows on mount and when rows change
watch(
	rows,
	(newRows) => {
		newRows.forEach((row, rowIdx) => {
			initializeRowOptions(rowIdx, row);
		});
	},
	{ immediate: true, deep: true }
);

function initializeRowOptions(rowIdx, rowData) {
	tableFields.value.forEach((field) => {
		if (field.get_options && typeof field.get_options === "function") {
			const key = `${rowIdx}-${field.fieldname}`;
			const options = field.get_options(rowData);
			dynamicOptions.value = { ...dynamicOptions.value, [key]: options };
		}
	});
}

function addRow() {
	const newRow = {};
	tableFields.value.forEach((f) => {
		newRow[f.fieldname] = f.default ?? "";
	});
	const newRows = [...rows.value, newRow];
	emit("update:modelValue", newRows);

	// Initialize options for new row
	setTimeout(() => initializeRowOptions(newRows.length - 1, newRow), 0);
}

function removeRow(idx) {
	const updated = [...rows.value];
	updated.splice(idx, 1);
	emit("update:modelValue", updated);
}

function updateCell(rowIdx, fieldname, value) {
	const updated = [...rows.value];
	const oldValue = updated[rowIdx][fieldname];
	updated[rowIdx] = { ...updated[rowIdx], [fieldname]: value };

	// Emit update first
	emit("update:modelValue", updated);

	// Find field definition
	const fieldDef = tableFields.value.find((f) => f.fieldname === fieldname);

	// Call onchange if defined
	if (fieldDef?.onchange && typeof fieldDef.onchange === "function") {
		const rowContext = createRowContext(rowIdx, updated[rowIdx]);
		fieldDef.onchange(value, updated[rowIdx], rowContext);
	}

	// Refresh dependent fields
	tableFields.value.forEach((depField) => {
		if (depField.depends_on_fields?.includes(fieldname) && depField.get_options) {
			const key = `${rowIdx}-${depField.fieldname}`;
			const options = depField.get_options(updated[rowIdx]);
			dynamicOptions.value = { ...dynamicOptions.value, [key]: options };
		}
	});
}

function createRowContext(rowIdx, rowData) {
	return {
		update_field: (fieldname, value) => {
			updateCell(rowIdx, fieldname, value);
		},
		refresh_field: (fieldname) => {
			const field = tableFields.value.find((f) => f.fieldname === fieldname);
			if (field?.get_options) {
				const key = `${rowIdx}-${fieldname}`;
				const options = field.get_options(rowData);
				dynamicOptions.value = { ...dynamicOptions.value, [key]: options };
			}
		},
		set_options: (fieldname, options) => {
			const key = `${rowIdx}-${fieldname}`;
			dynamicOptions.value = { ...dynamicOptions.value, [key]: options };
		},
		get_value: (fieldname) => rowData[fieldname],
		get_row_values: () => rowData,
		row_idx: rowIdx,
	};
}

function getFieldOptions(field, rowIdx) {
	// Check for dynamic options first
	const key = `${rowIdx}-${field.fieldname}`;
	if (dynamicOptions.value[key]) {
		return dynamicOptions.value[key];
	}

	// Fall back to static options
	const opts = field.options || "";
	if (typeof opts === "string") {
		return opts
			.split("\n")
			.filter(Boolean)
			.map((opt) => ({ label: opt, value: opt }));
	}
	if (Array.isArray(opts)) {
		return opts.map((opt) => (typeof opt === "string" ? { label: opt, value: opt } : opt));
	}
	return [];
}

function getSelectValue(options) {
	if (Array.isArray(options)) {
		return options.map((o) => (typeof o === "object" ? o.value : o));
	}
	return [];
}
</script>

<template>
	<div class="inline-table-control">
		<label v-if="df.label" class="control-label">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</label>

		<div class="table-wrapper">
			<table class="table table-sm table-bordered">
				<thead>
					<tr>
						<th
							v-for="col in visibleTableFields"
							:key="col.fieldname"
							:style="{
								width: col.width || (col.fieldtype === 'Percent' ? '100px' : ''),
								minWidth: col.width ? '' : '120px',
							}"
						>
							{{ __(col.label) }}
						</th>
						<th v-if="!read_only" style="width: 40px"></th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, idx) in rows" :key="idx">
						<td v-for="col in visibleTableFields" :key="col.fieldname">
							<!-- Select with dynamic options -->
							<select
								v-if="col.fieldtype === 'Select'"
								class="form-control form-control-sm"
								:data-fxr-fieldname="col.fieldname"
								:value="row[col.fieldname]"
								@change="updateCell(idx, col.fieldname, $event.target.value)"
								:disabled="read_only"
							>
								<option value="">{{ __("Select...") }}</option>
								<option
									v-for="opt in getFieldOptions(col, idx)"
									:key="typeof opt === 'object' ? opt.value : opt"
									:value="typeof opt === 'object' ? opt.value : opt"
								>
									{{ __(typeof opt === "object" ? opt.label : opt) }}
								</option>
							</select>

							<!-- DocField (Autocomplete) -->
							<div
								v-else-if="col.fieldtype === 'DocField'"
								class="table-cell-control"
								:data-fxr-fieldname="col.fieldname"
							>
								<ComboBoxControl
									:df="{ ...col, label: '', fieldtype: 'FieldPicker' }"
									:doctype="documentType"
									:modelValue="row[col.fieldname]"
									:trigger="'button'"
									:hideLabel="true"
									@update:modelValue="updateCell(idx, col.fieldname, $event)"
									:read_only="read_only"
								/>
							</div>

							<!-- Check -->
							<div v-else-if="col.fieldtype === 'Check'" class="text-center">
								<input
									type="checkbox"
									:data-fxr-fieldname="col.fieldname"
									:checked="row[col.fieldname]"
									@change="
										updateCell(
											idx,
											col.fieldname,
											$event.target.checked ? 1 : 0
										)
									"
									:disabled="read_only"
								/>
							</div>

							<!-- Number / Percent -->
							<input
								v-else-if="['Int', 'Float', 'Percent'].includes(col.fieldtype)"
								type="number"
								class="form-control form-control-sm"
								:data-fxr-fieldname="col.fieldname"
								:value="row[col.fieldname]"
								@input="
									updateCell(idx, col.fieldname, parseFloat($event.target.value))
								"
								:disabled="read_only"
								:step="col.fieldtype === 'Int' ? '1' : '0.01'"
							/>

							<!-- Default Text -->
							<input
								v-else
								type="text"
								class="form-control form-control-sm"
								:data-fxr-fieldname="col.fieldname"
								:value="row[col.fieldname]"
								@input="updateCell(idx, col.fieldname, $event.target.value)"
								:disabled="read_only"
								:placeholder="__(col.placeholder || '')"
							/>
						</td>
						<td v-if="!read_only">
							<button
								type="button"
								class="btn btn-xs btn-danger"
								@click="removeRow(idx)"
							>
								×
							</button>
						</td>
					</tr>
					<tr v-if="!rows.length">
						<td :colspan="tableFields.length + 1" class="text-muted text-center">
							{{ __("No rows. Click Add to create one.") }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<button v-if="!read_only" type="button" class="btn btn-xs btn-default" @click="addRow">
			+ {{ __("Add Row") }}
		</button>

		<small v-if="df.description" class="form-text text-muted">{{ df.description }}</small>
	</div>
</template>

<style scoped>
.inline-table-control {
	margin-bottom: 15px;
	width: 100%;
}
.control-label {
	font-size: 12px;
	font-weight: 500;
	margin-bottom: 5px;
	display: block;
}
.table-wrapper {
	margin-bottom: 8px;
	overflow-x: auto;
	width: 100%;
	border: 1px solid var(--border-color);
	border-radius: 4px;
}
.table {
	margin-bottom: 0;
	min-width: 100%;
	table-layout: auto;
}
.table th {
	font-size: 11px;
	font-weight: 500;
	white-space: nowrap;
	background: #f8f9fa;
}
.table td {
	padding: 4px;
	vertical-align: middle;
}
.table input,
.table select {
	font-size: 12px;
	min-width: 80px;
}
.table-cell-control :deep(.field-picker-control) {
	margin-bottom: 0;
}
.table-cell-control :deep(.control-label) {
	display: none;
}
</style>
