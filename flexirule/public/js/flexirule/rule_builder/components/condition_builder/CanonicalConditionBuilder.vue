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
					:store="store"
					@change="onSubNodeChange"
					@child-fields-loaded="onChildFieldsLoaded"
				/>
			</template>

			<template #leaf-summary="{ node }">
				<CanonicalConditionLeafSummary
					:node="node"
					:contract="contract"
					:docFields="getLeafDocFields(node)"
				/>
			</template>

			<template #leaf="{ node }">
				<CanonicalConditionLeaf
					:node="node"
					:contract="contract"
					:docFields="getLeafDocFields(node)"
					:variableOptions="getLeafVariableOptions(node)"
					:readOnly="readOnly"
					:store="store"
					:currentDocType="getLeafDocType(node)"
					:errors="getNodeErrors(node.id)"
					:isSoleCondition="isSoleCondition"
					:isEntryNode="isEntryNode"
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
	isEntryNode: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change", "validation"]);

const treeBuilderRef = ref(null);
const { contract, error: contractError, loadContract } = useCanonicalConditionContract();

const treeModel = ref(deserializeConditionTree(props.modelValue));
const validationErrors = ref([]);
const nodeErrorsMap = ref(new Map());
const collectionMetadataMap = ref(new Map());

const unsupportedDiagnostics = computed(() => findUnsupportedDiagnostics(treeModel.value));

const isSoleCondition = computed(() => {
	const children = treeModel.value?.children || [];
	return children.length === 1;
});

function onChildFieldsLoaded(payload) {
	if (payload && payload.collectionId) {
		collectionMetadataMap.value.set(payload.collectionId, payload);
	}
}

function findParentCollection(nodeId, tree = treeModel.value) {
	if (!tree || !tree.children) return null;
	for (const child of tree.children) {
		if (child.type === "collection") {
			if (child.children?.some((c) => c.id === nodeId)) {
				return child;
			}
			const found = findParentCollection(nodeId, child);
			if (found) return found;
		} else if (child.type === "group") {
			const found = findParentCollection(nodeId, child);
			if (found) return found;
		}
	}
	return null;
}

function getLeafDocFields(node) {
	const parentCol = findParentCollection(node?.id);
	if (parentCol) {
		const meta = collectionMetadataMap.value.get(parentCol.id);
		// Return child fields if loaded, or empty array if failed/loading (never substitute parent fields)
		if (meta && meta.status === "loaded") {
			return meta.childFields || [];
		}
		if (meta && (meta.status === "loading" || meta.status === "failed")) {
			return [];
		}
		return meta?.childFields || [];
	}
	return props.docFields;
}

function getLeafVariableOptions(node) {
	const parentCol = findParentCollection(node?.id);
	if (parentCol) {
		const meta = collectionMetadataMap.value.get(parentCol.id);
		const childFields = meta?.status === "loaded" ? meta.childFields || [] : [];
		// Combine child-row fields with general runtime variables (predecessors, rule context) without losing access
		const dedupe = new Map();
		childFields.forEach((f) => dedupe.set(f.value || f, f));
		(props.variableOptions || []).forEach((v) => {
			const key = v.value || v;
			if (!dedupe.has(key)) {
				dedupe.set(key, v);
			}
		});
		return Array.from(dedupe.values());
	}
	return props.variableOptions;
}

function getLeafDocType(node) {
	const parentCol = findParentCollection(node?.id);
	if (parentCol) {
		const meta = collectionMetadataMap.value.get(parentCol.id);
		if (meta && meta.childDocType) {
			return meta.childDocType;
		}
	}
	return props.currentDocType;
}

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
		alias: "items_row",
		children: [createLeaf()],
	};
}

function emitSerialized() {
	const canonical = serializeConditionTree(treeModel.value);
	emit("update:modelValue", canonical);
	emit("change", canonical);
}

function getNodeErrors(nodeId) {
	return nodeErrorsMap.value.get(nodeId) || [];
}

let lastValidationRequestId = 0;
let validatedPayloadJson = null;

function invalidateValidation() {
	lastValidationRequestId += 1;
	validatedPayloadJson = null;
}

function onTreeUpdate(newTree) {
	invalidateValidation();
	treeModel.value = newTree;
	emitSerialized();
}

function onSubNodeChange() {
	invalidateValidation();
	emitSerialized();
}

async function validate() {
	const localResult = validateCanonicalCondition(treeModel.value, {
		contract: contract.value,
		isMandatory: props.isMandatory,
	});

	validationErrors.value = localResult.errors;
	nodeErrorsMap.value = localResult.nodeErrors;

	if (!localResult.valid) {
		validatedPayloadJson = null;
		emit("validation", localResult);
		return localResult;
	}

	const payload = serializeConditionTree(treeModel.value);
	if (!payload) {
		if (props.isMandatory) {
			validatedPayloadJson = null;
			const emptyRes = {
				valid: false,
				errors: ["Condition is required."],
				nodeErrors: new Map(),
			};
			emit("validation", emptyRes);
			return emptyRes;
		}
		validatedPayloadJson = "null";
		emit("validation", { valid: true, errors: [], nodeErrors: new Map() });
		return { valid: true, errors: [], nodeErrors: new Map() };
	}

	const currentRequestId = ++lastValidationRequestId;
	const payloadJson = JSON.stringify(payload);

	try {
		if (typeof frappe === "undefined" || !frappe.call) {
			if (typeof window !== "undefined" && window.__FLEXIRULE_TEST_MODE__) {
				validatedPayloadJson = payloadJson;
				return localResult;
			}
			const outageRes = {
				valid: false,
				errors: ["Backend condition validator is unavailable. Save blocked (fail-closed)."],
				nodeErrors: new Map(),
			};
			validationErrors.value = outageRes.errors;
			validatedPayloadJson = null;
			emit("validation", outageRes);
			return outageRes;
		}

		const response = await frappe.call({
			method: "flexirule.ruleflow.api.validate_condition",
			args: {
				condition: payloadJson,
				doctype: props.currentDocType || undefined,
			},
		});

		// Stale-response protection: if request ID changed or tree mutated in flight, fail closed
		const currentPayload = serializeConditionTree(treeModel.value);
		const currentJson = JSON.stringify(currentPayload);
		if (currentRequestId !== lastValidationRequestId || payloadJson !== currentJson) {
			const staleRes = {
				valid: false,
				errors: ["Condition changed while validation was in progress. Please re-validate."],
				nodeErrors: new Map(),
			};
			validationErrors.value = staleRes.errors;
			validatedPayloadJson = null;
			emit("validation", staleRes);
			return staleRes;
		}

		const data = response.message || response;
		if (!data || !data.valid) {
			const backendErrors = Array.isArray(data?.errors)
				? data.errors
				: ["Condition failed backend validation."];
			const res = {
				valid: false,
				errors: backendErrors,
				nodeErrors: nodeErrorsMap.value,
				details: data?.details || [],
			};
			validationErrors.value = res.errors;
			validatedPayloadJson = null;
			emit("validation", res);
			return res;
		}

		validatedPayloadJson = payloadJson;
		const successRes = { valid: true, errors: [], nodeErrors: new Map() };
		validationErrors.value = [];
		emit("validation", successRes);
		return successRes;
	} catch (err) {
		const currentPayload = serializeConditionTree(treeModel.value);
		const currentJson = JSON.stringify(currentPayload);
		if (currentRequestId !== lastValidationRequestId || payloadJson !== currentJson) {
			const staleRes = {
				valid: false,
				errors: ["Condition changed while validation was in progress. Please re-validate."],
				nodeErrors: new Map(),
			};
			validationErrors.value = staleRes.errors;
			validatedPayloadJson = null;
			emit("validation", staleRes);
			return staleRes;
		}

		const msg =
			err?.message ||
			"Failed to reach backend condition validator. Save blocked (fail-closed).";
		const outageRes = {
			valid: false,
			errors: [msg],
			nodeErrors: new Map(),
		};
		validationErrors.value = outageRes.errors;
		validatedPayloadJson = null;
		emit("validation", outageRes);
		return outageRes;
	}
}

defineExpose({
	validate,
	validateSync: () =>
		validateCanonicalCondition(treeModel.value, {
			contract: contract.value,
			isMandatory: props.isMandatory,
		}),
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
