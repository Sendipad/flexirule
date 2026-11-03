<template>
	<div class="condition-step">
		<div class="condition-step-header">
			<h5>
				{{
					isEntryNode
						? __("Entry Condition Configuration")
						: __("Condition Configuration")
				}}
			</h5>

			<div class="d-flex align-items-center gap-2">
				<label class="old-doc-toggle">
					<input
						type="checkbox"
						v-model="showOldDoc"
						:disabled="readOnly || read_only"
						class="mr-1 fxr-checkbox-input"
					/>
					<span class="toggle-label">{{ __("Show Old Doc Fields") }}</span>
				</label>
			</div>
		</div>

		<div v-if="isEntryNode" class="alert alert-warning py-2 px-3 small my-2">
			<i class="fa fa-filter mr-1"></i>
			{{
				__(
					"This condition is evaluated before any rule actions run. If the condition is false, execution terminates immediately without starting configured rule actions."
				)
			}}
		</div>

		<div class="condition-builder-container">
			<CanonicalConditionBuilder
				ref="canonicalBuilderRef"
				:modelValue="localCanonicalCondition"
				:docFields="docFields"
				:variableOptions="combinedVariableOptions"
				:readOnly="readOnly || read_only"
				:isMandatory="isConditionMandatory"
				:currentDocType="currentDocType"
				:store="ruleStore"
				@update:modelValue="updateConditions"
			/>
		</div>

		<div v-if="localCanonicalCondition" class="condition-step-footer mt-3">
			<div class="alert alert-info py-2 px-3 small mb-0">
				<i class="fa fa-info-circle mr-1"></i>
				<template v-if="isEntryNode">
					{{
						__(
							"This entry condition is evaluated before rule actions start. If it is false, the rule stops before executing any actions."
						)
					}}
				</template>
				<template v-else>
					{{ __("Conditions will be evaluated at runtime to determine the next step.") }}
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRuleStore, useGraphStore, useMetaStore } from "../../../stores";
import CanonicalConditionBuilder from "../../condition_builder/CanonicalConditionBuilder.vue";
import { getConditionPayload } from "../../../utils/condition_payload";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
	read_only: Boolean,
	showValidation: { type: Boolean, default: false },
});

const ruleStore = useRuleStore();
const graphStore = useGraphStore();
const metaStore = useMetaStore();

const localCanonicalCondition = ref(null);
const showOldDoc = ref(false);
const variableFields = ref([]);
const canonicalBuilderRef = ref(null);

const isEntryNode = computed(() => {
	return props.node?.type === "start" || props.node?.data?.action_type === "Entry Action";
});

const isConditionMandatory = computed(() => {
	return props.node?.data?.action_type === "Condition" || props.node?.type === "Condition";
});

const currentDocType = computed(() => {
	return props.node?.data?.document_type || ruleStore.rule_doc?.document_type || "";
});

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
		if (JSON.stringify(val) !== JSON.stringify(localCanonicalCondition.value)) {
			localCanonicalCondition.value = val || null;
		}
	},
	{ immediate: true }
);

function updateConditions(val) {
	localCanonicalCondition.value = val;
	save();
}

function save() {
	if (!props.node?.data) return;

	if (props.node.type === "start") {
		props.node.data.trigger_condition = localCanonicalCondition.value;
	} else {
		props.node.data.config = localCanonicalCondition.value;
		props.node.data.condition_json = null;
	}
}

const docFields = computed(() => {
	const dedupe = new Map();
	const pushField = (field) => {
		if (!field?.value) return;
		dedupe.set(field.value, field);
	};

	(ruleStore.doc_fields || []).forEach(pushField);
	variableFields.value.forEach(pushField);
	let fields = Array.from(dedupe.values());

	if (showOldDoc.value) {
		const doctype = ruleStore.rule_doc?.document_type;
		if (doctype) {
			const oldFields = metaStore.get_fields_for_doctype(doctype, {
				alias: "old_doc",
				valueMode: "expression",
			});
			fields = [...fields, ...oldFields];
		}
	}

	const triggerTypeOptions = "DocType Event\nScheduler Event\nCallable Event";
	const triggerEventOptions = (ruleStore.trigger_event_options || []).join("\n");
	const contextFields = [
		{
			label: "context.doctype (Current Doctype)",
			value: "doctype",
			fieldname: "doctype",
			fieldtype: "Link",
			options: "DocType",
			operators: [
				"eq",
				"ne",
				"in",
				"not_in",
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
				"eq",
				"ne",
				"in",
				"not_in",
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
				"eq",
				"ne",
				"in",
				"not_in",
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

	docFields.value.forEach(pushOption);
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
		const available = await graphStore.getAvailableVariables(nodeId);
		variableFields.value = available || [];
	} catch (e) {
		variableFields.value = [];
	}
}

onMounted(async () => {
	const node = props.node;
	if (!node) return;

	const doctype = node.data?.document_type || ruleStore.rule_doc?.document_type;
	if (doctype && !ruleStore.doc_fields?.length) {
		await metaStore.fetch_metadata(doctype);
	}
	await refreshVariableFields();
});

watch(
	() => [
		props.node?.id,
		(graphStore.nodes || [])
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
	if (canonicalBuilderRef.value) {
		return canonicalBuilderRef.value.validate();
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

.condition-builder-container {
	position: relative;
	z-index: 10;
}
</style>
