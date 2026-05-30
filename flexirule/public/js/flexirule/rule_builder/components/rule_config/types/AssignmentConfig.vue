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
			<div class="grid-col-when">{{ __("Run If") }}</div>
			<div class="grid-col-target">{{ __("Target Field") }}</div>
			<div class="grid-col-operator">{{ __("Operator") }}</div>
			<div class="grid-col-value">{{ __("Value Expression") }}</div>
			<div class="grid-col-actions"></div>
		</div>

		<div class="assignments-list">
			<div
				v-for="(assignment, index) in assignments"
				:key="assignment.name"
				class="assignment-grid-row align-items-center mb-2"
			>
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
							<FlexValueControl
								class="flex-1 min-w-0"
								:context="{
									df:
										targetOptions.find((o) => o.value === assignment.target) ||
										{},
									operator: assignment.operator,
									referenceDoctype: getTargetDoctype(assignment.target),
								}"
								:modelValue="assignment.value"
								:read_only="isReadOnly"
								:engine="store"
								:doc="store.rule_doc"
								:variableOptions="variable_options"
								:placeholder="__('Type value...')"
								@update:modelValue="(val) => updateTemplate(index, val)"
							/>
						</div>
					</template>
					<div v-else class="operator-hint-text text-muted small">
						<i class="fa fa-info-circle me-1"></i>
						{{ operatorNoValueHint(assignment.operator) }}
					</div>
				</div>

				<!-- Row Actions -->
				<div
					class="grid-col-actions d-flex align-items-center justify-content-end fxr-gap-2"
				>
					<div class="d-flex flex-column justify-content-center" style="gap: 2px">
						<button
							class="fxr-btn fxr-btn--icon fxr-btn--ghost p-0"
							:style="{
								height: '16px',
								minHeight: '16px',
								width: '24px',
								visibility: index === 0 ? 'hidden' : 'visible',
							}"
							@click="moveAssignment(index, -1)"
							:disabled="isReadOnly"
							:title="__('Move Up')"
							aria-label="Move Up"
						>
							<i class="fa fa-chevron-up" style="font-size: 10px"></i>
						</button>
						<button
							class="fxr-btn fxr-btn--icon fxr-btn--ghost p-0"
							:style="{
								height: '16px',
								minHeight: '16px',
								width: '24px',
								visibility: index === assignments.length - 1 ? 'hidden' : 'visible',
							}"
							@click="moveAssignment(index, 1)"
							:disabled="isReadOnly"
							:title="__('Move Down')"
							aria-label="Move Down"
						>
							<i class="fa fa-chevron-down" style="font-size: 10px"></i>
						</button>
					</div>
					<button
						class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost text-danger ms-1"
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
							@update:modelValue="updateDraft"
						/>
					</div>
					<div class="d-flex justify-content-between mt-3">
						<button
							class="fxr-btn fxr-btn--sm fxr-btn--ghost text-danger"
							@click="clearWhenCondition"
						>
							{{ __("Clear Condition") }}
						</button>
						<button
							class="fxr-btn fxr-btn--sm fxr-btn--secondary"
							@click="closeWhenConditionEditor"
						>
							{{ __("Close") }}
						</button>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, watch, ref, onMounted, onBeforeUnmount } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import FlexValueControl from "../../../controls/FlexValueControl.vue";
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
const supportedTemplateModes = [
	"formula",
	"resolver",
	"link",
	"dynamic-link",
	"select",
	"boolean",
	"multiselect",
	"json",
	"add-key",
];
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

function addAssignment() {
	assignments.value.push({
		name: makeRandomString(9),
		target: "",
		operator: "set",
		when_condition: null,
		when_expression: "",
		pythonExpression: "",
		value: { mode: "static", value: "" },
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

	// Intelligent defaulting for resolver kind based on target
	if (assignments.value[index].value?.mode === "resolver") {
		const config = assignments.value[index].value.config || {};
		if (!config.kind || config.kind === "resolver") {
			config.kind = getDefaultResolverKind(value);
			assignments.value[index].value.config = config;
		}
	}

	// Reset operator if it's no longer compatible with new target type
	const available = getAvailableOperators(value).map((o) => o.value);
	if (!available.includes(assignments.value[index].operator)) {
		const fieldtype = getTargetFieldtype(value);
		if (fieldtype === "Check") {
			assignments.value[index].operator = "toggle";
		} else {
			assignments.value[index].operator = "set";
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

function handleKeydown(e) {
	if (e.key === "Escape" && whenEditor.value.open) {
		e.preventDefault();
		e.stopPropagation();
		e.stopImmediatePropagation();
		closeWhenConditionEditor();
	}
}

onMounted(() => {
	window.addEventListener("keydown", handleKeydown, { capture: true });
});

onBeforeUnmount(() => {
	window.removeEventListener("keydown", handleKeydown, { capture: true });
});

function updateDraft(val) {
	if (whenEditor.value.index < 0) return;
	whenEditor.value.draft = val;
	const tree = val;
	const hasConditions = !!(tree && Array.isArray(tree.conditions) && tree.conditions.length);
	assignments.value[whenEditor.value.index].when_condition = hasConditions ? tree : null;
	assignments.value[whenEditor.value.index].when_expression = "";
	syncToNode();
}

function clearWhenCondition() {
	if (whenEditor.value.index < 0) return;
	assignments.value[whenEditor.value.index].when_condition = null;
	assignments.value[whenEditor.value.index].when_expression = "";
	whenEditor.value.draft = { op: "and", conditions: [] };
	syncToNode();
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
	padding: 8px 12px;
}

.header-icon-box {
	width: 32px;
	height: 32px;
	background: var(--fxr-accent-light, #e0f2fe);
	color: var(--fxr-accent, #2490ef);
	border-radius: var(--fxr-radius-md, 6px);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
}

/* Horizontal Table Grid Styling */
.assignment-grid-header,
.assignment-grid-row {
	display: grid;
	grid-template-columns:
		minmax(120px, 0.8fr) minmax(160px, 1.2fr) minmax(100px, 0.7fr) minmax(240px, 2fr)
		80px;
	gap: 8px;
	align-items: center;
}

@media (max-width: 900px) {
	.assignment-grid-header {
		display: none;
	}
	.assignment-grid-row {
		display: flex;
		flex-direction: column;
		align-items: stretch;
		gap: 8px;
	}
	.grid-col-when,
	.grid-col-target,
	.grid-col-operator,
	.grid-col-value {
		width: 100%;
	}
	.grid-col-actions {
		justify-content: flex-end;
		margin-top: 4px;
	}
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
	padding: 6px 12px;
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
