<template>
	<div class="assignment-config">
		<div class="assignment-header-card mb-4">
			<div class="d-flex align-items-center justify-content-between">
				<div class="d-flex align-items-center fxr-gap-3">
					<div class="header-icon-box">
						<i class="fa fa-list-ol"></i>
					</div>
					<div class="d-flex flex-column">
						<h5 class="mb-0 fw-bold">{{ __("Batch Assignments") }}</h5>
						<span class="text-muted fxr-text-xs">
							{{
								__("Define sequential mutations for document fields and variables")
							}}
						</span>
					</div>
				</div>
				<button
					v-if="assignments.length > 1"
					class="fxr-btn fxr-btn--ghost fxr-btn--sm text-danger"
					@click="clearAssignments"
					:disabled="isReadOnly"
				>
					<i class="fa fa-eraser me-1"></i>
					{{ __("Clear All") }}
				</button>
			</div>
		</div>

		<!-- Horizontal Table Grid Header -->
		<div v-if="assignments.length" class="assignment-grid-header">
			<div class="grid-col-target">{{ __("Target Field") }}</div>
			<div class="grid-col-operator">{{ __("Operator") }}</div>
			<div class="grid-col-value">{{ __("Value Expression") }}</div>
			<div class="grid-col-when">{{ __("Run If") }}</div>
			<div class="grid-col-actions"></div>
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
						:read_only="isReadOnly"
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
						:read_only="isReadOnly"
						:hideLabel="true"
						:trigger="'button'"
						@update:modelValue="(val) => onOperatorChange(index, val)"
					/>
				</div>

				<!-- Value Expression Editor -->
				<div class="grid-col-value">
					<template v-if="needsValue(assignment.operator)">
						<div class="value-mode-wrap">
							<!-- Mode toggle -->
							<button
								class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost value-mode-toggle"
								:title="
									assignment.value_mode === 'resolver'
										? __('Switch to Template Editor')
										: __('Switch to Formula Resolver')
								"
								:disabled="isReadOnly"
								@click="toggleValueMode(index)"
							>
								<i
									:class="
										assignment.value_mode === 'resolver'
											? 'fa fa-pencil'
											: 'fa fa-calculator'
									"
								></i>
							</button>
							<!-- Resolver mode -->
							<ValueResolverControl
								v-if="assignment.value_mode === 'resolver'"
								class="flex-1 min-w-0"
								:modelValue="assignment.value_template_ui"
								:doctype="
									getTargetDoctype(assignment.target) ||
									store.rule_doc?.document_type ||
									''
								"
								:readOnly="isReadOnly"
								@update:modelValue="(val) => updateResolverTemplate(index, val)"
							/>
							<!-- Template (TipTap) mode -->
							<FlexStructuredValueControl
								v-else
								class="flex-1 min-w-0"
								:fieldType="getTargetFieldtype(assignment.target) || 'Data'"
								:modelValue="assignment.value_template_ui"
								:read_only="isReadOnly"
								:engine="store"
								:doc="store.rule_doc"
								:variableOptions="variable_options"
								:allowedModes="supportedTemplateModes"
								:referenceDoctype="getTargetDoctype(assignment.target)"
								:placeholder="__('Type value...')"
								:options="getTargetOptions(assignment.target)"
								@update:modelValue="(val) => updateTemplate(index, val)"
							/>
						</div>
					</template>
					<div v-else class="operator-hint-text text-muted small">
						<i class="fa fa-info-circle me-1"></i>
						{{ operatorNoValueHint(assignment.operator) }}
					</div>
				</div>

				<div class="grid-col-when">
					<div class="when-editor-cell">
						<button
							class="fxr-btn fxr-btn--sm w-100 when-toggle-btn"
							:class="hasWhenCondition(assignment) ? 'is-active' : 'is-default'"
							:disabled="isReadOnly"
							@click="openWhenConditionEditor(index)"
						>
							<i
								:class="
									hasWhenCondition(assignment)
										? 'fa fa-filter'
										: 'fa fa-play-circle-o'
								"
								class="me-2"
							></i>
							<span class="truncate">
								{{
									hasWhenCondition(assignment)
										? __("Condition Set")
										: __("Always Run")
								}}
							</span>
						</button>
					</div>
				</div>

				<!-- Row Actions -->
				<div
					class="grid-col-actions d-flex align-items-center justify-content-end fxr-gap-1"
				>
					<button
						class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost"
						@click="moveAssignment(index, -1)"
						:disabled="isReadOnly || index === 0"
						:title="__('Move Up')"
						aria-label="Move Up"
					>
						<i class="fa fa-chevron-up"></i>
					</button>
					<button
						class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost"
						@click="moveAssignment(index, 1)"
						:disabled="isReadOnly || index === assignments.length - 1"
						:title="__('Move Down')"
						aria-label="Move Down"
					>
						<i class="fa fa-chevron-down"></i>
					</button>
					<button
						class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost text-danger"
						@click="removeAssignment(index)"
						:disabled="isReadOnly"
						:title="__('Remove')"
						aria-label="Remove Assignment"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
			</div>
		</div>

		<div
			v-if="!assignments.length"
			class="empty-state d-flex flex-column align-items-center justify-content-center py-5"
		>
			<div class="empty-state-icon mb-3">
				<i class="fa fa-list-ol fa-3x text-muted opacity-25"></i>
			</div>
			<div class="text-center px-4">
				<h6 class="mb-1 fw-bold text-muted">{{ __("No Assignments Yet") }}</h6>
				<p class="small text-muted mb-0">
					{{ __("Add an assignment to start mutating document fields or variables.") }}
				</p>
			</div>
		</div>

		<button class="add-assignment-btn mt-2" @click="addAssignment" :disabled="isReadOnly">
			<i class="fa fa-plus"></i>
			<span>{{ __("Add Assignment") }}</span>
		</button>

		<Teleport to="body">
			<div
				v-if="whenEditor.open"
				class="fxr-modal-overlay"
				@click.self="closeWhenConditionEditor"
			>
				<div class="fxr-modal-card">
					<div class="d-flex align-items-center justify-content-between mb-2">
						<h5 class="mb-0">{{ __("Assignment Run Condition") }}</h5>
						<button
							class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost"
							@click="closeWhenConditionEditor"
						>
							<i class="fa fa-times"></i>
						</button>
					</div>
					<div class="condition-builder-wrap">
						<ConditionBuilder
							:modelValue="whenEditor.draft"
							:docFields="whenConditionDocFields"
							:variableOptions="variable_options"
							:readOnly="false"
							@update:modelValue="(val) => (whenEditor.draft = val)"
						/>
					</div>
					<div class="d-flex justify-content-between mt-3">
						<button
							class="fxr-btn fxr-btn--sm fxr-btn--ghost text-danger"
							@click="clearWhenCondition"
						>
							{{ __("Clear Condition") }}
						</button>
						<div class="d-flex fxr-gap-1">
							<button
								class="fxr-btn fxr-btn--sm fxr-btn--secondary"
								@click="closeWhenConditionEditor"
							>
								{{ __("Cancel") }}
							</button>
							<button
								class="fxr-btn fxr-btn--sm fxr-btn--primary"
								@click="saveWhenCondition"
							>
								{{ __("Save Condition") }}
							</button>
						</div>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, watch, ref } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import FlexStructuredValueControl from "../../../controls/FlexStructuredValueControl.vue";
import ValueResolverControl from "../../../controls/ValueResolverControl.vue";
import ConditionBuilder from "../../condition_builder/ConditionBuilder.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";
import { ASSIGNMENT_OPERATOR_METADATA } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
});

const isReadOnly = computed(() => !!props.readOnly || !!props.read_only);

const { doctype_fields, variable_options, update_action_field, store } = useActionConfig(props);
const supportedTemplateModes = ["formula", "resolver", "link", "dynamic-link"];
const whenEditor = ref({ open: false, index: -1, draft: null });

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
	const opt = targetOptions.value.find((o) => o.value === target);
	return opt?.fieldtype || opt?.type || null;
}

function getTargetDoctype(target) {
	if (!target) return null;
	const opt = targetOptions.value.find((o) => o.value === target);
	return opt?.options || null;
}

/**
 * Custom metadata target options list.
 */
function getTargetOptions(target) {
	if (!target) return [];
	const opt = targetOptions.value.find((o) => o.value === target);
	if (opt?.value === "doc.docstatus" && !opt.options) {
		return [
			{ label: __("0 (Draft)"), value: "0" },
			{ label: __("1 (Submitted)"), value: "1" },
			{ label: __("2 (Cancelled)"), value: "2" },
		];
	}
	return opt?.options || [];
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
			// Auto-detect resolver mode: value_template_ui has a `kind` field (no `segments` array)
			const isResolverUi =
				a.value_template_ui &&
				typeof a.value_template_ui === "object" &&
				"kind" in a.value_template_ui &&
				!Array.isArray(a.value_template_ui.segments);
			return {
				target: a.target || "",
				operator: a.operator || "set",
				value_mode: isResolverUi ? "resolver" : "template",
				value_template_ui: a.value_template_ui || { version: 2, segments: [] },
				when_condition: a.when_condition || null,
				when_expression: a.when_expression || a.when || "",
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
				options: v.options,
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
		value_mode: a.value_mode || "template",
		when_condition: a.when_condition || null,
		when_expression: a.when_condition ? "" : a.when_expression || "",
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
		value_mode: "template",
		when_condition: null,
		when_expression: "",
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

function clearAssignments() {
	frappe.confirm(__("Are you sure you want to clear all assignments?"), () => {
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

function hasWhenCondition(assignment) {
	return !!(assignment?.when_condition && Array.isArray(assignment.when_condition.conditions));
}

const whenConditionDocFields = computed(() =>
	(doctype_fields.value || []).map((f) => ({
		label: f.label || f.fieldname,
		value: f.value || `doc.${f.fieldname}`,
		fieldname: f.fieldname,
		fieldtype: f.fieldtype,
		options: f.options,
	}))
);

function openWhenConditionEditor(index) {
	const current = assignments.value[index];
	const fallback = { op: "and", conditions: [] };
	whenEditor.value = {
		open: true,
		index,
		draft: JSON.parse(JSON.stringify(current?.when_condition || fallback)),
	};
}

function closeWhenConditionEditor() {
	whenEditor.value = { open: false, index: -1, draft: null };
}

function saveWhenCondition() {
	if (whenEditor.value.index < 0) return;
	const tree = whenEditor.value.draft;
	const hasConditions = !!(tree && Array.isArray(tree.conditions) && tree.conditions.length);
	assignments.value[whenEditor.value.index].when_condition = hasConditions ? tree : null;
	assignments.value[whenEditor.value.index].when_expression = "";
	syncToNode();
	closeWhenConditionEditor();
}

function clearWhenCondition() {
	if (whenEditor.value.index < 0) return;
	assignments.value[whenEditor.value.index].when_condition = null;
	assignments.value[whenEditor.value.index].when_expression = "";
	syncToNode();
	closeWhenConditionEditor();
}
function getDefaultResolverKind(target) {
	const fieldtype = getTargetFieldtype(target);
	if (!fieldtype) return "string_formula";

	if (["Int", "Float", "Percent", "Currency"].includes(fieldtype)) {
		return "math_formula";
	}
	if (["Date", "Datetime"].includes(fieldtype)) {
		return "date_formula";
	}
	return "string_formula";
}

function toggleValueMode(index) {
	const current = assignments.value[index].value_mode || "template";
	const next = current === "resolver" ? "template" : "resolver";
	assignments.value[index].value_mode = next;
	// Reset UI state when switching modes
	if (next === "resolver") {
		const defaultKind = getDefaultResolverKind(assignments.value[index].target);
		assignments.value[index].value_template_ui = { kind: defaultKind };
	} else {
		assignments.value[index].value_template_ui = { version: 2, segments: [] };
	}
	assignments.value[index].value_template = "";
	assignments.value[index].value = "";
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

/**
 * Compile ValueResolverControl structured state → Jinja {{ expr }} string.
 * Mirrors the expressionSnippet logic in ValueResolverControl.vue.
 */
function compileValueResolverToJinja(s) {
	if (!s || !s.kind) return "";

	if (s.kind === "date_formula") {
		const baseExpr = s.base_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.base_field}`;
		const offset =
			s.offset_sign === "-" ? -Math.abs(s.offset_value || 0) : Math.abs(s.offset_value || 0);
		if (offset === 0) return `{{ ${baseExpr} }}`;
		if (s.offset_unit === "days") return `{{ frappe.utils.add_days(${baseExpr}, ${offset}) }}`;
		return `{{ frappe.utils.add_to_date(${baseExpr}, ${s.offset_unit}=${offset}) }}`;
	}

	if (s.kind === "math_formula") {
		const a = s.field_a ? `frappe.utils.flt(doc.${s.field_a})` : "0";
		const b =
			s.field_b_type === "field"
				? s.field_b
					? `frappe.utils.flt(doc.${s.field_b})`
					: "0"
				: String(s.constant_b ?? 0);
		const prec = s.precision ?? 2;
		return `{{ frappe.utils.flt(${a} ${s.math_op || "+"} ${b}, ${prec}) }}`;
	}

	if (s.kind === "date_diff") {
		const start =
			s.diff_start_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.diff_start_field}`;
		const end =
			s.diff_end_type === "today" ? "frappe.utils.nowdate()" : `doc.${s.diff_end_field}`;
		if (s.diff_unit === "days") return `{{ frappe.utils.date_diff(${end}, ${start}) }}`;
		if (s.diff_unit === "months") return `{{ frappe.utils.month_diff(${end}, ${start}) }}`;
		return `{{ int(frappe.utils.month_diff(${end}, ${start}) / 12) }}`;
	}

	if (s.kind === "child_aggregation") {
		const tbl = s.agg_table || "items";
		const fld = s.agg_field || "amount";
		if (s.agg_op === "sum")
			return `{{ sum([frappe.utils.flt(row.${fld}) for row in doc.get("${tbl}")]) }}`;
		if (s.agg_op === "avg")
			return `{{ sum([frappe.utils.flt(row.${fld}) for row in doc.get("${tbl}")]) / max(len(doc.get("${tbl}")), 1) }}`;
		if (s.agg_op === "count") return `{{ len(doc.get("${tbl}")) }}`;
	}

	if (s.kind === "string_formula") {
		const a = s.str_a_type === "field" ? `doc.${s.str_a || ""}` : `"${s.str_a || ""}"`;
		if (s.str_op === "concat") {
			const b = s.str_b_type === "field" ? `doc.${s.str_b || ""}` : `"${s.str_b || ""}"`;
			return `{{ str(${a} or "") + str(${b} or "") }}`;
		}
		if (s.str_op === "fmt_money") {
			const curr = s.str_b_type === "field" ? `doc.${s.str_b || ""}` : `"${s.str_b || ""}"`;
			return `{{ frappe.utils.fmt_money(${a}, currency=${curr}) }}`;
		}
		if (s.str_op === "uppercase") return `{{ str(${a} or "").upper() }}`;
		if (s.str_op === "lowercase") return `{{ str(${a} or "").lower() }}`;
	}

	if (s.kind === "system_context") {
		if (s.sys_token === "user") return `{{ frappe.session.user }}`;
		if (s.sys_token === "role_check")
			return `{{ "${s.sys_role || ""}" in frappe.get_roles(frappe.session.user) }}`;
	}

	return "";
}

/**
 * Handler for ValueResolverControl updates.
 */
function updateResolverTemplate(index, value) {
	assignments.value[index].value_template_ui = value;
	const compiled = compileValueResolverToJinja(value);
	assignments.value[index].value_template = compiled;
	assignments.value[index].value = compiled;
	syncToNode();
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
	gap: 4px;
}

.assignment-header-card {
	background: var(--fxr-bg-page, #f8fafc);
	border: 1px solid var(--fxr-border, #e2e8f0);
	border-radius: var(--fxr-radius-lg, 8px);
	padding: 16px;
}

.header-icon-box {
	width: 40px;
	height: 40px;
	background: var(--fxr-accent-light, #e0f2fe);
	color: var(--fxr-accent, #2490ef);
	border-radius: var(--fxr-radius-md, 6px);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 18px;
}

/* Horizontal Table Grid Styling */
.assignment-grid-header,
.assignment-grid-row {
	display: grid;
	grid-template-columns:
		minmax(160px, 1.2fr) minmax(100px, 0.7fr) minmax(240px, 2fr) minmax(120px, 0.8fr)
		80px;
	gap: 12px;
	align-items: center;
}

.assignment-grid-header {
	padding: 10px 16px;
	font-size: 10px;
	font-weight: 700;
	color: var(--fxr-text-muted, #64748b);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	border-bottom: 1px solid var(--fxr-border, #e2e8f0);
	margin-bottom: 8px;
}

.when-editor-cell {
	display: flex;
	flex-direction: column;
}

.when-toggle-btn {
	justify-content: flex-start;
	padding: 6px 10px;
	font-weight: 600;
	font-size: 11px;
	border-radius: var(--fxr-radius-md, 6px);
	border: 1px solid transparent;
	transition: all 0.2s ease;
}

.when-toggle-btn.is-default {
	background: var(--fxr-bg-muted, #f1f5f9);
	color: var(--fxr-text-secondary, #475569);
}

.when-toggle-btn.is-default:hover {
	background: var(--fxr-bg-hover, #f8fafc);
	border-color: var(--fxr-border-strong, #cbd5e1);
}

.when-toggle-btn.is-active {
	background: var(--fxr-badge-var, #f3e8ff);
	color: var(--fxr-badge-var-text, #7c3aed);
	border-color: rgba(124, 58, 237, 0.2);
}

.when-toggle-btn.is-active:hover {
	background: #ede9fe;
	border-color: rgba(124, 58, 237, 0.3);
}

.fxr-modal-overlay {
	position: fixed;
	inset: 0;
	background: rgba(15, 23, 42, 0.35);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 13000;
}

.fxr-modal-card {
	width: min(980px, 92vw);
	max-height: 86vh;
	background: #fff;
	border-radius: 10px;
	border: 1px solid #e2e8f0;
	padding: 14px;
	overflow: hidden;
	display: flex;
	flex-direction: column;
}

.condition-builder-wrap {
	overflow: auto;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	padding: 8px;
}

/* Value mode toggle + control wrapper */
.value-mode-wrap {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
}

.value-mode-toggle {
	flex-shrink: 0;
	width: 30px;
	height: 30px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: var(--fxr-radius-md, 6px);
	color: var(--fxr-text-muted, #64748b);
	border: 1px solid var(--fxr-border, #e2e8f0);
	background: var(--fxr-bg-input, #ffffff);
	transition: all 0.2s ease;
	cursor: pointer;
}

.value-mode-toggle:hover:not(:disabled) {
	color: var(--fxr-accent, #2490ef);
	border-color: var(--fxr-accent, #2490ef);
	background: var(--fxr-bg-hover, #f8fafc);
}

.assignment-grid-row {
	background: var(--fxr-bg-card, #ffffff);
	border: 1px solid var(--fxr-border, #e2e8f0);
	border-radius: var(--fxr-radius-lg, 8px);
	padding: 10px 16px;
	transition: all 0.2s ease;
	box-shadow: var(--fxr-shadow-sm);
}

.assignment-grid-row:hover {
	border-color: var(--fxr-accent, #2490ef);
	box-shadow: var(--fxr-shadow-md);
	transform: translateY(-1px);
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
	border: 2px dashed var(--fxr-border, #e2e8f0);
	border-radius: var(--fxr-radius-lg, 12px);
	background-color: var(--fxr-bg-muted, #f8fafc);
	transition: all 0.2s ease;
	flex: 0 0 auto;
}

.empty-state:hover {
	border-color: var(--fxr-border-strong);
	background-color: var(--fxr-bg-hover);
}

.add-assignment-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	background: var(--fxr-bg-page, #f8fafc);
	border: 1px dashed var(--fxr-border-strong, #cbd5e1);
	border-radius: var(--fxr-radius-lg, 8px);
	padding: 12px;
	width: 100%;
	color: var(--fxr-text-secondary, #475569);
	font-weight: 600;
	font-size: 13px;
	transition: all 0.2s ease;
	cursor: pointer;
	margin-top: 12px;
}

.add-assignment-btn:hover:not(:disabled) {
	background: var(--fxr-accent-light, #e0f2fe);
	border-color: var(--fxr-accent, #2490ef);
	color: var(--fxr-accent, #2490ef);
}
</style>
