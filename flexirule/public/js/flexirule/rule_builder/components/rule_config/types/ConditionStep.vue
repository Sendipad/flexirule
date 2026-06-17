<template>
	<div class="condition-step">
		<div class="condition-step-header">
			<div class="d-flex align-items-center gap-2">
				<i class="fa fa-code-fork text-primary"></i>
				<h5 class="mb-0">{{ __("Conditions") }}</h5>
				<span v-if="hasErrors" class="badge badge-danger ml-1" title="Validation Errors">
					<i class="fa fa-exclamation-circle"></i>
				</span>
			</div>
			<div class="header-actions">
				<label class="old-doc-toggle">
					<input type="checkbox" v-model="showOldDoc" class="fxr-checkbox" />
					<span class="toggle-label">{{ __("Show Old Doc Fields") }}</span>
				</label>
			</div>
		</div>

		<div class="condition-builder-container">
			<ConditionBuilder
				ref="conditionBuilderRef"
				:modelValue="localConditions"
				:docFields="docFields"
				:variableOptions="combinedVariableOptions"
				@update:modelValue="updateConditions"
			/>
		</div>

		<div v-if="localConditions.conditions?.length" class="condition-step-footer mt-3">
			<div class="alert alert-info py-2 px-3 small mb-0">
				<i class="fa fa-info-circle"></i>
				{{ __("Conditions will be evaluated at runtime to determine the next step.") }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "../../../stores";
import { fromCodeString } from "../../../utils/serialization";
import ConditionBuilder from "../../condition_builder/ConditionBuilder.vue";
import { validateConditions } from "../../condition_builder/condition_validator.js";
import { getConditionPayload } from "../../../utils/condition_payload";

const props = defineProps({
	node: Object,
});

const store = useStore();
const localConditions = ref({ op: "and", conditions: [] });
const conditionBuilderRef = ref(null);
const hasErrors = ref(false);
const showOldDoc = ref(false);
const variableFields = ref([]);

/**
 * Hydrates conditions with ephemeral IDs for Vue reactivity.
 */
function hydrate(tree) {
	if (!tree || typeof tree !== "object") return tree;
	const hydrated = Array.isArray(tree) ? [...tree] : { ...tree };

	if (!hydrated.id) {
		hydrated.id = frappe.utils.get_random(12);
	}

	if (hydrated.conditions && Array.isArray(hydrated.conditions)) {
		hydrated.conditions = hydrated.conditions.map((c) => hydrate(c));
	}

	if (hydrated.where) {
		hydrated.where = hydrate(hydrated.where);
	}

	return hydrated;
}

/**
 * Strips ephemeral IDs before saving.
 */
function dehydrate(tree) {
	if (!tree || typeof tree !== "object") return tree;
	const clean = Array.isArray(tree) ? [...tree] : { ...tree };

	if (clean.id) delete clean.id;

	if (clean.conditions && Array.isArray(clean.conditions)) {
		clean.conditions = clean.conditions.map((c) => dehydrate(c));
	}

	if (clean.where) {
		clean.where = dehydrate(clean.where);
	}

	return clean;
}

// Initial hydration
watch(
	() => {
		if (props.node?.type === "start") {
			return props.node?.data?.trigger_condition;
		}
		return getConditionPayload({
			config: props.node?.data?.config,
			condition_json: props.node?.data?.condition_json,
		});
	},
	(val) => {
		if (val) {
			const parsed = typeof val === "string" ? fromCodeString(val) : val;

			const currentClean = dehydrate(localConditions.value);
			if (JSON.stringify(parsed) === JSON.stringify(currentClean)) {
				return;
			}

			localConditions.value = hydrate(parsed);
		} else {
			localConditions.value = { id: frappe.utils.get_random(12), op: "and", conditions: [] };
		}
	},
	{ immediate: true }
);

function updateConditions(val) {
	localConditions.value = val;
	save();
}

function save() {
	if (!props.node?.data) return;

	// Strip IDs
	const clean = dehydrate(localConditions.value);

	if (props.node.type === "start") {
		props.node.data.trigger_condition = clean;
	} else {
		props.node.data.config = clean;
		props.node.data.condition_json = null;
	}
	// DO NOT mark dirty here. useRuleConfig will handle it on modal Save.
}

/**
 * Compute fields available for conditions.
 */
const docFields = computed(() => {
	const dedupe = new Map();
	const pushField = (field) => {
		if (!field?.value) return;
		dedupe.set(field.value, field);
	};

	store.doc_fields.forEach(pushField);
	variableFields.value.forEach(pushField);
	let fields = Array.from(dedupe.values());

	if (showOldDoc.value) {
		const metaStore = store;
		const doctype = store.rule_doc?.document_type;
		if (doctype) {
			const oldFields = metaStore.get_fields_for_doctype(doctype, {
				alias: "old_doc",
				valueMode: "expression",
			});
			fields = [...fields, ...oldFields];
		}
	}

	const triggerTypeOptions = "DocType Event\nScheduler Event\nCallable Event";
	const triggerEventOptions = (store.trigger_event_options || []).join("\n");
	const contextFields = [
		{
			label: "context.doctype (Current Doctype)",
			value: "doctype",
			fieldname: "doctype",
			fieldtype: "Link",
			options: "DocType",
			operators: [
				"==",
				"!=",
				"in",
				"not in",
				"is_set",
				"is_not_set",
				"is_submittable",
				"has_field",
			],
			is_context: true,
		},
		{
			label: "caller.trigger_type (Caller Trigger Type)",
			value: "caller.trigger_type",
			fieldname: "caller_trigger_type",
			fieldtype: "Select",
			options: triggerTypeOptions,
			is_context: true,
		},
		{
			label: "caller.trigger_event (Caller Trigger Event)",
			value: "caller.trigger_event",
			fieldname: "caller_trigger_event",
			fieldtype: "Select",
			options: triggerEventOptions,
			is_context: true,
		},
		{
			label: "caller.document_type (Caller DocType)",
			value: "caller.document_type",
			fieldname: "caller_document_type",
			fieldtype: "Link",
			options: "DocType",
			operators: [
				"==",
				"!=",
				"in",
				"not in",
				"is_set",
				"is_not_set",
				"is_submittable",
				"has_field",
			],
			is_context: true,
		},
		{
			label: "rule.trigger_type (Target Trigger Type)",
			value: "rule.trigger_type",
			fieldname: "rule_trigger_type",
			fieldtype: "Select",
			options: triggerTypeOptions,
			is_context: true,
		},
		{
			label: "rule.trigger_event (Target Trigger Event)",
			value: "rule.trigger_event",
			fieldname: "rule_trigger_event",
			fieldtype: "Select",
			options: triggerEventOptions,
			is_context: true,
		},
		{
			label: "rule.document_type (Target DocType)",
			value: "rule.document_type",
			fieldname: "rule_document_type",
			fieldtype: "Link",
			options: "DocType",
			operators: [
				"==",
				"!=",
				"in",
				"not in",
				"is_set",
				"is_not_set",
				"is_submittable",
				"has_field",
			],
			is_context: true,
		},
	];
	fields = [...fields, ...contextFields];

	return fields.sort((a, b) => a.label.localeCompare(b.label));
});

const combinedVariableOptions = computed(() => {
	const dedupe = new Map();
	const pushOption = (v) => {
		const key = v.value || v;
		if (!key) return;
		dedupe.set(key, v);
	};

	// 1. Context fields (doc.*, caller.*, rule.*)
	docFields.value.forEach(pushOption);

	// 2. Runtime variables (vars.*)
	variableFields.value.forEach(pushOption);

	return Array.from(dedupe.values());
});

async function refreshVariableFields() {
	const nodeId = props.node?.id;
	if (!nodeId || props.node?.type === "start") {
		variableFields.value = [];
		return;
	}

	try {
		const available = await store.getAvailableVariables(nodeId);
		variableFields.value = available || [];
	} catch (e) {
		variableFields.value = [];
	}
}

// Load metadata on mount if needed
onMounted(async () => {
	const node = props.node;
	if (!node) return;

	const doctype = node.data?.document_type || store.rule_doc?.document_type;
	if (doctype && !store.doc_fields.length) {
		await store.fetch_metadata(doctype);
	}
	await refreshVariableFields();
});

watch(
	() => [
		props.node?.id,
		(store.nodes || [])
			.filter(Boolean)
			.map((node) => [
				node.id,
				node.data?.return_variable,
				node.data?.return_type,
				node.data?.resolved_output_schema,
			]),
	],
	() => {
		refreshVariableFields();
	},
	{ deep: true }
);

function validate() {
	if (!conditionBuilderRef.value) return { valid: true, errors: [] };

	const type = props.node?.data?.action_type || props.node?.type;
	// Only 'Condition' nodes MUST have a condition defined.
	// For all other nodes, conditions are optional execution filters.
	const isMandatory = type === "Condition";
	const result = conditionBuilderRef.value.validate(isMandatory);

	hasErrors.value = !result.valid;

	if (!result.valid) {
		return { valid: false, errors: result.errors.map((e) => e.message) };
	}
	return { valid: true, errors: [] };
}

defineExpose({
	validate,
});
</script>

<style scoped>
.condition-step {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-4);
}

.condition-step-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding-bottom: var(--fxr-space-3);
	border-bottom: 1px solid var(--fxr-border);
	flex-wrap: wrap;
	gap: var(--fxr-space-3);
}

@media (max-width: 768px) {
	.condition-step-header {
		padding: 0 var(--fxr-space-1) var(--fxr-space-3);
	}
}

.condition-step-header h5 {
	font-size: 13px;
	font-weight: 600;
	color: var(--fxr-text-strong);
}

.old-doc-toggle {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-2);
	margin-bottom: 0;
	cursor: pointer;
	user-select: none;
}

.old-doc-toggle .toggle-label {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-soft);
	font-weight: var(--fxr-weight-medium);
}

.fxr-checkbox {
	width: 14px;
	height: 14px;
	margin: 0;
	cursor: pointer;
}

.condition-builder-container {
	position: relative;
	z-index: 10;
}

.condition-builder-container :deep(.condition-builder) {
	padding: 0;
	background: transparent;
}
</style>
