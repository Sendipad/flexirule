<template>
	<div class="assignment-config">
		<div class="fxr-card mb-4">
			<div class="fxr-card-body d-flex align-items-center justify-content-between">
				<div class="d-flex align-items-center fxr-row--gap-4">
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
					class="fxr-btn text-danger"
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
				class="assignment-row-card mb-2"
			>
				<div class="grid-col-when">
					<div class="when-editor-cell" data-fxr-fieldname="assignments.run_if">
						<button
							class="fxr-btn w-100 when-toggle-btn"
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
						data-fxr-fieldname="assignments.target"
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
						data-fxr-fieldname="assignments.operator"
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
								data-fxr-fieldname="assignments.value"
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
					<div v-else class="operator-hint-text">
						<i class="fa fa-info-circle me-1 opacity-50"></i>
						{{ operatorNoValueHint(assignment.operator) }}
					</div>
				</div>

				<!-- Row Actions -->
				<div class="grid-col-actions d-flex align-items-center justify-content-end gap-2">
					<div class="d-flex flex-column justify-content-center" style="gap: 2px">
						<button
							class="btn-icon-grid"
							:style="{
								visibility: index === 0 ? 'hidden' : 'visible',
							}"
							@click="moveAssignment(index, -1)"
							:disabled="isReadOnly"
							:title="__('Move Up')"
						>
							<i class="fa fa-chevron-up" style="font-size: 10px"></i>
						</button>
						<button
							class="btn-icon-grid"
							:style="{
								visibility: index === assignments.length - 1 ? 'hidden' : 'visible',
							}"
							@click="moveAssignment(index, 1)"
							:disabled="isReadOnly"
							:title="__('Move Down')"
						>
							<i class="fa fa-chevron-down" style="font-size: 10px"></i>
						</button>
					</div>
					<button
						class="btn-icon-grid text-danger"
						@click="removeAssignment(index)"
						:disabled="isReadOnly"
						:title="__('Remove')"
					>
						<i class="fa fa-trash-o"></i>
					</button>
				</div>
			</div>
		</div>

		<div v-if="!assignments.length" class="empty-state py-5">
			<i class="fa fa-list-ol opacity-20 mb-3" style="font-size: 32px"></i>
			<div class="text-center px-4">
				<h6 class="mb-1 fw-bold text-muted">{{ __("No Assignments Yet") }}</h6>
				<p class="small text-muted mb-0">
					{{ __("Add an assignment to start mutating document fields or variables.") }}
				</p>
			</div>
		</div>

		<button
			class="fxr-btn py-3 mt-2 border-dashed w-100"
			@click="addAssignment"
			:disabled="isReadOnly"
		>
			<i class="fa fa-plus me-2"></i>
			<span>{{ __("Add Assignment") }}</span>
		</button>

		<Teleport to="body">
			<div
				v-if="whenEditor.open"
				class="fxr-modal-overlay"
				@click.self="closeWhenConditionEditor"
			>
				<div class="fxr-modal-card">
					<div class="d-flex align-items-center justify-content-between mb-4">
						<h5 class="mb-0 fw-bold">{{ __("Assignment Run Condition") }}</h5>
						<button class="btn-close-subtle" @click="closeWhenConditionEditor">
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
					<div class="d-flex justify-content-between mt-4">
						<button class="fxr-btn text-danger" @click="clearWhenCondition">
							{{ __("Clear Condition") }}
						</button>
						<button class="fxr-btn fxr-btn--primary" @click="closeWhenConditionEditor">
							{{ __("Done") }}
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

	if (assignments.value[index].value?.mode === "resolver") {
		const config = assignments.value[index].value.config || {};
		if (!config.kind || config.kind === "resolver") {
			config.kind = getDefaultResolverKind(value);
			assignments.value[index].value.config = config;
		}
	}

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
}

.header-icon-box {
	width: 36px;
	height: 36px;
	background: var(--fr-primary-subtle);
	color: var(--fr-primary);
	border-radius: var(--fr-radius-md);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 16px;
}

.assignment-grid-header {
	display: grid;
	grid-template-columns: 140px 180px 120px 1fr 100px;
	gap: 12px;
	padding: 10px 16px;
	font-size: 10px;
	font-weight: 700;
	color: var(--fr-text-muted);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	border-bottom: 1px solid var(--fr-border-subtle);
	margin-bottom: 8px;
}

.assignment-row-card {
	display: grid;
	grid-template-columns: 140px 180px 120px 1fr 100px;
	gap: 12px;
	align-items: center;
	background: var(--fr-bg-surface);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	padding: 10px 16px;
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	box-shadow: var(--fr-shadow-sm);
}

.assignment-row-card:hover {
	border-color: var(--fr-primary);
	box-shadow: var(--fr-shadow-md);
	transform: translateY(-1px);
}

.when-toggle-btn {
	justify-content: flex-start;
	padding: 0 10px;
	height: 32px;
	font-weight: 600;
	font-size: 11px;
}

.when-toggle-btn.is-default {
	background: var(--fr-bg-muted);
	color: var(--fr-text-secondary);
}

.when-toggle-btn.is-active {
	background: #f5f3ff;
	color: #7c3aed;
	border-color: rgba(124, 58, 237, 0.2);
}

.operator-hint-text {
	display: flex;
	align-items: center;
	padding: 0 12px;
	background: var(--fr-bg-muted);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-md);
	height: 32px;
	font-size: 11px;
	color: var(--fr-text-muted);
}

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	background: var(--fr-bg-surface);
	border: 1px dashed var(--fr-border);
	border-radius: var(--fr-radius-xl);
}

.border-dashed {
	border-style: dashed !important;
}

.fxr-modal-overlay {
	position: fixed;
	inset: 0;
	background: rgba(15, 23, 42, 0.4);
	backdrop-filter: blur(8px);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 2000;
}

.fxr-modal-card {
	width: min(1000px, 94vw);
	max-height: 90vh;
	background: var(--fr-bg-surface);
	border-radius: var(--fr-radius-xl);
	border: 1px solid var(--fr-border);
	padding: 24px;
	box-shadow: var(--fr-shadow-lg);
	display: flex;
	flex-direction: column;
}

.condition-builder-wrap {
	overflow: auto;
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	padding: 16px;
	background: var(--fr-bg-muted);
}

.btn-icon-grid {
	width: 24px;
	height: 24px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border-radius: 4px;
	border: none;
	background: transparent;
	color: var(--fr-text-muted);
	cursor: pointer;
	transition: all 0.15s;
}

.btn-icon-grid:hover:not(:disabled) {
	background: var(--fr-gray-200);
	color: var(--fr-text);
}

.btn-close-subtle {
	width: 32px;
	height: 32px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: transparent;
	border: none;
	color: var(--fr-text-muted);
	border-radius: var(--fr-radius-md);
	cursor: pointer;
	transition: all 0.15s;
}

.btn-close-subtle:hover {
	background: var(--fr-bg-muted);
	color: var(--fr-text);
}

@media (max-width: 1100px) {
	.assignment-grid-header {
		display: none;
	}
	.assignment-row-card {
		display: flex;
		flex-direction: column;
		align-items: stretch;
		gap: 12px;
	}
}
</style>
