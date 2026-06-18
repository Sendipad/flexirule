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
	showValidation: { type: Boolean, default: false },
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

const isValid = computed(() => {
	if (!props.df?.reqd) return true;
	if (!rows.value.length) return false;
	// Basic validation: check if all required fields in each row are filled
	return !rows.value.some((row) => {
		return tableFields.value.some((f) => f.reqd && !row[f.fieldname]);
	});
});

function validate() {
	const errors = [];
	if (props.df?.reqd && !rows.value.length) {
		errors.push(
			__("{0} must have at least one row").replace("{0}", props.df?.label || __("Table"))
		);
	} else if (
		rows.value.some((row) => {
			return tableFields.value.some((f) => f.reqd && !row[f.fieldname]);
		})
	) {
		errors.push(
			__("{0} contains incomplete rows").replace("{0}", props.df?.label || __("Table"))
		);
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<template>
	<div
		class="inline-table-control fxr-control"
		:class="{ 'has-error': showValidation && !isValid }"
	>
		<label v-if="df.label" class="control-label">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</label>

		<div class="table-wrapper">
			<table class="table-custom">
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
						<td
							v-for="col in visibleTableFields"
							:key="col.fieldname"
							:data-label="__(col.label)"
						>
							<!-- Select with dynamic options -->
							<select
								v-if="col.fieldtype === 'Select'"
								class="input-custom"
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
								class="input-custom"
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
								class="input-custom"
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
								class="remove-row-btn"
								@click="removeRow(idx)"
								title="Remove Row"
							>
								×
							</button>
						</td>
					</tr>
					<tr v-if="!rows.length">
						<td
							:colspan="visibleTableFields.length + (read_only ? 0 : 1)"
							class="empty-state"
						>
							{{ __("No rows. Click Add to create one.") }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<button v-if="!read_only" type="button" class="add-row-btn" @click="addRow">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="14"
				height="14"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2.5"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<line x1="12" y1="5" x2="12" y2="19"></line>
				<line x1="5" y1="12" x2="19" y2="12"></line>
			</svg>
			{{ __("Add Row") }}
		</button>

		<p v-if="df.description" class="control-description">{{ df.description }}</p>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{
				__("{0} is required and must be complete").replace("{0}", df?.label || __("Field"))
			}}
		</div>
	</div>
</template>

<style scoped>
.inline-table-control {
	margin-bottom: 20px;
	width: 100%;
}
.control-label {
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-semibold);
	margin-bottom: 8px;
	display: block;
	color: var(--fxr-text-strong);
}
.table-wrapper {
	margin-bottom: 12px;
	overflow-x: auto;
	width: 100%;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	background: var(--fxr-bg-card);
	box-shadow: var(--fxr-shadow-sm);
}
.table-custom {
	width: 100%;
	border-collapse: separate;
	border-spacing: 0;
	table-layout: fixed;
}
.table-custom th {
	font-size: var(--fxr-helper-font-size);
	font-weight: var(--fxr-weight-bold);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	white-space: nowrap;
	background: var(--fxr-surface-soft);
	color: var(--fxr-text-soft);
	border-bottom: 1px solid var(--fxr-border-subtle);
	padding: var(--spacing-sm) var(--spacing-md);
	text-align: left;
}
.table-custom td {
	padding: var(--spacing-xs) var(--spacing-md);
	vertical-align: middle;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-bg-card);
	color: var(--fxr-text);
}
.table-custom tr:last-child td {
	border-bottom: none;
}
.input-custom {
	font-size: var(--fxr-text-sm);
	width: 100%;
	height: var(--fxr-input-height);
	padding: 0 var(--spacing-md);
	border-radius: var(--fxr-radius-sm);
	border: 1px solid var(--fxr-border);
	background: var(--fxr-bg-input);
	color: var(--fxr-text);
	transition: var(--fxr-transition-fast);
}
.input-custom:focus {
	outline: none;
	border-color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-focus);
}
.input-custom:disabled {
	background: var(--fxr-bg-input-disabled);
	cursor: not-allowed;
	opacity: 0.7;
}
.table-cell-control :deep(.field-picker-control) {
	margin-bottom: 0;
}
.table-cell-control :deep(.control-label) {
	display: none;
}
.table-custom tbody tr:hover td {
	background: var(--fxr-bg-hover);
}
.remove-row-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 24px;
	height: 24px;
	border-radius: 50%;
	border: none;
	background: transparent;
	color: var(--fxr-text-soft);
	transition: var(--fxr-transition-fast);
	cursor: pointer;
}
.remove-row-btn:hover {
	background: var(--fxr-bg-danger);
	color: var(--fxr-text-danger);
}
.empty-state {
	text-align: center;
	padding: 32px !important;
	color: var(--fxr-text-soft);
	font-style: italic;
	font-size: var(--fxr-text-sm);
}
.add-row-btn {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 6px 12px;
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-medium);
	color: var(--fxr-text-strong);
	background: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	cursor: pointer;
	transition: var(--fxr-transition-fast);
	box-shadow: var(--fxr-shadow-sm);
}
.add-row-btn:hover {
	background: var(--fxr-bg-hover);
	border-color: var(--fxr-border-strong);
}
.control-description {
	margin-top: 8px;
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-soft);
}

@media (max-width: 768px) {
	.inline-table-control {
		margin-bottom: 16px;
	}

	.table-custom,
	.table-custom thead,
	.table-custom tbody,
	.table-custom th,
	.table-custom td,
	.table-custom tr {
		display: block;
		width: 100%;
	}

	.table-custom thead tr {
		position: absolute;
		top: -9999px;
		left: -9999px;
	}

	.table-custom tr {
		border: 1px solid var(--fxr-border-subtle);
		border-radius: var(--fxr-radius-md);
		margin-bottom: var(--spacing-lg);
		padding: var(--spacing-md);
		background: var(--fxr-surface-soft);
	}

	.table-custom td {
		border: none;
		border-bottom: 1px solid var(--fxr-border-subtle);
		position: relative;
		padding-left: 50% !important;
		padding-top: var(--spacing-sm) !important;
		padding-bottom: var(--spacing-sm) !important;
		min-height: 40px;
		display: flex;
		align-items: center;
		justify-content: flex-end;
		background: transparent;
	}

	.table-custom td:last-child {
		border-bottom: none;
		justify-content: center;
		padding-left: var(--spacing-md) !important;
	}

	.table-custom td:before {
		position: absolute;
		top: 50%;
		left: var(--spacing-md);
		width: 45%;
		padding-right: 10px;
		white-space: nowrap;
		transform: translateY(-50%);
		content: attr(data-label);
		font-size: var(--fxr-helper-font-size);
		font-weight: var(--fxr-weight-bold);
		color: var(--fxr-text-soft);
		text-transform: uppercase;
		text-align: left;
	}

	.table-custom td .input-custom,
	.table-custom td select,
	.table-custom td .table-cell-control {
		width: 100%;
		max-width: 200px;
	}
}
</style>
