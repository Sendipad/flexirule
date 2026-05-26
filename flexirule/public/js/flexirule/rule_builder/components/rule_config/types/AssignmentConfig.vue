<template>
	<div class="assignment-config">
		<div class="assignment-header-card mb-4">
			<div class="d-flex align-items-center justify-content-between">
				<div class="d-flex align-items-center fxr-gap-3">
					<div class="header-icon-box">
						<i class="fa fa-list-ol" />
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
			</div>
		</div>

		<div class="assignment-grid-wrap mt-2">
			<FlexiGrid
				:df="gridDf"
				:model-value="assignments"
				:engine="assignmentEngine"
				:read_only="isReadOnly"
				@update:model-value="onAssignmentsUpdate"
				@cell-click="onCellClick"
			/>
		</div>

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
							<i class="fa fa-times" />
						</button>
					</div>
					<div class="condition-builder-wrap">
						<ConditionBuilder
							:model-value="whenEditor.draft"
							:doc-fields="whenConditionDocFields"
							:variable-options="variable_options"
							:read-only="false"
							@update:model-value="(val) => (whenEditor.draft = val)"
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
import { computed, watch, ref, reactive } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import FlexiGrid from "../../../controls/FlexiGrid.vue";
import ConditionBuilder from "../../condition_builder/ConditionBuilder.vue";
import { ASSIGNMENT_OPERATOR_METADATA } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
});

const isReadOnly = computed(() => !!props.readOnly || !!props.read_only);

const { doctype_fields, variable_options, update_action_field, store } = useActionConfig(props);

const whenEditor = ref({ open: false, index: -1, draft: null });

// ── FlexiGrid Configuration ──────────────────────────────────────────────────

const gridDf = computed(() => ({
	fieldname: "assignments",
	fieldtype: "FlexiGrid",
	label: "",
	fields: [
		{
			fieldname: "when_label",
			label: __("Run If"),
			fieldtype: "Button",
			btn_class: "when-toggle-btn",
			icon: "fa fa-play-circle-o",
			in_list_view: 1,
			width: "120px",
		},
		{
			fieldname: "target",
			label: __("Target Field"),
			fieldtype: "FieldPicker",
			options: targetOptions.value,
			placeholder: __("Target field/variable..."),
			in_list_view: 1,
			width: "200px",
			default: "",
		},
		{
			fieldname: "operator",
			label: __("Operator"),
			fieldtype: "Select",
			options: [], // Dynamic options handled by getEffectiveDf
			in_list_view: 1,
			width: "120px",
			default: "set",
		},
		{
			fieldname: "value",
			label: __("Value Expression"),
			fieldtype: "Structured Value",
			in_list_view: 1,
			width: "300px",
			default: { mode: "static", value: "" },
		},
	],
}));

/**
 * assignmentEngine: Provides dynamic dependency handling for FlexiGrid.
 */
const assignmentEngine = reactive({
	rule_doc: store.rule_doc,
	dependency_states: {},

	handleFieldChange(fieldname, value, row) {
		const index = assignments.value.findIndex((a) => a.name === row.name);
		if (index === -1) return;

		if (fieldname === "target") {
			onTargetChange(index, value);
		} else if (fieldname === "operator") {
			onOperatorChange(index, value);
		} else if (fieldname === "value") {
			updateTemplate(index, value);
		}
	},

	getNormalizedDf(df, rowName) {
		const row = assignments.value.find((a) => a.name === rowName);
		if (!row) return df;

		const normalized = { ...df };

		if (df.fieldname === "when_label") {
			const hasCond = hasWhenCondition(row);
			normalized.label = hasCond ? __("Condition Set") : __("Always Run");
			normalized.icon = hasCond ? "fa fa-filter" : "fa fa-play-circle-o";
			normalized.btn_class = hasCond
				? "when-toggle-btn is-active"
				: "when-toggle-btn is-default";
		}

		if (df.fieldname === "operator") {
			normalized.options = getAvailableOperators(row.target);
		}

		if (df.fieldname === "value") {
			if (!needsValue(row.operator)) {
				normalized.hidden = true;
				// normalized.description = operatorNoValueHint(row.operator);
			} else {
				normalized.hidden = false;
				normalized.target_fieldtype = getTargetFieldtype(row.target);
				normalized.target_options = getTargetOptions(row.target);
				normalized.target_doctype = getTargetDoctype(row.target);
				normalized.context = {
					df: targetOptions.value.find((o) => o.value === row.target) || {},
					operator: row.operator,
					referenceDoctype: getTargetDoctype(row.target),
				};
			}
		}

		return normalized;
	},

	getFieldState(df, rowName) {
		const row = assignments.value.find((a) => a.name === rowName);
		if (!row) return {};

		if (df.fieldname === "value" && !needsValue(row.operator)) {
			return { hidden: true };
		}
		return { hidden: false };
	},
});

function onAssignmentsUpdate(newAssignments) {
	assignments.value = newAssignments;
	syncToNode();
}

function onCellClick({ fieldname, rowIndex }) {
	if (fieldname === "when_label") {
		openWhenConditionEditor(rowIndex);
	}
}

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

// ─── Unique Row ID Helper ───────────────────────────────────────────────────

function makeRandomString(length = 9) {
	const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
	let result = "";
	for (let i = 0; i < length; i++) {
		result += chars.charAt(Math.floor(Math.random() * chars.length));
	}
	return result;
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

		parsed = parsed.map((a) => {
			const name = a.name || makeRandomString(9);
			let structuredVal = null;
			if (a.value && typeof a.value === "object" && a.value.mode) {
				structuredVal = a.value;
			} else {
				const legacyVal = a.value || a.value_template || "";
				const legacyUI = a.value_template_ui;
				if (legacyUI && typeof legacyUI === "object" && legacyUI.mode) {
					structuredVal = legacyUI;
				} else {
					structuredVal = { mode: "static", value: legacyVal };
				}
			}

			// Unified mode migration: migrate specialized modes to 'resolver'
			if (["formula", "format", "normalize"].includes(structuredVal.mode)) {
				const config = structuredVal.config || {};
				if (!config.kind) {
					const kindMap = {
						formula: "math_formula",
						format: "format",
						normalize: "normalization",
					};
					config.kind = kindMap[structuredVal.mode];
				}
				structuredVal.mode = "resolver";
				structuredVal.config = config;
			}

			return {
				name,
				target: a.target || "",
				operator: a.operator || "set",
				when_condition: a.when_condition || null,
				when_expression: a.when_expression || a.when || "",
				pythonExpression: a.pythonExpression || "",
				value: structuredVal,
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
		name: a.name || makeRandomString(9),
		target: a.target,
		operator: a.operator,
		when_condition: a.when_condition || null,
		when_expression: a.when_condition ? "" : a.when_expression || "",
		pythonExpression: a.pythonExpression || "",
		value: a.value,
	}));
	update_action_field("config", JSON.stringify(clean));
	store.mark_dirty();
}

function onTargetChange(index, value) {
	const assignment = assignments.value[index];
	assignment.target = value;

	// Intelligent defaulting for resolver kind based on target
	if (assignment.value?.mode === "resolver") {
		const config = assignment.value.config || {};
		if (!config.kind || config.kind === "resolver") {
			config.kind = getDefaultResolverKind(value);
			assignment.value.config = config;
		}
	}

	// Reset operator if it's no longer compatible with new target type
	const available = getAvailableOperators(value).map((o) => o.value);
	if (!available.includes(assignment.operator)) {
		const fieldtype = getTargetFieldtype(value);
		if (fieldtype === "Check") {
			assignment.operator = "toggle";
		} else {
			assignment.operator = "set";
		}
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

function onOperatorChange(index, value) {
	assignments.value[index].operator = value;
	if (!needsValue(value)) {
		assignments.value[index].value = { mode: "static", value: "" };
	}
	syncToNode();
}

function updateTemplate(index, value) {
	assignments.value[index].value = value;
	syncToNode();
}

// ─── Validation ──────────────────────────────────────────────────────────────

function validate() {
	const errors = [];
	assignments.value.forEach((a, idx) => {
		const n = idx + 1;
		if (!a.target) errors.push(__("Assignment #{0}: Target is required", [n]));
		if (!a.operator) errors.push(__("Assignment #{0}: Operator is required", [n]));
		if (needsValue(a.operator)) {
			const ui = a.value;
			if (!ui || (!Array.isArray(ui.segments) && !ui.mode)) {
				errors.push(
					__("Assignment #{0}: Value is required for operator '{1}'", [n, a.operator])
				);
			}
		}
		// Target path validation
		if (a.target && !a.target.startsWith("doc.") && !a.target.startsWith("vars.")) {
			errors.push(__("Assignment #{0}: Target must start with 'doc.' or 'vars.'", [n]));
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

:deep(.when-toggle-btn) {
	justify-content: flex-start;
	padding: 6px 10px;
	font-weight: 600;
	font-size: 11px;
	border-radius: var(--fxr-radius-md, 6px);
	border: 1px solid transparent;
	transition: all 0.2s ease;
	text-align: left;
}

:deep(.when-toggle-btn.is-default) {
	background: var(--fxr-bg-muted, #f1f5f9);
	color: var(--fxr-text-secondary, #475569);
}

:deep(.when-toggle-btn.is-default:hover) {
	background: var(--fxr-bg-hover, #f8fafc);
	border-color: var(--fxr-border-strong, #cbd5e1);
}

:deep(.when-toggle-btn.is-active) {
	background: var(--fxr-badge-var, #f3e8ff);
	color: var(--fxr-badge-var-text, #7c3aed);
	border-color: rgba(124, 58, 237, 0.2);
}

:deep(.when-toggle-btn.is-active:hover) {
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
</style>
