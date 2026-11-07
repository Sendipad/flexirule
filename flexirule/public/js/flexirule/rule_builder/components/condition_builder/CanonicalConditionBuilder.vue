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
			:beforeRemove="confirmNodeRemoval"
			@update:modelValue="onTreeUpdate"
		>
			<template #collection="{ node }">
				<CanonicalCollectionEditor
					:node="node"
					:docFields="getCollectionDocFields(node)"
					:ancestorAliases="getAncestorAliases(node)"
					:siblingAliases="getSiblingAliases(node)"
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
	getCollectionSiblingAliases,
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

function syncTreeFromBuilder() {
	if (treeBuilderRef.value?.getTree) {
		const liveTree = treeBuilderRef.value.getTree();
		if (liveTree) {
			treeModel.value = liveTree;
		}
	}
}

function serializeCurrentTree() {
	syncTreeFromBuilder();
	return serializeConditionTree(treeModel.value, contract.value?.operators || {});
}

const isSoleCondition = computed(() => {
	const children = treeModel.value?.children || [];
	return children.length === 1;
});

function confirmNodeRemoval(nodeId, root) {
	// If it is the sole condition of an Entry Action, removal removes all filtering (unconditional execution)
	const children = root?.children || [];
	const isSole = children.length === 1 && children[0].id === nodeId;

	let msg = "";
	if (isSole && props.isEntryNode) {
		msg = __(
			"WARNING: Removing the only Entry Condition will remove all trigger filtering, causing the rule to run unconditionally for all documents! Are you sure you want to delete it?"
		);
	}

	if (!msg) return true;

	if (typeof frappe !== "undefined" && frappe.confirm) {
		return new Promise((resolve) => {
			frappe.confirm(
				msg,
				() => resolve(true),
				() => resolve(false)
			);
		});
	} else if (typeof window !== "undefined" && window.confirm) {
		return window.confirm(msg);
	}
	return true;
}

function onChildFieldsLoaded(payload) {
	if (payload && payload.collectionId) {
		collectionMetadataMap.value.set(payload.collectionId, payload);
	}
}

function findAncestorCollections(nodeId, tree = treeModel.value, ancestors = []) {
	if (!tree || !tree.children) return [];
	for (const child of tree.children) {
		if (child.id === nodeId) {
			return ancestors;
		}
		if (child.type === "collection") {
			const nested = findAncestorCollections(nodeId, child, [...ancestors, child]);
			if (nested.length || child.children?.some((c) => c.id === nodeId)) {
				return nested.length ? nested : [...ancestors, child];
			}
		} else if (child.type === "group") {
			const nested = findAncestorCollections(nodeId, child, ancestors);
			if (nested.length || child.children?.some((c) => c.id === nodeId)) {
				return nested.length ? nested : ancestors;
			}
		}
	}
	return [];
}

function findParentCollection(nodeId, tree = treeModel.value) {
	const ancestors = findAncestorCollections(nodeId, tree);
	return ancestors.length ? ancestors[ancestors.length - 1] : null;
}

function getAncestorAliases(node) {
	if (!node?.id) return [];
	const ancestors = findAncestorCollections(node.id, treeModel.value);
	return ancestors.map((a) => a.alias).filter(Boolean);
}

function getSiblingAliases(node) {
	if (!node?.id) return [];
	return getCollectionSiblingAliases(treeModel.value, node.id);
}

function getCollectionDocFields(node) {
	const ancestors = findAncestorCollections(node?.id, treeModel.value);
	if (ancestors.length > 0) {
		const immediateEnclosing = ancestors[ancestors.length - 1];
		const meta = collectionMetadataMap.value.get(immediateEnclosing.id);
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
		const currentCanonical = serializeCurrentTree();
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
		operator: "",
		left: null,
		right: null,
		is_incomplete_draft: true,
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
	const canonical = serializeCurrentTree();
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
	// Immediately recompute local validation so resolved errors disappear and new errors update reactively
	const local = validateCanonicalCondition(treeModel.value, {
		contract: contract.value,
		isMandatory: props.isMandatory,
	});
	validationErrors.value = local.errors;
	nodeErrorsMap.value = local.nodeErrors;
}

function onTreeUpdate(newTree) {
	// Assign newTree first so validation runs against the newly installed tree structure
	treeModel.value = newTree;
	invalidateValidation();
	emitSerialized();
}

function onSubNodeChange() {
	syncTreeFromBuilder();
	invalidateValidation();
	emitSerialized();
}

async function validate() {
	syncTreeFromBuilder();
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

	const payload = serializeCurrentTree();
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

	if (!contract.value) {
		const contractRes = {
			valid: false,
			errors: [
				"Canonical condition contract is not ready. Retry loading the contract before saving.",
			],
			nodeErrors: new Map(),
		};
		validationErrors.value = contractRes.errors;
		validatedPayloadJson = null;
		emit("validation", contractRes);
		return contractRes;
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
		const currentPayload = serializeCurrentTree();
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
		const currentPayload = serializeCurrentTree();
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
	getCanonicalPayload: () => serializeCurrentTree(),
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
