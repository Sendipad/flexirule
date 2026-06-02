<template>
	<div class="flexi-grid fxr-card" :class="{ 'is-readonly': read_only }">
		<!-- Label -->
		<div v-if="df.label" class="grid-label px-4 pt-3 pb-1">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</div>

		<div v-if="df.reqd && !localRows.length" class="text-danger small px-4 mb-2">
			<i class="fa fa-exclamation-circle"></i> {{ __("{0} is mandatory", [df.label]) }}
		</div>

		<div class="grid-container">
			<div class="grid-table" :style="{ '--grid-cols': gridTemplateColumns }">
				<!-- HEADER -->
				<div class="grid-header">
					<div class="header-row">
						<div class="header-cell static-col">
							<input
								type="checkbox"
								:checked="isAllSelected"
								:indeterminate="isAnySelected && !isAllSelected"
								@change="toggleAll"
							/>
						</div>

						<div class="header-cell static-col">
							{{ __("#") }}
						</div>

						<div
							v-for="col in visibleColumns"
							:key="col.fieldname"
							class="header-cell"
							:class="{ 'sticky-col': col.sticky }"
							:style="stickyStyle(col)"
						>
							<span class="header-text">{{ __(col.label) }}</span>
							<div
								class="resize-handle"
								@mousedown="startResize($event, col.fieldname)"
							></div>
						</div>

						<div v-if="!read_only" class="header-cell static-col">
							<i class="fa fa-cog opacity-50"></i>
						</div>
					</div>
				</div>

				<!-- BODY -->
				<div class="grid-body">
					<div v-for="(row, rowIndex) in localRows" :key="row.name" class="grid-row">
						<div class="grid-cell static-col">
							<input
								type="checkbox"
								:checked="selectedRows.has(row.name)"
								@change="toggleRow(row.name)"
							/>
						</div>

						<div
							class="grid-cell static-col text-muted"
							:class="{ 'row-has-error': isRowInvalid(row) }"
						>
							<i
								v-if="isRowInvalid(row)"
								class="fa fa-exclamation-circle text-danger mr-1"
							></i>
							{{ rowIndex + 1 }}
						</div>

						<div
							v-for="col in visibleColumns"
							:key="col.fieldname"
							class="grid-cell"
							:class="{
								'sticky-col': col.sticky,
								'is-required': getCellState(row, col.fieldname).reqd,
								'has-error':
									getCellState(row, col.fieldname).reqd &&
									isValueEmpty(row[col.fieldname]),
							}"
							:style="stickyStyle(col)"
						>
							<ControlFactory
								v-if="!isCellHidden(row, col.fieldname)"
								:df="getEffectiveDf(row, col)"
								:modelValue="row[col.fieldname]"
								:doc="row"
								:engine="engine"
								hideLabel
								hideDescription
								class="grid-control-factory"
								@update:modelValue="updateCell(rowIndex, col.fieldname, $event)"
							/>
						</div>

						<div v-if="!read_only" class="grid-cell static-col actions-col">
							<button
								class="btn-icon-grid"
								:title="__('Move Up')"
								:disabled="rowIndex === 0"
								@click="moveRow(rowIndex, -1)"
							>
								<i class="fa fa-chevron-up"></i>
							</button>
							<button
								class="btn-icon-grid"
								:title="__('Move Down')"
								:disabled="rowIndex === localRows.length - 1"
								@click="moveRow(rowIndex, 1)"
							>
								<i class="fa fa-chevron-down"></i>
							</button>
							<button
								class="btn-icon-grid text-danger"
								:title="__('Remove Row')"
								@click="removeRow(rowIndex)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
					</div>

					<div v-if="!localRows.length" class="empty-state">
						<div class="empty-state-content">
							<i class="fa fa-table opacity-20 mb-2" style="font-size: 24px"></i>
							<p>{{ __("No rows added.") }}</p>
							<button v-if="!read_only" class="fxr-btn btn-xs mt-2" @click="addRow">
								<i class="fa fa-plus"></i> {{ __("Add first row") }}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div v-if="!read_only" class="grid-footer px-4 py-2 border-t">
			<div class="footer-actions">
				<button class="fxr-btn" @click="addRow">
					<i class="fa fa-plus"></i> {{ __("Add Row") }}
				</button>
				<button
					v-if="isAnySelected"
					class="fxr-btn text-danger ml-2"
					@click="removeSelectedRows"
				>
					<i class="fa fa-trash"></i> {{ __("Delete Selected") }} ({{
						selectedRows.size
					}})
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import ControlFactory from "./ControlFactory.vue";
import { useFieldNormalization } from "../composables/useFieldNormalization";

const props = defineProps({
	df: Object,
	modelValue: Array,
	engine: Object,
	read_only: Boolean,
});

const emit = defineEmits(["update:modelValue"]);

const localRows = ref([]);
const selectedRows = ref(new Set());
const columnWidths = reactive({});
const dynamicOptions = ref({});

/* ---------------- Columns ---------------- */

const columns = computed(() => props.df.fields || []);

const visibleColumns = computed(() =>
	columns.value.filter((c) => {
		if (c.hidden || c.in_list_view === 0) return false;
		if (["Section Break", "Column Break", "HTML"].includes(c.fieldtype)) return false;
		return true;
	})
);

/* ---------------- Grid Template ---------------- */

const gridTemplateColumns = computed(() => {
	const cols = ["40px", "40px"];
	visibleColumns.value.forEach((c) => {
		cols.push(getColumnWidth(c.fieldname));
	});
	if (!props.read_only) {
		cols.push("100px"); // Action buttons
	}
	return cols.join(" ");
});

function getColumnWidth(fieldname) {
	return columnWidths[fieldname] || "180px";
}

/* ---------------- Sticky ---------------- */

function stickyStyle(col) {
	if (!col.sticky) return {};
	let left = 80;
	for (const c of visibleColumns.value) {
		if (c.fieldname === col.fieldname) break;
		if (c.sticky) left += parseInt(getColumnWidth(c.fieldname));
	}
	return { left: left + "px" };
}

/* ---------------- Resize ---------------- */

let resizing = null;
let startX = 0;
let startW = 0;

function startResize(e, fieldname) {
	resizing = fieldname;
	startX = e.pageX;
	startW = parseInt(getColumnWidth(fieldname));
	document.addEventListener("mousemove", resize);
	document.addEventListener("mouseup", stopResize);
}

function resize(e) {
	if (!resizing) return;
	columnWidths[resizing] = Math.max(80, startW + e.pageX - startX) + "px";
}

function stopResize() {
	resizing = null;
	document.removeEventListener("mousemove", resize);
	document.removeEventListener("mouseup", stopResize);
}

/* ---------------- Row Context & Dynamic Options ---------------- */

function createRowContext(rowIndex, rowData) {
	return {
		update_field: (fieldname, value) => {
			updateCell(rowIndex, fieldname, value);
		},
		refresh_field: (fieldname) => {
			resolveFieldOptions(rowIndex, rowData, fieldname);
		},
		set_options: (fieldname, opts) => {
			const key = `${rowData.name}-${fieldname}`;
			dynamicOptions.value = { ...dynamicOptions.value, [key]: opts };
		},
		get_value: (fieldname) => rowData[fieldname],
		get_row_values: () => rowData,
		row_idx: rowIndex,
	};
}

async function resolveFieldOptions(rowIndex, rowData, fieldname) {
	const col = columns.value.find((c) => c.fieldname === fieldname);
	if (!col?.get_options || typeof col.get_options !== "function") return;

	const key = `${rowData.name}-${fieldname}`;
	try {
		const meta = props.engine?.doc_meta || {
			name: props.engine?.document_type || props.engine?.rule_doc?.document_type,
		};
		const ctx = createRowContext(rowIndex, rowData);
		const result = await col.get_options(rowData, ctx, meta);
		dynamicOptions.value = { ...dynamicOptions.value, [key]: result };
	} catch (e) {
		console.error("FlexiGrid: get_options failed for", fieldname, e);
	}
}

async function initializeRowOptions(rowIndex, rowData) {
	for (const col of columns.value) {
		if (col.get_options && typeof col.get_options === "function") {
			await resolveFieldOptions(rowIndex, rowData, col.fieldname);
		}
	}
}

/* ---------------- Data Sync ---------------- */

watch(
	() => props.modelValue,
	(val) => {
		localRows.value = (val || []).map((r) => ({
			...r,
			name: r.name || frappe.utils.get_random(10),
		}));
		localRows.value.forEach((row, idx) => {
			initializeRowOptions(idx, row);
		});
	},
	{ immediate: true }
);

function updateCell(idx, field, value) {
	const row = localRows.value[idx];
	row[field] = value;
	emit("update:modelValue", [...localRows.value]);

	if (props.engine && props.engine.handleFieldChange) {
		row.__table_fieldname = props.df.fieldname;
		props.engine.handleFieldChange(field, value, row);
	}

	const col = columns.value.find((c) => c.fieldname === field);
	if (col?.onchange && typeof col.onchange === "function") {
		const ctx = createRowContext(idx, row);
		col.onchange(value, row, ctx);
	}

	columns.value.forEach((depCol) => {
		if (
			depCol.fieldname !== field &&
			depCol.get_options &&
			typeof depCol.get_options === "function"
		) {
			resolveFieldOptions(idx, row, depCol.fieldname);
		}
	});
}

/* ---------------- Helpers ---------------- */

async function addRow() {
	const newRow = {
		name: frappe.utils.get_random(10),
		__table_fieldname: props.df.fieldname,
	};

	columns.value.forEach((col) => {
		if (col.default !== undefined) {
			newRow[col.fieldname] = col.default;
		}
	});

	localRows.value.push(newRow);
	emit("update:modelValue", [...localRows.value]);

	await initializeRowOptions(localRows.value.length - 1, newRow);

	if (props.engine && props.engine.evaluate_dependencies) {
		await props.engine.evaluate_dependencies(
			props.engine.config,
			newRow,
			props.df.fieldname,
			props.df.fields
		);
	}
}

function toggleRow(name) {
	selectedRows.value.has(name) ? selectedRows.value.delete(name) : selectedRows.value.add(name);
}

const isAllSelected = computed(
	() => localRows.value.length && selectedRows.value.size === localRows.value.length
);
const isAnySelected = computed(() => selectedRows.value.size);

function toggleAll() {
	isAllSelected.value
		? selectedRows.value.clear()
		: localRows.value.forEach((r) => selectedRows.value.add(r.name));
}

function removeRow(idx) {
	localRows.value.splice(idx, 1);
	emit("update:modelValue", [...localRows.value]);
}

function removeSelectedRows() {
	localRows.value = localRows.value.filter((r) => !selectedRows.value.has(r.name));
	selectedRows.value.clear();
	emit("update:modelValue", [...localRows.value]);
}

function moveRow(idx, direction) {
	const newIdx = idx + direction;
	if (newIdx < 0 || newIdx >= localRows.value.length) return;
	const row = localRows.value.splice(idx, 1)[0];
	localRows.value.splice(newIdx, 0, row);
	emit("update:modelValue", [...localRows.value]);
}

const { getNormalizedDf, getFieldState } = useFieldNormalization(props.engine);

function getCellState(row, field) {
	return getFieldState({ fieldname: field }, row.name);
}

function isCellHidden(row, field) {
	return getCellState(row, field).hidden;
}

function getEffectiveDf(row, col) {
	const normalized = getNormalizedDf(col, row.name, props.read_only);
	const key = `${row.name}-${col.fieldname}`;
	const dynOpts = dynamicOptions.value[key];
	if (dynOpts !== undefined) {
		return { ...normalized, options: dynOpts };
	}
	return normalized;
}

function isRowInvalid(row) {
	return visibleColumns.value.some((col) => {
		const state = getCellState(row, col.fieldname);
		return state.reqd && isValueEmpty(row[col.fieldname]);
	});
}

function isValueEmpty(val) {
	return val === undefined || val === null || val === "";
}
</script>

<style scoped>
.flexi-grid {
	width: 100%;
	margin-bottom: 24px;
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	background: var(--fr-bg-surface);
	overflow: hidden;
}

.grid-label {
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--fr-text-muted);
}

.grid-container {
	overflow-x: auto;
	position: relative;
}

.grid-table {
	display: block;
	width: max-content;
	min-width: 100%;
}

.header-row,
.grid-row {
	display: grid;
	grid-template-columns: var(--grid-cols);
}

.header-cell,
.grid-cell {
	height: 40px;
	display: flex;
	align-items: center;
	padding: 0 10px;
	border-right: 1px solid var(--fr-border-subtle);
	box-sizing: border-box;
	min-width: 0;
}

.grid-cell {
	border-bottom: 1px solid var(--fr-border-subtle);
}

.grid-row:last-child .grid-cell {
	border-bottom: none;
}

.header-cell {
	font-size: 11px;
	font-weight: 600;
	color: var(--fr-text-secondary);
	background: var(--fr-bg-muted);
	border-bottom: 1px solid var(--fr-border);
	white-space: nowrap;
}

.header-text {
	overflow: hidden;
	text-overflow: ellipsis;
}

.grid-row:hover {
	background: var(--fr-bg-surface-hover);
}

.static-col {
	justify-content: center;
	background: var(--fr-bg-muted);
	font-size: 11px;
	color: var(--fr-text-muted);
}

.sticky-col {
	position: sticky;
	z-index: 20;
	background: inherit;
}

.resize-handle {
	position: absolute;
	right: -3px;
	top: 0;
	bottom: 0;
	width: 6px;
	cursor: col-resize;
	z-index: 10;
}

.resize-handle:hover {
	background: var(--fr-primary);
	opacity: 0.3;
}

/* Control Normalization */
.grid-control-factory {
	width: 100%;
}

:deep(.fxr-control) {
	margin-bottom: 0 !important;
	width: 100%;
}

:deep(.form-control),
:deep(.fxr-input),
:deep(.fxr-select),
:deep(.combobox-wrapper) {
	border-color: transparent !important;
	background: transparent !important;
	box-shadow: none !important;
	height: 32px !important;
	padding: 0 8px !important;
}

:deep(.form-control:focus),
:deep(.fxr-input:focus),
:deep(.fxr-select:focus),
:deep(.combobox-wrapper.is-focused) {
	background: var(--fr-bg-surface) !important;
	border-color: var(--fr-primary) !important;
	box-shadow: 0 0 0 2px var(--fr-primary-subtle) !important;
}

.actions-col {
	justify-content: center;
	gap: 4px;
}

.btn-icon-grid {
	width: 24px;
	height: 24px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border-radius: 4px;
	border: none;
	background: transparent;
	color: var(--fr-text-muted);
	cursor: pointer;
	transition: all 0.15s;
}

.btn-icon-grid:hover:not(:disabled) {
	background: var(--fr-gray-200);
	color: var(--fr-text);
}

.btn-icon-grid:disabled {
	opacity: 0.2;
	cursor: not-allowed;
}

.is-required::before {
	content: "";
	position: absolute;
	left: 0;
	top: 0;
	bottom: 0;
	width: 2px;
	background: var(--fr-danger);
}

.has-error {
	background: rgba(239, 68, 68, 0.05);
}

.empty-state {
	padding: 40px;
	text-align: center;
	background: var(--fr-bg-surface);
	color: var(--fr-text-muted);
	font-size: 13px;
}

.grid-footer {
	background: var(--fr-bg-muted);
}

.border-t {
	border-top: 1px solid var(--fr-border);
}

.grid-container::-webkit-scrollbar {
	height: 8px;
}
.grid-container::-webkit-scrollbar-thumb {
	background: var(--fr-gray-300);
	border-radius: 4px;
}
</style>
