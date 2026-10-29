<template>
	<div class="canonical-condition-builder">
		<!-- Contract Load Error Alert -->
		<div v-if="contractError" class="alert alert-danger d-flex align-items-center justify-content-between p-2 mb-2">
			<div>
				<i class="fa fa-exclamation-triangle mr-2"></i>
				<span>{{ __("Failed to load condition contract from server: ") }} {{ contractError }}</span>
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
					<ConditionLeafSummary
						:domain="domain"
						:operators="contractOperators"
					/>
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
const isLoadingContract = ref(false);

const uiTreeState = ref(hydrateToTreeBuilder(props.modelValue));

const combinedVariableOptions = computed(() => props.variableOptions || []);

async function loadContract(force = false) {
	isLoadingContract.value = true;
	contractError.value = null;
	try {
		const contract = await fetchConditionContract({ forceRefresh: force });
		contractOperators.value = contract?.operators || [];
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
		const currentCanonical = serializeToCanonicalAst(uiTreeState.value);
		if (JSON.stringify(newVal) !== JSON.stringify(currentCanonical)) {
			uiTreeState.value = hydrateToTreeBuilder(newVal);
		}
	},
	{ deep: true }
);

function onUpdateUiTreeState(newState) {
	uiTreeState.value = newState;
	if (contractError.value) {
		// Do not emit serialized AST if contract loading failed
		return;
	}
	const canonicalAst = serializeToCanonicalAst(newState);
	emit("update:modelValue", canonicalAst);
}

function validate() {
	if (contractError.value) {
		return {
			isValid: false,
			errors: ["Cannot validate or save condition while server contract failed to load."],
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
