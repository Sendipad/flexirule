<template>
	<div class="flexi-grid" :class="{ 'is-readonly': read_only }">
		<!-- Label -->
		<div v-if="df.label" class="grid-label">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</div>

		<div v-if="df.reqd && !localRows.length" class="text-danger small mb-2">
			<i class="fa fa-exclamation-circle" /> {{ __("{0} is mandatory", [df.label]) }}
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
							>
						</div>

						<div class="header-cell static-col">
							{{ __("No") }}
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
							/>
						</div>

						<div v-if="!read_only" class="header-cell static-col">
							<i class="fa fa-cog text-muted" />
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
							>
						</div>

						<div
							class="grid-cell static-col text-muted"
							:class="{ 'row-has-error': isRowInvalid(row) }"
						>
							<i
								v-if="isRowInvalid(row)"
								class="fa fa-exclamation-circle text-danger mr-1"
							/>
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
								:model-value="row[col.fieldname]"
								:doc="row"
								:engine="engine"
								hide-label
								hide-description
								@update:model-value="updateCell(rowIndex, col.fieldname, $event)"
								@click="$emit('cell-click', { row, rowIndex, col, fieldname: col.fieldname, event: $event })"
							/>
						</div>

						<div v-if="!read_only" class="grid-cell static-col actions-col">
							<button
								class="btn btn-xs btn-link text-muted p-0"
								:title="__('Move Up')"
								:disabled="rowIndex === 0"
								@click="moveRow(rowIndex, -1)"
							>
								<i class="fa fa-chevron-up" />
							</button>
							<button
								class="btn btn-xs btn-link text-muted p-0 ml-1"
								:title="__('Move Down')"
								:disabled="rowIndex === localRows.length - 1"
								@click="moveRow(rowIndex, 1)"
							>
								<i class="fa fa-chevron-down" />
							</button>
							<button
								class="btn btn-xs btn-link text-danger p-0 ml-2"
								:title="__('Remove Row')"
								@click="removeRow(rowIndex)"
							>
								<i class="fa fa-trash" />
							</button>
						</div>
					</div>

					<div v-if="!localRows.length" class="empty-state">
						{{ __("No rows added.") }}
					</div>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div v-if="!read_only" class="grid-footer">
			<div class="footer-actions">
				<button class="btn btn-xs btn-default" @click="addRow">
					<i class="fa fa-plus" /> {{ __("Add Row") }}
				</button>
				<button
					v-if="isAnySelected"
					class="btn btn-xs btn-danger-light ml-2"
					@click="removeSelectedRows"
				>
					<i class="fa fa-trash" /> {{ __("Delete Selected") }} ({{
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

const emit = defineEmits(["update:modelValue", "cell-click"]);

const localRows = ref([]);
const selectedRows = ref(new Set());
const columnWidths = reactive({});

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
		cols.push("80px"); // Wider for action buttons
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

/* ---------------- Data Sync ---------------- */

watch(
	() => props.modelValue,
	(val) => {
		const incoming = val || [];

		// Efficiently sync localRows while preserving object identities for matching 'name'
		const currentMap = new Map(localRows.value.map((r) => [r.name, r]));

		localRows.value = incoming.map((r) => {
			const existing = r.name ? currentMap.get(r.name) : null;

			if (existing) {
				// Update existing row properties without breaking reference
				Object.keys(r).forEach((key) => {
					if (existing[key] !== r[key]) {
						existing[key] = r[key];
					}
				});
				return existing;
			}

			// New row or no stable name
			return {
				...r,
				name: r.name || frappe.utils.get_random(10),
			};
		});
	},
	{ immediate: true, deep: false }
);

function updateCell(idx, field, value) {
	const row = localRows.value[idx];
	row[field] = value;
	emit("update:modelValue", [...localRows.value]);

	// If engine is available, trigger logical change handling
	if (props.engine && props.engine.handleFieldChange) {
		row.__table_fieldname = props.df.fieldname;
		props.engine.handleFieldChange(field, value, row);
	}
}

/* ---------------- Helpers ---------------- */

async function addRow() {
	const newRow = {
		name: frappe.utils.get_random(10),
		__table_fieldname: props.df.fieldname,
	};

	// Apply Defaults
	columns.value.forEach((col) => {
		if (col.default !== undefined) {
			newRow[col.fieldname] = col.default;
		}
	});

	localRows.value.push(newRow);
	emit("update:modelValue", [...localRows.value]);

	// Trigger initial evaluation for this row
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
	return getNormalizedDf(col, row.name, props.read_only);
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

<style>
/* ============================================================
   FlexiGrid – Frappe-aligned Grid Styling
   ============================================================ */

.flexi-grid {
	width: 100%;
	margin-bottom: 24px;
	font-size: 13px;
	color: var(--text-color);
}

/* ---------- Label ---------- */

.flexi-grid .grid-label {
	font-size: 13px;
	font-weight: 600;
	margin-bottom: 8px;
}

/* ---------- Container ---------- */

.flexi-grid .grid-container {
	border: 1px solid var(--border-color, #d1d8dd);
	border-radius: 8px;
	background: #fff;
	overflow-x: auto;
	position: relative;
}

/* ---------- Table ---------- */

.flexi-grid .grid-table {
	display: block;
	width: max-content;
	min-width: 100%;
}

/* ---------- Header ---------- */

.flexi-grid .grid-header {
	position: sticky;
	top: 0;
	z-index: 100;
	background: #f8f9fa;
	border-bottom: 1px solid var(--border-color, #e5e7eb);
}

.flexi-grid .header-row {
	display: flex;
	height: 40px;
}

/* ---------- Rows ---------- */

.flexi-grid .grid-row {
	display: flex;
	height: 40px;
	border-bottom: 1px solid var(--border-color, #f0f0f0);
	background: #fff;
}

.flexi-grid .grid-row:hover {
	background: #fafafb;
}

.flexi-grid .grid-row:last-child {
	border-bottom: none;
}

/* ---------- Cells (CRITICAL) ---------- */

.flexi-grid .header-cell,
.flexi-grid .grid-cell {
	flex: 0 0 auto !important; /* NEVER grow or shrink */
	box-sizing: border-box;
	border-right: 1px solid var(--border-color, #f0f0f0);
	display: flex;
	align-items: center;
	height: 100%;
	padding: 0 8px; /* Frappe-style padding */
	position: relative;
	overflow: hidden;
}

.flexi-grid .header-cell:last-child,
.flexi-grid .grid-cell:last-child {
	border-right: none;
}

/* ---------- Header Cell ---------- */

.flexi-grid .header-cell {
	font-weight: 600;
	color: var(--text-color);
	background: #f8f9fa;
	z-index: 50;
}

.flexi-grid .header-text {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	width: 100%;
}

/* ---------- Static Columns ---------- */

.flexi-grid .static-col {
	justify-content: center;
	padding: 0;
	background: #fafafa;
}

/* ---------- Sticky Columns ---------- */

.flexi-grid .sticky-col {
	position: sticky;
	background: inherit;
	z-index: 40;
}

.flexi-grid .header-cell.sticky-col {
	z-index: 60;
	box-shadow: 2px 0 5px rgba(0, 0, 0, 0.04);
}

/* ---------- Resize Handle ---------- */

.flexi-grid .resize-handle {
	position: absolute;
	right: -3px;
	top: 0;
	bottom: 0;
	width: 6px;
	cursor: col-resize;
}

.flexi-grid .resize-handle:hover {
	background: var(--primary-color, #1071e5);
	opacity: 0.3;
}

/* ============================================================
   Frappe Control Normalization (IMPORTANT)
   ============================================================ */

.flexi-grid .grid-cell .control-factory,
.flexi-grid .grid-cell .frappe-control,
.flexi-grid .grid-cell .form-group {
	margin: 0 !important;
	padding: 0 !important;
	width: 100% !important;
}

/* Inputs must NOT fill height */
.flexi-grid .grid-cell .form-control {
	height: 28px !important; /* Frappe default */
	min-height: 28px !important;
	padding: 4px 8px !important;
	border-radius: 4px !important;
	border: 1px solid transparent !important;
	background: transparent !important;
	box-shadow: none !important;
	width: 100% !important;
	font-size: 13px;
}

/* Focus behavior */
.flexi-grid .grid-cell .form-control:focus {
	background: #fff !important;
	border-color: var(--fxr-accent) !important;
	box-shadow: none !important;
}

/* ComboBox in Grid */
.flexi-grid .grid-cell .combobox-wrapper {
	border-color: transparent !important;
	background: transparent !important;
	box-shadow: none !important;
	height: 32px !important;
}

.flexi-grid .grid-cell .combobox-wrapper:hover,
.flexi-grid .grid-cell .combobox-wrapper.is-focused {
	border-color: var(--fxr-accent) !important;
	background: #fff !important;
}

.flexi-grid .grid-cell .combobox-input-group {
	height: 100% !important;
}

.flexi-grid .grid-cell .combobox-input {
	height: 100% !important;
}

/* Selects */
.flexi-grid .grid-cell select.form-control {
	padding-right: 24px !important;
}

/* Textarea stays controlled */
.flexi-grid .grid-cell textarea.form-control {
	height: 28px !important;
	resize: none;
}

/* Checkbox alignment */
.flexi-grid .grid-cell .checkbox,
.flexi-grid .grid-cell input[type="checkbox"] {
	margin: 0;
	display: flex;
	align-items: center;
	justify-content: center;
}

/* Required indicator (Frappe-style left bar) */
.flexi-grid .grid-cell.is-required::before {
	content: "";
	position: absolute;
	left: 0;
	top: 0;
	bottom: 0;
	width: 3px;
	background: var(--red-500, #ef4444);
}

/* ---------- Z-index safety ---------- */

.flexi-grid .grid-row:focus-within {
	z-index: 90;
}

.flexi-grid .grid-cell.has-error {
	background-color: #fff8f8;
}

.flexi-grid .grid-cell.has-error .form-control {
	border-color: var(--red-500, #ef4444) !important;
}

.flexi-grid .actions-col {
	justify-content: flex-end;
	padding-right: 12px;
	gap: 4px;
}

.flexi-grid .actions-col .btn-link {
	text-decoration: none;
	opacity: 0.6;
	transition: opacity 0.2s;
}

.flexi-grid .actions-col .btn-link:hover:not(:disabled) {
	opacity: 1;
}

.flexi-grid .actions-col .btn-link:disabled {
	opacity: 0.2;
	cursor: not-allowed;
}

.flexi-grid .row-has-error {
	color: var(--red-500, #ef4444) !important;
	font-weight: bold;
}

/* ---------- Footer ---------- */

.flexi-grid .grid-footer {
	padding: 12px 0;
	display: flex;
	align-items: center;
}

.flexi-grid .footer-actions {
	display: flex;
	align-items: center;
	gap: 8px;
}

.flexi-grid .btn-danger-light {
	background: #fff5f5;
	color: #e53e3e;
	border: 1px solid #feb2b2;
}

.flexi-grid .btn-danger-light:hover {
	background: #fed7d7;
	border-color: #fc8181;
}

/* ---------- Empty State ---------- */

.flexi-grid .empty-state {
	padding: 48px;
	text-align: center;
	color: var(--text-muted);
	background: #fcfcfc;
}

/* ---------- Readonly ---------- */

.flexi-grid.is-readonly {
	pointer-events: none;
	opacity: 0.75;
}

/* ============================================================
   Scrollbar
   ============================================================ */

.flexi-grid .grid-container::-webkit-scrollbar {
	height: 10px;
}

.flexi-grid .grid-container::-webkit-scrollbar-thumb {
	background: #e5e7eb;
	border-radius: 5px;
}

.flexi-grid .grid-container::-webkit-scrollbar-thumb:hover {
	background: #d1d5db;
}
.flexi-grid .header-row,
.flexi-grid .grid-row {
	display: grid;
	grid-template-columns: var(--grid-cols);
}

.header-cell,
.grid-cell {
	height: 40px;
	display: flex;
	align-items: center;
	padding: 0 8px;
	border-right: 1px solid #e5e7eb;
	box-sizing: border-box;
}

.header-cell {
	font-weight: 600;
	background: #f8f9fa;
}

.grid-row:hover {
	background: #fafafb;
}

.static-col {
	justify-content: center;
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
}
</style>
