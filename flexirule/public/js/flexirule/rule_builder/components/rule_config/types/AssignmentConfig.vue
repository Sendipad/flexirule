<template>
	<div class="assignment-config">
		<div class="config-section section-card header-compact mb-3">
			<div class="d-flex align-items-center justify-content-between">
				<div class="d-flex flex-column">
					<h5 class="mb-0">{{ __("Batch Assignments") }}</h5>
					<span class="text-muted small">{{
						__("Sequential state mutations applied in order")
					}}</span>
				</div>
				<button
					v-if="assignments.length > 1 && !readOnly"
					class="btn btn-xs btn-outline-danger"
					@click="clearAll"
				>
					<i class="fa fa-trash me-1"></i> {{ __("Clear All") }}
				</button>
			</div>
		</div>

		<!-- Horizontal Table Grid Header -->
		<div
			v-if="assignments.length"
			class="assignment-grid-header mb-1 text-muted small fw-semibold"
		>
			<div class="grid-col-target">{{ __("Target Field") }}</div>
			<div class="grid-col-operator">{{ __("Operator") }}</div>
			<div class="grid-col-value">{{ __("Value Expression") }}</div>
			<div class="grid-col-actions text-end">{{ __("Actions") }}</div>
		</div>

		<div class="assignments-list">
			<div
				v-for="(assignment, index) in assignments"
				:key="index"
				class="assignment-grid-row align-items-center mb-2"
			>
				<!-- Target ComboBox with Type Badge support -->
				<div class="grid-col-target">
					<ComboBoxControl
						:df="{ fieldtype: 'FieldPicker', label: '' }"
						:modelValue="assignment.target"
						:options="targetOptions"
						:read_only="readOnly"
						:hideLabel="true"
						:trigger="'button'"
						:placeholder="__('Target field/variable...')"
						:allowCustomValue="false"
						@update:modelValue="(val) => onTargetChange(index, val)"
					/>
				</div>

				<!-- Operator Selector -->
				<div class="grid-col-operator">
					<ComboBoxControl
						:df="{ fieldtype: 'Select', label: '' }"
						:options="getAvailableOperators(assignment.target)"
						:modelValue="assignment.operator"
						:read_only="readOnly"
						:hideLabel="true"
						:trigger="'button'"
						@update:modelValue="(val) => onOperatorChange(index, val)"
					/>
				</div>

				<!-- Value Expression Editor -->
				<div class="grid-col-value">
					<FlexStructuredValueControl
						v-if="needsValue(assignment.operator)"
						:fieldType="getTargetFieldtype(assignment.target) || 'Data'"
						:modelValue="assignment.value_template_ui"
						:read_only="readOnly"
						:variableOptions="variable_options"
						:referenceDoctype="getTargetDoctype(assignment.target)"
						:placeholder="__('Type value...')"
						:options="getTargetOptions(assignment.target)"
						@update:modelValue="(val) => updateTemplate(index, val)"
					/>
					<div v-else class="operator-hint-text text-muted small">
						<i class="fa fa-info-circle me-1"></i>
						{{ operatorNoValueHint(assignment.operator) }}
					</div>
				</div>

				<!-- Row Actions -->
				<div
					class="grid-col-actions text-end d-flex align-items-center justify-content-end"
				>
					<div class="d-flex flex-column me-1" v-if="assignments.length > 1">
						<button
							class="btn btn-xs btn-link p-0 text-muted shadow-none"
							@click="moveAssignment(index, -1)"
							:disabled="readOnly || index === 0"
							:title="__('Move Up')"
						>
							<i class="fa fa-chevron-up" style="font-size: 8px"></i>
						</button>
						<button
							class="btn btn-xs btn-link p-0 text-muted shadow-none"
							@click="moveAssignment(index, 1)"
							:disabled="readOnly || index === assignments.length - 1"
							:title="__('Move Down')"
						>
							<i class="fa fa-chevron-down" style="font-size: 8px"></i>
						</button>
					</div>
					<button
						class="btn btn-sm btn-link text-danger p-1 shadow-none"
						@click="removeAssignment(index)"
						:disabled="readOnly"
						:title="__('Remove')"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
			</div>
		</div>

		<div v-if="!assignments.length" class="empty-state text-center text-muted py-4">
			<i class="fa fa-list-ol fa-2x mb-2 d-block"></i>
			<p class="small">{{ __("No assignments defined. Add one below.") }}</p>
		</div>

		<button
			class="btn btn-sm btn-default w-100 mt-2"
			@click="addAssignment"
			:disabled="readOnly"
		>
			<i class="fa fa-plus me-1"></i> {{ __("Add Assignment") }}
		</button>
	</div>
</template>

<script setup>
import { computed, watch, ref } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import FlexStructuredValueControl from "../../../controls/FlexStructuredValueControl.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";
import { ASSIGNMENT_OPERATOR_METADATA } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { doctype_fields, variable_options, update_action_field, store } = useActionConfig(props);

// ─── Operator Helpers ────────────────────────────────────────────────────────

const OPERATOR_HINTS = {
	set: null,
	clear: "Clears the value without needing an input.",
	increment: "Adds the value to the current numeric total.",
	decrement: "Subtracts the value from the current numeric total.",
	append: "Appends the value to an existing list.",
	merge: "Merges an object into the current dictionary value.",
	toggle: "Flips a boolean field (0 ↔ 1) without needing an input.",
};

function needsValue(operator) {
	return ASSIGNMENT_OPERATOR_METADATA[operator]?.requires_value !== false;
}

function operatorNoValueHint(operator) {
	return OPERATOR_HINTS[operator] || __("No value input required for this operator.");
}

function getOperatorHint(operator) {
	return OPERATOR_HINTS[operator] || null;
}

/**
 * Resolve a Frappe fieldtype for a target path.
 * Reuses existing doctype_fields and variable_options arrays.
 */
function getTargetFieldtype(target) {
	if (!target) return null;
	if (target.startsWith("doc.")) {
		const fieldname = target.slice(4).split(".")[0];
		if (fieldname === "docstatus") return "Select";
		const field = (doctype_fields.value || []).find((f) => f.fieldname === fieldname);
		return field?.fieldtype || null;
	}
	if (target.startsWith("vars.")) {
		const varname = target.slice(5).split(".")[0];
		const variable = (variable_options.value || []).find(
			(v) => v.value === varname || v.fieldname === varname
		);
		return variable?.fieldtype || variable?.type || null;
	}
	return null;
}

function getTargetDoctype(target) {
	if (!target || !target.startsWith("doc.")) return null;
	const fieldname = target.slice(4).split(".")[0];
	const field = (doctype_fields.value || []).find((f) => f.fieldname === fieldname);
	return field?.options || null;
}

/**
 * Custom metadata target options list.
 */
function getTargetOptions(target) {
	if (!target) return [];
	if (target.startsWith("doc.")) {
		const fieldname = target.slice(4).split(".")[0];
		if (fieldname === "docstatus") {
			return [
				{ label: __("0 (Draft)"), value: "0" },
				{ label: __("1 (Submitted)"), value: "1" },
				{ label: __("2 (Cancelled)"), value: "2" },
			];
		}
		const field = (doctype_fields.value || []).find((f) => f.fieldname === fieldname);
		if (field && field.fieldtype === "Select" && field.options) {
			return field.options;
		}
	}
	return [];
}

/**
 * Target-aware operator filtering: the key architectural enhancement.
 */
function getAvailableOperators(target) {
	const fieldtype = getTargetFieldtype(target);

	const operatorIcons = {
		set: "fa fa-pencil",
		clear: "fa fa-eraser",
		increment: "fa fa-plus",
		decrement: "fa fa-minus",
		append: "fa fa-list-ul",
		merge: "fa fa-compress",
		toggle: "fa fa-toggle-on",
	};

	return Object.entries(ASSIGNMENT_OPERATOR_METADATA)
		.filter(([, meta]) => {
			if (!meta.supported_target_types.length) return true; // "all types"
			if (!fieldtype) return true; // vars.* or unknown – show all
			return meta.supported_target_types.includes(fieldtype);
		})
		.map(([key, meta]) => ({
			value: key,
			label: __(meta.label),
			icon: operatorIcons[key] || "fa fa-cog",
		}));
}

// ─── Assignments State ────────────────────────────────────────────────────────

const assignments = ref([]);

watch(
	() => props.node?.data?.config,
	(val) => {
		let parsed = [];
		if (typeof val === "string") {
			try {
				parsed = JSON.parse(val);
			} catch (e) {
				parsed = [];
			}
		} else if (Array.isArray(val)) {
			parsed = val;
		}

		// Map parsed to ensure both value_template and value are populated on load
		parsed = parsed.map((a) => {
			const value_tpl = a.value_template || a.value || "";
			return {
				target: a.target || "",
				operator: a.operator || "set",
				value_template_ui: a.value_template_ui || { version: 2, segments: [] },
				value_template: value_tpl,
				value: value_tpl,
			};
		});

		if (JSON.stringify(parsed) !== JSON.stringify(assignments.value)) {
			assignments.value = JSON.parse(JSON.stringify(parsed));
		}
	},
	{ immediate: true, deep: true }
);

// ─── Target options for ComboBox ─────────────────────────────────────────────

const targetOptions = computed(() => {
	const opts = [];

	// ── Context variables (vars.*) ────────────────────────────────────────────
	(variable_options.value || [])
		.filter((v) => v.is_variable)
		.forEach((v) => {
			opts.push({
				value: `vars.${v.value}`,
				label: `${v.label} (vars.${v.value})`,
				icon: "fa fa-code",
				fieldtype: v.fieldtype || "Variable",
				type: v.fieldtype || "Variable",
				is_variable: true,
				fieldname: v.value,
			});
		});

	// ── Doc fields (doc.*) ────────────────────────────────────────────────────
	(doctype_fields.value || []).forEach((f) => {
		opts.push({
			value: f.value,
			label: f.label,
			icon: f.icon || "fa fa-columns",
			fieldtype: f.fieldtype,
			type: f.fieldtype,
			fieldname: f.fieldname,
			options: f.options,
		});
	});

	return opts;
});

// ─── Mutations ────────────────────────────────────────────────────────────────

function syncToNode() {
	const clean = assignments.value.map((a) => ({
		target: a.target,
		operator: a.operator,
		value_template_ui: a.value_template_ui,
		value_template: a.value_template,
		value: a.value_template, // standardized output key alignment
	}));
	update_action_field("config", JSON.stringify(clean));
	store.mark_dirty();
}

function addAssignment() {
	assignments.value.push({
		target: "",
		operator: "set",
		value_template_ui: { version: 2, segments: [] },
		value_template: "",
		value: "",
	});
	syncToNode();
}

function removeAssignment(index) {
	assignments.value.splice(index, 1);
	syncToNode();
}

function moveAssignment(index, direction) {
	const newIndex = index + direction;
	if (newIndex < 0 || newIndex >= assignments.value.length) return;
	const item = assignments.value.splice(index, 1)[0];
	assignments.value.splice(newIndex, 0, item);
	syncToNode();
}

function clearAll() {
	frappe.confirm(__("Are you sure you want to remove all assignments?"), () => {
		assignments.value = [];
		syncToNode();
	});
}

function onTargetChange(index, value) {
	assignments.value[index].target = value;
	// Reset operator if it's no longer compatible with new target type
	const available = getAvailableOperators(value).map((o) => o.value);
	if (!available.includes(assignments.value[index].operator)) {
		assignments.value[index].operator = "set";
	}
	syncToNode();
}

function onOperatorChange(index, value) {
	assignments.value[index].operator = value;
	// Clear value template if operator no longer needs it
	if (!needsValue(value)) {
		assignments.value[index].value_template_ui = { version: 2, segments: [] };
		assignments.value[index].value_template = "";
		assignments.value[index].value = "";
	}
	syncToNode();
}

function compileStructuredValueToJinja(val) {
	if (!val) return "";
	if (val.mode === "static") {
		return String(val.value ?? "");
	}
	if (val.mode === "variable") {
		let path = val.path;
		if (path && !path.startsWith("vars.") && !path.startsWith("doc.")) {
			const isVar = (variable_options.value || []).some(
				(opt) => opt.value === path && opt.is_variable
			);
			path = isVar ? `vars.${path}` : `doc.${path}`;
		}
		return `{{ ${path} }}`;
	}
	if (val.mode === "formula") {
		return `{{ ${val.expression} }}`;
	}
	if (val.mode === "resolver") {
		const args = Object.entries(val.config || {})
			.map(([k, v]) => `${k}=${JSON.stringify(v)}`)
			.join(", ");
		return `{{ resolve("${val.resolver}", ${args}) }}`;
	}
	if (val.mode === "formatter") {
		return `{{ format(${JSON.stringify(val.formatter)}, ${JSON.stringify(val.options)}) }}`;
	}
	if (val.mode === "link" || val.mode === "dynamic_link") {
		return String(val.value ?? "");
	}
	return "";
}

function updateTemplate(index, value) {
	assignments.value[index].value_template_ui = value;

	let compiled = "";
	if (value && typeof value === "object" && "mode" in value) {
		compiled = compileStructuredValueToJinja(value);
	} else if (value && typeof value === "object" && Array.isArray(value.segments)) {
		const knownVarRoots = (variable_options.value || [])
			.map((v) => String(v?.value || ""))
			.filter((p) => p.startsWith("vars."))
			.map((p) => p.slice(5).split(".")[0]);
		compiled = compileSegmentsToJinja(value.segments, { knownVarRoots });
	} else {
		compiled = String(value || "");
	}

	assignments.value[index].value_template = compiled;
	assignments.value[index].value = compiled;
	syncToNode();
}

// ─── Validation ──────────────────────────────────────────────────────────────

function validate() {
	const errors = [];
	assignments.value.forEach((a, idx) => {
		const n = idx + 1;
		if (!a.target) errors.push(__(`Assignment #${n}: Target is required`));
		if (!a.operator) errors.push(__(`Assignment #${n}: Operator is required`));
		if (needsValue(a.operator)) {
			const ui = a.value_template_ui;
			if (!ui || (!Array.isArray(ui.segments) && !ui.mode)) {
				errors.push(
					__(`Assignment #${n}: Value Template is required for operator '${a.operator}'`)
				);
			}
		}
		// Target path validation
		if (a.target && !a.target.startsWith("doc.") && !a.target.startsWith("vars.")) {
			errors.push(__(`Assignment #${n}: Target must start with 'doc.' or 'vars.'`));
		}
	});
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.assignment-config {
	display: flex;
	flex-direction: column;
}

.section-card {
	border: 1px solid var(--border-color, #e2e8f0);
	border-radius: 8px;
	padding: 12px;
	background: var(--bg-light, #fff);
}

.header-compact {
	background: var(--gray-50, #f8fafc);
}

/* Horizontal Table Grid Styling */
.assignment-grid-header,
.assignment-grid-row {
	display: grid;
	grid-template-columns: 30% 18% 44% 8%;
	gap: 8px;
}

.assignment-grid-header {
	padding: 0 4px;
	font-size: 11px;
	text-transform: uppercase;
	letter-spacing: 0.05em;
}

.assignment-grid-row {
	background: var(--card-bg, #ffffff);
	border: 1px solid var(--border-color, #e2e8f0);
	border-radius: 6px;
	padding: 4px;
	transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.assignment-grid-row:hover {
	border-color: #cbd5e1;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.operator-hint-text {
	display: flex;
	align-items: center;
	padding: 6px 12px;
	background: #f8fafc;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	height: 32px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.empty-state {
	border: 1px dashed var(--border-color, #e2e8f0);
	border-radius: 8px;
}
</style>
