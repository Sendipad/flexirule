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

		<div class="sub-section section-subcard">
			<h6>{{ __("Fields") }}</h6>
			<MultiSelectList
				:df="{
					label: '',
					fieldname: 'fields',
					placeholder: __('Select fields to fetch...'),
				}"
				:options="navigableFields.currentFields.value"
				:modelValue="localConfig.fields || []"
				:read_only="readOnly"
				:hideLabel="true"
				@update:modelValue="updateConfig('fields', $event)"
			/>
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
import ControlFactory from "../../../controls/ControlFactory.vue";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import MultiSelectList from "../../../controls/MultiSelectList.vue";
import { useNavigableFields } from "../../../composables/useNavigableFields";
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

const localConfig = reactive(normalizeConfig(props.modelValue));
const orderRows = ref(parseOrderBy(localConfig.order_by));
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
	if (!next.filters?.length) delete next.filters;
	if (!next.fields?.length) delete next.fields;
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
