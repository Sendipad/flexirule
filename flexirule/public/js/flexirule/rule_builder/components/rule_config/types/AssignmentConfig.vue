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

		<GenericGrid
			v-model="assignments"
			rowKey="name"
			:readOnly="isReadOnly"
			:pagination="false"
			:showSearch="false"
			:selection="false"
			:primaryAction="{
				label: __('Add Assignment'),
				icon: 'fa fa-plus',
			}"
			@primary-action="addAssignment"
			@row-action="handleGridRowAction"
		>
			<template #header>
				<div v-if="assignments.length" class="assignment-grid-header">
					<div class="grid-col-when">{{ __("Run If") }}</div>
					<div class="grid-col-target">{{ __("Target Field") }}</div>
					<div class="grid-col-operator">{{ __("Operator") }}</div>
					<div class="grid-col-value">{{ __("Value Expression") }}</div>
				</div>
			</template>

			<template #empty>
				<div
					class="empty-state d-flex flex-column align-items-center justify-content-center py-5"
				>
					<div class="empty-state-icon mb-3">
						<i class="fa fa-list-ol fa-3x text-muted opacity-25"></i>
					</div>
					<div class="text-center px-4">
						<h6 class="mb-1 fw-bold text-muted">{{ __("No Assignments Yet") }}</h6>
						<p class="small text-muted mb-0">
							{{
								__(
									"Add an assignment to start mutating document fields or variables."
								)
							}}
						</p>
					</div>
				</div>
			</template>

			<template #row="{ row: assignment, index }">
				<div class="assignment-grid-row align-items-center">
					<div class="grid-col-when">
						<div class="when-editor-cell" v-fxr-fieldname="'assignments.run_if'">
							<button
								class="fxr-btn fxr-btn--sm w-100 when-toggle-btn"
								:class="{
									'is-active': hasWhenCondition(assignment),
									'is-default': !hasWhenCondition(assignment),
									'is-invalid':
										showValidation &&
										getWhenConditionStatus(assignment).isInvalid,
								}"
								:disabled="isReadOnly"
								@click="openWhenConditionEditor(index)"
							>
								<i
									:class="
										getWhenConditionStatus(assignment).isInvalid
											? 'fa fa-exclamation-triangle'
											: hasWhenCondition(assignment)
												? 'fa fa-filter'
												: 'fa fa-play-circle-o'
									"
									class="me-2"
								></i>
								<span class="truncate">
									{{
										getWhenConditionStatus(assignment).isInvalid
											? __("Invalid Condition")
											: hasWhenCondition(assignment)
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
							:ref="setControlRef"
							fieldname="assignments.target"
							:df="{ fieldtype: 'FieldPicker', label: '', reqd: 1 }"
							:modelValue="assignment.target"
							:options="targetOptions"
							:read_only="isReadOnly"
							:hideLabel="true"
							:showValidation="showValidation"
							:trigger="'button'"
							:placeholder="__('Target field/variable...')"
							:allowCustomValue="false"
							@update:modelValue="(val) => onTargetChange(index, val)"
						/>
					</div>

					<!-- Operator Selector -->
					<div class="grid-col-operator">
						<ComboBoxControl
							:ref="setControlRef"
							fieldname="assignments.operator"
							:df="{ fieldtype: 'Select', label: '', reqd: 1 }"
							:options="getAvailableOperators(assignment.target)"
							:modelValue="assignment.operator"
							:read_only="isReadOnly"
							:hideLabel="true"
							:showValidation="showValidation"
							:trigger="'button'"
							@update:modelValue="(val) => onOperatorChange(index, val)"
						/>
					</div>

					<!-- Value Expression Editor -->
					<div class="grid-col-value">
						<template v-if="needsValue(assignment.operator)">
							<div class="value-mode-wrap">
								<FlexValueControl
									:ref="setControlRef"
									class="flex-1 min-w-0"
									fieldname="assignments.value"
									:context="{
										df: {
											...(targetOptions.find(
												(o) => o.value === assignment.target
											) || {}),
											reqd: 1,
										},
										target: assignment.target,
										operator: assignment.operator,
										referenceDoctype: getTargetDoctype(assignment.target),
									}"
									:modelValue="assignment.value"
									:read_only="isReadOnly"
									:showValidation="showValidation"
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
				</div>
			</template>
		</GenericGrid>

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
							ref="conditionBuilderRef"
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
							<i class="fa fa-trash me-1"></i>
							{{ __("Clear Condition") }}
						</button>

						<button
							class="fxr-btn fxr-btn--sm fxr-btn--primary"
							@click="closeWhenConditionEditor"
						>
							{{ __("Done") }}
						</button>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import GenericGrid from "../../../controls/GenericGrid.vue";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import FlexValueControl from "../../../controls/FlexValueControl.vue";
import ConditionBuilder from "../../condition_builder/ConditionBuilder.vue";
import { useRuleStore } from "../../../stores/useRuleStore";
import { useMetaStore } from "../../../stores/useMetaStore";
import { validateConditions } from "../../../utils/condition_payload";

const props = defineProps({
	modelValue: { type: Object, default: () => ({}) },
	readOnly: { type: Boolean, default: false },
	action: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue"]);

const store = useRuleStore();
const metaStore = useMetaStore();

const showValidation = ref(false);
const controlRefs = ref([]);
const conditionBuilderRef = ref(null);

function setControlRef(el) {
	if (el && !controlRefs.value.includes(el)) {
		controlRefs.value.push(el);
	}
}

// Ensure array reset on re-render / validation reset
watch(
	() => props.modelValue,
	() => {
		controlRefs.value = [];
	},
	{ deep: true }
);

const isReadOnly = computed(() => props.readOnly);
const assignments = ref([]);

function normalizeValuePayload(raw) {
	if (!raw) return { mode: "static", value: "" };
	if (typeof raw === "string") return { mode: "static", value: raw };
	if (typeof raw === "object") {
		return {
			mode: raw.mode || (raw.resolver ? "resolver" : "static"),
			value: raw.value ?? "",
			resolver: raw.resolver ?? null,
		};
	}
	return { mode: "static", value: "" };
}

function normalizeAssignmentItem(item, index) {
	const raw = item && typeof item === "object" ? item : {};
	return {
		name:
			raw.name ||
			raw.id ||
			`assign_${Date.now()}_${index}_${Math.random().toString(36).substr(2, 4)}`,
		target: raw.target || "",
		operator: raw.operator || "=",
		value: normalizeValuePayload(raw.value),
		when_condition:
			raw.when_condition &&
			typeof raw.when_condition === "object" &&
			Array.isArray(raw.when_condition.conditions)
				? raw.when_condition
				: null,
		when_expression: typeof raw.when_expression === "string" ? raw.when_expression : "",
	};
}

function deepClone(val) {
	if (val === null || val === undefined) return val;
	return JSON.parse(JSON.stringify(val));
}

// ─── Condition Modal State ──────────────────────────────────────────────────
const whenEditor = ref({
	open: false,
	index: -1,
	draft: null,
});

function hasWhenCondition(assignment) {
	const c = assignment?.when_condition;
	return !!(c && Array.isArray(c.conditions) && c.conditions.length > 0);
}

function getWhenConditionStatus(assignment) {
	if (!hasWhenCondition(assignment)) {
		return { isInvalid: false, errors: [] };
	}
	const res = validateConditions(assignment.when_condition, true, true);
	return { isInvalid: !res.valid, errors: res.errors || [] };
}

// Sync from props
watch(
	() => props.modelValue,
	(newVal) => {
		const rawAssignments = Array.isArray(newVal?.assignments) ? newVal.assignments : [];
		const normalized = rawAssignments.map(normalizeAssignmentItem);

		if (JSON.stringify(assignments.value) !== JSON.stringify(normalized)) {
			assignments.value = normalized;
		}
	},
	{ immediate: true, deep: true }
);

function syncToNode() {
	const cleaned = assignments.value.map((a) => {
		const payload = {
			name: a.name,
			target: a.target,
			operator: a.operator,
			value: a.value,
		};
		if (
			a.when_condition &&
			Array.isArray(a.when_condition.conditions) &&
			a.when_condition.conditions.length
		) {
			payload.when_condition = a.when_condition;
		}
		if (a.when_expression) {
			payload.when_expression = a.when_expression;
		}
		return payload;
	});

	emit("update:modelValue", {
		...props.modelValue,
		assignments: cleaned,
	});
}

function addAssignment() {
	if (isReadOnly.value) return;
	assignments.value.push({
		name: `assign_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
		target: "",
		operator: "=",
		value: { mode: "static", value: "" },
		when_condition: null,
		when_expression: "",
	});
	syncToNode();
}

function removeAssignment(index) {
	if (isReadOnly.value) return;
	assignments.value.splice(index, 1);
	syncToNode();
}

function moveAssignment(index, direction) {
	if (isReadOnly.value) return;
	const newIndex = index + direction;
	if (newIndex < 0 || newIndex >= assignments.value.length) return;
	const item = assignments.value.splice(index, 1)[0];
	assignments.value.splice(newIndex, 0, item);
	syncToNode();
}

function handleGridRowAction({ action, index }) {
	if (isReadOnly.value) return;
	switch (action) {
		case "remove":
			removeAssignment(index);
			break;
		case "move-up":
			moveAssignment(index, -1);
			break;
		case "move-down":
			moveAssignment(index, 1);
			break;
	}
}

function clearAssignments() {
	if (isReadOnly.value) return;
	assignments.value = [];
	syncToNode();
}

// ─── Target & Field Options ──────────────────────────────────────────────────

const primaryDoctype = computed(() => store.rule_doc?.primary_doctype);

onMounted(() => {
	if (primaryDoctype.value) {
		metaStore.fetch_metadata(primaryDoctype.value);
	}
});

const docFields = computed(() => {
	if (!primaryDoctype.value) return [];
	const meta = metaStore.doc_meta[primaryDoctype.value] || [];
	return meta
		.filter(
			(f) =>
				f.fieldname && !["Section Break", "Column Break", "Tab Break"].includes(f.fieldtype)
		)
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: `doc.${f.fieldname}`,
			fieldname: f.fieldname,
			fieldtype: f.fieldtype,
			options: f.options,
			group: __("Document Fields"),
		}));
});

const variable_options = computed(() => {
	const vars = store.rule_doc?.variables || [];
	return vars.map((v) => ({
		label: `${v.variable_name} (${v.data_type || "Data"})`,
		value: `vars.${v.variable_name}`,
		fieldname: v.variable_name,
		fieldtype: v.data_type || "Data",
		group: __("Variables"),
	}));
});

const targetOptions = computed(() => {
	return [...docFields.value, ...variable_options.value];
});

function getTargetFieldtype(targetPath) {
	if (!targetPath) return "Data";
	const match = targetOptions.value.find((o) => o.value === targetPath);
	return match?.fieldtype || "Data";
}

function getTargetDoctype(targetPath) {
	if (targetPath?.startsWith("doc.")) return primaryDoctype.value;
	return null;
}

function onTargetChange(index, value) {
	assignments.value[index].target = value;
	const defaultKind = getDefaultResolverKind(value);
	const currentVal = assignments.value[index].value;

	if (currentVal?.mode === "resolver" && currentVal?.resolver) {
		assignments.value[index].value = {
			...currentVal,
			resolver: {
				...currentVal.resolver,
				kind: defaultKind,
			},
		};
	}
	syncToNode();
}

// ─── Operator Options ────────────────────────────────────────────────────────

const NUMERIC_TYPES = ["Int", "Float", "Currency", "Percent"];

function getAvailableOperators(targetPath) {
	const ft = getTargetFieldtype(targetPath);
	const isNumeric = NUMERIC_TYPES.includes(ft);

	const ops = [
		{ label: "= (Set)", value: "=" },
		{ label: "Clear (Null)", value: "clear" },
	];

	if (isNumeric) {
		ops.push(
			{ label: "+= (Increment)", value: "+=" },
			{ label: "-= (Decrement)", value: "-=" },
			{ label: "*= (Multiply)", value: "*=" },
			{ label: "/= (Divide)", value: "/=" }
		);
	}

	return ops;
}

function needsValue(operator) {
	return operator !== "clear";
}

function operatorNoValueHint(operator) {
	if (operator === "clear") return __("Clears the field value to null / empty");
	return "";
}

// ─── Condition Options ───────────────────────────────────────────────────────

const whenConditionDocFields = computed(() =>
	(docFields.value || []).map((f) => ({
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
		draft: deepClone(current?.when_condition || fallback),
	};

	if (showValidation.value && getWhenConditionStatus(current).isInvalid) {
		nextTick(() => {
			if (conditionBuilderRef.value) {
				conditionBuilderRef.value.validate();
				nextTick(() => {
					const firstError = document.querySelector(
						".condition-builder-wrap .is-invalid"
					);
					if (firstError) {
						firstError.scrollIntoView({ behavior: "smooth", block: "center" });
					}
				});
			}
		});
	}
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
	if (!fieldtype) return "text";

	if (["Int", "Float", "Percent", "Currency"].includes(fieldtype)) {
		return "math_formula";
	}
	if (["Date", "Datetime", "Time"].includes(fieldtype)) {
		return "date_time";
	}
	return "text";
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
	assignments.value.forEach((a, idx) => {
		const n = idx + 1;

		// Target path validation
		if (a.target && !a.target.startsWith("doc.") && !a.target.startsWith("vars.")) {
			errors.push(__("Assignment #{0}: Target must start with 'doc.' or 'vars.'", [n]));
		}

		// Validate nested conditions if editor is open for THIS assignment
		if (whenEditor.value.open && whenEditor.value.index === idx && conditionBuilderRef.value) {
			const res = conditionBuilderRef.value.validate();
			if (!res.valid) {
				errors.push(...res.errors.map((e) => __("Assignment #{0} Condition: {1}", [n, e])));
			}
		} else if (a.when_condition) {
			// Deep validation of existing conditions
			const res = validateConditions(a.when_condition, true, true);
			if (!res.valid) {
				errors.push(...res.errors.map((e) => __("Assignment #{0} Condition: {1}", [n, e])));
			}
		}
	});

	if (assignments.value.length === 0) {
		errors.push(__("Please add at least one assignment."));
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.assignment-config {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-xs);
}

.assignment-header-card {
	background-color: var(--fxr-surface-soft);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	padding: var(--spacing-md) var(--spacing-lg);
	margin-bottom: var(--spacing-md) !important;
}

.header-icon-box {
	width: 32px;
	height: 32px;
	background-color: var(--fxr-accent-soft);
	color: var(--fxr-accent);
	border-radius: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
}

/* Horizontal Table Grid Styling */
.assignment-grid-header,
.assignment-grid-row {
	display: grid;
	grid-template-columns: minmax(100px, 0.7fr) minmax(140px, 1.1fr) minmax(100px, 0.7fr) minmax(
			240px,
			2.5fr
		);
	gap: var(--spacing-md);
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
}

.assignment-grid-header {
	padding: var(--spacing-xs) var(--spacing-md);
	font-size: 10px;
	font-weight: 800;
	color: var(--fxr-text-faint);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	border-bottom: 1px solid var(--fxr-border-subtle);
	margin-bottom: 4px;
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
	background-color: var(--fxr-surface-2);
	color: var(--fxr-text-soft);
}

.when-toggle-btn.is-default:hover {
	background-color: var(--fxr-bg-hover);
	border-color: var(--fxr-border-strong);
}

.when-toggle-btn.is-active {
	background-color: color-mix(in srgb, var(--fxr-accent) 15%, transparent);
	color: var(--fxr-accent);
	border: 1px solid var(--fxr-accent-border);
	box-shadow: 0 0 0 1px var(--fxr-accent-soft);
}

.when-toggle-btn.is-invalid {
	background-color: var(--fxr-danger-soft) !important;
	color: var(--fxr-text-danger) !important;
	border: 1px solid var(--fxr-border-danger) !important;
	box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.1) !important;
}

.when-toggle-btn.is-active:hover {
	background-color: color-mix(in srgb, var(--fxr-accent) 25%, transparent);
	border-color: var(--fxr-accent);
}

.fxr-modal-overlay {
	position: fixed;
	inset: 0;
	background-color: rgba(0, 0, 0, 0.5);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 13000;
}

.fxr-modal-card {
	width: min(980px, 92vw);
	max-height: 86vh;
	background-color: var(--fxr-surface-elevated);
	border-radius: 14px;
	border: 1px solid var(--fxr-border-subtle);
	padding: 14px;
	overflow: hidden;
	display: flex;
	flex-direction: column;
}

.condition-builder-wrap {
	overflow: auto;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 12px;
	padding: 8px;
	background-color: var(--fxr-surface-soft);
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
	border-radius: var(--fxr-radius-md);
	color: var(--fxr-text-soft);
	border: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-bg-input);
	transition: all 0.2s ease;
	cursor: pointer;
}

.value-mode-toggle:hover:not(:disabled) {
	color: var(--fxr-accent);
	border-color: var(--fxr-accent);
	background-color: var(--fxr-bg-hover);
}

.assignment-grid-row {
	background-color: var(--fxr-bg-input);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	padding: var(--spacing-xs) var(--spacing-md);
	transition: all var(--fxr-transition-fast);
	margin-bottom: 0 !important;
}

.assignment-grid-row:hover {
	border-color: var(--fxr-accent);
	background-color: var(--fxr-surface-soft);
	z-index: 1;
}

.operator-hint-text {
	display: flex;
	align-items: center;
	padding: 6px 12px;
	background-color: var(--fxr-surface-2);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 6px;
	height: 32px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	color: var(--fxr-text-soft);
}

.empty-state {
	border: 2px dashed var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
	background-color: var(--fxr-surface-soft);
	transition: all 0.2s ease;
	flex: 0 0 auto;
}

.empty-state:hover {
	border-color: var(--fxr-border-strong);
	background-color: var(--fxr-surface);
}

@media (max-width: 768px) {
	.assignment-header-card {
		padding: 10px;
	}

	.assignment-grid-row {
		padding: 10px;
	}

	.value-mode-wrap {
		flex-direction: column;
		align-items: stretch;
	}

	.value-mode-toggle {
		width: 100%;
	}
}
</style>
