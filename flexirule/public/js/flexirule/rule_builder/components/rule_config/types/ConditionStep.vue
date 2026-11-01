<template>
	<div class="condition-step p-2">
		<div class="condition-step-header mb-3">
			<h5 class="mb-0">
				<i class="fa fa-filter text-primary mr-2"></i>
				{{ isEntryNode ? __("Rule Entry Condition") : __("Condition Configuration") }}
			</h5>
			<div class="old-doc-toggle">
				<label class="mb-0 d-flex align-items-center">
					<input type="checkbox" v-model="showOldDoc" class="fxr-checkbox" />
					<span class="toggle-label ml-1">{{ __("Show Old Doc Fields") }}</span>
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
			<ConditionBuilder
				ref="conditionBuilderRef"
				:modelValue="localConditions"
				:docFields="docFields"
				:variableOptions="combinedVariableOptions"
				:readOnly="readOnly || read_only"
				:showValidation="showValidation"
				:isMandatory="
					props.node?.data?.action_type === 'Condition' ||
					props.node?.type === 'Condition'
				"
				@update:modelValue="updateConditions"
			/>
		</div>

		<div
			v-if="
				localConditions &&
				(localConditions.children?.length || localConditions.conditions?.length)
			"
			class="condition-step-footer mt-3"
		>
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
import { useStore } from "../../../stores";
import ConditionBuilder from "../../condition_builder/ConditionBuilder.vue";
import { normalizeConditionNode } from "../../condition_builder/canonical_condition_adapter.mjs";
import { getConditionPayload } from "../../../utils/condition_payload";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
	read_only: Boolean,
	showValidation: { type: Boolean, default: false },
});

const store = useStore();
const localConditions = ref({ type: "group", op: "and", children: [] });
const showOldDoc = ref(false);
const variableFields = ref([]);
const conditionBuilderRef = ref(null);

const isEntryNode = computed(() => {
	return props.node?.type === "start" || props.node?.data?.action_type === "Entry Action";
});

// Load and normalize conditions into canonical AST
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
			const normalized = normalizeConditionNode(val);
			if (JSON.stringify(normalized) !== JSON.stringify(localConditions.value)) {
				localConditions.value = normalized;
			}
		} else {
			localConditions.value = { type: "group", op: "and", children: [] };
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

	if (props.node.type === "start") {
		props.node.data.trigger_condition = localConditions.value;
	} else {
		props.node.data.config = localConditions.value;
		props.node.data.condition_json = null;
	}
}

/**
 * Compute docFields available for condition operands.
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
		const available = await store.getAvailableVariables(nodeId);
		variableFields.value = available || [];
	} catch (e) {
		variableFields.value = [];
	}
}

onMounted(async () => {
	const node = props.node;
	if (!node) return;

	const doctype = node.data?.document_type || store.rule_doc?.document_type;
	if (doctype && !store.doc_fields.length) {
		await store.fetch_metadata(doctype);
	}
	await refreshVariableFields();
});

function validate() {
	if (conditionBuilderRef.value) {
		return conditionBuilderRef.value.validate();
	}
	return { isValid: true, errors: [] };
}

defineExpose({
	validate,
});
</script>

<style scoped>
.condition-step-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding-bottom: var(--fxr-space-3, 12px);
	border-bottom: 1px solid var(--fxr-border, #e5e7eb);
}
</style>
