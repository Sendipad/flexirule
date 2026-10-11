<template>
	<div class="fetch-records-config">
		<!-- Result Mode Selector -->
		<div class="sub-section section-subcard" v-fxr-fieldname="'config.result_mode'">
			<div class="section-heading">
				<div>
					<h6 class="mb-0">{{ __("Result Output Mode") }}</h6>
					<p class="section-description">
						{{ __("Select the desired output shape for fetched records.") }}
					</p>
				</div>
			</div>

			<div class="mode-grid">
				<div
					v-for="mode in MODE_OPTIONS"
					:key="mode.value"
					class="mode-card"
					:class="{ active: localConfig.result_mode === mode.value }"
					@click="setResultMode(mode.value)"
				>
					<div class="mode-card-header">
						<input
							type="radio"
							name="result_mode"
							:value="mode.value"
							:checked="localConfig.result_mode === mode.value"
							:disabled="readOnly"
							class="mode-radio"
						/>
						<span class="mode-title">{{ mode.label }}</span>
					</div>
					<p class="mode-desc">{{ mode.description }}</p>
				</div>
			</div>
		</div>

		<!-- Mode A Info Card -->
		<div
			v-if="localConfig.result_mode === 'names'"
			class="sub-section section-subcard mode-info-card"
		>
			<div class="info-body">
				<i class="fa fa-info-circle info-icon"></i>
				<div>
					<strong>{{ __("Document Names Mode") }}</strong>
					<p class="mb-0 text-muted">
						{{
							__(
								'Returns a list of matching document names: [{ "name": "SO-00001" }]. Field selection and SQL function controls are not applicable.'
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<!-- Mode B Info Card -->
		<div
			v-if="localConfig.result_mode === 'whole_doc'"
			class="sub-section section-subcard mode-info-card"
		>
			<div class="info-body">
				<i class="fa fa-file-text-o info-icon"></i>
				<div>
					<strong>{{ __("Whole Documents Mode") }}</strong>
					<p class="mb-0 text-muted">
						{{
							__(
								"Returns complete parent documents as dictionaries, including all child table arrays. Read permissions are enforced per document."
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<!-- Unified Output Fields Builder -->
		<div
			v-if="localConfig.result_mode === 'flat_fields' || localConfig.result_mode === 'embedded_child'"
			class="sub-section section-subcard"
			v-fxr-fieldname="'config.outputs'"
		>
			<FetchRecordsOutputFieldsBuilder
				:fields="localConfig.fields || []"
				:functions="localConfig.functions || []"
				:embeddedChildren="localConfig.embedded_children || []"
				:fieldsOptions="navigableFields.currentFields.value"
				:childTableOptions="childTableFields"
				:resultMode="localConfig.result_mode"
				:readOnly="readOnly"
				@update:fields="updateConfig('fields', $event)"
				@update:functions="updateConfig('functions', $event)"
				@update:embeddedChildren="updateConfig('embedded_children', $event)"
			/>
		</div>

		<!-- Common Filters Section -->
		<div class="sub-section section-subcard" v-fxr-fieldname="'config.filters'">
			<div class="section-heading">
				<div>
					<h6 class="mb-0">{{ __("Filters") }}</h6>
					<p class="section-description">
						{{
							__(
								"Build nested AND/OR filters. Groups are compiled as query criteria at runtime."
							)
						}}
					</p>
				</div>
			</div>
			<QueryFilterTree
				ref="filterTreeRef"
				:doctype="doctype"
				:modelValue="localConfig.filters || []"
				:readOnly="readOnly"
				:showValidation="showValidation"
				:nodeId="nodeId"
				:variableOptions="variableOptions"
				@update:modelValue="updateConfig('filters', $event)"
			/>
		</div>

		<!-- Common Order By Section -->
		<div class="sub-section section-subcard">
			<h6 class="mb-2">{{ __("Order By") }}</h6>
			<div class="table-rows">
				<div v-for="(row, index) in orderRows" :key="row.id" class="order-row">
					<ComboBoxControl
						:df="{ label: '', fieldtype: 'FieldPicker' }"
						:options="navigableFields.currentFields.value"
						:doctype="doctype"
						:modelValue="row.field"
						:read_only="readOnly"
						:trigger="'button'"
						:hideLabel="true"
						:navigable="true"
						:navStack="navigableFields.navStack.value"
						@navigate="navigableFields.handleNavigate"
						@back="navigableFields.handleBack"
						class="flex-1"
						@update:modelValue="
							(value) => {
								row.field = value;
								navigableFields.resetStack();
								syncOrderBy();
							}
						"
					/>
					<select
						v-model="row.direction"
						class="form-control direction-select"
						:disabled="readOnly"
						@change="syncOrderBy"
					>
						<option value="asc">{{ __("ASC") }}</option>
						<option value="desc">{{ __("DESC") }}</option>
					</select>
					<button
						v-if="!readOnly"
						type="button"
						class="btn btn-xs btn-link text-danger remove-sort-btn"
						:title="__('Remove sort criteria')"
						@click="removeOrder(index)"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
				<button
					v-if="!readOnly"
					type="button"
					class="btn btn-xs btn-link p-0 text-primary align-self-start mt-1"
					@click="addOrder"
				>
					<i class="fa fa-plus mr-1"></i>{{ __("Add Sort Criteria") }}
				</button>
			</div>
		</div>

		<!-- Common Retrieval Settings -->
		<div class="sub-section section-subcard">
			<h6 class="mb-2">{{ __("Retrieval Settings") }}</h6>
			<div class="query-doc-grid">
				<div class="grid-item">
					<ControlFactory
						:df="limitField"
						:modelValue="localConfig.limit"
						@update:modelValue="updateConfig('limit', $event)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="offsetField"
						:modelValue="localConfig.offset"
						@update:modelValue="updateConfig('offset', $event)"
					/>
				</div>
				<div
					v-if="
						localConfig.result_mode === 'flat_fields' ||
						localConfig.result_mode === 'names'
					"
					class="grid-item"
				>
					<ComboBoxControl
						:df="{ label: __('Group By'), fieldtype: 'Autocomplete' }"
						:modelValue="localConfig.group_by"
						:get_query="getGroupByOptions"
						:read_only="readOnly"
						:showOnFocus="true"
						@update:modelValue="updateConfig('group_by', $event)"
					/>
				</div>
			</div>
			<ControlFactory
				:df="distinctField"
				:modelValue="localConfig.distinct"
				@update:modelValue="updateConfig('distinct', $event)"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import ControlFactory from "../../../../controls/ControlFactory.vue";
import ComboBoxControl from "../../../../controls/ComboBoxControl.vue";
import MultiSelectList from "../../../../controls/MultiSelectList.vue";
import { useNavigableFields } from "../../../../composables/useNavigableFields";
import { useMetaStore } from "../../../../stores/useMetaStore";
import QueryFilterTree from "../../query_filters/QueryFilterTree.vue";
import FetchRecordsOutputFieldsBuilder from "./FetchRecordsOutputFieldsBuilder.vue";

const props = defineProps({
	modelValue: { type: Object, default: () => ({}) },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
});

const emit = defineEmits(["update:modelValue", "change"]);
const filterTreeRef = ref(null);
const metaStore = useMetaStore();

const MODE_OPTIONS = [
	{
		value: "names",
		label: __("Document Names"),
		description: __('Returns list of name dicts: [{ "name": "SO-00001" }]. Default mode.'),
	},
	{
		value: "whole_doc",
		label: __("Whole Documents"),
		description: __("Returns complete parent documents with embedded child records."),
	},
	{
		value: "flat_fields",
		label: __("Selected Fields (Flat)"),
		description: __(
			"Returns flat dicts with selected parent, link, child fields & SQL functions."
		),
	},
	{
		value: "embedded_child",
		label: __("Selected Fields with Embedded Children"),
		description: __("Returns selected parent fields and nested child record arrays."),
	},
];

const localConfig = reactive(normalizeConfig(props.modelValue));
const orderRows = ref(parseOrderBy(localConfig.order_by));
const navigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => orderRows.value[0]?.field || ""
);

onMounted(() => {
	if (props.doctype) {
		metaStore.fetch_metadata(props.doctype);
	}
});

const childTableFields = computed(() => {
	if (!props.doctype || !metaStore.doc_meta[props.doctype]) return [];
	return metaStore.doc_meta[props.doctype]
		.filter((f) => f.fieldtype === "Table" && f.options)
		.map((f) => ({
			label: f.original_label || f.fieldname,
			value: f.fieldname,
			child_doctype: f.options,
		}));
});

const limitField = computed(() => ({
	fieldname: "limit",
	fieldtype: "Int",
	label: __("Limit"),
	reqd: 0,
	read_only: props.readOnly,
	description: __("Maximum number of records to return. Leave blank for default."),
}));

const offsetField = computed(() => ({
	fieldname: "offset",
	fieldtype: "Int",
	label: __("Offset"),
	reqd: 0,
	read_only: props.readOnly,
	description: __("Number of matching records to skip."),
}));

const distinctField = computed(() => ({
	fieldname: "distinct",
	fieldtype: "Check",
	label: __("Deduplicate Rows (DISTINCT)"),
	read_only: props.readOnly,
	description: __("Return unique rows after joins and child-table traversal."),
}));

function normalizeConfig(value) {
	const source = value && typeof value === "object" ? value : {};
	const inferredMode =
		source.result_mode ||
		(source.embedded_children?.length
			? "embedded_child"
			: source.fields?.length || source.functions?.length
			? "flat_fields"
			: "names");
	return {
		result_mode: inferredMode,
		filters: source.filters || [],
		fields: Array.isArray(source.fields) ? [...source.fields] : [],
		functions: Array.isArray(source.functions) ? source.functions.map(clone) : [],
		embedded_children: Array.isArray(source.embedded_children)
			? source.embedded_children.map(clone)
			: [],
		order_by: source.order_by || "",
		group_by: source.group_by || "",
		limit: source.limit ?? "",
		offset: source.offset ?? "",
		distinct: !!source.distinct,
	};
}

function clone(value) {
	return JSON.parse(JSON.stringify(value));
}

function parseOrderBy(value) {
	if (!value || typeof value !== "string") return [];
	return value
		.split(",")
		.map((part) => part.trim())
		.filter(Boolean)
		.map((part, index) => {
			const tokens = part.split(/\s+/);
			return {
				id: "sort-" + index + "-" + Math.random().toString(36).slice(2, 8),
				field: tokens[0] || "",
				direction: (tokens[1] || "asc").toLowerCase() === "desc" ? "desc" : "asc",
			};
		});
}

function syncOrderBy() {
	localConfig.order_by = orderRows.value
		.filter((row) => row.field)
		.map((row) => `${row.field} ${row.direction || "asc"}`)
		.join(", ");
	emitConfig();
}

function addOrder() {
	if (props.readOnly) return;
	orderRows.value.push({
		id: "sort-" + Date.now() + "-" + Math.random().toString(36).slice(2, 7),
		field: "",
		direction: "asc",
	});
}

function removeOrder(index) {
	if (props.readOnly) return;
	orderRows.value.splice(index, 1);
	syncOrderBy();
}

function setResultMode(modeValue) {
	if (props.readOnly || localConfig.result_mode === modeValue) return;
	localConfig.result_mode = modeValue;
	emitConfig();
}

function getGroupByOptions() {
	const current = localConfig.group_by || "";
	const parts = current
		.split(",")
		.map((part) => part.trim())
		.filter(Boolean);
	const prefix = parts.length > 1 ? parts.slice(0, -1).join(", ") + ", " : "";
	return navigableFields.currentFields.value.map((field) => ({
		label: prefix + field.label,
		value: prefix + field.value,
	}));
}

function updateConfig(key, value) {
	localConfig[key] = clone(value);
	emitConfig();
}

function emitConfig() {
	const next = { ...clone(localConfig) };

	if (Array.isArray(next.functions)) {
		next.functions = next.functions.map(({ id, ...rest }) => rest);
	}

	if (Array.isArray(next.embedded_children)) {
		next.embedded_children = next.embedded_children.map(({ id, ...rest }) => rest);
	}

	// Keep output selections when changing modes so users can switch back without
	// losing work. The runtime selects the active result shape via result_mode.
	if (!next.fields?.length) delete next.fields;
	if (!next.functions?.length) delete next.functions;
	if (!next.embedded_children?.length) delete next.embedded_children;

	const filters = next.filters;
	const hasFilters = Array.isArray(filters)
		? filters.length > 0
		: !!(
				filters &&
				typeof filters === "object" &&
					(Array.isArray(filters.children) ? filters.children.length > 0 : true)
			);
	if (!hasFilters) delete next.filters;
	if (!next.order_by) delete next.order_by;
	if (!next.group_by) delete next.group_by;
	if (next.limit === "" || next.limit === null || next.limit === undefined) delete next.limit;
	if (next.offset === "" || next.offset === null || next.offset === undefined) delete next.offset;
	if (!next.distinct) delete next.distinct;

	emit("update:modelValue", next);
	emit("change", next);
}

watch(
	() => props.modelValue,
	(value) => {
		const next = normalizeConfig(value);
		if (JSON.stringify(next) === JSON.stringify(localConfig)) return;
		Object.keys(localConfig).forEach((key) => delete localConfig[key]);
		Object.assign(localConfig, next);
		orderRows.value = parseOrderBy(next.order_by);
	},
	{ deep: true }
);

watch(
	() => props.doctype,
	(dt) => {
		if (dt) {
			metaStore.fetch_metadata(dt);
		}
	}
);

async function validate() {
	const result = (await filterTreeRef.value?.validate?.()) || { valid: true, errors: [] };
	const errors = [...(result.errors || [])];

	for (const [label, value] of [
		[__("Limit"), localConfig.limit],
		[__("Offset"), localConfig.offset],
	]) {
		if (value === "" || value === null || value === undefined) continue;
		if (
			typeof value === "string" &&
			(value.trim().startsWith("{") || value.trim().startsWith("@"))
		) {
			continue;
		}
		const parsed = Number(value);
		if (!Number.isInteger(parsed) || parsed < 0) {
			errors.push(__("{0} must be a non-negative integer.").format(label));
		}
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.fetch-records-config {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.section-heading {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: var(--spacing-md);
}

.section-description {
	margin: 2px 0 0;
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
}

.mode-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
	gap: var(--spacing-sm);
	margin-top: var(--spacing-xs);
}

.mode-card {
	background: var(--fxr-bg-subtle, #f8fafc);
	border: 1px solid var(--fxr-border-color, #e2e8f0);
	border-radius: 6px;
	padding: var(--spacing-sm);
	cursor: pointer;
	transition: all 0.15s ease-in-out;
}

.mode-card:hover {
	border-color: var(--fxr-primary, #2563eb);
}

.mode-card.active {
	background: var(--fxr-bg-subtle-active, #eff6ff);
	border-color: var(--fxr-primary, #2563eb);
	box-shadow: 0 0 0 1px var(--fxr-primary, #2563eb);
}

.mode-card-header {
	display: flex;
	align-items: center;
	gap: var(--spacing-xs);
	margin-bottom: 2px;
}

.mode-radio {
	cursor: pointer;
}

.mode-title {
	font-weight: 600;
	font-size: var(--fxr-text-sm, 13px);
	color: var(--fxr-text-heading, #0f172a);
}

.mode-desc {
	margin: 0;
	font-size: 11px;
	color: var(--fxr-text-muted, #64748b);
	line-height: 1.3;
}

.mode-info-card {
	background: var(--fxr-bg-info-subtle, #f0f9ff);
	border: 1px solid var(--fxr-border-info, #bae6fd);
}

.info-body {
	display: flex;
	align-items: flex-start;
	gap: var(--spacing-md);
}

.info-icon {
	font-size: 18px;
	color: var(--fxr-info, #0284c7);
	margin-top: 2px;
}

.table-rows {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

.order-row {
	display: flex;
	align-items: center;
	gap: var(--spacing-md);
	width: 100%;
}

.direction-select {
	width: 100px !important;
	flex-shrink: 0;
}

.remove-sort-btn {
	width: 32px;
	height: 32px;
	padding: 0;
	flex-shrink: 0;
}

.query-doc-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: var(--spacing-md);
	align-items: start;
}

.grid-item {
	min-width: 0;
}

.flex-1 {
	flex: 1;
}

:deep(.filter-group-wrapper) {
	margin: 0;
}
</style>
