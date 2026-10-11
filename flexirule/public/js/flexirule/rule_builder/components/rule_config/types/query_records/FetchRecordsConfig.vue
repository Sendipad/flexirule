<template>
	<div class="fetch-records-config">
		<div class="sub-section section-subcard" v-fxr-fieldname="'config.filters'">
			<div class="section-heading">
				<div>
					<h6>{{ __("Filters") }}</h6>
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

		<div class="sub-section section-subcard result-shape-section">
			<h6>{{ __("Result Shape") }}</h6>
			<p class="section-description">
				{{ __("Choose the structure returned to downstream rule actions. Frappe Query Builder performs the field selection.") }}
			</p>
			<select
				class="form-control"
				:value="localConfig.result_shape || 'document_names'"
				:disabled="readOnly"
				@change="setResultShape($event.target.value)"
			>
				<option value="document_names">{{ __("Document names — { name: ... }") }}</option>
				<option value="whole_documents">{{ __("Whole documents with embedded child tables") }}</option>
				<option value="selected_flat">{{ __("Selected fields — flat rows") }}</option>
				<option value="selected_embedded">{{ __("Selected fields with embedded child tables") }}</option>
				<option value="flattened_rows">{{ __("Flattened rows — include child-table fields") }}</option>
			</select>
			<div v-if="(localConfig.result_shape || 'document_names') === 'document_names'" class="result-shape-hint">
				{{ __("Returns only document names as dictionaries. Field selection and expressions are hidden.") }}
			</div>
			<div v-else-if="localConfig.result_shape === 'whole_documents'" class="result-shape-hint">
				{{ __("Select parent and child fields below. Embedded child rows remain grouped under their parent document.") }}
			</div>
			<div v-else-if="localConfig.result_shape === 'flattened_rows'" class="result-shape-hint">
				{{ __("Child-table field paths use joins and can produce multiple rows for one parent document.") }}
			</div>
		</div>

		<div
			v-if="(localConfig.result_shape || 'document_names') !== 'document_names'"
			class="sub-section section-subcard field-selection-section"
		>
			<div class="section-heading">
				<div>
					<h6>{{ __("Field Selection") }}</h6>
					<p class="section-description">{{ __("Choose fields, output aliases, and supported SQL functions.") }}</p>
				</div>
				<button v-if="!readOnly" type="button" class="btn btn-xs btn-primary" @click="addFieldSpec">
					<i class="fa fa-plus mr-1"></i>{{ __("Add Field") }}
				</button>
			</div>

			<div v-if="!fieldSpecs.length" class="empty-field-state">
				{{ __("No fields selected. Add a field or function to define the returned row.") }}
			</div>
			<div v-for="(item, index) in fieldSpecs" :key="item.id" class="field-spec-row">
				<select v-model="item.kind" class="form-control field-kind" :disabled="readOnly" @change="syncFieldSpecs">
					<option value="field">{{ __("Field") }}</option>
					<option value="child_table" v-if="supportsEmbeddedChildren">{{ __("Embed child table") }}</option>
					<option value="function">{{ __("SQL function") }}</option>
				</select>

				<template v-if="item.kind === 'field'">
					<ComboBoxControl
						:df="{ label: '', fieldtype: 'FieldPicker' }"
						:options="navigableFields.currentFields.value"
						:doctype="doctype"
						:modelValue="item.field"
						:read_only="readOnly"
						:trigger="'button'"
						:hideLabel="true"
						:navigable="true"
						:navStack="navigableFields.navStack.value"
						@navigate="navigableFields.handleNavigate"
						@back="navigableFields.handleBack"
						@update:modelValue="item.field = $event; navigableFields.resetStack(); syncFieldSpecs()"
					/>
				</template>
				<template v-else-if="item.kind === 'child_table'">
					<input v-model.trim="item.field" class="form-control" :placeholder="__('Child table fieldname')" :disabled="readOnly" @change="syncFieldSpecs" />
					<input v-model="item.childFieldsText" class="form-control" :placeholder="__('Child fields, comma-separated (e.g. item_code, qty)')" :disabled="readOnly" @change="syncFieldSpecs" />
				</template>
				<template v-else>
					<select v-model="item.fn" class="form-control" :disabled="readOnly" @change="syncFieldSpecs">
						<option v-for="fn in fieldFunctions" :key="fn.value" :value="fn.value">{{ fn.label }}</option>
					</select>
					<input v-model.trim="item.argument" class="form-control" :placeholder="__('Field argument (e.g. grand_total)')" :disabled="readOnly" @change="syncFieldSpecs" />
					<input v-model.trim="item.alias" class="form-control" :placeholder="__('Output alias')" :disabled="readOnly" @change="syncFieldSpecs" />
				</template>

				<input
					v-if="item.kind === 'field'"
					v-model.trim="item.alias"
					class="form-control field-alias"
					:placeholder="__('Optional alias')"
					:disabled="readOnly"
					@change="syncFieldSpecs"
				/>
				<button v-if="!readOnly" type="button" class="btn btn-xs btn-link text-danger" :title="__('Remove field')" @click="removeFieldSpec(index)">
					<i class="fa fa-trash"></i>
				</button>
			</div>
			<p class="section-description">{{ __("Functions are allowlisted in the UI; validate the generated native fields server-side before execution.") }}</p>
		</div>

		<div class="sub-section section-subcard">
			<h6>{{ __("Order By") }}</h6>
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
					class="btn btn-xs btn-link p-0 text-primary align-self-start"
					@click="addOrder"
				>
					<i class="fa fa-plus mr-1"></i>{{ __("Add Sort Criteria") }}
				</button>
			</div>
		</div>

		<div class="sub-section section-subcard">
			<h6>{{ __("Retrieval Settings") }}</h6>
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
				<div class="grid-item">
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
import { computed, reactive, ref, watch } from "vue";
import ControlFactory from "../../../../controls/ControlFactory.vue";
import ComboBoxControl from "../../../../controls/ComboBoxControl.vue";
import { useNavigableFields } from "../../../../composables/useNavigableFields";
import QueryFilterTree from "../../query_filters/QueryFilterTree.vue";

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
const fieldSpecs = ref([]);
const fieldFunctions = [
	{ value: "COUNT", label: "COUNT" }, { value: "SUM", label: "SUM" },
	{ value: "AVG", label: "AVG" }, { value: "MAX", label: "MAX" },
	{ value: "MIN", label: "MIN" }, { value: "ABS", label: "ABS" },
	{ value: "IFNULL", label: "IFNULL" }, { value: "CONCAT", label: "CONCAT" },
	{ value: "EXTRACT", label: "EXTRACT" }, { value: "NOW", label: "NOW" },
];
const supportsEmbeddedChildren = computed(() => ["selected_embedded", "whole_documents"].includes(localConfig.result_shape));
let fieldSpecId = 0;

const localConfig = reactive(normalizeConfig(props.modelValue));
const orderRows = ref(parseOrderBy(localConfig.order_by));
fieldSpecs.value = parseFieldSpecs(localConfig.field_specs);
const navigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => orderRows.value[0]?.field || ""
);

const limitField = computed(() => ({
	fieldname: "limit",
	fieldtype: "Int",
	label: __("Limit"),
	reqd: 0,
	read_only: props.readOnly,
	description: __("Maximum number of records to return. Leave blank for the framework default."),
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
	return {
		...source,
		filters: source.filters || [],
		fields: Array.isArray(source.fields) ? source.fields : [],
		result_shape: source.result_shape || "document_names",
		field_specs: Array.isArray(source.field_specs) ? source.field_specs : [],
		order_by: source.order_by || "",
		group_by: source.group_by || "",
		limit: source.limit ?? "",
		offset: source.offset ?? "",
		distinct: !!source.distinct,
	};
}

NaN
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
	const filters = next.filters;
	const hasFilters = Array.isArray(filters)
		? filters.length > 0
		: !!(
				filters &&
				typeof filters === "object" &&
				(Array.isArray(filters.children) ? filters.children.length > 0 : true)
		  );
	if (!hasFilters) delete next.filters;
	if (!next.fields?.length) delete next.fields;
	if (next.result_shape === "document_names") { next.fields = ["name"]; delete next.field_specs; }
	else if (next.field_specs?.length) next.field_specs = clone(next.field_specs);
	else delete next.field_specs;
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
		fieldSpecs.value = parseFieldSpecs(next.field_specs || []);
	},
	{ deep: true }
);

async function validate() {
	const result = (await filterTreeRef.value?.validate?.()) || { valid: true, errors: [] };
	const errors = [...(result.errors || [])];
	if ((localConfig.result_shape || "document_names") !== "document_names" && !fieldSpecs.value.some((item) => item.kind === "child_table" ? !!item.field && !!item.childFieldsText.trim() : item.kind === "function" ? !!item.fn : !!item.field)) {
		errors.push(__("Select at least one valid field or expression for this result shape."));
	}

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

:deep(.filter-group-wrapper) {
	margin: 0;
}
</style>
