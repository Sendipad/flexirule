<template>
	<div class="canonical-condition-builder">
		<div v-if="contractError" class="alert alert-danger py-2 px-3 small mb-2">
			<i class="fa fa-exclamation-circle mr-1"></i>
			<span
				>{{ __("Failed to load canonical condition contract: ") }}{{ contractError }}</span
			>
			<button
				type="button"
				class="btn btn-xs btn-outline-danger ml-2"
				@click="loadContract(true)"
			>
				{{ __("Retry") }}
			</button>
		</div>

		<div v-if="unsupportedDiagnostics.length" class="alert alert-warning py-2 px-3 small mb-2">
			<i class="fa fa-exclamation-triangle mr-1"></i>
			<span>
				{{
					__(
						"This rule contains legacy condition patterns that require review. They are preserved until you edit and resolve them."
					)
				}}
			</span>
		</div>

		<TreeBuilder
			ref="treeBuilderRef"
			:modelValue="treeModel"
			:readOnly="readOnly"
			:allowGroups="true"
			:allowCollections="true"
			:groupOperators="['and', 'or']"
			:leafLabel="__('Condition')"
			:groupLabel="__('Group')"
			:collectionLabel="__('Collection')"
			:emptyLabel="__('No conditions defined. Click + Condition to add one.')"
			:leafFactory="createLeaf"
			:collectionFactory="createCollection"
			:operatorLabel="(op) => (op === 'and' ? __('AND') : __('OR'))"
			:presentationMode="presentationMode"
			@update:modelValue="onTreeUpdate"
		>
			<template #collection="{ node }">
				<CanonicalCollectionEditor
					:node="node"
					:docFields="docFields"
					:readOnly="readOnly"
					@change="onSubNodeChange"
				/>
			</template>

			<template #leaf-summary="{ node }">
				<CanonicalConditionLeafSummary :node="node" :contract="contract" />
			</template>

			<template #leaf="{ node }">
				<CanonicalConditionLeaf
					:node="node"
					:contract="contract"
					:docFields="docFields"
					:variableOptions="variableOptions"
					:readOnly="readOnly"
					:store="store"
					:currentDocType="currentDocType"
					:errors="getNodeErrors(node.id)"
					@change="onSubNodeChange"
					@remove="treeBuilderRef?.removeNode(node.id)"
				/>
			</template>
		</TreeBuilder>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import TreeBuilder from "../tree_builder/TreeBuilder.vue";
import CanonicalConditionLeaf from "./CanonicalConditionLeaf.vue";
import CanonicalConditionLeafSummary from "./CanonicalConditionLeafSummary.vue";
import CanonicalCollectionEditor from "./CanonicalCollectionEditor.vue";
import { useCanonicalConditionContract } from "./useCanonicalConditionContract.js";
import {
	deserializeConditionTree,
	serializeConditionTree,
	findUnsupportedDiagnostics,
} from "./canonical_condition_adapter.mjs";
import { validateCanonicalCondition } from "./canonical_condition_validation.mjs";
import { createNodeId } from "../tree_builder/tree_builder_utils.mjs";

const props = defineProps({
	modelValue: { type: [Object, Array, String], default: null },
	docFields: { type: Array, default: () => [] },
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	isMandatory: { type: Boolean, default: false },
	currentDocType: { type: String, default: "" },
	store: { type: Object, default: null },
	presentationMode: { type: String, default: "hybrid" },
});

const emit = defineEmits(["update:modelValue", "change", "validation"]);

const treeBuilderRef = ref(null);
const { contract, error: contractError, loadContract } = useCanonicalConditionContract();

const treeModel = ref(deserializeConditionTree(props.modelValue));
const validationErrors = ref([]);
const nodeErrorsMap = ref(new Map());

const unsupportedDiagnostics = computed(() => findUnsupportedDiagnostics(treeModel.value));

onMounted(() => {
	loadContract().catch(() => {});
});

watch(
	() => props.modelValue,
	(newVal) => {
		const currentCanonical = serializeConditionTree(treeModel.value);
		if (JSON.stringify(newVal) === JSON.stringify(currentCanonical)) {
			return;
		}
		treeModel.value = deserializeConditionTree(newVal);
	},
	{ deep: true }
);

function createLeaf() {
	return {
		id: createNodeId("leaf"),
		type: "leaf",
		operator: "eq",
		left: {
			mode: "variable",
			path: { scope: "doc", segments: [] },
		},
		right: {
			mode: "static",
			value_type: "string",
			value: "",
		},
	};
}

function createCollection() {
	return {
		id: createNodeId("collection"),
		type: "collection",
		quantifier: "any",
		collection: "",
		source: { scope: "doc", segments: [] },
		alias: "row",
		children: [createLeaf()],
	};
}

function onTreeUpdate(newTree) {
	treeModel.value = newTree;
	emitSerialized();
}

function onSubNodeChange() {
	emitSerialized();
}

function emitSerialized() {
	const canonical = serializeConditionTree(treeModel.value);
	emit("update:modelValue", canonical);
	emit("change", canonical);
}

function getNodeErrors(nodeId) {
	return nodeErrorsMap.value.get(nodeId) || [];
}

function validate() {
	const result = validateCanonicalCondition(treeModel.value, {
		contract: contract.value,
		isMandatory: props.isMandatory,
	});

	validationErrors.value = result.errors;
	nodeErrorsMap.value = result.nodeErrors;

	emit("validation", result);
	return result;
}

defineExpose({
	validate,
	getCanonicalPayload: () => serializeConditionTree(treeModel.value),
	getTree: () => treeModel.value,
});
</script>

<style scoped>
.canonical-condition-builder {
	display: flex;
	flex-direction: column;
	width: 100%;
}
</style>
