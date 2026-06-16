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
				<ControlFactory
					:df="{
						fieldname: 'skip_permissions',
						fieldtype: 'Check',
						label: __('Skip Permissions'),
						description: __(
							'Bypass read permissions for this action. Requires audit reason.'
						),
						read_only: readOnly,
					}"
					:modelValue="node?.data?.skip_permissions"
					@update:modelValue="(val) => update_action_key('skip_permissions', val)"
				/>
				<ControlFactory
					v-if="!!node?.data?.skip_permissions"
					:df="{
						fieldname: 'permission_audit_reason',
						fieldtype: 'Small Text',
						label: __('Permission Audit Reason'),
						read_only: readOnly,
					}"
					:modelValue="node?.data?.permission_audit_reason"
					@update:modelValue="(val) => update_action_key('permission_audit_reason', val)"
				/>
			</div>

			<!-- Configuration based on selected Mode -->
			<template v-if="mode === 'Query List'">
				<div class="sub-section section-subcard">
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
						:nodeId="node?.id"
						:variableOptions="variable_options"
						@update:modelValue="(val) => update_config_key('filters', val)"
					/>
				</div>

				<div class="sub-section section-subcard">
					<MultiSelectList
						:df="{
							label: __('Fields'),
							fieldname: 'fields',
							placeholder: __('Select fields to fetch...'),
						}"
						:options="doctype_fields"
						:modelValue="config.fields || []"
						:read_only="readOnly"
						@update:modelValue="(val) => update_config_key('fields', val)"
					/>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Order By") }}</h6>
					<div class="table-rows">
						<div
							v-for="(row, idx) in order_by_rows"
							:key="idx"
							class="row-item field-row"
						>
							<ComboBoxControl
								:df="{ label: '', fieldtype: 'FieldPicker' }"
								:options="doctype_fields"
								:doctype="reference_doctype"
								:modelValue="row.field"
								:read_only="readOnly"
								:trigger="'button'"
								:hideLabel="true"
								class="flex-1"
								:class="{
									'border-warning':
										row.field && !is_field_valid(row.field, doctype_fields),
								}"
								@update:modelValue="(val) => (row.field = val)"
							/>
							<select
								class="form-control input-xs ml-2"
								style="width: 80px"
								v-model="row.direction"
								:disabled="readOnly"
							>
								<option value="asc">{{ __("ASC") }}</option>
								<option value="desc">{{ __("DESC") }}</option>
							</select>
							<button
								v-if="!readOnly"
								class="btn btn-xs btn-link text-danger"
								@click="remove_order_by(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
						<button v-if="!readOnly" class="btn btn-xs btn-link" @click="add_order_by">
							<i class="fa fa-plus"></i> {{ __("Add Sort Criteria") }}
						</button>
					</div>
				</div>

				<div class="sub-section section-subcard">
					<h6>{{ __("Retrieval Settings") }}</h6>
					<div class="query-doc-grid">
						<div class="grid-item">
							<ControlFactory
								:df="with_read_only(limitTypeField)"
								:modelValue="config.limit_type || 'Custom Limit'"
								@update:modelValue="(val) => update_config_key('limit_type', val)"
							/>
						</div>
						<div
							v-if="(config.limit_type || 'Custom Limit') === 'Custom Limit'"
							class="grid-item"
						>
							<ControlFactory
								:df="with_read_only(limitField)"
								:modelValue="config.limit"
								@update:modelValue="(val) => update_config_key('limit', val)"
							/>
						</div>
						<div class="grid-item">
							<label class="control-label small">{{ __("Group By") }}</label>
							<ComboBoxControl
								:df="{ label: '', fieldtype: 'Autocomplete' }"
								:modelValue="config.group_by"
								:get_query="get_group_by_options"
								:read_only="readOnly"
								:hideLabel="true"
								:showOnFocus="true"
								@update:modelValue="update_config_key('group_by', $event)"
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
								:df="{
									fieldname: 'fetch_strategy',
									fieldtype: 'Select',
									label: __('Fetch Strategy'),
									options: [
										'Get Doc from Cache',
										'Get doc',
										'Get Single DocType',
										'Get latest Doc',
									],
									read_only: readOnly,
								}"
								:modelValue="config.fetch_strategy || 'Get doc'"
								@update:modelValue="
									(val) => update_config_key('fetch_strategy', val)
								"
							/>
						</div>

						<div class="grid-item">
							<label class="control-label small">{{ __("DocType Name") }}</label>
							<FlexValueControl
								:modelValue="config.doctype_name"
								:variableOptions="variable_options"
								:readOnly="readOnly"
								:context="{
									df: { fieldtype: 'Link', options: 'DocType' },
								}"
								@update:modelValue="update_doctype_name"
							/>
						</div>

						<div v-if="show_docname_field" class="grid-item">
							<label class="control-label small">{{
								__("Document Name (ID)")
							}}</label>
							<FlexValueControl
								:modelValue="config.docname"
								:variableOptions="variable_options"
								:readOnly="readOnly"
								:context="{
									df: { fieldtype: 'Link', options: reference_doctype },
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
				>
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
						:nodeId="node?.id"
						:variableOptions="variable_options"
						@update:modelValue="(val) => update_config_key('filters', val)"
					/>
				</div>
			</template>

			<template v-else-if="mode === 'Exist Record'">
				<div class="sub-section section-subcard">
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
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
								<label class="filter-label">{{ df.label }}</label>
								<div class="filter-type-toggle">
									<button
										class="btn btn-xs btn-link p-0"
										:class="{
											active:
												report_filter_types[df.fieldname] === 'Expression',
										}"
										@click="toggle_report_filter_type(df.fieldname)"
										:title="__('Toggle Expression')"
									>
										<span class="extra-small font-weight-bold">{{
											report_filter_types[df.fieldname] === "Expression"
												? "{ }"
												: "abc"
										}}</span>
									</button>
								</div>
							</div>

							<div class="filter-input-wrapper">
								<template v-if="report_filter_types[df.fieldname] === 'Expression'">
									<div class="expression-input-group">
										<span class="expr-prefix">{</span>
										<ComboBoxControl
											:df="{
												fieldtype: 'Autocomplete',
												label: '',
												read_only: readOnly,
											}"
											:modelValue="
												strip_expression(report_filter_values[df.fieldname])
											"
											:get_query="get_variable_options"
											:placeholder="__('variable')"
											:read_only="readOnly"
											:hideLabel="true"
											@update:modelValue="
												report_filter_values[df.fieldname] = `{${$event}}`;
												sync_local_config();
											"
										/>
										<span class="expr-suffix">}</span>
									</div>
								</template>
								<template v-else>
									<ControlFactory
										:df="{ ...with_read_only(df), label: '' }"
										:modelValue="report_filter_values[df.fieldname]"
										@update:modelValue="
											update_report_filter(df.fieldname, $event)
										"
									/>
								</template>
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
				<div class="sub-section section-subcard">
					<h6>{{ __("Filters") }}</h6>
					<FilterGroup
						:doctype="reference_doctype"
						:modelValue="config.filters"
						:readOnly="readOnly"
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
										:df="{ ...fieldField, fieldtype: 'FieldPicker' }"
										:options="doctype_fields"
										:doctype="reference_doctype"
										:modelValue="config.field"
										:read_only="readOnly"
										:trigger="'button'"
										:hideLabel="true"
										:class="{
											'border-warning':
												config.field &&
												!is_field_valid(config.field, doctype_fields),
										}"
										@update:modelValue="
											(val) => update_config_key('field', val)
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
										:df="{ ...aggGroupByField, fieldtype: 'FieldPicker' }"
										:options="doctype_fields"
										:doctype="reference_doctype"
										:modelValue="config.group_by_field"
										:read_only="readOnly"
										:trigger="'button'"
										:hideLabel="true"
										:class="{
											'border-warning':
												config.group_by_field &&
												!is_field_valid(
													config.group_by_field,
													doctype_fields
												),
										}"
										@update:modelValue="
											(val) => update_config_key('group_by_field', val)
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
										:df="{ ...aggFieldField, fieldtype: 'FieldPicker' }"
										:options="doctype_fields"
										:doctype="reference_doctype"
										:modelValue="config.agg_field"
										:read_only="readOnly"
										:trigger="'button'"
										:hideLabel="true"
										:class="{
											'border-warning':
												config.agg_field &&
												!is_field_valid(config.agg_field, doctype_fields),
										}"
										@update:modelValue="
											(val) => update_config_key('agg_field', val)
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
			<button
				class="btn btn-xs btn-primary shadow-sm"
				@click="test_query"
				:disabled="readOnly"
				tabindex="0"
			>
				<i class="fa fa-flask mr-1"></i> {{ __("Refresh Schema (Debug Query)") }}
			</button>
			<span v-if="test_status" class="ml-2 text-muted font-weight-bold">{{
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
import { reactive, ref, computed, watch, onMounted } from "vue";
import { fromCodeString } from "../../../utils/serialization";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import FilterGroup from "../FilterGroup.vue";
import MultiSelectList from "../../../controls/MultiSelectList.vue";
import { useNodeConfigPolicy } from "../../../composables/useNodeConfigPolicy";

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
const { getPolicyField } = useNodeConfigPolicy({
	actionType: () => props.node?.data?.action_type || "Query Records",
	operation: mode,
	processName: () => props.node?.data?.process_name || "",
});

// Local state for UI controls
const order_by_rows = ref([]);
const report_filters = ref([]);
const report_filter_values = reactive({});
const report_filter_types = reactive({});
const test_status = ref("");
const is_single_doctype = ref(false);

// Internal flag to prevent recursive sync loops
let is_internal_update = false;

// Initialize local config
onMounted(async () => {
	is_internal_update = true;
	try {
		load_local_config(props.node?.data?.config);
		if (reference_doctype.value) {
			await loadDocMeta(reference_doctype.value);
			await load_doctype_fields(reference_doctype.value);

			const meta = await flexirule.utils.get_doctype_meta(reference_doctype.value);
			is_single_doctype.value = !!meta?.issingle;
		}
		// Ensure schema is initialized on first load even before any user edits.
		// This avoids empty OutputPanel schema when config already has selected fields.
		await update_resolved_schema_local();
		await refresh_variables();
		await debounced_schema_update();
	} finally {
		is_internal_update = false;
	}
});

// Watch for external config changes
watch(
	() => props.node?.data?.config,
	(val) => {
		if (!is_internal_update) {
			load_local_config(val);
		}
	}
);

// Watch for doctype changes to reload meta
watch(
	() => reference_doctype.value,
	async (val, oldVal) => {
		if (val && val !== oldVal) {
			await loadDocMeta(val);
			await load_doctype_fields(val);
			// Only sync if this was a user change (not during initial mount)
			if (!is_internal_update) {
				// Clear filters when DocType changes
				if (Array.isArray(config.filters)) {
					config.filters = [];

					// Re-initialize for Query Doc if not single
					if (mode.value === "Query Doc") {
						const meta = await flexirule.utils.get_doctype_meta(val);
						if (meta && !meta.issingle) {
							config.filters = [[val, "name", "=", { mode: "static", value: "" }]];
						}
					}
				} else if (typeof config.filters === "object") {
					config.filters = {};
				}
				sync_local_config();
			}
		}
	}
);

// Sync local config changes back to node (handled by debounced_sync)

// Shim for frappe.query_report to support report JS scripts that use it
if (!window.frappe.query_report) {
	window.frappe.query_report = {
		get_filter_value: (name) => report_filter_values[name] || "",
		set_filter_value: (name, val) => {
			report_filter_values[name] = val;
			sync_local_config();
		},
	};
}

function evaluate_depends_on(expression, values) {
	if (!expression) return true;
	if (typeof expression === "boolean") return expression;

	if (typeof expression === "string" && expression.startsWith("eval:")) {
		try {
			return frappe.utils.eval(expression.substring(5), {
				doc: values,
				values,
			});
		} catch (e) {
			return false;
		}
	} else if (typeof expression === "string") {
		return !!values[expression];
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

function toggle_report_filter_type(fieldname) {
	const current = report_filter_types[fieldname];
	const new_state = current === "Expression" ? "Value" : "Expression";
	report_filter_types[fieldname] = new_state;

	if (new_state === "Expression") {
		report_filter_values[fieldname] = "{}";
	} else {
		report_filter_values[fieldname] = "";
	}
	sync_local_config();
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

function isVariableSyntax(val) {
	return (
		typeof val === "string" &&
		(val.startsWith("@") || val.startsWith("doc.") || val.startsWith("vars."))
	);
}

/**
 * Local metadata-based schema detection.
 * Provides instant feedback for Query List and Query Doc modes.
 */
async function update_resolved_schema_local() {
	if (!props.node?.data) return;

	if (mode.value === "Query List" || mode.value === "Query Doc") {
		const is_query_doc = mode.value === "Query Doc";
		const fields = (config.fields || []).filter((f) => f);

		if (!is_query_doc && !fields.length) {
			props.node.data.resolved_output_schema = [];
			return;
		}

		const schema = [];
		const target_doctype = reference_doctype.value;
		if (!target_doctype || is_doctype_dynamic.value) {
			if (is_doctype_dynamic.value) {
				props.node.data.resolved_output_schema = [
					{ label: __("Dynamic Object"), fieldname: "doc", fieldtype: "JSON" },
				];
			}
			return;
		}

		const meta = await flexirule.utils.get_doctype_meta(target_doctype);
		if (!meta) return;

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
							options: df.options,
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
										options: cf.options,
									});
								}
							});
						}
					} else {
						schema.push({
							label: df.label,
							fieldname: f,
							fieldtype: df.fieldtype,
							options: df.options,
						});
					}
				}
			}
		}

		props.node.data.resolved_output_schema = schema;
		store.mark_dirty();
	} else if (mode.value === "Query Report" && props.node?.data?.reference_docname) {
		await update_report_columns();
	}
}

async function update_report_columns() {
	if (mode.value !== "Query Report" || !props.node?.data?.reference_docname) return;

	try {
		const report_name = props.node.data.reference_docname;
		const res = await frappe.call({
			method: "frappe.desk.query_report.run",
			args: {
				report_name: report_name,
				filters: report_filter_values,
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
						fieldtype: fieldtype,
						options: options,
					};
				}
				return {
					label: c.label || c.fieldname,
					fieldname: c.fieldname,
					fieldtype: c.fieldtype || "Data",
					options: c.options,
				};
			});
			props.node.data.resolved_output_schema = schema;
			store.mark_dirty();
		}
	} catch (e) {
		console.warn("Failed to update report columns", e);
	}
}

function resolveFieldPolicy(fieldname, fallback) {
	return with_read_only(getPolicyField(fieldname, fallback));
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

const is_doctype_dynamic = computed(() => {
	const val = config.doctype_name;
	if (!val) return false;
	if (typeof val === "object") return val.mode !== "static";
	return false;
});

const show_docname_field = computed(() => {
	if (config.fetch_strategy === "Get latest Doc") return false;
	if (config.fetch_strategy === "Get Single DocType") return false;
	if (is_single_doctype.value) return false;
	return true;
});

async function update_doctype_name(val) {
	config.doctype_name = val;

	const is_dynamic =
		val && typeof val === "object" ? val.mode !== "static" : isVariableSyntax(val);

	if (is_dynamic) {
		update_action_field("reference_doctype", "");
		is_single_doctype.value = false;
	} else {
		const dt_name = typeof val === "object" ? val.value : val;
		update_action_field("reference_doctype", dt_name);

		if (dt_name) {
			const meta = await flexirule.utils.get_doctype_meta(dt_name);
			is_single_doctype.value = !!meta?.issingle;
		} else {
			is_single_doctype.value = false;
		}
	}
	sync_local_config();
}

function update_config_key(key, value) {
	config[key] = value;
	sync_local_config();
}

function update_action_key(key, value) {
	if (!props.node?.data) return;
	props.node.data[key] = value;
}

// Watch for operation changes directly to handle Report special case
watch(
	() => mode.value,
	async (newMode) => {
		if (newMode === "Query Report" && props.node?.data) {
			if (props.node.data.reference_doctype !== "Report") {
				update_action_field("reference_doctype", "Report");
			}
		}

		if (newMode === "Query Doc" && !is_internal_update) {
			// Initialize filters if empty
			if (!config.filters || (Array.isArray(config.filters) && config.filters.length === 0)) {
				const doctype = reference_doctype.value;
				if (doctype) {
					const meta = await flexirule.utils.get_doctype_meta(doctype);
					if (meta && !meta.issingle) {
						config.filters = [[doctype, "name", "=", { mode: "static", value: "" }]];
						sync_local_config();
					}
				}
			}
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
		if (report_name) new_config.report_name = report_name;
		const filters = { ...report_filter_values };
		if (Object.keys(filters).length) new_config.filters = filters;
	}

	// Compare before sending out to avoid loops
	const current_str = JSON.stringify(props.node?.data?.config || {});
	const next_str = JSON.stringify(new_config || {});

	if (current_str !== next_str) {
		is_internal_update = true;
		sync_config(new_config);
		// Reset flag after a short delay to allow the prop update to flow back
		setTimeout(() => {
			is_internal_update = false;
		}, 150);
	}
}

const debounced_sync = flexirule.utils.debounce(sync_local_config, 300);

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

		report_filters.value = filters.map((f) => ({
			...f,
			fieldname: f.fieldname,
			fieldtype: f.fieldtype || "Data",
			label: f.label || f.fieldname,
		}));

		const cfg = props.node?.data?.config || {};
		const saved_filters = cfg.filters || {};
		report_filters.value.forEach((f) => {
			if (saved_filters[f.fieldname] !== undefined) {
				const val = saved_filters[f.fieldname];
				report_filter_values[f.fieldname] = val;
				report_filter_types[f.fieldname] = parse_value_type(val);
			} else {
				report_filter_values[f.fieldname] = f.default || "";
				report_filter_types[f.fieldname] = "Value";
			}
		});
	} catch (e) {
		console.error("Failed to load report filters", e);
	} finally {
		loading.value = false;
	}
}

function update_report_filter(fieldname, value) {
	report_filter_values[fieldname] = value;
	report_filter_types[fieldname] = parse_value_type(value);
	sync_local_config();
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
			props.node.data.resolved_output_schema = res.message.schema || [];
			test_status.value = __("Success");
			store.mark_dirty();
		}
	} catch (e) {
		test_status.value = __("Failed");
	}
}

const debounced_schema_update = flexirule.utils.debounce(async function update_resolved_schema() {
	if (!props.node?.data) return;
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
				props.node.data.resolved_output_schema = res.message.schema;
				store.mark_dirty();
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

// Unified watch for all local state changes
watch(
	() => [order_by_rows.value, config, report_filter_values, mode.value, reference_doctype.value],
	() => {
		if (!is_internal_update) {
			debounced_sync();
			update_resolved_schema_local();
			debounced_schema_update();
		}
	},
	{ deep: true }
);

defineExpose({
	validate: () => ({ valid: true }),
});
</script>

<style scoped>
/* ─── QueryRecordsConfig – Unified Design ─── */
.query-config {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-8);
	font-family: var(--fxr-font-family);
}

.config-section {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-6);
}

.section-card {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-xl);
	padding: var(--fxr-space-6);
	background-color: var(--fxr-bg-card);
}

.section-subcard {
	border: 1px dashed var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
	padding: var(--fxr-space-5);
}

.sub-section {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-4);
}

.query-doc-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
	gap: var(--fxr-space-4);
	align-items: flex-end;
}

.grid-item {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
}

.table-rows {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

.row-item {
	display: grid;
	grid-template-columns: 1.4fr 0.8fr 1.6fr 0.8fr auto;
	gap: var(--fxr-space-3);
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
	gap: var(--fxr-space-4);
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
	transition:
		border-color var(--fxr-transition-fast),
		box-shadow var(--fxr-transition-fast) !important;
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
