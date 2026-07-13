<template>
	<div
		class="resource-mapper-control fxr-control fxr-accent-scope"
		:class="{ 'has-error': showValidation && !isValid }"
		v-fxr-fieldname="df?.fieldname || fieldname || null"
	>
		<div v-if="df?.label && !hideLabel" class="fxr-label" :class="{ reqd: df?.reqd }">
			{{ __(df.label) }}
		</div>

		<!-- Mode & Options Bar -->
		<div class="rm-options-bar">
			<div class="rm-option-group">
				<label class="rm-check">
					<input type="checkbox" v-model="ui.copy_same_fields" :disabled="readOnly" />
					<span class="rm-label-sm">{{ __("Auto-copy matching fields") }}</span>
				</label>
			</div>
			<div class="rm-option-group">
				<label class="rm-label-sm">{{ __("Source") }}</label>
				<ComboBoxControl
					:df="{ fieldtype: 'Autocomplete', label: '' }"
					:options="sourceOptionsNormalized"
					:modelValue="ui.source_path"
					:read_only="readOnly"
					:hideLabel="true"
					@update:modelValue="(val) => (ui.source_path = val || 'doc')"
				/>
			</div>
			<div class="rm-option-group">
				<label class="rm-check">
					<input type="checkbox" v-model="ui.save_document" :disabled="readOnly" />
					<span class="rm-label-sm">{{ __("Save Document") }}</span>
				</label>
			</div>
			<button
				v-if="!readOnly"
				class="fxr-btn fxr-btn--primary fxr-btn--magic"
				@click="previewScalarAutoMap"
			>
				<i class="fa fa-magic"></i> {{ __("Auto-map") }}
			</button>
		</div>

		<!-- Exclude Fields (when copy_same_fields) -->
		<div v-if="ui.copy_same_fields" class="rm-exclude-section">
			<label class="rm-label-sm">{{ __("Exclude Fields") }}</label>
			<div class="rm-exclude-row">
				<select class="fxr-select" v-model="pendingExcludeField" :disabled="readOnly">
					<option value="">{{ __("Select field…") }}</option>
					<option
						v-for="f in scalarTargetOptions"
						:key="`exclude-${f.value}`"
						:value="f.value"
					>
						{{ f.label || f.value }}
					</option>
				</select>
				<button v-if="!readOnly" class="fxr-btn fxr-btn--sm" @click="addExcludedField">
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
			<div class="rm-preview-title" style="justify-content: space-between">
				<div style="display: flex; align-items: center; gap: 6px">
					<input
						type="checkbox"
						:checked="selectedPreviews.size === scalarAutoMapPreview.length"
						@change="toggleAllPreviews"
					/>
					{{ __("Auto-map Preview") }}
					<span class="rm-badge">{{ scalarAutoMapPreview.length }}</span>
				</div>
				<button
					v-if="selectedPreviews.size > 0"
					class="fxr-btn fxr-btn--danger fxr-btn--sm"
					@click="deleteSelectedPreviews"
				>
					<i class="fa fa-trash"></i>
					{{ __("Delete ({0})").replace("{0}", selectedPreviews.size) }}
				</button>
			</div>
			<div class="rm-preview-list">
				<div
					v-for="(row, idx) in scalarAutoMapPreview"
					:key="`preview-${idx}`"
					class="rm-preview-row rm-mapping-row"
					style="grid-template-columns: auto 1fr auto 1.6fr auto; padding: 4px 6px"
				>
					<div class="rm-cell rm-cell-check">
						<input
							type="checkbox"
							:checked="selectedPreviews.has(idx)"
							@change="toggleSelectPreview(idx)"
						/>
					</div>
					<div
						class="rm-cell rm-cell-target"
						style="display: flex; align-items: center; gap: 4px"
					>
						<code class="rm-target">{{ row.target }}</code>
						<span
							v-if="row.is_readonly"
							class="indicator-pill orange"
							style="font-size: 10px; padding: 2px 6px"
							>{{ __("Read Only") }}</span
						>
						<span
							v-if="row.no_copy"
							class="indicator-pill blue"
							style="font-size: 10px; padding: 2px 6px"
							>{{ __("No Copy") }}</span
						>
					</div>
					<div class="rm-cell rm-cell-arrow">
						<i class="fa fa-long-arrow-left rm-arrow"></i>
					</div>
					<div class="rm-cell rm-cell-source">
						<ComboBoxControl
							:df="{ label: '', fieldtype: 'FieldPicker' }"
							:options="scalarSourceOptions"
							:modelValue="row.path"
							:read_only="readOnly"
							:trigger="'button'"
							:hideLabel="true"
							:showValidation="showValidation"
							@update:modelValue="(val) => (row.path = val || '')"
						/>
					</div>
					<div class="rm-cell rm-cell-action">
						<button
							class="fxr-btn fxr-btn--icon fxr-btn--danger"
							@click="scalarAutoMapPreview.splice(idx, 1)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>
			<div class="rm-preview-footer">
				<button class="fxr-btn fxr-btn--primary" @click="applyScalarAutoMap">
					{{ __("Apply Mappings") }}
				</button>
				<button class="fxr-btn" @click="cancelScalarAutoMap">
					{{ __("Cancel") }}
				</button>
			</div>
		</div>

		<!-- ═══ Scalar Field Mappings ═══ -->
		<div class="rm-section">
			<div class="rm-section-header">
				<div style="display: flex; align-items: center; gap: 8px">
					<input
						v-if="filteredScalars.length > 0"
						type="checkbox"
						:checked="
							selectedScalars.size >= pagedScalars.length && pagedScalars.length > 0
						"
						@change="toggleAllScalars"
					/>
					<h6><i class="fa fa-columns"></i> {{ __("Field Mappings") }}</h6>
					<button
						v-if="selectedScalars.size > 0"
						class="fxr-btn fxr-btn--danger fxr-btn--sm"
						@click="deleteSelectedScalars"
					>
						<i class="fa fa-trash"></i>
						{{ __("Delete ({0})").replace("{0}", selectedScalars.size) }}
					</button>
				</div>
				<div class="rm-header-actions" style="display: flex; gap: 8px; align-items: center">
					<input
						type="text"
						class="fxr-input"
						v-model="scalarSearch"
						:placeholder="__('Search fields...')"
					/>
				</div>
			</div>

			<div v-if="!filteredScalars.length" class="rm-empty">
				{{ __("No field mappings found. Click + Add Field or use Auto-map.") }}
			</div>

			<div
				v-for="(row, idx) in pagedScalars"
				:key="`scalar-${row._id || idx}`"
				class="rm-mapping-row"
				style="grid-template-columns: auto 1.4fr auto 0.7fr 1.6fr auto"
			>
				<div class="rm-cell rm-cell-check">
					<input
						type="checkbox"
						:checked="selectedScalars.has(row._id)"
						@change="toggleSelectScalar(row._id)"
					/>
				</div>
				<!-- Target -->
				<div class="rm-cell rm-cell-target">
					<ComboBoxControl
						:df="{ label: '', fieldtype: 'FieldPicker' }"
						:options="scalarTargetOptions"
						:doctype="targetDoctype"
						:modelValue="row.target"
						:read_only="readOnly"
						:trigger="'button'"
						:hideLabel="true"
						:showValidation="showValidation"
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
						class="fxr-select"
						v-model="row.source_type"
						:disabled="readOnly"
						:class="{ 'has-error': showValidation && !row.source_type }"
					>
						<option value="path">{{ __("Path") }}</option>
						<option value="expr">{{ __("Expr") }}</option>
						<option value="literal">{{ __("Static") }}</option>
					</select>
				</div>

				<!-- Source Value -->
				<div class="rm-cell rm-cell-source">
					<ComboBoxControl
						v-if="row.source_type === 'path'"
						:df="{ fieldtype: 'Autocomplete', label: '' }"
						:options="scalarSourceOptions"
						:modelValue="row.path"
						:read_only="readOnly"
						:hideLabel="true"
						:showValidation="showValidation"
						@update:modelValue="(val) => (row.path = val || '')"
					/>
					<input
						v-else-if="row.source_type === 'expr'"
						class="fxr-input"
						v-model="row.expr"
						:placeholder="__('Expression')"
						:disabled="readOnly"
					/>
					<input
						v-else
						class="fxr-input"
						v-model="row.literal"
						:placeholder="__('Static value')"
						:disabled="readOnly"
					/>
				</div>

				<!-- Delete -->
				<div class="rm-cell rm-cell-action">
					<button
						v-if="!readOnly"
						class="fxr-btn fxr-btn--icon fxr-btn--danger"
						@click="removeScalarRow(row)"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
			</div>

			<div class="rm-section-footer">
				<button v-if="!readOnly" class="fxr-btn fxr-btn--sm" @click="addScalarRow">
					<i class="fa fa-plus"></i> {{ __("Add Field") }}
				</button>
				<div class="rm-pagination" v-if="filteredScalars.length > 10">
					<button
						class="fxr-btn fxr-btn--sm"
						:class="{ active: scalarLimit === 10 }"
						@click="scalarLimit = 10"
					>
						10
					</button>
					<button
						class="fxr-btn fxr-btn--sm"
						:class="{ active: scalarLimit === 20 }"
						@click="scalarLimit = 20"
					>
						20
					</button>
					<button
						class="fxr-btn fxr-btn--sm"
						:class="{ active: scalarLimit === Infinity }"
						@click="scalarLimit = Infinity"
					>
						{{ __("All") }}
					</button>
					<span class="rm-label-sm" style="margin-left: 8px"
						>Showing {{ pagedScalars.length }} of {{ filteredScalars.length }}</span
					>
				</div>
			</div>
		</div>

		<!-- ═══ Child Table Mappings ═══ -->
		<div class="rm-section">
			<div class="rm-section-header">
				<div style="display: flex; align-items: center; gap: 8px">
					<input
						v-if="ui.tables.length > 0"
						type="checkbox"
						:checked="selectedTables.size === ui.tables.length && ui.tables.length > 0"
						@change="toggleAllTables"
					/>
					<h6><i class="fa fa-table"></i> {{ __("Child Table Mappings") }}</h6>
					<button
						v-if="selectedTables.size > 0"
						class="fxr-btn fxr-btn--danger fxr-btn--sm"
						@click="deleteSelectedTables"
					>
						<i class="fa fa-trash"></i>
						{{ __("Delete ({0})").replace("{0}", selectedTables.size) }}
					</button>
				</div>
				<button v-if="!readOnly" class="fxr-btn fxr-btn--sm" @click="addTableMap">
					<i class="fa fa-plus"></i> {{ __("Add Table") }}
				</button>
			</div>

			<div v-if="!ui.tables.length" class="rm-empty">
				{{ __("No child table mappings configured.") }}
			</div>

			<div v-for="(table, tIdx) in ui.tables" :key="`tbl-${tIdx}`" class="rm-table-card">
				<div class="rm-table-header">
					<div class="rm-table-header-fields">
						<input
							type="checkbox"
							:checked="selectedTables.has(tIdx)"
							@change="toggleSelectTable(tIdx)"
							style="margin-top: 5px"
						/>
						<select
							class="fxr-select"
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
							class="fxr-input"
							v-model="table.source_path"
							:placeholder="__('Source path (e.g. doc.items)')"
							:disabled="readOnly"
						/>

						<input
							class="fxr-input rm-alias-input"
							v-model="table.item_alias"
							:placeholder="__('Alias')"
							:disabled="readOnly"
						/>
					</div>

					<div class="rm-table-header-actions">
						<button
							v-if="!readOnly"
							class="fxr-btn fxr-btn--sm"
							@click="previewTableAutoMap(table, tIdx)"
						>
							{{ __("Auto-map") }}
						</button>
						<button
							v-if="!readOnly"
							class="fxr-btn fxr-btn--icon fxr-btn--danger"
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
							class="rm-preview-row rm-mapping-row"
							style="grid-template-columns: 1fr auto 1.6fr auto; padding: 4px 0"
						>
							<div
								class="rm-cell rm-cell-target"
								style="display: flex; align-items: center; gap: 4px"
							>
								<code class="rm-target">{{ row.target }}</code>
								<span
									v-if="row.is_readonly"
									class="indicator-pill orange"
									style="font-size: 10px; padding: 2px 6px"
									>{{ __("Read Only") }}</span
								>
								<span
									v-if="row.no_copy"
									class="indicator-pill blue"
									style="font-size: 10px; padding: 2px 6px"
									>{{ __("No Copy") }}</span
								>
							</div>
							<div class="rm-cell rm-cell-arrow">
								<i class="fa fa-long-arrow-left rm-arrow"></i>
							</div>
							<div class="rm-cell rm-cell-source">
								<ComboBoxControl
									:df="{ label: '', fieldtype: 'FieldPicker' }"
									:options="getTableRowSourceOptions(table)"
									:modelValue="row.path"
									:read_only="readOnly"
									:trigger="'button'"
									:hideLabel="true"
									:showValidation="showValidation"
									@update:modelValue="(val) => (row.path = val || '')"
								/>
							</div>
							<div class="rm-cell rm-cell-action">
								<button
									class="fxr-btn fxr-btn--icon fxr-btn--danger"
									@click="tableAutoMapPreview[tIdx].splice(pIdx, 1)"
								>
									<i class="fa fa-trash"></i>
								</button>
							</div>
						</div>
					</div>
					<div class="rm-preview-footer">
						<button
							class="fxr-btn fxr-btn--primary"
							@click="applyTableAutoMap(table, tIdx)"
						>
							{{ __("Apply Mappings") }}
						</button>
						<button class="fxr-btn" @click="cancelTableAutoMap(tIdx)">
							{{ __("Cancel") }}
						</button>
					</div>
				</div>

				<!-- Table Options -->
				<div class="rm-table-options">
					<label class="rm-check">
						<input type="checkbox" v-model="table.reset_value" :disabled="readOnly" />
						<span class="rm-label-sm">{{ __("Replace existing rows") }}</span>
					</label>
					<label class="rm-check">
						<input type="checkbox" v-model="table.add_if_empty" :disabled="readOnly" />
						<span class="rm-label-sm">{{ __("Only if empty") }}</span>
					</label>
					<input
						class="fxr-input"
						v-model="table.condition"
						:placeholder="__('Include condition (e.g. item.qty > 0)')"
						:disabled="readOnly"
					/>
					<input
						class="fxr-input"
						v-model="table.filter"
						:placeholder="__('Skip filter (e.g. item.disabled == 1)')"
						:disabled="readOnly"
					/>
				</div>

				<!-- Row Mappings -->
				<div class="rm-table-rows">
					<div class="rm-section-header rm-section-header-sm">
						<div style="display: flex; align-items: center; gap: 6px">
							<input
								v-if="getFilteredTableRows(table, tIdx).length > 0"
								type="checkbox"
								:checked="
									selectedTableRows[tIdx]?.size >=
										getPagedTableRows(table, tIdx).length &&
									getPagedTableRows(table, tIdx).length > 0
								"
								@change="toggleAllTableRows(tIdx, table)"
							/>
							<span class="rm-label-sm">{{ __("Row Field Mapping") }}</span>
							<button
								v-if="selectedTableRows[tIdx]?.size > 0"
								class="fxr-btn fxr-btn--danger fxr-btn--sm"
								@click="deleteSelectedTableRows(tIdx, table)"
							>
								<i class="fa fa-trash"></i>
								{{
									__("Delete ({0})").replace("{0}", selectedTableRows[tIdx].size)
								}}
							</button>
						</div>
						<div
							class="rm-header-actions"
							style="display: flex; gap: 8px; align-items: center"
						>
							<input
								type="text"
								class="fxr-input"
								v-model="getTableState(tIdx).search"
								:placeholder="__('Search...')"
							/>
						</div>
					</div>

					<div
						v-if="!getFilteredTableRows(table, tIdx).length"
						class="rm-empty rm-empty-sm"
					>
						{{ __("No row mappings found.") }}
					</div>

					<div
						v-for="(row, rIdx) in getPagedTableRows(table, tIdx)"
						:key="`tbl-row-${tIdx}-${row._id || rIdx}`"
						class="rm-mapping-row"
						style="grid-template-columns: auto 1.4fr auto 0.7fr 1.6fr auto"
					>
						<div class="rm-cell rm-cell-check">
							<input
								type="checkbox"
								:checked="selectedTableRows[tIdx]?.has(row._id)"
								@change="toggleSelectTableRow(tIdx, row._id)"
							/>
						</div>
						<div class="rm-cell rm-cell-target">
							<select class="fxr-select" v-model="row.target" :disabled="readOnly">
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
								class="fxr-select"
								v-model="row.source_type"
								:disabled="readOnly"
							>
								<option value="path">{{ __("Path") }}</option>
								<option value="expr">{{ __("Expr") }}</option>
								<option value="literal">{{ __("Static") }}</option>
							</select>
						</div>

						<div class="rm-cell rm-cell-source">
							<ComboBoxControl
								v-if="row.source_type === 'path'"
								:df="{ fieldtype: 'Autocomplete', label: '' }"
								:options="getTableRowSourceOptions(table)"
								:modelValue="row.path"
								:read_only="readOnly"
								:hideLabel="true"
								:showValidation="showValidation"
								@update:modelValue="(val) => (row.path = val || '')"
							/>
							<input
								v-else-if="row.source_type === 'expr'"
								class="fxr-input"
								v-model="row.expr"
								:placeholder="__('Expression')"
								:disabled="readOnly"
							/>
							<input
								v-else
								class="fxr-input"
								v-model="row.literal"
								:placeholder="__('Static value')"
								:disabled="readOnly"
							/>
						</div>

						<div class="rm-cell rm-cell-action">
							<button
								v-if="!readOnly"
								class="fxr-btn fxr-btn--icon fxr-btn--danger"
								@click="removeTableRowByRow(table, row)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
					</div>

					<div class="rm-section-footer">
						<button
							v-if="!readOnly"
							class="fxr-btn fxr-btn--sm"
							@click="addTableRow(table)"
						>
							<i class="fa fa-plus"></i> {{ __("Add Field") }}
						</button>
						<div
							class="rm-pagination"
							v-if="getFilteredTableRows(table, tIdx).length > 10"
						>
							<button
								class="fxr-btn fxr-btn--sm"
								:class="{ active: getTableState(tIdx).limit === 10 }"
								@click="getTableState(tIdx).limit = 10"
							>
								10
							</button>
							<button
								class="fxr-btn fxr-btn--sm"
								:class="{ active: getTableState(tIdx).limit === 20 }"
								@click="getTableState(tIdx).limit = 20"
							>
								20
							</button>
							<button
								class="fxr-btn fxr-btn--sm"
								:class="{ active: getTableState(tIdx).limit === Infinity }"
								@click="getTableState(tIdx).limit = Infinity"
							>
								{{ __("All") }}
							</button>
							<span class="rm-label-sm" style="margin-left: 8px"
								>Showing {{ getPagedTableRows(table, tIdx).length }} of
								{{ getFilteredTableRows(table, tIdx).length }}</span
							>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("Resource Mapper configuration is incomplete") }}
		</div>

		<div v-if="df?.description && !hideDescription" class="fxr-description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { deepClone } from "../utils/serialization";
import ComboBoxControl from "./ComboBoxControl.vue";

const props = defineProps({
	df: { type: Object, default: null },
	fieldname: String,
	modelValue: { type: [Object, String], default: null },
	targetDoctype: { type: String, default: "" },
	targetFields: { type: Array, default: () => [] },
	sourceOptions: { type: Array, default: () => [] },
	read_only: { type: Boolean, default: false },
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const readOnly = computed(() => !!props.read_only || !!props.df?.read_only);
const targetDoctype = computed(() => props.targetDoctype || props.df?.targetDoctype || "");

const ui = ref({
	version: 2,
	mode: "field_mappings",
	source_path: "doc",
	copy_same_fields: false,
	save_document: true,
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

let idCounter = 0;
function generateId() {
	return `rm_${Date.now()}_${idCounter++}`;
}

function makeScalar() {
	return {
		_id: generateId(),
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
			save_document: val.save_document !== false,
			field_no_map: Array.isArray(val.field_no_map) ? val.field_no_map.filter(Boolean) : [],
			scalars: Array.isArray(val.scalars)
				? val.scalars
						.filter((s) => s && s.target && !String(s.target).includes("."))
						.map((s) => ({ ...s, _id: s._id || generateId() }))
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
						mappings: Array.isArray(table?.mappings)
							? table.mappings.map((m) => ({ ...m, _id: m._id || generateId() }))
							: [],
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
		save_document: true,
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

const scalarSearch = ref("");
const scalarLimit = ref(10);

const filteredScalars = computed(() => {
	if (!scalarSearch.value) return ui.value.scalars;
	const q = scalarSearch.value.toLowerCase();
	return ui.value.scalars.filter(
		(row) =>
			(row.target || "").toLowerCase().includes(q) ||
			(row.path || "").toLowerCase().includes(q)
	);
});

const pagedScalars = computed(() => {
	return filteredScalars.value.slice(0, scalarLimit.value);
});

const tableViewState = ref({});
function getTableState(tIdx) {
	if (!tableViewState.value[tIdx]) {
		tableViewState.value[tIdx] = { search: "", limit: 10 };
	}
	return tableViewState.value[tIdx];
}

function getFilteredTableRows(table, tIdx) {
	if (!table.mappings) return [];
	const state = getTableState(tIdx);
	if (!state.search) return table.mappings;
	const q = state.search.toLowerCase();
	return table.mappings.filter(
		(row) =>
			(row.target || "").toLowerCase().includes(q) ||
			(row.path || "").toLowerCase().includes(q)
	);
}

function getPagedTableRows(table, tIdx) {
	const filtered = getFilteredTableRows(table, tIdx);
	const state = getTableState(tIdx);
	return filtered.slice(0, state.limit);
}

function removeTableRowByRow(table, row) {
	if (!table.mappings) return;
	const idx = table.mappings.findIndex((r) => r === row || r._id === row._id);
	if (idx >= 0) table.mappings.splice(idx, 1);
}

function addScalarRow() {
	ui.value.scalars.push(makeScalar());
}

function removeScalarRow(row) {
	const idx = ui.value.scalars.findIndex((r) => r === row || r._id === row._id);
	if (idx >= 0) ui.value.scalars.splice(idx, 1);
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
	const exactCandidates = (options || []).filter((opt) => {
		if (!opt?.value) return false;
		const value = String(opt.value);
		if (prefix && !value.startsWith(prefix)) return false;
		return getLeaf(value) === targetField;
	});
	if (exactCandidates.length) {
		return (
			exactCandidates.find((c) => String(c.value).startsWith("doc.")) || exactCandidates[0]
		);
	}

	// Fuzzy search for better automap matching
	const fuzzyCandidates = (options || []).filter((opt) => {
		if (!opt?.value) return false;
		const value = String(opt.value);
		if (prefix && !value.startsWith(prefix)) return false;
		const leaf = getLeaf(value);
		// match if one is contained in the other
		return targetField.includes(leaf) || leaf.includes(targetField);
	});
	if (fuzzyCandidates.length) {
		return (
			fuzzyCandidates.find((c) => String(c.value).startsWith("doc.")) || fuzzyCandidates[0]
		);
	}

	return null;
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
			is_readonly: field.read_only === 1 || field.fieldtype === "Read Only",
			no_copy: field.no_copy === 1,
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
		// Find a valid match in source schema
		const source = preferredSource(target, rowSourceOptions);
		if (!source) return; // Do not map if source field does not exist

		let sourcePath = source.value;
		// If the source comes from a child table (e.g. items.item_code), use rowAlias
		if (
			source.value.includes(".") &&
			!source.value.startsWith("doc.") &&
			!source.value.startsWith("vars.")
		) {
			sourcePath = `${rowAlias}.${target}`;
		} else if (source.value.startsWith("doc.") || source.value.startsWith("vars.")) {
			sourcePath = source.value;
		} else {
			sourcePath = `${rowAlias}.${target}`;
		}

		suggestions.push({
			target,
			source_type: "path",
			path: sourcePath,
			expr: "",
			literal: "",
			is_readonly: cf.read_only === 1 || cf.fieldtype === "Read Only",
			no_copy: cf.no_copy === 1,
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
	const rowAlias = (table.item_alias || "item").trim() || "item";
	const parentOptions = [];
	const childOptions = [];

	sourceOptionsNormalized.value.forEach((opt) => {
		const val = String(opt.value || "");
		if (val.includes(".") && !val.startsWith("doc.") && !val.startsWith("vars.")) {
			const leaf = getLeaf(val);
			childOptions.push({
				label: `${rowAlias}.${leaf} (${opt.label})`,
				value: `${rowAlias}.${leaf}`,
			});
		} else {
			parentOptions.push(opt);
		}
	});

	if (childOptions.length > 0) {
		childOptions.unshift({
			label: `--- ${rowAlias} (Row Scope) ---`,
			value: "",
			fieldtype: "Section Break",
		});
	}

	return uniqueOptions([...childOptions, ...parentOptions]);
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
			options: df.options,
			reqd: df.reqd,
			read_only: df.read_only,
			no_copy: df.no_copy,
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
				options: cf.options,
				reqd: cf.reqd,
				read_only: cf.read_only,
				no_copy: cf.no_copy,
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
		emit("update:modelValue", deepClone(ui.value));
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

// --- Multiselect logic ---
const selectedScalars = ref(new Set());
const selectedTables = ref(new Set());
const selectedPreviews = ref(new Set());
const selectedTableRows = ref({}); // { tableIndex: Set(rowId) }

function toggleSelectScalar(rowId) {
	if (selectedScalars.value.has(rowId)) selectedScalars.value.delete(rowId);
	else selectedScalars.value.add(rowId);
}

function toggleAllScalars() {
	if (selectedScalars.value.size >= pagedScalars.value.length && pagedScalars.value.length > 0) {
		selectedScalars.value.clear();
	} else {
		pagedScalars.value.forEach((r) => selectedScalars.value.add(r._id));
	}
}

function deleteSelectedScalars() {
	if (!confirm(__("Delete {0} selected fields?").replace("{0}", selectedScalars.value.size)))
		return;
	ui.value.scalars = ui.value.scalars.filter((s) => !selectedScalars.value.has(s._id));
	selectedScalars.value.clear();
}

function toggleSelectPreview(idx) {
	if (selectedPreviews.value.has(idx)) selectedPreviews.value.delete(idx);
	else selectedPreviews.value.add(idx);
}

function toggleAllPreviews() {
	if (
		selectedPreviews.value.size >= scalarAutoMapPreview.value.length &&
		scalarAutoMapPreview.value.length > 0
	) {
		selectedPreviews.value.clear();
	} else {
		scalarAutoMapPreview.value.forEach((_, idx) => selectedPreviews.value.add(idx));
	}
}

function deleteSelectedPreviews() {
	scalarAutoMapPreview.value = scalarAutoMapPreview.value.filter(
		(_, idx) => !selectedPreviews.value.has(idx)
	);
	selectedPreviews.value.clear();
}

function toggleSelectTable(idx) {
	if (selectedTables.value.has(idx)) selectedTables.value.delete(idx);
	else selectedTables.value.add(idx);
}

function deleteSelectedTables() {
	if (!confirm(__("Delete {0} selected tables?").replace("{0}", selectedTables.value.size)))
		return;
	ui.value.tables = ui.value.tables.filter((_, idx) => !selectedTables.value.has(idx));
	selectedTables.value.clear();
}

function toggleSelectTableRow(tIdx, rId) {
	if (!selectedTableRows.value[tIdx]) selectedTableRows.value[tIdx] = new Set();
	if (selectedTableRows.value[tIdx].has(rId)) selectedTableRows.value[tIdx].delete(rId);
	else selectedTableRows.value[tIdx].add(rId);
}

function toggleAllTableRows(tIdx, table) {
	const rows = getPagedTableRows(table, tIdx);
	if (!selectedTableRows.value[tIdx]) selectedTableRows.value[tIdx] = new Set();
	if (selectedTableRows.value[tIdx].size >= rows.length && rows.length > 0) {
		selectedTableRows.value[tIdx].clear();
	} else {
		rows.forEach((r) => selectedTableRows.value[tIdx].add(r._id));
	}
}

function deleteSelectedTableRows(tIdx, table) {
	const selected = selectedTableRows.value[tIdx];
	if (!selected || !selected.size) return;
	if (!confirm(__("Delete {0} selected child fields?").replace("{0}", selected.size))) return;
	table.mappings = table.mappings.filter((m) => !selected.has(m._id));
	selected.clear();
}

const isValid = computed(() => {
	// A ResourceMapper is considered valid if it has at least one scalar mapping
	// or at least one child table mapping (assuming it's required by context).
	// For now, let's just ensure if it's required, it's not completely empty.
	if (!props.df?.reqd) return true;

	const hasScalars = ui.value.scalars.some((s) => s.target && (s.path || s.expr || s.literal));
	const hasTables = ui.value.tables.some((t) => t.target_table && t.source_path);

	return hasScalars || hasTables || ui.value.copy_same_fields;
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("Resource Mapper: At least one field mapping is required"));
	}

	// Validate incomplete rows
	ui.value.scalars.forEach((s, idx) => {
		if (s.target && !(s.path || s.expr || s.literal)) {
			errors.push(__("Field Mapping #{0}: Source value is missing").replace("{0}", idx + 1));
		}
	});

	ui.value.tables.forEach((t, idx) => {
		if (t.target_table && !t.source_path) {
			errors.push(__("Table Mapping #{0}: Source path is missing").replace("{0}", idx + 1));
		}
	});

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
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
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border-subtle);
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
	color: var(--fxr-text-soft);
	white-space: nowrap;
}

.rm-check {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	font-size: 12px;
	cursor: pointer;
	color: var(--fxr-text);
}

/* ─── Exclude Section ─── */
.rm-exclude-section {
	padding: 8px 12px;
	background-color: var(--fxr-surface-soft);
	border: 1px solid var(--fxr-border-subtle);
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
	gap: var(--fxr-space-2);
	padding: var(--fxr-space-1) var(--fxr-space-3);
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-pill);
	font-size: var(--fxr-text-sm);
	color: var(--fxr-text-secondary);
}

.rm-chip-x {
	background: transparent;
	border: 0;
	padding: 0;
	line-height: 1;
	font-size: 14px;
	color: var(--fxr-text-soft);
	cursor: pointer;
	transition: color var(--fxr-transition-fast);
}

.rm-chip-x:hover {
	color: var(--fxr-text-danger);
}

/* ─── Section ─── */
.rm-section {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
	padding: var(--fxr-space-6);
	background-color: var(--fxr-bg-card);
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-4);
}

.rm-section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fxr-space-4);
}

.rm-section-header h6 {
	margin: 0;
	font-size: var(--fxr-text-md);
	font-weight: var(--fxr-weight-semibold);
	color: var(--fxr-text);
	display: flex;
	align-items: center;
	gap: var(--fxr-space-3);
}

.rm-section-header h6 i {
	color: var(--fxr-accent);
}

.rm-section-header-sm {
	padding-top: var(--fxr-space-3);
	border-top: 1px dashed var(--fxr-border);
}

/* ─── Mapping Row ─── */
.rm-mapping-row {
	display: grid;
	gap: var(--fxr-space-3);
	align-items: center;
}

.rm-cell-check {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 24px;
}

.rm-cell-check input[type="checkbox"] {
	cursor: pointer;
	margin: 0;
}

.rm-cell-arrow {
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-md);
	text-align: center;
}

/* ─── Table Card ─── */
.rm-table-card {
	border: 1px dashed var(--fxr-border);
	border-radius: var(--fxr-radius-lg);
	padding: var(--fxr-space-5);
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-4);
	background: var(--fxr-bg-hover);
}

.rm-table-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fxr-space-4);
}

.rm-table-header-fields {
	display: flex;
	gap: var(--fxr-space-3);
	flex: 1;
}

.rm-table-header-actions {
	display: flex;
	gap: var(--fxr-space-2);
	flex-shrink: 0;
}

.rm-alias-input {
	max-width: 80px;
}

.rm-table-options {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: var(--fxr-space-3);
	align-items: center;
}

.rm-table-rows {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

/* ─── Preview Box ─── */
.rm-preview-box {
	border: 1px solid var(--fxr-accent);
	border-radius: var(--fxr-radius-lg);
	padding: var(--fxr-space-5);
	background-color: var(--fxr-accent-soft);
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

.rm-preview-title {
	font-size: var(--fxr-text-md);
	font-weight: var(--fxr-weight-semibold);
	color: var(--fxr-accent);
	display: flex;
	align-items: center;
	gap: var(--fxr-space-3);
}

.rm-badge {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 20px;
	height: 20px;
	padding: 0 var(--fxr-space-2);
	border-radius: var(--fxr-radius-pill);
	background-color: var(--fxr-accent);
	color: #ffffff;
	font-size: 10px;
	font-weight: var(--fxr-weight-bold);
}

.rm-preview-list {
	max-height: 300px;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
	padding-right: var(--fxr-space-2);
}

.rm-preview-row {
	display: grid;
	gap: var(--fxr-space-5);
	align-items: center;
	padding: var(--fxr-space-2) var(--fxr-space-4);
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
}

.rm-preview-row .rm-target {
	color: var(--fxr-text);
	font-weight: var(--fxr-weight-medium);
	font-family: var(--fxr-font-mono);
}

.rm-preview-row .rm-arrow {
	color: var(--fxr-text-muted);
}

.rm-preview-footer {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: var(--fxr-space-4);
	padding-top: var(--fxr-space-4);
	border-top: 1px solid var(--fxr-accent-border);
	margin-top: var(--fxr-space-2);
}

/* ─── Empty ─── */
.rm-empty {
	font-size: var(--fxr-text-md);
	color: var(--fxr-text-muted);
	text-align: center;
	padding: var(--fxr-space-6);
	font-style: italic;
}

.rm-empty-sm {
	padding: var(--fxr-space-3);
	font-size: var(--fxr-text-sm);
}

/* ─── Footer and Pagination ─── */
.rm-section-footer {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding-top: var(--fxr-space-4);
	border-top: 1px dashed var(--fxr-border);
}

.rm-pagination {
	display: flex;
	align-items: center;
	border-color: var(--fxr-node-accent, var(--fxr-accent));
}

:deep(.form-control:focus),
:deep(.awesomplete input:focus),
:deep(.fxr-input:focus),
:deep(.fxr-select:focus) {
	border-color: var(--fxr-accent) !important;
	box-shadow: var(--fxr-shadow-focus) !important;
}

@media (max-width: 920px) {
	.rm-table-options {
		grid-template-columns: 1fr;
	}

	.rm-section-header {
		flex-wrap: wrap;
	}
}

@media (max-width: 768px) {
	.rm-options-bar {
		padding: var(--fxr-space-4);
	}

	.rm-mapping-row,
	.rm-preview-row {
		grid-template-columns: 1fr !important;
		gap: var(--fxr-space-2);
	}

	.rm-section-footer {
		flex-direction: column;
		align-items: flex-start;
		gap: var(--fxr-space-3);
	}
}
</style>
