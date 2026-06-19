<template>
	<div class="create-docs-config">
		<div v-if="!mode" class="empty-mode-state text-center p-5">
			<i class="fa fa-plus-circle fa-3x text-muted mb-3 opacity-20"></i>
			<p class="text-muted">
				{{ __("Please select a Creation Mode in the Setup panel to proceed.") }}
			</p>
		</div>

		<div v-else class="config-container">
			<div class="sub-section section-subcard">
				<h6>{{ __("Execution Permission") }}</h6>
				<ControlFactory
					:ref="setControlRef"
					:df="{
						fieldname: 'skip_permissions',
						fieldtype: 'Check',
						label: __('Skip Permissions'),
						description: __(
							'Bypass write/delete permissions for this action. Requires audit reason.'
						),
						read_only: readOnly,
					}"
					:modelValue="node?.data?.skip_permissions"
					@update:modelValue="(val) => update_action_key('skip_permissions', val)"
				/>
				<ControlFactory
					v-if="!!node?.data?.skip_permissions"
					:ref="setControlRef"
					:df="{
						fieldname: 'permission_audit_reason',
						fieldtype: 'Small Text',
						label: __('Permission Audit Reason'),
						read_only: readOnly,
						reqd: 1,
					}"
					:modelValue="node?.data?.permission_audit_reason"
					:showValidation="showValidation"
					@update:modelValue="(val) => update_action_key('permission_audit_reason', val)"
				/>
			</div>

			<template v-if="mode === 'Create ToDo'">
				<div class="assign-to-group">
					<div class="d-flex align-items-center gap-2 mb-1">
						<label class="control-label small mb-0">{{ __("Assigned To") }}</label>
						<SelectControl
							v-if="!readOnly"
							class="assign-type-select"
							:df="{
								label: '',
								options: 'Value\nVariable\nExpression',
							}"
							v-model="assignToType"
							:hideLabel="true"
							@change="onAssignToTypeChange"
						/>
					</div>
					<ControlFactory
						v-if="assignToType === 'Value'"
						:ref="setControlRef"
						:df="with_read_only(assignedToLinkField)"
						:modelValue="stripBrackets(config.assigned_to)"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('assigned_to', val)"
					/>
					<ComboBoxControl
						v-else-if="assignToType === 'Variable'"
						:ref="setControlRef"
						fieldname="assigned_to"
						:df="{
							fieldtype: 'Autocomplete',
							label: '',
							reqd: requiredConfigKeys.includes('assigned_to') ? 1 : 0,
						}"
						:get_query="async () => variable_options"
						:modelValue="stripBrackets(config.assigned_to)"
						:read_only="readOnly"
						:hideLabel="true"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('assigned_to', `{${val}}`)"
					/>
					<ControlFactory
						v-else
						:ref="setControlRef"
						:df="with_read_only(assignedToExprField)"
						:modelValue="config.assigned_to"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('assigned_to', val)"
					/>
				</div>
				<ControlFactory
					:ref="setControlRef"
					:df="with_read_only(todoDescriptionField)"
					:modelValue="config.description"
					:showValidation="showValidation"
					@update:modelValue="(val) => update_config_key('description', val)"
				/>
				<ControlFactory
					:ref="setControlRef"
					:df="with_read_only(todoPriorityField)"
					:modelValue="config.priority"
					@update:modelValue="(val) => update_config_key('priority', val)"
				/>
			</template>

			<template v-else-if="mode === 'Add Comment'">
				<ControlFactory
					:ref="setControlRef"
					:df="with_read_only(commentTypeField)"
					:modelValue="config.comment_type"
					@update:modelValue="(val) => update_config_key('comment_type', val)"
				/>
				<ControlFactory
					:ref="setControlRef"
					:df="with_read_only(commentTextField)"
					:modelValue="config.comment_text"
					:showValidation="showValidation"
					@update:modelValue="(val) => update_config_key('comment_text', val)"
				/>
			</template>

			<template v-else-if="['Update Existing', 'Delete Record'].includes(mode)">
				<ControlFactory
					:ref="setControlRef"
					:df="with_read_only(docnameExprField)"
					:modelValue="config.docname_expression"
					@update:modelValue="(val) => update_config_key('docname_expression', val)"
				/>
				<div class="alert alert-info py-2 px-3 small mt-2">
					<i class="fa fa-info-circle"></i>
					{{ __("Reference DocName is managed in the Setup & Input panel.") }}
				</div>
			</template>

			<div v-if="showMapper" class="sub-section section-subcard">
				<div class="d-flex justify-content-between align-items-center mb-2">
					<h6 class="mb-0">{{ __("Resource Mapper") }}</h6>
					<div class="btn-group">
						<button
							class="btn btn-xs"
							:class="mapperView === 'classic' ? 'btn-primary' : 'btn-default'"
							@click="mapperView = 'classic'"
						>
							{{ __("Classic") }}
						</button>
						<button
							class="btn btn-xs"
							:class="mapperView === 'visual' ? 'btn-primary' : 'btn-default'"
							@click="mapperView = 'visual'"
						>
							{{ __("Visual") }}
						</button>
					</div>
				</div>

				<ResourceMapperControl
					v-if="mapperView === 'classic'"
					:ref="setControlRef"
					:df="mapperField"
					:modelValue="config.resource_mapper_ui"
					:targetDoctype="reference_doctype"
					:sourceOptions="variable_options"
					:read_only="readOnly"
					:hideLabel="true"
					:showValidation="showValidation"
					@update:modelValue="update_mapper_ui"
				/>

				<TransformControl
					v-else
					:ref="setControlRef"
					fieldname="resource_mapper_ui"
					:modelValue="visualMappings"
					:sourceSchema="sourceSchema"
					:targetSchema="targetSchema"
					:readOnly="readOnly"
					:showValidation="showValidation"
					@update:modelValue="update_visual_mappings"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUpdate } from "vue";
import { fromCodeString } from "../../../utils/serialization";
import { useActionConfig } from "../../../composables/useActionConfig";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import ControlFactory from "../../../controls/ControlFactory.vue";
import SelectControl from "../../../controls/SelectControl.vue";
import ResourceMapperControl from "../../../controls/ResourceMapperControl.vue";
import TransformControl from "../../../controls/TransformControl.vue";
import transformUtils from "../../../utils/transform.js";
import { getEffectiveActionPolicy } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const showValidation = ref(false);
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

const { config, variable_options, mode, reference_doctype, with_read_only, sync_config } =
	useActionConfig(props);

const mapperField = {
	fieldname: "resource_mapper_ui",
	fieldtype: "Resource Mapper",
	label: __("Resource Mapper"),
	description: __(
		"Builder JSON is stored in config.resource_mapper_ui and compiled to mapping keys on save."
	),
};

const docnameExprField = {
	fieldname: "docname_expression",
	fieldtype: "Code",
	label: __("Docname Expression"),
	options: "PythonExpression",
};

const assignedToLinkField = computed(() => ({
	fieldname: "assigned_to",
	fieldtype: "Link",
	label: "",
	options: "User",
	reqd: requiredConfigKeys.value.includes("assigned_to") ? 1 : 0,
}));

const assignedToExprField = computed(() => ({
	fieldname: "assigned_to",
	fieldtype: "Code",
	label: "",
	options: "Jinja",
	reqd: requiredConfigKeys.value.includes("assigned_to") ? 1 : 0,
}));

const todoDescriptionField = computed(() => ({
	fieldname: "description",
	fieldtype: "Code",
	label: __("Description"),
	options: "Jinja",
	reqd: requiredConfigKeys.value.includes("description") ? 1 : 0,
}));

const todoPriorityField = {
	fieldname: "priority",
	fieldtype: "Select",
	label: __("Priority"),
	options: "Low\nMedium\nHigh",
};

const commentTypeField = {
	fieldname: "comment_type",
	fieldtype: "Select",
	label: __("Comment Type"),
	options: "Comment\nInfo\nEdit\nWorkflow",
};

const commentTextField = computed(() => ({
	fieldname: "comment_text",
	fieldtype: "Code",
	label: __("Comment Text"),
	options: "Jinja",
	reqd: requiredConfigKeys.value.includes("comment_text") ? 1 : 0,
}));

const assignToType = ref("Value");
const mapperView = ref("classic");
const targetSchema = ref([]);

const showMapper = computed(
	() => !["Create ToDo", "Add Comment", "Delete Record"].includes(mode.value)
);
const operationPolicy = computed(() =>
	getEffectiveActionPolicy(props.node?.data?.action_type || "Document Action", {
		operation: mode.value,
		processName: props.node?.data?.process_name,
	})
);
const requiredConfigKeys = computed(() => operationPolicy.value?.required_config_keys || []);

const sourceSchema = computed(() => {
	return (variable_options.value || []).map((opt) => ({
		label: opt.label || opt.value,
		value: opt.value,
		fieldtype: opt.fieldtype || "Data",
	}));
});

const visualMappings = computed(() => {
	// Transform resource_mapper_ui to the flat format used by TransformControl
	const ui = config.resource_mapper_ui || {};
	const mappings = [];

	if (Array.isArray(ui.scalars)) {
		ui.scalars.forEach((s) => {
			if (s.source_type === "path") {
				mappings.push({
					source: s.path,
					target: s.target,
					source_label: s.path,
					target_label: s.target,
				});
			}
		});
	}
	// Note: Child table mappings in ResourceMapperControl are complex.
	// For now, we only show scalar mappings in the visual view.

	return mappings;
});

function update_visual_mappings(mappings) {
	// Convert back to resource_mapper_ui format
	const ui = { ...(config.resource_mapper_ui || { version: 2, scalars: [], tables: [] }) };

	// Keep existing table mappings
	ui.scalars = mappings.map((m) => ({
		target: m.target,
		source_type: "path",
		path: m.source,
		expr: "",
		literal: "",
	}));

	update_mapper_ui(ui);
}

watch(
	reference_doctype,
	async (val) => {
		if (val) {
			const fullSchema = await transformUtils.getDocTypeSchema(val);
			// Only show scalar fields in Visual Mapper
			targetSchema.value = fullSchema.filter((f) => {
				return (
					!String(f.value).includes(".") &&
					f.fieldtype !== "Table" &&
					f.fieldtype !== "Table MultiSelect"
				);
			});
		} else {
			targetSchema.value = [];
		}
	},
	{ immediate: true }
);

function looksLikePath(expr) {
	return /^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*$/.test((expr || "").trim());
}

function hasLegacyMapperConfig(cfg) {
	if (!cfg || typeof cfg !== "object") return false;
	const hasStatic = cfg.static_values && Object.keys(cfg.static_values).length;
	const hasFields = Array.isArray(cfg.field_mappings) && cfg.field_mappings.length;
	const hasInput = cfg.input_mapping && Object.keys(cfg.input_mapping).length;
	const hasTables = Array.isArray(cfg.table_mappings) && cfg.table_mappings.length;
	const hasMapperOptions = cfg.mapper_options && typeof cfg.mapper_options === "object";
	return !!(hasStatic || hasFields || hasInput || hasTables || hasMapperOptions);
}

function mapSourceToUiRow(target, sourceExpr) {
	const value = String(sourceExpr || "").trim();
	if (!value) {
		return { target, source_type: "path", path: "", expr: "", literal: "" };
	}
	if (looksLikePath(value)) {
		return { target, source_type: "path", path: value, expr: "", literal: "" };
	}
	return { target, source_type: "expr", path: "", expr: value, literal: "" };
}

function mapTableAssignmentToUi(assignment) {
	if (!assignment || typeof assignment !== "object") {
		return { target: "", source_type: "path", path: "", expr: "", literal: "" };
	}
	if (assignment.source_type === "literal") {
		return {
			target: assignment.target || "",
			source_type: "literal",
			path: "",
			expr: "",
			literal: assignment.literal ?? "",
		};
	}
	const sourceExpr = String(assignment.source || "").trim();
	return mapSourceToUiRow(assignment.target || "", sourceExpr);
}

function buildMapperUiFromLegacy(cfg) {
	const ui = {
		version: 2,
		mode: "field_mappings",
		source_path: cfg?.mapper_options?.source_path || "doc",
		copy_same_fields: !!cfg?.mapper_options?.copy_same_fields,
		field_no_map: Array.isArray(cfg?.mapper_options?.field_no_map)
			? cfg.mapper_options.field_no_map.filter(Boolean)
			: [],
		scalars: [],
		tables: [],
	};

	const staticValues = cfg?.static_values || {};
	Object.entries(staticValues).forEach(([target, literal]) => {
		ui.scalars.push({
			target,
			source_type: "literal",
			path: "",
			expr: "",
			literal,
		});
	});

	const fieldMappings = Array.isArray(cfg?.field_mappings) ? cfg.field_mappings : [];
	fieldMappings.forEach((mapping) => {
		if (!mapping?.target || String(mapping.target).includes(".")) return;
		ui.scalars.push(mapSourceToUiRow(mapping.target, mapping.source));
	});

	const inputMapping = cfg?.input_mapping || {};
	if (Object.keys(inputMapping).length) {
		ui.mode = "input_mapping";
		Object.entries(inputMapping).forEach(([target, sourceExpr]) => {
			ui.scalars.push(mapSourceToUiRow(target, sourceExpr));
		});
	}

	const tableMappings = Array.isArray(cfg?.table_mappings) ? cfg.table_mappings : [];
	tableMappings.forEach((table) => {
		if (!table?.target_table) return;
		ui.tables.push({
			target_table: table.target_table || "",
			source_path: table.source || "",
			item_alias: table.item_alias || "item",
			reset_value: table.reset_value !== undefined ? !!table.reset_value : true,
			add_if_empty: !!table.add_if_empty,
			condition: table.condition || "",
			filter: table.filter || "",
			mappings: Array.isArray(table.assignments)
				? table.assignments.map(mapTableAssignmentToUi)
				: [],
		});
	});

	return ui;
}

function stripBrackets(val) {
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}") && val.length > 2) {
		return val.slice(1, -1);
	}
	return val || "";
}

function detectAssignToType(val) {
	if (!val) return "Value";
	if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) return "Variable";
	if (typeof val === "string" && (val.includes("{{") || val.includes("{%"))) return "Expression";
	return "Value";
}

function onAssignToTypeChange() {
	config.assigned_to = "";
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

function update_mapper_ui(value) {
	config.resource_mapper_ui = value;
	sync_local_config();
}

function load_local_config(val) {
	const parsed = typeof val === "string" ? fromCodeString(val) : val || {};

	// Backwards compat: mapper
	if (!parsed.resource_mapper_ui && hasLegacyMapperConfig(parsed)) {
		parsed.resource_mapper_ui = buildMapperUiFromLegacy(parsed);
	}

	// Compare with current local state to avoid re-triggering watchers
	const current_str = JSON.stringify(config);
	const next_str = JSON.stringify(parsed);
	if (current_str === next_str) return;

	Object.keys(config).forEach((k) => delete config[k]);
	Object.assign(config, parsed);

	if (parsed.assigned_to) {
		assignToType.value = detectAssignToType(parsed.assigned_to);
	}
}

function sync_local_config() {
	const new_config = {};
	Object.entries(config).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== "") {
			new_config[key] = value;
		}
	});

	// sync_config in useActionConfig already performs a string compare against props.node.data.config
	sync_config(new_config);
}

watch(
	() => props.node?.data?.config,
	(val) => load_local_config(val),
	{ immediate: true, deep: true }
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

	// 2. Logic-based Validation
	if (showMapper.value && !config.resource_mapper_ui && !hasLegacyMapperConfig(config)) {
		errors.push(__("Resource Mapper configuration is required for {0}", [mode.value]));
	}

	// 3. Permission Audit Reason (Global check)
	if (props.node?.data?.skip_permissions && !props.node?.data?.permission_audit_reason) {
		errors.push(__("Permission Audit Reason is required when bypassing permissions."));
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({
	validate,
});
</script>

<style scoped>
.create-docs-config {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.config-section {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.section-card {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 8px;
	padding: 12px;
	background-color: var(--fxr-bg-card);
}

.section-subcard {
	border: 1px dashed var(--fxr-border-subtle);
	border-radius: 6px;
	padding: 10px;
}

.sub-section {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.assign-type-select {
	width: auto !important;
	min-width: 80px;
	font-size: 10px;
	height: 22px;
	padding: 1px 4px;
}
</style>
