<template>
	<div class="canonical-condition-builder">
		<!-- Contract Load Error Alert -->
		<div
			v-if="contractError"
			class="alert alert-danger d-flex align-items-center justify-content-between p-2 mb-2"
		>
			<div>
				<i class="fa fa-exclamation-triangle mr-2"></i>
				<span
					>{{ __("Failed to load condition contract from server: ") }}
					{{ contractError }}</span
				>
			</div>
			<button class="btn btn-sm btn-outline-danger" @click="loadContract(true)">
				<i class="fa fa-refresh mr-1"></i> {{ __("Retry") }}
			</button>
		</div>

		<!-- Loading Spinner -->
		<div v-else-if="isLoadingContract" class="text-center py-3 text-muted">
			<i class="fa fa-spinner fa-spin mr-2"></i> {{ __("Loading condition operators...") }}
		</div>

		<!-- Main Generic TreeBuilder Container -->
		<template v-else>
			<TreeBuilder
				:modelValue="uiTreeState"
				:allowCollections="true"
				:collectionFactory="() => ({ quantifier: 'any', collection: { mode: 'variable', value: '' }, alias: 'item' })"
				:docFields="docFields"
				:variableOptions="combinedVariableOptions"
				:readOnly="readOnly"
				:showValidation="showValidation"
				@update:modelValue="onUpdateUiTreeState"
			>
				<!-- Custom Leaf Editor Slot -->
				<template #leaf="{ domain, updateDomain }">
					<ConditionLeaf
						:domain="domain"
						:operators="contractOperators"
						:docFields="docFields"
						:variableOptions="combinedVariableOptions"
						:readOnly="readOnly"
						:showValidation="showValidation"
						@update:domain="updateDomain"
					/>
				</template>

				<!-- Custom Leaf Summary Slot -->
				<template #leaf-summary="{ domain }">
					<ConditionLeafSummary :domain="domain" :operators="contractOperators" />
				</template>

				<!-- Custom Collection Group Slot (if TreeBuilder provides collection slot) -->
				<template #collection="{ node, updateNode, childrenSlot }">
					<CollectionPredicateGroup
						:node="node"
						:docFields="docFields"
						:variableOptions="combinedVariableOptions"
						:readOnly="readOnly"
						@update:node="updateNode"
					>
						<component :is="childrenSlot" />
					</CollectionPredicateGroup>
				</template>
			</TreeBuilder>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import TreeBuilder from "../tree_builder/TreeBuilder.vue";
import ConditionLeaf from "./ConditionLeaf.vue";
import ConditionLeafSummary from "./ConditionLeafSummary.vue";
import CollectionPredicateGroup from "./CollectionPredicateGroup.vue";
import { fetchConditionContract } from "./condition_contract_client.mjs";
import { hydrateToTreeBuilder, serializeToCanonicalAst } from "./canonical_condition_adapter.mjs";
import { validateConditionTree } from "./canonical_condition_validator.mjs";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => null,
	},
	docFields: {
		type: Array,
		default: () => [],
	},
	variableOptions: {
		type: Array,
		default: () => [],
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
	showValidation: {
		type: Boolean,
		default: false,
	},
	isMandatory: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:modelValue"]);

const contractOperators = ref([]);
const contractError = ref(null);
const isLoadingContract = ref(true);

const uiTreeState = ref(hydrateToTreeBuilder(props.modelValue));

const combinedVariableOptions = computed(() => props.variableOptions || []);

async function loadContract(force = false) {
	isLoadingContract.value = true;
	contractError.value = null;
	try {
		const contract = await fetchConditionContract({ forceRefresh: force });
		if (!Array.isArray(contract?.operators) || contract.operators.length === 0) {
			throw new Error("The backend condition contract did not provide any operators.");
		}
		contractOperators.value = contract.operators;
	} catch (err) {
		contractError.value = err?.message || err || "Contract API request failed.";
		contractOperators.value = [];
	} finally {
		isLoadingContract.value = false;
	}
}

onMounted(() => {
	loadContract();
});

// Sync external modelValue changes
watch(
	() => props.modelValue,
	(newVal) => {
		if (!contractOperators.value.length) {
			uiTreeState.value = hydrateToTreeBuilder(newVal);
			return;
		}
		try {
			const currentCanonical = serializeToCanonicalAst(uiTreeState.value, { operators: contractOperators.value });
			if (JSON.stringify(newVal) !== JSON.stringify(currentCanonical)) {
				uiTreeState.value = hydrateToTreeBuilder(newVal);
			}
		} catch {
			uiTreeState.value = hydrateToTreeBuilder(newVal);
		}
	},
	{ deep: true }
);

function onUpdateUiTreeState(newState) {
	uiTreeState.value = newState;
	if (contractError.value || !contractOperators.value.length) {
		// Do not emit data unless the authoritative backend contract is available.
		return;
	}
	try {
		const canonicalAst = serializeToCanonicalAst(newState, { operators: contractOperators.value });
		emit("update:modelValue", canonicalAst);
	} catch {
		// Intermediate editor state is allowed; validation blocks persistence until complete.
	}
}

function validate() {
	if (contractError.value || !contractOperators.value.length) {
		return {
			isValid: false,
			errors: ["Cannot validate or save condition until the canonical server contract is available."],
		};
	}

	return validateConditionTree(uiTreeState.value, {
		operators: contractOperators.value,
		isMandatory: props.isMandatory,
	});
}

defineExpose({
	validate,
	reloadContract: () => loadContract(true),
});
</script>

<style scoped>
.canonical-condition-builder {
	width: 100%;
}
</style>
