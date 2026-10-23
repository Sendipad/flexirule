<template>
	<div class="query-config">
		<div v-if="!mode" class="empty-mode-state text-center p-5">
			<i class="fa fa-mouse-pointer fa-3x text-muted mb-3 opacity-20"></i>
			<p class="text-muted">
				{{ __("Please select a Query Mode in the Setup panel to proceed.") }}
			</p>
		</div>

		<div v-else class="config-container">
			<div class="sub-section section-subcard">
				<h6>{{ __("Execution Permission") }}</h6>
				<div class="permission-control-row">
					<ControlFactory
						:ref="setControlRef"
						:df="{
							fieldname: 'ignore_permissions',
							fieldtype: 'Check',
							label: __('Skip Permissions'),
							description: __(
								'Bypass read permissions for this action. Requires audit reason.'
							),
							read_only: readOnly || (mode === 'Fetch Records' && isFrappe15),
						}"
						:modelValue="effectiveIgnorePermissions"
						@update:modelValue="(val) => update_action_key('ignore_permissions', val)"
					/>
					<div
						v-if="mode === 'Fetch Records' && isFrappe15"
						class="fetch-records-permission-notice"
						role="note"
					>
						<i class="fa fa-info-circle" aria-hidden="true"></i>
						<span>{{ __("Required on Frappe 15.") }}</span>
						<details class="permission-notice-details">
							<summary>{{ __("Details") }}</summary>
							<p>
								{{
									__(
										"Frappe 15's Query Builder does not provide the native permission-aware Fetch Records API. Enable Skip Permissions and provide an audit reason. Runtime authorization and audit checks still apply. Use Query List when you need frappe.get_list permission behavior."
									)
								}}
							</p>
						</details>
					</div>
				</div>
				<ControlFactory
					v-if="!!effectiveIgnorePermissions"
					:ref="setControlRef"
					:df="{
						fieldname: 'permission_audit_reason',
						fieldtype: 'Small Text',
						label: __('Permission Audit Reason'),
						reqd: 1,
						read_only: readOnly,
					}"
					:modelValue="node?.data?.permission_audit_reason"
					:showValidation="showValidation"
					@update:modelValue="(val) => update_action_key('permission_audit_reason', val)"
				/>
			</div>

			<!-- Fetch Records uses the reusable TreeBuilder-backed filter editor. -->
			<template v-if="mode === 'Fetch Records'">
				<FetchRecordsConfig
					ref="fetchRecordsConfigRef"
					:modelValue="config"
					:doctype="reference_doctype"
					:readOnly="readOnly"
					:showValidation="showValidation"
					:nodeId="node?.id"
					:variableOptions="variable_options"
					@update:modelValue="update_fetch_records_config"
				/>
			</template>

			<!-- Configuration based on selected Mode -->
			<template v-if="mode === 'Query List'">
				<div class="sub-section section-subcard" v-fxr-fieldname="'config.filters'">
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						ref="filterGroupRef"
						:ref="setControlRef"
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
						:showValidation="showValidation"
						:nodeId="node?.id"
						:variableOptions="variable_options"
						@update:modelValue="(val) => update_config_key('filters', val)"
					/>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Fields") }}</h6>
					<MultiSelectList
						:ref="setControlRef"
						:df="{
							label: '',
							fieldname: 'fields',
							placeholder: __('Select fields to fetch...'),
						}"
						:options="navigableFields.currentFields.value"
						:modelValue="config.fields || []"
						:read_only="readOnly"
						:hideLabel="true"
						@update:modelValue="(val) => update_config_key('fields', val)"
					/>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Order By") }}</h6>
					<div class="table-rows">
						<div v-for="(row, idx) in order_by_rows" :key="idx" class="order-by-row">
							<ComboBoxControl
								:ref="setControlRef"
								:df="{ label: '', fieldtype: 'FieldPicker' }"
								:options="navigableFields.currentFields.value"
								:doctype="reference_doctype"
								:modelValue="row.field"
								:read_only="readOnly"
								:trigger="'button'"
								:hideLabel="true"
								:navigable="true"
								:navStack="navigableFields.navStack.value"
								@navigate="navigableFields.handleNavigate"
								@back="navigableFields.handleBack"
								class="flex-1"
								:class="{
									'border-warning':
										row.field && !is_field_valid(row.field, doctype_fields),
								}"
								@update:modelValue="
									(val) => {
										row.field = val;
										navigableFields.resetStack();
									}
								"
							/>
							<SelectControl
								class="direction-select"
								:df="{
									fieldtype: 'Select',
									label: '',
									options: [
										{ label: 'ASC', value: 'asc' },
										{ label: 'DESC', value: 'desc' },
									],
									reqd: 1,
								}"
								:modelValue="row.direction"
								:read_only="readOnly"
								:hideLabel="true"
								@update:modelValue="
									(value) => {
										row.direction = value;
										sync_local_config();
									}
								"
							/>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger remove-sort-btn"
								@click="remove_order_by(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link p-0 text-primary mt-2 align-self-start"
							@click="add_order_by"
						>
							<i class="fa fa-plus mr-1"></i> {{ __("Add Sort Criteria") }}
						</button>
					</div>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Retrieval Settings") }}</h6>
					<div class="query-doc-grid">
						<div class="grid-item">
							<ControlFactory
								:ref="setControlRef"
								:df="with_read_only(limitTypeField)"
								:modelValue="config.limit_type || 'Custom Limit'"
								:showValidation="showValidation"
								@update:modelValue="(val) => update_config_key('limit_type', val)"
							/>
						</div>
						<div
							v-if="(config.limit_type || 'Custom Limit') === 'Custom Limit'"
							class="grid-item"
						>
							<ControlFactory
								:ref="setControlRef"
								:df="with_read_only(limitField)"
								:modelValue="config.limit"
								:showValidation="showValidation"
								@update:modelValue="(val) => update_config_key('limit', val)"
							/>
						</div>
						<div class="grid-item">
							<ComboBoxControl
								:ref="setControlRef"
								fieldname="group_by"
								:df="{ label: __('Group By'), fieldtype: 'Autocomplete' }"
								:modelValue="config.group_by"
								:get_query="get_group_by_options"
								:read_only="readOnly"
								:showOnFocus="true"
								@update:modelValue="update_config_key('group_by', $event)"
							/>
						</div>
						<div class="grid-item" v-if="is_child_table_target">
							<ControlFactory
								:ref="setControlRef"
								:df="
									with_read_only({
										fieldname: 'parent_doctype',
										fieldtype: 'Link',
										options: 'DocType',
										label: __('Parent DocType'),
										description: __(
											'Required for querying Child DocTypes directly'
										),
									})
								"
								:modelValue="config.parent_doctype"
								@update:modelValue="
									(val) => update_config_key('parent_doctype', val)
								"
							/>
						</div>
					</div>

					<div v-if="!config.group_by" class="retrieval-checkboxes mt-2">
						<div class="checkbox-item">
							<ControlFactory
								:ref="setControlRef"
								:df="
									with_read_only({
										fieldname: 'distinct',
										fieldtype: 'Check',
										label: __('Deduplicate Rows (DISTINCT)'),
										description: __('Return only unique parent records'),
									})
								"
								:modelValue="config.distinct"
								@update:modelValue="(val) => update_config_key('distinct', val)"
							/>
						</div>
					</div>
				</div>
			</template>

			<template v-else-if="mode === 'Query Doc'">
				<div class="sub-section section-subcard">
					<h6>{{ __("Target Document") }}</h6>
					<div class="query-doc-grid">
						<div class="grid-item">
							<ControlFactory
								:ref="setControlRef"
								:df="{
									fieldname: 'fetch_strategy',
									fieldtype: 'Select',
									label: __('Fetch Strategy'),
									options: fetch_strategy_options,
									read_only: readOnly || is_single_doctype,
								}"
								:modelValue="config.fetch_strategy || 'Get doc'"
								@update:modelValue="
									(val) => update_config_key('fetch_strategy', val)
								"
							/>
						</div>

						<div class="grid-item fxr-control">
							<label class="fxr-label" :class="{ reqd: doctypeNameField.reqd }">
								{{ __("DocType Name") }}
							</label>
							<FlexValueControl
								:ref="setControlRef"
								:modelValue="config.doctype_name"
								:variableOptions="variable_options"
								:readOnly="readOnly"
								:showValidation="showValidation"
								:context="{
									df: doctypeNameField,
								}"
								@update:modelValue="update_doctype_name"
							/>
							<div v-if="is_doctype_dynamic" class="mt-1 text-muted small">
								{{ __("The document type is resolved at runtime.") }}
							</div>
						</div>

						<div v-if="show_docname_field" class="grid-item fxr-control">
							<label class="fxr-label" :class="{ reqd: docnameField.reqd }">
								{{ __("Document Name (ID)") }}
							</label>
							<FlexValueControl
								:ref="setControlRef"
								:modelValue="config.docname"
								:variableOptions="variable_options"
								:readOnly="readOnly"
								:showValidation="showValidation"
								:context="{
									df: docnameField,
									referenceDoctype: reference_doctype,
								}"
								@update:modelValue="(val) => update_config_key('docname', val)"
							/>
						</div>
					</div>
				</div>

				<div
					v-if="config.fetch_strategy === 'Get latest Doc'"
					class="sub-section section-subcard"
					v-fxr-fieldname="'config.filters'"
				>
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						ref="filterGroupRef"
						:ref="setControlRef"
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
						:showValidation="showValidation"
						:nodeId="node?.id"
						:variableOptions="variable_options"
						@update:modelValue="(val) => update_config_key('filters', val)"
					/>
				</div>
			</template>

			<template v-else-if="mode === 'Exist Record'">
				<div class="sub-section section-subcard" v-fxr-fieldname="'config.filters'">
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						ref="filterGroupRef"
						:ref="setControlRef"
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
						:showValidation="showValidation"
						:nodeId="node?.id"
						:variableOptions="variable_options"
						@update:modelValue="(val) => update_config_key('filters', val)"
					/>
				</div>
			</template>

			<template v-else-if="mode === 'Query Report'">
				<div v-if="report_filters.length || loading" class="sub-section">
					<div class="section-header">
						<h6>{{ __("Report Filters") }}</h6>
						<div
							v-if="loading"
							class="spinner-border spinner-border-sm text-muted"
						></div>
					</div>
					<div class="table-rows report-filter-table">
						<div
							v-for="df in visible_filters"
							:key="df.fieldname"
							class="row-item report-filter-row"
						>
							<div class="filter-label-group">
								<label class="filter-label" :class="{ reqd: df.reqd }">
									{{ df.label }}
								</label>
							</div>

							<div class="filter-input-wrapper">
								<FlexValueControl
									:ref="setControlRef"
									:modelValue="report_filter_values[df.fieldname]"
									:variableOptions="variable_options"
									:readOnly="readOnly"
									:showValidation="showValidation"
									:context="{
										df: df,
										referenceDoctype: df.options,
									}"
									@update:modelValue="update_report_filter(df.fieldname, $event)"
								/>
							</div>
						</div>
					</div>
				</div>
				<div v-else class="text-muted small p-4 text-center border-dashed rounded">
					<i class="fa fa-info-circle mb-2 d-block opacity-50"></i>
					{{ __("Select a report to load its filters.") }}
				</div>
			</template>

			<template
				v-else-if="['Sum', 'Average', 'Min', 'Max', 'Count', 'Group By'].includes(mode)"
			>
				<div class="sub-section section-subcard" v-fxr-fieldname="'config.filters'">
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						ref="filterGroupRef"
						:ref="setControlRef"
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
						:showValidation="showValidation"
						:nodeId="node?.id"
						:variableOptions="variable_options"
						@update:modelValue="(val) => update_config_key('filters', val)"
					/>
				</div>

				<div class="sub-section section-subcard mt-3">
					<h6>{{ __("Aggregation Settings") }}</h6>
					<div class="query-doc-grid">
						<template v-if="['Sum', 'Average', 'Min', 'Max'].includes(mode)">
							<div class="grid-item">
								<label class="control-label small">{{
									__("Field to Aggregate")
								}}</label>
								<div class="field-picker-container">
									<ComboBoxControl
										:ref="setControlRef"
										:df="{ ...fieldField, fieldtype: 'FieldPicker' }"
										:options="navigableFields.currentFields.value"
										:doctype="reference_doctype"
										:modelValue="config.field"
										:read_only="readOnly"
										:trigger="'button'"
										:hideLabel="true"
										:navigable="true"
										:navStack="navigableFields.navStack.value"
										@navigate="navigableFields.handleNavigate"
										@back="navigableFields.handleBack"
										:class="{
											'border-warning':
												config.field &&
												!is_field_valid(config.field, doctype_fields),
										}"
										@update:modelValue="
											(val) => {
												update_config_key('field', val);
												navigableFields.resetStack();
											}
										"
									/>
									<i
										v-if="
											config.field &&
											!is_field_valid(config.field, doctype_fields)
										"
										class="fa fa-warning text-warning field-warning-icon"
										:title="__('Field not found in DocType')"
									></i>
								</div>
							</div>
						</template>
						<template v-else-if="mode === 'Group By'">
							<div class="grid-item">
								<label class="control-label small">{{
									__("Group By Field")
								}}</label>
								<div class="field-picker-container">
									<ComboBoxControl
										:ref="setControlRef"
										:df="{ ...aggGroupByField, fieldtype: 'FieldPicker' }"
										:options="navigableFields.currentFields.value"
										:doctype="reference_doctype"
										:modelValue="config.group_by_field"
										:read_only="readOnly"
										:trigger="'button'"
										:hideLabel="true"
										:navigable="true"
										:navStack="navigableFields.navStack.value"
										@navigate="navigableFields.handleNavigate"
										@back="navigableFields.handleBack"
										:class="{
											'border-warning':
												config.group_by_field &&
												!is_field_valid(
													config.group_by_field,
													doctype_fields
												),
										}"
										@update:modelValue="
											(val) => {
												update_config_key('group_by_field', val);
												navigableFields.resetStack();
											}
										"
									/>
									<i
										v-if="
											config.group_by_field &&
											!is_field_valid(config.group_by_field, doctype_fields)
										"
										class="fa fa-warning text-warning field-warning-icon"
										:title="__('Field not found in DocType')"
									></i>
								</div>
							</div>
							<div class="grid-item">
								<ControlFactory
									:ref="setControlRef"
									:df="with_read_only(aggFunctionField)"
									:modelValue="config.agg_function"
									@update:modelValue="
										(val) => update_config_key('agg_function', val)
									"
								/>
							</div>
							<div class="grid-item">
								<label class="control-label small">{{
									__("Aggregate Field")
								}}</label>
								<div class="field-picker-container">
									<ComboBoxControl
										:ref="setControlRef"
										:df="{ ...aggFieldField, fieldtype: 'FieldPicker' }"
										:options="navigableFields.currentFields.value"
										:doctype="reference_doctype"
										:modelValue="config.agg_field"
										:read_only="readOnly"
										:trigger="'button'"
										:hideLabel="true"
										:navigable="true"
										:navStack="navigableFields.navStack.value"
										@navigate="navigableFields.handleNavigate"
										@back="navigableFields.handleBack"
										:class="{
											'border-warning':
												config.agg_field &&
												!is_field_valid(config.agg_field, doctype_fields),
										}"
										@update:modelValue="
											(val) => {
												update_config_key('agg_field', val);
												navigableFields.resetStack();
											}
										"
									/>
									<i
										v-if="
											config.agg_field &&
											!is_field_valid(config.agg_field, doctype_fields)
										"
										class="fa fa-warning text-warning field-warning-icon"
										:title="__('Field not found in DocType')"
									></i>
								</div>
							</div>
						</template>
					</div>
				</div>
			</template>
		</div>

		<div class="config-section section-card test-section">
			<div class="d-flex align-items-center flex-wrap" style="gap: 8px">
				<button
					v-if="supportsManualSchemaRefresh"
					class="btn btn-xs btn-primary shadow-sm"
					@click="refresh_schema_manually"
					:disabled="
						readOnly ||
						schema_refreshing ||
						schema_preview_loading ||
						!schema_refresh_needed
					"
					:title="
						schema_refresh_needed
							? __('The stored schema differs from the current output configuration.')
							: __('The stored schema is up to date.')
					"
					tabindex="0"
				>
					<i
						:class="
							schema_refreshing ? 'fa fa-spinner fa-spin mr-1' : 'fa fa-refresh mr-1'
						"
					></i>
					{{ schema_refreshing ? __("Refreshing Schema...") : __("Refresh Schema") }}
				</button>
				<button
					class="btn btn-xs btn-outline-secondary shadow-sm"
					@click="test_query"
					:disabled="readOnly || is_doctype_dynamic"
					tabindex="0"
				>
					<i class="fa fa-flask mr-1"></i> {{ __("Debug Query") }}
				</button>
			</div>
			<span v-if="schema_refresh_needed" class="mt-2 text-warning small" role="status">
				{{ __("The stored output schema differs from the current configuration.") }}
			</span>
			<span v-if="schema_refresh_status" class="mt-2 text-muted font-weight-bold">{{
				schema_refresh_status
			}}</span>
			<span v-if="test_status" class="mt-2 text-muted font-weight-bold">{{
				test_status
			}}</span>
			<div
				v-if="is_doctype_dynamic"
				class="mt-2 text-warning small d-flex align-items-center"
				style="gap: 8px"
			>
				<i class="fa fa-info-circle"></i>
				{{
					__(
						"Schema mapping is deferred to runtime because the target DocType is dynamically evaluated."
					)
				}}
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	reactive,
	ref,
	computed,
	watch,
	onMounted,
	onBeforeUnmount,
	onBeforeUpdate,
	nextTick,
} from "vue";
import { fromCodeString } from "../../../utils/serialization";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import SelectControl from "../../../controls/SelectControl.vue";
import FilterGroup from "../FilterGroup.vue";
import FetchRecordsConfig from "./query_records/FetchRecordsConfig.vue";
import MultiSelectList from "../../../controls/MultiSelectList.vue";
import FlexValueControl from "../../../controls/FlexValueControl.vue";
import { useNodeConfigPolicy } from "../../../composables/useNodeConfigPolicy";
import { useUIStore } from "../../../stores/useUIStore";
import { provideControlContext } from "../../../composables/useControlContext";
import { useNavigableFields } from "../../../composables/useNavigableFields";
import {
	buildResolvedOutputSchema,
	inferResultShape,
	parseOutputFields,
} from "./query_records/output_fields_model.mjs";
import { normalizeResolvedOutputSchema } from "../../../../utils/output_schema.js";
import { getQueryRecordsSchemaRefreshSignature } from "./query_records/schema_refresh.mjs";

const isFrappe15 = computed(() => {
	const version = frappe.boot?.versions?.frappe;
	return typeof version === "string" && /^15(?:\.|$)/.test(version);
});

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const {
	store,
	config,
	docMeta,
	doctype_fields,
	variable_options,
	loading,
	mode,
	reference_doctype,
	with_read_only,
	loadDocMeta,
	load_doctype_fields,
	strip_expression,
	parse_value_type,
	sync_config,
	is_field_valid,
	refresh_variables,
	update_action_field,
} = useActionConfig(props, {
	fieldValueMode: "fieldname",
});

// Frappe 15's Fetch Records mode requires the permission bypass. Expose the
// required default to the UI without mutating the draft simply by opening it.
const effectiveIgnorePermissions = computed(() => {
	if (mode.value === "Fetch Records" && isFrappe15.value) return 1;
	return props.node?.data?.ignore_permissions;
});

const navigableFields = useNavigableFields(
	reference_doctype,
	() => config.field || config.group_by_field || config.agg_field
);
const { getPolicyField } = useNodeConfigPolicy({
	actionType: () => props.node?.data?.action_type || "Query Records",
	operation: mode,
	processName: () => props.node?.data?.process_name || "",
});

function resolveFieldPolicy(fieldname, fallback) {
	const field = getPolicyField(fieldname, fallback);
	// Apply dynamic requirements based on mode/config
	if (fieldname === "limit" && config.limit_type === "Custom Limit") {
		field.reqd = 1;
	}
	if (fieldname === "field" && ["Sum", "Average", "Min", "Max"].includes(mode.value)) {
		field.reqd = 1;
	}
	if (
		["group_by_field", "agg_field", "agg_function"].includes(fieldname) &&
		mode.value === "Group By"
	) {
		field.reqd = 1;
	}
	if (fieldname === "doctype_name") {
		field.reqd = 1;
	}
	if (fieldname === "docname") {
		const strategy = config.fetch_strategy || "Get doc";
		const is_single = strategy === "Get Single DocType" || is_single_doctype.value;
		const is_latest = strategy === "Get latest Doc";
		if (!is_single && !is_latest) {
			field.reqd = 1;
		} else {
			field.reqd = 0;
		}
	}
	return with_read_only(field);
}

// Local state for UI controls
const order_by_rows = ref([]);
const report_filters = ref([]);
const report_filter_values = reactive({});
const report_filter_types = reactive({});
const test_status = ref("");
const schema_refreshing = ref(false);
const schema_preview_loading = ref(false);
const schema_refresh_needed = ref(false);
const schema_refresh_status = ref("");
const supportsManualSchemaRefresh = computed(() =>
	["Fetch Records", "Query List", "Query Doc", "Query Report", "Group By"].includes(mode.value)
);
const is_single_doctype = ref(false);
const is_child_table_target = ref(false);
const showValidation = ref(false);
const filterGroupRef = ref(null);
const fetchRecordsConfigRef = ref(null);
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

// Internal flag to prevent recursive sync loops
const is_internal_update = ref(false);
const schemaRefreshReady = ref(false);

// Initialize local config
const reference_docname = computed(
	() => props.node?.data?.reference_docname || props.node?.data?.docname || ""
);

function isVariableSyntax(val) {
	if (typeof val !== "string") return false;
	const trimmed = val.trim();
	if (!trimmed) return false;
	return (
		trimmed.startsWith("@") ||
		trimmed.startsWith("doc.") ||
		trimmed.startsWith("vars.") ||
		trimmed.startsWith("item.") ||
		trimmed.startsWith("row.") ||
		trimmed.startsWith("loop.") ||
		trimmed.startsWith("caller.") ||
		trimmed.startsWith("rule.") ||
		trimmed.startsWith("ctx.") ||
		(trimmed.startsWith("{") && trimmed.endsWith("}")) ||
		(trimmed.startsWith("{{") && trimmed.endsWith("}}"))
	);
}

function isConcreteStaticValue(val) {
	if (val === null || val === undefined || val === "") return false;
	if (typeof val === "object") {
		const m = val.mode;
		if (!m || m === "static" || m === "value") {
			const inner = val.value;
			if (inner === null || inner === undefined || inner === "") return false;
			return typeof inner === "string" ? !isVariableSyntax(inner) : true;
		}
		return false;
	}
	if (typeof val === "string") {
		return !isVariableSyntax(val);
	}
	return true;
}

function extractStaticValue(val) {
	if (!isConcreteStaticValue(val)) return "";
	if (typeof val === "object") {
		return String(val.value ?? "").trim();
	}
	return String(val ?? "").trim();
}

async function reconcile_query_doc_state() {
	if (mode.value !== "Query Doc") return;

	const dt_val = config.doctype_name;
	const doc_val = config.docname;

	const dt_is_static = isConcreteStaticValue(dt_val);
	const doc_is_static = isConcreteStaticValue(doc_val);

	// 1. DocType Field Reconciliation
	if (dt_is_static) {
		const dt_name = extractStaticValue(dt_val);
		update_action_field("reference_doctype", dt_name);

		let meta = null;
		if (dt_name) {
			try {
				meta = await flexirule.utils.get_doctype_meta(dt_name);
			} catch (e) {
				meta = null;
			}
		}

		if (meta && meta.issingle) {
			is_single_doctype.value = true;
			config.fetch_strategy = "Get Single DocType";
			if (config.docname) {
				delete config.docname;
			}
			update_action_field("reference_docname", "");
			return; // Single DocType does not take a docname
		} else {
			is_single_doctype.value = false;
			if (config.fetch_strategy === "Get Single DocType" || !config.fetch_strategy) {
				config.fetch_strategy = "Get doc";
			}
		}
	} else {
		// Dynamic or empty DocType
		update_action_field("reference_doctype", "");
		is_single_doctype.value = false;
		if (config.fetch_strategy === "Get Single DocType") {
			config.fetch_strategy = "Get doc";
		}
	}

	// 2. Document Name Field Reconciliation (for normal/dynamic DocTypes)
	if (doc_is_static) {
		const doc_name = extractStaticValue(doc_val);
		update_action_field("reference_docname", doc_name);
	} else {
		// Dynamic or empty docname -> clear Rule Action reference field
		update_action_field("reference_docname", "");
		// config.docname itself is preserved when dynamic
	}
}

// Track only inputs that affect the exposed return schema. Unrelated edits such as
// changing filters, sort order, or limits must not rewrite the saved schema.
let lastSchemaRefreshSignature = null;
let schemaRefreshInitialized = false;
let schemaRefreshPromptShown = false;
let schemaEditorMounted = true;

function getSchemaRefreshSignature() {
	return getQueryRecordsSchemaRefreshSignature({
		mode: mode.value,
		referenceDoctype: reference_doctype.value,
		referenceDocname: props.node?.data?.reference_docname,
		config,
	});
}

// Initialize local config
onMounted(async () => {
	is_internal_update.value = true;
	try {
		load_local_config(props.node?.data?.config);
		// Establish the dependency baseline before asynchronous metadata loads.
		// A real field/result-shape edit during loading must still invalidate it.
		lastSchemaRefreshSignature = getSchemaRefreshSignature();
		schemaRefreshInitialized = true;
		// Do not mutate a persisted action just by opening its configuration.
		// Defaults apply when the user selects Fetch Records or explicitly saves
		// a valid edit; whole-rule save also normalizes the backend-declared default.
		if (mode.value === "Query Doc") {
			// Read the saved target's metadata for rendering, but don't reconcile
			// and rewrite the saved action during initialization. Reconciliation
			// belongs to a real user change, not opening the modal.
			const targetDoctype = isConcreteStaticValue(config.doctype_name)
				? extractStaticValue(config.doctype_name)
				: !config.doctype_name
				? reference_doctype.value
				: "";
			if (targetDoctype) {
				await loadDocMeta(targetDoctype);
				await load_doctype_fields(targetDoctype);
				const meta = await flexirule.utils.get_doctype_meta(targetDoctype);
				is_single_doctype.value = !!meta?.issingle;
				is_child_table_target.value = !!meta?.istable;
			} else {
				is_single_doctype.value = false;
				is_child_table_target.value = false;
			}
		} else if (reference_doctype.value) {
			await loadDocMeta(reference_doctype.value);
			await load_doctype_fields(reference_doctype.value);

			const meta = await flexirule.utils.get_doctype_meta(reference_doctype.value);
			is_single_doctype.value = !!meta?.issingle;
			is_child_table_target.value = !!meta?.istable;
		}
		// Mounting the editor is a read/restore operation. Never write
		// resolved_output_schema here; the watcher below refreshes it only when
		// a schema-defining input changes. Missing schemas remain missing until
		// the user changes one of those inputs.
		await refresh_variables();
	} finally {
		is_internal_update.value = false;
		// Changes produced while hydrating saved controls are initialization, not edits.
		lastSchemaRefreshSignature = getSchemaRefreshSignature();
		schemaRefreshReady.value = true;
		// Compare the saved schema as soon as the editor is hydrated. A mismatch
		// prompts for an explicit refresh; skipping preserves the stored schema.
		await update_schema_refresh_preview({ promptIfChanged: true });
	}
});

// Watch for external config changes
watch(
	() => props.node?.data?.config,
	async (val) => {
		if (!is_internal_update.value) {
			load_local_config(val);
			if (mode.value === "Query Doc") {
				await reconcile_query_doc_state();
			}
		}
	}
);

// Watch for doctype changes to reload meta
watch(
	() => reference_doctype.value,
	async (val, oldVal) => {
		if (val !== oldVal) {
			if (val) {
				await loadDocMeta(val);
				await load_doctype_fields(val);
			}

			if (mode.value === "Query Doc" && !is_internal_update.value) {
				if (isConcreteStaticValue(config.doctype_name) || !config.doctype_name) {
					if (config.doctype_name !== val) {
						config.doctype_name = val;
						await reconcile_query_doc_state();
					}
				} else {
					// If config.doctype_name is dynamic, reconcile clears reference_doctype back
					await reconcile_query_doc_state();
				}
			}

			// Only sync if this was a user change (not during initial mount)
			if (!is_internal_update.value && val) {
				// Clear filters when DocType changes
				if (Array.isArray(config.filters)) {
					config.filters = [];

					// Re-initialize for Query Doc if not single
					if (mode.value === "Query Doc") {
						const meta = await flexirule.utils.get_doctype_meta(val);
						is_child_table_target.value = !!meta?.istable;
						if (meta && !meta.issingle) {
							config.filters = [[val, "name", "=", { mode: "static", value: "" }]];
						}
					} else {
						const meta = await flexirule.utils.get_doctype_meta(val);
						is_child_table_target.value = !!meta?.istable;
					}
				} else if (typeof config.filters === "object") {
					config.filters = {};
				}
				sync_local_config();
			}
		}
	}
);

// Watch for reference_docname changes (e.g. from InputPanel)
watch(
	() => reference_docname.value,
	async (val, oldVal) => {
		if (mode.value === "Query Doc" && val !== oldVal && !is_internal_update.value) {
			if (isConcreteStaticValue(config.docname) || !config.docname) {
				if (config.docname !== val) {
					if (val) {
						config.docname = val;
					} else {
						delete config.docname;
					}
					await reconcile_query_doc_state();
				}
			} else {
				// If config.docname is dynamic, reconcile clears reference_docname back
				await reconcile_query_doc_state();
			}
		}
	}
);

// Sync local config changes back to node (handled by debounced_sync)

// Setup active uiStore reference for mock context value resolution
const uiStore = useUIStore();

// Recursive strategy to cleanly resolve nested static, dynamic, or list filter values to native primitives
function resolve_value_recursively(val) {
	if (val === undefined || val === null) return "";

	// Handle Array of filter values
	if (Array.isArray(val)) {
		const resolved = val
			.map(resolve_value_recursively)
			.filter((x) => x !== undefined && x !== null && x !== "" && JSON.stringify(x) !== "{}");
		return resolved.length === 1 && Array.isArray(resolved[0]) ? resolved[0] : resolved;
	}

	if (typeof val === "object") {
		// Handle standard FlexValueControl mode objects
		if (val.mode !== undefined) {
			if (val.mode === "static") {
				return resolve_value_recursively(val.value);
			}
			const context_vars = uiStore.test_context || {};
			if (val.mode === "variable") {
				const path = val.value || "";
				if (path.startsWith("doc.")) {
					const key = path.substring(4);
					if (context_vars.doc && context_vars.doc[key] !== undefined) {
						return resolve_value_recursively(context_vars.doc[key]);
					}
				} else if (path.startsWith("vars.")) {
					const key = path.substring(5);
					if (context_vars[key] !== undefined) {
						return resolve_value_recursively(context_vars[key]);
					}
				} else if (context_vars[path] !== undefined) {
					return resolve_value_recursively(context_vars[path]);
				}
				return "";
			}
			if (val.mode === "resolver" || val.mode === "expression") {
				const expression = val.value || "";
				if (expression.includes("doc.")) {
					const match = expression.match(/doc\.([a-zA-Z0-9_]+)/);
					if (match && context_vars.doc && context_vars.doc[match[1]] !== undefined) {
						return resolve_value_recursively(context_vars.doc[match[1]]);
					}
				} else if (expression.includes("vars.")) {
					const match = expression.match(/vars\.([a-zA-Z0-9_]+)/);
					if (match && context_vars[match[1]] !== undefined) {
						return resolve_value_recursively(context_vars[match[1]]);
					}
				}
				return "";
			}
		}

		// If it's a generic plain object, check if it's empty
		if (Object.keys(val).length === 0) {
			return "";
		}

		// Return val.value if present, otherwise serialize/return empty string to avoid dictionary passing
		return val.value !== undefined ? resolve_value_recursively(val.value) : "";
	}

	return val;
}

// Design-time fallback and simulation context resolution strategy
function get_resolved_filter_value(name) {
	const raw = report_filter_values[name];
	return resolve_value_recursively(raw);
}

const original_query_report = window.frappe.query_report;

// Guard to prevent infinite recursion/re-entry when filters trigger cascading set_filter_value updates
const is_updating_filters = ref(false);

// Isolated, scoped frappe.query_report adapter to evaluate report filter dependencies safely without global state bleed
const query_report_adapter = {
	filters: report_filters.value,
	get_filter_value: (name) => get_resolved_filter_value(name),
	set_filter_value: (name, val) => {
		const current = report_filter_values[name];
		if (current && typeof current === "object" && current.mode && current.mode !== "static") {
			// Do not overwrite dynamic variables or expressions via UI set, preserve user config!
			return;
		}
		// If value actually changed, update it and run local listener securely
		const current_primitive = get_resolved_filter_value(name);
		const target_primitive = val && typeof val === "object" ? val.value : val;
		if (current_primitive !== target_primitive) {
			report_filter_values[name] = val;
			sync_local_config();

			if (!is_updating_filters.value) {
				is_updating_filters.value = true;
				try {
					const df = report_filters.value.find((f) => f.fieldname === name);
					if (df && typeof df.on_change === "function") {
						df.on_change();
					}
				} finally {
					is_updating_filters.value = false;
				}
			}
		}
	},
	toggle_filter_display: (name, show) => {
		const filter = report_filters.value.find((f) => f.fieldname === name);
		if (filter) {
			filter.hidden = !show;
		}
	},
	page: {
		add_inner_button: () => {},
	},
};

// ── Provide ControlContext for child controls ──
// This replaces the need for child controls to access window.frappe.query_report directly.
// Controls can now inject this context and call getFieldValue(fieldname) to resolve
// sibling/parent filter values within the local report adapter scope.
provideControlContext({
	getFieldValue: (name) => get_resolved_filter_value(name),
});

onMounted(() => {
	window.frappe.query_report = query_report_adapter;
});

onBeforeUnmount(() => {
	window.frappe.query_report = original_query_report;
	schemaEditorMounted = false;
	schemaPreviewRequestId += 1;
});

function evaluate_depends_on(expression, values) {
	if (!expression) return true;
	if (typeof expression === "boolean") return expression;

	// Resolve actual primitive values of report filters
	const resolved_values = {};
	Object.keys(report_filter_values).forEach((k) => {
		resolved_values[k] = get_resolved_filter_value(k);
	});

	if (typeof expression === "string" && expression.startsWith("eval:")) {
		try {
			return frappe.utils.eval(expression.substring(5), {
				doc: resolved_values,
				values: resolved_values,
			});
		} catch (e) {
			return false;
		}
	} else if (typeof expression === "string") {
		return !!resolved_values[expression];
	}
	return true;
}

const visible_filters = computed(() => {
	return report_filters.value.filter((df) => {
		if (!df.label || df.fieldtype?.includes("Break") || df.hidden) return false;
		if (df.depends_on) {
			return evaluate_depends_on(df.depends_on, report_filter_values);
		}
		return true;
	});
});

// Refresh dependent filters whenever report filter values update (non-reentrant)
function refresh_dependent_filters() {
	query_report_adapter.filters = report_filters.value;
	if (is_updating_filters.value) return;
	is_updating_filters.value = true;
	try {
		visible_filters.value.forEach((df) => {
			if (typeof df.on_change === "function") {
				try {
					df.on_change();
				} catch (err) {
					console.warn("Report filter on_change failed", df.fieldname, err);
				}
			}
		});
	} finally {
		is_updating_filters.value = false;
	}
}

const SYSTEM_FIELDS = [
	{ fieldname: "name", label: __("ID (name)"), fieldtype: "Data" },
	{ fieldname: "owner", label: __("Created By (owner)"), fieldtype: "Link", options: "User" },
	{ fieldname: "creation", label: __("Created On (creation)"), fieldtype: "Datetime" },
	{ fieldname: "modified", label: __("Modified On (modified)"), fieldtype: "Datetime" },
	{
		fieldname: "modified_by",
		label: __("Modified By (modified_by)"),
		fieldtype: "Link",
		options: "User",
	},
	{ fieldname: "docstatus", label: __("Document Status (docstatus)"), fieldtype: "Int" },
];

/**
 * Build the output schema for Fetch Records from its result shape. Unlike
 * Query List, Fetch Records supports aliases and aggregate expressions, and the
 * "whole_documents" shape is represented by fields="*" rather than an empty
 * field list.
 */
let fetch_records_schema_request_id = 0;

async function build_fetch_records_schema_local() {
	const requestId = ++fetch_records_schema_request_id;
	const isStale = () =>
		requestId !== fetch_records_schema_request_id || mode.value !== "Fetch Records";
	if (!props.node?.data || mode.value !== "Fetch Records") return null;

	const targetDoctype = reference_doctype.value;
	if (!targetDoctype || is_doctype_dynamic.value) {
		return isStale()
			? null
			: is_doctype_dynamic.value
			? [
					{
						label: __("Dynamic Object"),
						fieldname: "doc",
						fieldtype: "JSON",
						reqd: 0,
						source: {
							kind: "dynamic",
							fieldname: "doc",
							expression: "doctype_name",
						},
					},
			  ]
			: [];
	}

	const meta = await flexirule.utils.get_doctype_meta(targetDoctype);
	if (isStale() || !meta) return null;

	const fieldInfoByPath = {};
	const toSchemaField = (field, fieldname = field.fieldname, label = field.label) => {
		const sourceFieldname = String(fieldname || field.fieldname || "");
		const sourceKind = sourceFieldname.includes(".")
			? "child_field"
			: SYSTEM_FIELDS.some((item) => item.fieldname === sourceFieldname)
			? "system"
			: "field";
		return {
			fieldname: sourceFieldname,
			label: label || sourceFieldname,
			fieldtype: field.fieldtype || "Data",
			...(field.options ? { options: field.options } : {}),
			reqd: Number(field.reqd) === 1 ? 1 : 0,
			source: field.source || {
				kind: sourceKind,
				fieldname: sourceFieldname,
				expression: sourceFieldname,
				...(sourceKind === "child_field"
					? { table_fieldname: sourceFieldname.split(".", 1)[0] }
					: {}),
			},
		};
	};
	for (const field of meta.fields || []) {
		if (field.fieldname) fieldInfoByPath[field.fieldname] = toSchemaField(field);
	}
	for (const field of SYSTEM_FIELDS) {
		if (field.fieldname) fieldInfoByPath[field.fieldname] = toSchemaField(field);
	}

	const rows = parseOutputFields(config.fields);
	const paths = new Set();
	for (const row of rows) {
		if (row.kind === "field" || row.kind === "function") {
			if (row.field) paths.add(String(row.field));
		} else if (row.kind === "child" && row.tableField) {
			paths.add(String(row.tableField));
			for (const childField of row.fields || []) {
				paths.add(String(row.tableField) + "." + String(childField));
			}
		}
	}

	for (const path of paths) {
		if (isStale()) return null;
		if (!path.includes(".")) continue;
		const [rootName, nestedName] = path.split(".", 2);
		const rootField = (meta.fields || []).find((field) => field.fieldname === rootName);
		if (!rootField?.options || !nestedName) continue;
		try {
			const relatedMeta = await flexirule.utils.get_doctype_meta(rootField.options);
			if (isStale()) return null;
			const nestedField = (relatedMeta?.fields || []).find(
				(field) => field.fieldname === nestedName
			);
			if (nestedField) {
				fieldInfoByPath[path] = toSchemaField(
					nestedField,
					path,
					(rootField.label || rootName) +
						": " +
						(nestedField.label || nestedField.fieldname)
				);
			}
		} catch (error) {
			// Unknown or dynamic related metadata falls back to Data in the schema helper.
		}
	}

	const noValueTypes = frappe.model?.no_value_type || frappe.model?.no_value_fields || [];
	const wholeDocumentFields = (meta.fields || [])
		.filter(
			(field) =>
				field.fieldname &&
				!noValueTypes.includes(field.fieldtype) &&
				!["Table", "Table MultiSelect"].includes(field.fieldtype)
		)
		.map((field) => toSchemaField(field));

	const shape = inferResultShape(config.fields, config.result_shape);
	const schema = buildResolvedOutputSchema({
		shape,
		fields: config.fields,
		fieldInfoByPath,
		wholeDocumentFields,
		systemFields: SYSTEM_FIELDS.map((field) => toSchemaField(field)),
	});
	return isStale() ? null : schema;
}
async function update_fetch_records_schema_local() {
	const schema = await build_fetch_records_schema_local();
	if (!Array.isArray(schema)) return false;
	set_resolved_output_schema(schema);
	return true;
}

function set_resolved_output_schema(schema) {
	if (!props.node?.data) return;
	const next = normalizeResolvedOutputSchema(Array.isArray(schema) ? schema : []);
	let current = props.node.data.resolved_output_schema;
	let currentIsArray = Array.isArray(current);
	if (typeof current === "string") {
		try {
			current = JSON.parse(current);
			currentIsArray = Array.isArray(current);
		} catch (error) {
			currentIsArray = false;
		}
	}
	if (
		currentIsArray &&
		JSON.stringify(normalizeResolvedOutputSchema(current)) === JSON.stringify(next)
	) {
		schema_refresh_needed.value = false;
		return;
	}
	props.node.data.resolved_output_schema = next;
	schema_refresh_needed.value = false;
	const isDraft = !store.nodes.some((node) => node === props.node);
	if (!isDraft) store.mark_dirty();
}

/**
 * Local metadata-based schema detection.
 * Provides instant feedback for Query List and Query Doc modes.
 */
async function build_resolved_schema_preview() {
	if (!props.node?.data) return null;
	if (mode.value === "Fetch Records") {
		return await build_fetch_records_schema_local();
	}
	if (mode.value === "Group By") {
		return await build_group_by_schema_preview();
	}

	if (["Query List", "Query Doc"].includes(mode.value)) {
		const is_query_doc = mode.value === "Query Doc";
		const fields = (config.fields || []).filter((f) => f);

		if (!is_query_doc && !fields.length) {
			return [];
		}

		const schema = [];
		const target_doctype = is_query_doc
			? isConcreteStaticValue(config.doctype_name)
				? extractStaticValue(config.doctype_name)
				: reference_doctype.value
			: reference_doctype.value;
		if (!target_doctype || is_doctype_dynamic.value) {
			if (is_doctype_dynamic.value) {
				return [
					{
						label: __("Dynamic Object"),
						fieldname: "doc",
						fieldtype: "JSON",
						reqd: 0,
						source: { kind: "dynamic", fieldname: "doc", expression: "doctype_name" },
					},
				];
			}
			return null;
		}

		const meta = await flexirule.utils.get_doctype_meta(target_doctype);
		if (!meta) return null;

		// For Query Doc, we return the full schema if fields are not explicitly set
		const fields_to_process =
			is_query_doc && (!fields.length || config.fetch_strategy !== "Get latest Doc")
				? meta.fields.map((f) => f.fieldname).concat(SYSTEM_FIELDS.map((f) => f.fieldname))
				: fields;

		for (const f of fields_to_process) {
			if (f.includes(".")) {
				const [table, field] = f.split(".");
				const table_df = meta.fields.find((d) => d.fieldname === table);
				if (table_df && table_df.options) {
					const child_meta = await flexirule.utils.get_doctype_meta(table_df.options);
					const df =
						child_meta.fields.find((d) => d.fieldname === field) ||
						SYSTEM_FIELDS.find((sf) => sf.fieldname === field);
					if (df) {
						schema.push({
							label: `${table_df.label}: ${df.label}`,
							fieldname: f,
							fieldtype: df.fieldtype,
							...(df.options ? { options: df.options } : {}),
							reqd: Number(df.reqd) === 1 ? 1 : 0,
							source: {
								kind: "child_field",
								table_fieldname: table,
								fieldname: field,
								expression: f,
							},
						});
					}
				}
			} else {
				const df =
					meta.fields.find((d) => d.fieldname === f) ||
					SYSTEM_FIELDS.find((sf) => sf.fieldname === f);
				if (df) {
					if (["Table", "Table MultiSelect"].includes(df.fieldtype) && df.options) {
						// Expand child table fields
						const child_meta = await flexirule.utils.get_doctype_meta(df.options);
						if (child_meta) {
							child_meta.fields.forEach((cf) => {
								if (!frappe.model.no_value_type.includes(cf.fieldtype)) {
									schema.push({
										label: `${df.label}: ${cf.label}`,
										fieldname: `${df.fieldname}.${cf.fieldname}`,
										fieldtype: cf.fieldtype,
										...(cf.options ? { options: cf.options } : {}),
										reqd: Number(cf.reqd) === 1 ? 1 : 0,
										source: {
											kind: "child_field",
											table_fieldname: df.fieldname,
											fieldname: cf.fieldname,
											expression: `${df.fieldname}.${cf.fieldname}`,
										},
									});
								}
							});
						}
					} else {
						schema.push({
							label: df.label,
							fieldname: f,
							fieldtype: df.fieldtype,
							...(df.options ? { options: df.options } : {}),
							reqd: Number(df.reqd) === 1 ? 1 : 0,
							source: {
								kind: SYSTEM_FIELDS.some((item) => item.fieldname === f)
									? "system"
									: "field",
								fieldname: f,
								expression: f,
							},
						});
					}
				}
			}
		}

		return schema;
	} else if (mode.value === "Query Report" && props.node?.data?.reference_docname) {
		return await build_report_schema_preview();
	}
	return null;
}

async function build_group_by_schema_preview() {
	const targetDoctype = reference_doctype.value;
	const groupFieldname = String(config.group_by_field || "").trim();
	const aggregateFieldname = String(config.agg_field || "name").trim();
	const aggregateFunction = String(config.agg_function || "count").toLowerCase();
	const allowedFunctions = new Set(["count", "sum", "avg", "min", "max"]);

	if (
		!targetDoctype ||
		!groupFieldname ||
		!aggregateFieldname ||
		!allowedFunctions.has(aggregateFunction)
	) {
		return null;
	}

	const meta = await flexirule.utils.get_doctype_meta(targetDoctype);
	if (!meta?.fields) return null;

	async function resolveField(fieldname) {
		if (fieldname.includes(".")) {
			const [tableFieldname, childFieldname] = fieldname.split(".", 2);
			const tableField = meta.fields.find((field) => field.fieldname === tableFieldname);
			if (!tableField?.options) return null;

			const childMeta = await flexirule.utils.get_doctype_meta(tableField.options);
			const field =
				childMeta?.fields?.find((candidate) => candidate.fieldname === childFieldname) ||
				SYSTEM_FIELDS.find((candidate) => candidate.fieldname === childFieldname);
			if (!field) return null;

			return {
				label: `${tableField.label || tableFieldname}: ${field.label || field.fieldname}`,
				fieldname,
				fieldtype: field.fieldtype || "Data",
				...(field.options ? { options: field.options } : {}),
				reqd: Number(field.reqd) === 1 ? 1 : 0,
				source: {
					kind: "child_field",
					table_fieldname: tableFieldname,
					fieldname: childFieldname,
					expression: fieldname,
				},
			};
		}

		const field =
			meta.fields.find((candidate) => candidate.fieldname === fieldname) ||
			SYSTEM_FIELDS.find((candidate) => candidate.fieldname === fieldname);
		if (!field) return null;

		return {
			label: field.label || field.fieldname,
			fieldname,
			fieldtype: field.fieldtype || "Data",
			...(field.options ? { options: field.options } : {}),
			reqd: Number(field.reqd) === 1 ? 1 : 0,
			source: {
				kind: SYSTEM_FIELDS.some((candidate) => candidate.fieldname === fieldname)
					? "system"
					: "field",
				fieldname,
				expression: fieldname,
			},
		};
	}

	const groupSchemaField = await resolveField(groupFieldname);
	const aggregateSourceField = await resolveField(aggregateFieldname);
	if (!groupSchemaField || (aggregateFunction !== "count" && !aggregateSourceField)) {
		return null;
	}

	const aggregateFieldtype =
		aggregateFunction === "count"
			? "Int"
			: aggregateFunction === "avg"
			? "Float"
			: aggregateSourceField?.fieldtype || "Data";

	return [
		groupSchemaField,
		{
			label: __("Value"),
			fieldname: "value",
			fieldtype: aggregateFieldtype,
			...(aggregateSourceField?.options ? { options: aggregateSourceField.options } : {}),
			reqd: 0,
			source: {
				kind: "aggregate",
				function: aggregateFunction,
				fieldname: aggregateFieldname,
				expression: `${aggregateFunction}(${aggregateFieldname}) as value`,
			},
		},
	];
}

async function update_resolved_schema_local() {
	const schema = await build_resolved_schema_preview();
	if (!Array.isArray(schema)) return false;
	set_resolved_output_schema(schema);
	return true;
}

async function build_report_schema_preview() {
	if (mode.value !== "Query Report" || !props.node?.data?.reference_docname) return null;

	try {
		const report_name = props.node.data.reference_docname;
		// Resolve raw report filters structure into clean primitive values before executing the API request from the client
		const resolved_filters = {};
		Object.keys(report_filter_values).forEach((k) => {
			resolved_filters[k] = get_resolved_filter_value(k);
		});

		const res = await frappe.call({
			method: "frappe.desk.query_report.run",
			args: {
				report_name: report_name,
				filters: resolved_filters,
				are_default_filters: false,
			},
		});

		if (res.message && res.message.columns) {
			const schema = res.message.columns.map((c) => {
				if (typeof c === "string") {
					const parts = c.split(":");
					let fieldtype = parts[1] || "Data";
					let options = parts[2];

					if (fieldtype.includes("/")) {
						[fieldtype, options] = fieldtype.split("/");
					}

					return {
						label: parts[0],
						fieldname: parts[0],
						fieldtype,
						options,
						reqd: 0,
						source: {
							kind: "report",
							fieldname: parts[0],
							expression: parts[0],
						},
					};
				}
				return {
					label: c.label || c.fieldname,
					fieldname: c.fieldname || c.label,
					fieldtype: c.fieldtype || "Data",
					...(c.options ? { options: c.options } : {}),
					reqd: Number(c.reqd ?? c.mandatory) === 1 ? 1 : 0,
					source: c.source || {
						kind: "report",
						fieldname: c.fieldname || c.label,
						expression: c.fieldname || c.label,
					},
				};
			});
			return schema;
		}
		return null;
	} catch (e) {
		console.warn("Failed to update report columns", e);
		return null;
	}
}

async function update_report_columns() {
	const schema = await build_report_schema_preview();
	if (!Array.isArray(schema)) return false;
	set_resolved_output_schema(schema);
	return true;
}

const limitTypeField = computed(() =>
	resolveFieldPolicy("limit_type", {
		fieldname: "limit_type",
		fieldtype: "Select",
		label: __("Result Limit"),
		options: ["All", "First Record", "Custom Limit"],
	})
);

const limitField = computed(() =>
	resolveFieldPolicy("limit", {
		fieldname: "limit",
		fieldtype: "Int",
		label: __("Custom Limit Number"),
		description: __("Max rows to return. Default: 20"),
	})
);

const groupByField = computed(() =>
	resolveFieldPolicy("group_by", {
		fieldname: "group_by",
		fieldtype: "Data",
		label: __("Group By"),
		description: __("Optional group by field."),
	})
);

const fieldField = computed(() =>
	resolveFieldPolicy("field", {
		fieldname: "field",
		fieldtype: "Data",
		label: __("Field to Aggregate"),
	})
);

const aggGroupByField = computed(() =>
	resolveFieldPolicy("group_by_field", {
		fieldname: "group_by_field",
		fieldtype: "Data",
		label: __("Group By Field"),
	})
);

const aggFunctionField = computed(() =>
	resolveFieldPolicy("agg_function", {
		fieldname: "agg_function",
		fieldtype: "Select",
		label: __("Aggregate Function"),
		options: "count\nsum\navg\nmin\nmax",
	})
);

const aggFieldField = computed(() =>
	resolveFieldPolicy("agg_field", {
		fieldname: "agg_field",
		fieldtype: "Data",
		label: __("Aggregate Field"),
	})
);

const docnameExprField = computed(() =>
	resolveFieldPolicy("docname_expression", {
		fieldname: "docname_expression",
		fieldtype: "Code",
		label: __("Docname Expression"),
		options: "PythonExpression",
	})
);

const doctypeNameField = computed(() =>
	resolveFieldPolicy("doctype_name", {
		fieldname: "doctype_name",
		fieldtype: "Link",
		options: "DocType",
		label: __("DocType Name"),
		reqd: 1,
	})
);

const docnameField = computed(() =>
	resolveFieldPolicy("docname", {
		fieldname: "docname",
		fieldtype: "Link",
		options: reference_doctype.value,
		label: __("Document Name (ID)"),
		reqd: 1,
	})
);

const is_doctype_dynamic = computed(() => {
	if (!config.doctype_name) return false;
	return !isConcreteStaticValue(config.doctype_name);
});

const fetch_strategy_options = computed(() => {
	if (is_single_doctype.value) {
		return ["Get Single DocType"];
	}
	return ["Get doc", "Get Doc from Cache", "Get latest Doc"];
});

const show_docname_field = computed(() => {
	if (config.fetch_strategy === "Get latest Doc") return false;
	if (config.fetch_strategy === "Get Single DocType") return false;
	if (is_single_doctype.value) return false;
	return true;
});

async function update_doctype_name(val) {
	config.doctype_name = val;
	await reconcile_query_doc_state();
	sync_local_config();
}

async function update_config_key(key, value) {
	config[key] = value;
	if (mode.value === "Query Doc" && (key === "docname" || key === "fetch_strategy")) {
		await reconcile_query_doc_state();
	}
	sync_local_config();
}

function update_action_key(key, value) {
	if (!props.node?.data) return;
	props.node.data[key] = value;
}

function applyFetchRecordsFrappe15Defaults() {
	if (props.readOnly || !props.node?.data) return;
	if (mode.value !== "Fetch Records" || !isFrappe15.value) return;
	const current = props.node.data.ignore_permissions;
	// Frappe 15's Fetch Records Query Builder path cannot provide native
	// record-level read permission enforcement. Apply the explicit audited-bypass
	// default when the user changes the operation to Fetch Records. Opening an
	// existing modal is intentionally non-mutating; valid modal saves and the
	// whole-rule save path normalize existing legacy values separately.
	if (![true, 1, "1"].includes(current)) {
		props.node.data.ignore_permissions = 1;
	}
}

function update_fetch_records_config(value) {
	const next = value && typeof value === "object" ? value : {};
	Object.keys(config).forEach((key) => delete config[key]);
	Object.assign(config, next);
	sync_local_config();
}

// Watch for operation changes directly to handle Report special case
watch(
	() => mode.value,
	async (newMode, oldMode) => {
		if (!is_internal_update.value && newMode !== oldMode) {
			// Clear irrelevant configuration fields when mode changes
			const keysToKeep = ["doctype_name", "fetch_strategy"];

			Object.keys(config).forEach((key) => {
				if (!keysToKeep.includes(key)) {
					// Specific mode cleanup
					if (key === "filters") {
						config.filters = newMode === "Query Report" ? {} : [];
					} else if (key === "docname" && newMode !== "Query Doc") {
						delete config[key];
					} else if (
						[
							"limit",
							"limit_type",
							"order_by",
							"fields",
							"offset",
							"distinct",
							"group_by",
						].includes(key) &&
						!["Query List", "Fetch Records"].includes(newMode)
					) {
						delete config[key];
					} else if (
						["field", "group_by_field", "agg_field", "agg_function"].includes(key) &&
						!["Sum", "Average", "Min", "Max", "Count", "Group By"].includes(newMode)
					) {
						delete config[key];
					}
				}
			});

			if (newMode === "Query List") {
				config.limit = config.limit || 20;
				config.limit_type = config.limit_type || "Custom Limit";
				// Clear reference_docname as it must be hidden/not used in Query List
				update_action_field("reference_docname", "");
			}
		}

		if (!is_internal_update.value && newMode !== oldMode) {
			applyFetchRecordsFrappe15Defaults();

			if (newMode === "Query Report" && props.node?.data) {
				if (props.node.data.reference_doctype !== "Report") {
					update_action_field("reference_doctype", "Report");
				}
				if (props.node.data.reference_docname) {
					config.report_name = props.node.data.reference_docname;
				}
			}
		}

		if (newMode === "Query Doc" && !is_internal_update.value) {
			// Initialize filters if empty
			if (!config.filters || (Array.isArray(config.filters) && config.filters.length === 0)) {
				const doctype = reference_doctype.value;
				if (doctype) {
					const meta = await flexirule.utils.get_doctype_meta(doctype);
					if (meta && !meta.issingle) {
						config.filters = [[doctype, "name", "=", { mode: "static", value: "" }]];
					}
				}
			}
		}
		if (!is_internal_update.value) {
			sync_local_config();
		}
	}
);

// Watch for report docname changes to load filters
watch(
	() => props.node?.data?.reference_docname,
	(newVal, oldVal) => {
		if (mode.value === "Query Report" && newVal && newVal !== oldVal) {
			load_report_filters(newVal);
		}
	},
	{ immediate: true }
);

function add_order_by() {
	order_by_rows.value.push({ field: "", direction: "asc" });
}

function remove_order_by(idx) {
	order_by_rows.value.splice(idx, 1);
	sync_local_config();
}

function build_fields() {
	return config.fields || [];
}

function get_order_by_options() {
	return doctype_fields.value.map((f) => ({ label: f.label, value: f.value }));
}

function get_group_by_options() {
	const current = config.group_by || "";
	const parts = current.split(",").map((p) => p.trim());
	// const last_part = parts[parts.length - 1]; // not used yet but good for logic
	const prefix = parts.length > 1 ? parts.slice(0, -1).join(", ") + ", " : "";

	return doctype_fields.value.map((f) => ({
		label: `${prefix}${f.label}`,
		value: `${prefix}${f.value}`,
	}));
}

async function get_variable_options() {
	if (!props.node?.id) return [];
	return await store.getAvailableVariables(props.node.id);
}

function build_order_by() {
	return order_by_rows.value.map((r) => `${r.field} ${r.direction || "asc"}`).join(", ");
}

function sync_local_config() {
	const new_config = {};
	Object.keys(config).forEach((k) => {
		const val = config[k];
		if (val !== undefined && val !== null && val !== "") new_config[k] = val;
	});

	if (mode.value === "Query List" || mode.value === "Query Doc") {
		const fields = build_fields();
		if (fields.length) new_config.fields = fields;

		const order_by = build_order_by();
		if (order_by) new_config.order_by = order_by;
	}

	if (mode.value === "Query Report") {
		const report_name = props.node?.data?.reference_docname || config.report_name;
		if (report_name) {
			new_config.report_name = report_name;
			if (props.node?.data && props.node.data.reference_docname !== report_name) {
				update_action_field("reference_docname", report_name);
			}
		}
		const filters = { ...report_filter_values };
		if (Object.keys(filters).length) new_config.filters = filters;
	}

	// Compare before sending out to avoid loops
	const current_str = JSON.stringify(props.node?.data?.config || {});
	const next_str = JSON.stringify(new_config || {});

	if (current_str !== next_str) {
		is_internal_update.value = true;
		sync_config(new_config);
		// Reset flag after a short delay to allow the prop update to flow back
		setTimeout(() => {
			is_internal_update.value = false;
		}, 150);
	}
}

async function load_report_filters(report_name) {
	if (!report_name || mode.value !== "Query Report") {
		report_filters.value = [];
		Object.keys(report_filter_values).forEach((k) => delete report_filter_values[k]);
		Object.keys(report_filter_types).forEach((k) => delete report_filter_types[k]);
		return;
	}
	try {
		loading.value = true;
		const res = await frappe.call({
			method: "frappe.desk.query_report.get_script",
			args: { report_name: report_name },
		});

		let filters = res.message?.filters || [];
		filters = filters.filter((f) => !f.fieldtype?.includes("Break"));

		if (res.message?.script) {
			try {
				frappe.dom.eval(res.message.script);
				await new Promise((resolve) => setTimeout(resolve, 100));
				const settings = frappe.query_reports[report_name] || {};
				if (settings.filters && settings.filters.length) {
					const map = new Map();
					filters.forEach((f) => map.set(f.fieldname, f));
					settings.filters.forEach((f) => map.set(f.fieldname, f));
					filters = Array.from(map.values());
				}
			} catch (e) {
				console.warn("Failed to extract filters from report script", e);
			}
		}

		if (!filters.length) {
			const report_doc = await frappe.db.get_doc("Report", report_name);
			if (report_doc.filters && report_doc.filters.length) {
				filters = report_doc.filters;
			} else if (report_doc.json) {
				try {
					const data = JSON.parse(report_doc.json);
					filters = data.filters || [];
				} catch (e) {
					// Ignore JSON parse errors
				}
			}
		}

		report_filters.value = filters.map((f) => {
			const mapped = {
				...f,
				fieldname: f.fieldname,
				fieldtype: f.fieldtype || "Data",
				label: f.label || f.fieldname,
			};
			// Dynamically set get_query / get_data callback shims to route options through our adapter context
			if (typeof f.get_query === "function") {
				mapped.get_query = f.get_query;
			}
			if (typeof f.get_data === "function") {
				mapped.get_data = f.get_data;
			}
			return mapped;
		});

		const cfg = props.node?.data?.config || {};
		const saved_filters = cfg.filters || {};
		report_filters.value.forEach((f) => {
			if (saved_filters[f.fieldname] !== undefined) {
				const val = saved_filters[f.fieldname];
				report_filter_values[f.fieldname] =
					val && typeof val === "object" ? JSON.parse(JSON.stringify(val)) : val;
				if (report_filter_types) {
					report_filter_types[f.fieldname] = parse_value_type(val);
				}
			} else {
				report_filter_values[f.fieldname] = f.default || "";
				if (report_filter_types) {
					report_filter_types[f.fieldname] = "Value";
				}
			}
		});

		// Trigger initial execution of report settings callbacks (onload & dependency refreshes)
		nextTick(() => {
			const settings = frappe.query_reports[report_name] || {};
			if (typeof settings.onload === "function") {
				try {
					// Execute onload setup
					settings.onload(query_report_adapter);
				} catch (e) {
					console.warn("Report onload callback failed", e);
				}
			}
			refresh_dependent_filters();
		});
	} catch (e) {
		console.error("Failed to load report filters", e);
	} finally {
		loading.value = false;
	}
}

function update_report_filter(fieldname, value) {
	report_filter_values[fieldname] = value;
	if (report_filter_types) {
		report_filter_types[fieldname] = parse_value_type(value);
	}
	sync_local_config();
	nextTick(() => {
		refresh_dependent_filters();
	});
}

function sortSchemaObjectKeys(value) {
	if (Array.isArray(value)) return value.map(sortSchemaObjectKeys);
	if (!value || typeof value !== "object") return value;
	return Object.fromEntries(
		Object.keys(value)
			.sort()
			.map((key) => [key, sortSchemaObjectKeys(value[key])])
	);
}

function normalizeSchemaForComparison(schema) {
	let value = schema;
	if (typeof value === "string") {
		try {
			value = JSON.parse(value);
		} catch (error) {
			return null;
		}
	}
	if (value != null && !Array.isArray(value)) return null;
	return sortSchemaObjectKeys(normalizeResolvedOutputSchema(Array.isArray(value) ? value : []));
}

function areResolvedSchemasEqual(left, right) {
	const normalizedLeft = normalizeSchemaForComparison(left);
	const normalizedRight = normalizeSchemaForComparison(right);
	if (!Array.isArray(normalizedLeft) || !Array.isArray(normalizedRight)) return false;
	return JSON.stringify(normalizedLeft) === JSON.stringify(normalizedRight);
}

let schemaPreviewRequestId = 0;

async function update_schema_refresh_preview({
	applyIfChanged = false,
	promptIfChanged = false,
} = {}) {
	const requestId = ++schemaPreviewRequestId;
	schema_preview_loading.value = true;
	try {
		const preview = await build_resolved_schema_preview();
		if (requestId !== schemaPreviewRequestId || !schemaEditorMounted) return;
		if (!Array.isArray(preview)) {
			schema_refresh_needed.value = false;
			return;
		}
		const differs = !areResolvedSchemasEqual(props.node?.data?.resolved_output_schema, preview);
		schema_refresh_needed.value = differs;
		if (applyIfChanged && differs && mode.value === "Fetch Records") {
			set_resolved_output_schema(preview);
			schema_refresh_status.value = __("Output schema updated.");
		} else if (
			promptIfChanged &&
			differs &&
			!schemaRefreshPromptShown &&
			!props.readOnly &&
			supportsManualSchemaRefresh.value
		) {
			schemaRefreshPromptShown = true;
			await confirm_schema_refresh();
		}
	} catch (error) {
		console.warn("Failed to compare Query Records output schema", error);
		schema_refresh_needed.value = false;
	} finally {
		if (requestId === schemaPreviewRequestId) schema_preview_loading.value = false;
	}
}

const SCHEMA_REFRESH_CONFIRMATION = __(
	"Refresh the output schema from the current configuration? Downstream actions that reference renamed or removed output fields may need to be reviewed."
);

async function confirm_schema_refresh() {
	if (
		!props.node?.data ||
		props.readOnly ||
		!supportsManualSchemaRefresh.value ||
		schema_refreshing.value ||
		!schema_refresh_needed.value
	) {
		return;
	}
	const confirmed = await new Promise((resolve) => {
		frappe.confirm(
			SCHEMA_REFRESH_CONFIRMATION,
			() => resolve(true),
			() => resolve(false),
			__("Refresh Schema"),
			__("Skip")
		);
	});
	if (!schemaEditorMounted || !confirmed) {
		if (schemaEditorMounted && !confirmed) {
			schema_refresh_status.value = __(
				"Schema refresh skipped. The existing output schema was kept."
			);
		}
		return;
	}
	await apply_schema_refresh();
}

async function apply_schema_refresh() {
	if (
		!props.node?.data ||
		props.readOnly ||
		!supportsManualSchemaRefresh.value ||
		schema_refreshing.value
	) {
		return;
	}
	schema_refreshing.value = true;
	schema_refresh_status.value = __("Checking output schema...");
	try {
		const preview = await build_resolved_schema_preview();
		if (!schemaEditorMounted) return;
		if (!Array.isArray(preview)) {
			schema_refresh_status.value = __(
				"Schema could not be built. Check the selected DocType or report configuration."
			);
			return;
		}
		if (areResolvedSchemasEqual(props.node.data.resolved_output_schema, preview)) {
			schema_refresh_needed.value = false;
			schema_refresh_status.value = __("The output schema is already up to date.");
			return;
		}
		set_resolved_output_schema(preview);
		schema_refresh_needed.value = false;
		schema_refresh_status.value = __("Output schema refreshed.");
	} catch (error) {
		console.warn("Failed to refresh Query Records schema", error);
		schema_refresh_status.value = __(
			"Schema refresh failed. Check the configuration and try again."
		);
	} finally {
		schema_refreshing.value = false;
	}
}

async function refresh_schema_manually() {
	await confirm_schema_refresh();
}

async function test_query() {
	if (!props.node?.data || is_doctype_dynamic.value) return;
	test_status.value = __("Debugging...");
	try {
		const res = await frappe.call({
			method: "flexirule.ruleflow.api.test_action_query",
			args: {
				rule_name: store.rule.name,
				action_id: props.node.id,
				overrides: props.node.data,
			},
		});

		if (res.message) {
			if (mode.value === "Fetch Records") {
				// Fetch Records' configured result shape is more reliable than sample
				// rows: empty queries and aggregate results must keep their schema.
				await update_fetch_records_schema_local();
			} else {
				set_resolved_output_schema(res.message.schema || []);
			}
			test_status.value = __("Success");
		}
	} catch (e) {
		test_status.value = __("Failed");
	}
}

const debounced_schema_update = flexirule.utils.debounce(async function update_resolved_schema() {
	// Fetch Records has an immediate metadata-based schema for all result shapes.
	// A sample execution can return [] when there are no matching rows and must
	// not erase that schema.
	if (!props.node?.data || mode.value === "Fetch Records") return;
	try {
		const res = await frappe.call({
			method: "flexirule.ruleflow.api.test_action_query",
			args: {
				rule_name: store.rule.name,
				action_id: props.node.id,
				overrides: props.node.data,
			},
			silent: true,
		});

		if (res.message && res.message.schema) {
			// Deep check to avoid spam
			const current = JSON.stringify(props.node.data.resolved_output_schema || []);
			const next = JSON.stringify(res.message.schema || []);
			if (current !== next) {
				set_resolved_output_schema(res.message.schema);

				const isDraft = !store.nodes.some((n) => n === props.node);
				if (!isDraft) {
					store.mark_dirty();
				}
			}
		}
	} catch (e) {
		// silent error
	}
}, 500);

function get_field_options() {
	return variable_options.value;
}

function load_local_config(val) {
	const parsed = typeof val === "string" ? fromCodeString(val) : val || {};

	const current_config_str = JSON.stringify(config);
	const next_config_str = JSON.stringify(parsed);

	if (current_config_str !== next_config_str) {
		Object.keys(config).forEach((k) => delete config[k]);
		Object.assign(config, parsed);

		if (!config.filters) {
			config.filters = mode.value === "Query Report" ? {} : [];
		}
		if (!config.limit && mode.value === "Query List") config.limit = 20;
	}

	if (mode.value === "Query Report") {
		const r_filters = parsed.filters || {};
		Object.entries(r_filters).forEach(([k, v]) => {
			report_filter_values[k] = v;
			report_filter_types[k] = parse_value_type(v);
		});
	}

	const order_by = parsed.order_by || "";
	const next_order_by_rows = order_by
		? order_by.split(",").map((s) => {
				const parts = s.trim().split(/\s+/);
				return {
					field: parts[0],
					direction: (parts[1] || "asc").toLowerCase(),
				};
		  })
		: [];
	const current_order_by_rows = order_by_rows.value.map((r) => ({
		field: r.field,
		direction: r.direction,
	}));
	if (JSON.stringify(next_order_by_rows) !== JSON.stringify(current_order_by_rows)) {
		order_by_rows.value = next_order_by_rows;
	}
}

// Keep serialized config in sync with local controls, but do not refresh the
// schema merely because an unrelated query option changed.
watch(
	() => [
		order_by_rows.value,
		config,
		report_filter_values,
		mode.value,
		reference_doctype.value,
		props.node?.data?.reference_docname,
	],
	() => {
		const previousSignature = lastSchemaRefreshSignature;
		const beforeSyncSignature = getSchemaRefreshSignature();
		if (previousSignature === null) {
			lastSchemaRefreshSignature = beforeSyncSignature;
			return;
		}
		const dependenciesChangedBeforeSync = beforeSyncSignature !== previousSignature;
		lastSchemaRefreshSignature = beforeSyncSignature;

		if (!is_internal_update.value) {
			sync_local_config();
		}

		const afterSyncSignature = getSchemaRefreshSignature();
		const dependenciesChangedDuringSync = afterSyncSignature !== lastSchemaRefreshSignature;
		lastSchemaRefreshSignature = afterSyncSignature;

		// A dependency change made while restoring the modal is initialization,
		// not a user edit. Afterwards, relevant changes refresh even if the config
		// synchronization guard is active for the same edit.
		if (
			schemaRefreshInitialized &&
			schemaRefreshReady.value &&
			(dependenciesChangedBeforeSync || dependenciesChangedDuringSync)
		) {
			if (mode.value !== "Fetch Records") {
				fetch_records_schema_request_id += 1;
			}
			if (mode.value === "Fetch Records") {
				// Rebuild from user-edited output fields even if the config update is
				// still marked internal by the serialization loop guard.
				void update_schema_refresh_preview({ applyIfChanged: true });
			} else {
				void update_resolved_schema_local();
				debounced_schema_update();
			}
		}
	},
	{ deep: true }
);

async function validate() {
	showValidation.value = true;
	const errors = [];

	// 1. Core Control Validation (Aggregated)
	const results = await Promise.all(
		(controlRefs.value || []).map((ctrl) => {
			if (ctrl && typeof ctrl.validate === "function") {
				return ctrl.validate();
			}
			return { valid: true };
		})
	);
	results.forEach((res) => {
		if (!res.valid && res.errors) errors.push(...res.errors);
	});

	// 2. Validate filters for the active query editor.
	if (mode.value === "Fetch Records") {
		if (fetchRecordsConfigRef.value?.validate) {
			const res = await fetchRecordsConfigRef.value.validate();
			if (!res.valid) errors.push(...res.errors);
		}
	} else if (filterGroupRef.value && typeof filterGroupRef.value.validate === "function") {
		const res = await filterGroupRef.value.validate();
		if (!res.valid) errors.push(...res.errors);
	}

	// 3. Logic-based Validation
	if (mode.value === "Query List") {
		if (!reference_doctype.value) {
			errors.push(__("Reference DocType is required for Query List"));
		}
	}

	if (mode.value === "Query Report") {
		if (!props.node?.data?.reference_docname) {
			errors.push(__("Report Name is required"));
		}
	}

	// 4. Permission Audit Reason (Global check, though child CheckControl should handle reqd)
	if (
		effectiveIgnorePermissions.value &&
		!String(props.node?.data?.permission_audit_reason ?? "").trim()
	) {
		errors.push(__("Permission Audit Reason is required when bypassing permissions."));
	}

	// Persist the Frappe 15 default only when the user is saving a valid edit.
	// Merely opening the modal must not mutate the action or dirty-state baseline.
	if (
		!errors.length &&
		!props.readOnly &&
		mode.value === "Fetch Records" &&
		isFrappe15.value &&
		![true, 1, "1"].includes(props.node?.data?.ignore_permissions)
	) {
		props.node.data.ignore_permissions = 1;
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({
	validate,
});
</script>

<style scoped>
.permission-control-row {
	display: flex;
	align-items: flex-start;
	flex-wrap: wrap;
	column-gap: var(--fxr-space-2, 8px);
}
.permission-control-row > :first-child {
	flex: 1 1 240px;
	min-width: 0;
}
.fetch-records-permission-notice {
	display: inline-flex;
	align-items: center;
	flex: 0 1 auto;
	gap: 4px;
	margin-top: 4px;
	color: var(--fxr-warning-text, #875b00);
	font-size: var(--fxr-text-xs, 11px);
	line-height: 1.35;
}
.fetch-records-permission-notice > i {
	flex: 0 0 auto;
}
.permission-notice-details {
	position: relative;
	font-size: inherit;
}
.permission-notice-details summary {
	cursor: pointer;
	white-space: nowrap;
	font-weight: 600;
}
.permission-notice-details p {
	position: absolute;
	z-index: 5;
	top: 100%;
	right: 0;
	width: min(320px, 75vw);
	margin: 5px 0 0;
	padding: 8px 10px;
	border: 1px solid var(--fxr-border-color, #d1d5db);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-surface, #fff);
	color: var(--fxr-text-color, #374151);
	box-shadow: 0 4px 12px rgb(0 0 0 / 10%);
	white-space: normal;
	font-size: var(--fxr-text-sm, 12px);
	line-height: 1.45;
}
/* ─── QueryRecordsConfig – Unified Design ─── */
.query-config {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
	font-family: var(--fxr-font-family);
}

.config-section {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.sub-section h6 {
	margin: 0;
	font-size: 13px;
	font-weight: 600;
	color: var(--fxr-text-strong);
	letter-spacing: 0.02em;
}

.order-by-row {
	display: flex;
	align-items: center;
	gap: var(--spacing-md);
	width: 100%;
}

.direction-select {
	flex: 0 0 100px;
	width: 100px !important;
	min-width: 100px;
}

.remove-sort-btn {
	width: 32px;
	height: 32px;
	padding: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: var(--fxr-radius-sm);
	opacity: 0.6;
	transition: all var(--fxr-transition-fast);
	flex-shrink: 0;
}

.remove-sort-btn:hover {
	opacity: 1;
	background-color: var(--fxr-bg-danger);
	text-decoration: none;
}

.section-card {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	padding: var(--spacing-md);
	background-color: var(--fxr-surface);
}

.section-subcard {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	padding: var(--spacing-md);
	background-color: var(--fxr-surface-soft);
}

.sub-section {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.query-doc-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: var(--spacing-md);
	align-items: start;
}

.retrieval-checkboxes {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.grid-item {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.table-rows {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

.row-item {
	display: grid;
	grid-template-columns: 1.4fr 0.8fr 1.6fr 0.8fr auto;
	gap: var(--spacing-sm);
	align-items: center;
}

.row-item.report-filter-row {
	grid-template-columns: 1fr 2fr;
	padding: var(--fxr-space-2) 0;
	border-bottom: 1px solid var(--fxr-bg-muted);
}

.filter-label-group {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-4);
}

.filter-label {
	margin: 0;
	font-size: var(--fxr-text-base);
	color: var(--fxr-text-secondary);
	font-weight: var(--fxr-weight-medium);
}

.filter-label.reqd::after {
	content: " *";
	color: var(--fxr-text-danger, #ef4444);
	font-weight: bold;
}

.expression-input-group {
	display: flex;
	align-items: center;
	background-color: var(--fxr-badge-expr);
	border-radius: var(--fxr-radius-md);
	padding: 0 var(--fxr-space-4);
	border: 1px solid var(--fxr-border-focus);
	transition: border-color var(--fxr-transition-fast);
}

.expression-input-group:focus-within {
	border-color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-focus);
}

.expr-prefix,
.expr-suffix {
	font-weight: var(--fxr-weight-bold);
	color: var(--fxr-badge-expr-text);
	user-select: none;
}

.field-picker-container {
	position: relative;
	flex: 1;
	display: flex;
	align-items: center;
}

.field-warning-icon {
	position: absolute;
	right: 30px;
	z-index: 5;
	pointer-events: all;
	cursor: help;
	font-size: var(--fxr-text-sm);
}

:deep(.border-warning .form-control) {
	border-color: var(--fxr-border-focus) !important;
	background-color: var(--fxr-badge-resolver) !important;
}

.field-row {
	display: flex;
	align-items: center;
	gap: var(--spacing-sm);
}

:deep(.field-picker-control) {
	margin-bottom: 0 !important;
}

:deep(.control.frappe-control) {
	margin-bottom: 0 !important;
}

/* ─── Unified input sizing inside QRC ─── */
:deep(.form-control),
:deep(input.form-control),
:deep(select.form-control) {
	height: var(--fxr-input-height) !important;
	padding: var(--fxr-input-padding-y) var(--fxr-input-padding-x) !important;
	font-size: var(--fxr-input-font-size) !important;
	border: 1px solid var(--fxr-border) !important;
	border-radius: var(--fxr-radius-md) !important;
	background-color: var(--fxr-bg-input) !important;
	color: var(--fxr-text) !important;
	transition: border-color var(--fxr-transition-fast), box-shadow var(--fxr-transition-fast) !important;
}

:deep(.form-control:focus) {
	border-color: var(--fxr-border-focus) !important;
	box-shadow: var(--fxr-shadow-focus) !important;
}

:deep(.form-control:hover:not(:disabled):not(:focus)) {
	border-color: var(--fxr-border-strong) !important;
}

:deep(select.form-control) {
	appearance: none !important;
	-webkit-appearance: none !important;
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E") !important;
	background-repeat: no-repeat !important;
	background-position: right 6px center !important;
	background-size: 12px !important;
	padding-right: 24px !important;
	cursor: pointer;
}
</style>
