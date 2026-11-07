<template>
	<div class="canonical-condition-leaf" :class="{ 'is-invalid': hasError }">
		<!-- Preserved Unsupported Condition Card -->
		<UnsupportedConditionCard
			v-if="node.is_unsupported"
			:node="node"
			:readOnly="readOnly"
			:isSoleCondition="isSoleCondition"
			:isEntryNode="isEntryNode"
			@replace="onReplaceUnsupported"
			@remove="$emit('remove')"
		/>

		<!-- Intelligent Rule Composer Line -->
		<template v-else>
			<RuleComposerLine
				:node="node"
				:contract="contract"
				:docFields="docFields"
				:variableOptions="variableOptions"
				:readOnly="readOnly"
				:store="store"
				:currentDocType="currentDocType"
				:errors="nodeErrors"
				@change="$emit('change', node)"
				@remove="$emit('remove')"
			/>

			<!-- Errors List -->
			<div v-if="nodeErrors.length" class="node-errors mt-1">
				<div v-for="(err, idx) in nodeErrors" :key="idx" class="text-danger small">
					<i class="fa fa-info-circle mr-1"></i>{{ err }}
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue";
import RuleComposerLine from "../composer/RuleComposerLine.vue";
import UnsupportedConditionCard from "./UnsupportedConditionCard.vue";

const props = defineProps({
	node: { type: Object, required: true },
	contract: { type: Object, default: () => ({}) },
	docFields: { type: Array, default: () => [] },
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	store: { type: Object, default: null },
	currentDocType: { type: String, default: "" },
	errors: { type: Array, default: () => [] },
	isSoleCondition: { type: Boolean, default: false },
	isEntryNode: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change", "remove", "replace"]);

const nodeErrors = computed(() => {
	const errs = [...(props.errors || [])];
	if (props.node._invalid_right_error) {
		errs.push(props.node._invalid_right_error);
	}
	return errs;
});

const hasError = computed(() => nodeErrors.value.length > 0 || props.node.is_unsupported);

function onReplaceUnsupported() {
	props.node.is_unsupported = false;
	props.node.is_incomplete_draft = true;
	props.node.operator = "";
	props.node.left = null;
	props.node.right = null;
	delete props.node.original_payload;
	delete props.node.unsupported_reason;
	emit("change", props.node);
}
</script>

<style scoped>
.canonical-condition-leaf {
	background: var(--fxr-bg-card, #ffffff);
	border: 1px solid var(--fxr-border, #e5e7eb);
	border-radius: var(--fxr-radius-md, 6px);
	padding: var(--fxr-space-1, 4px) var(--fxr-space-2, 8px);
	transition: border-color var(--fxr-transition-fast), background-color var(--fxr-transition-fast);
}

.canonical-condition-leaf:hover {
	border-color: var(--fxr-border-strong, #cbd5e1);
}

.canonical-condition-leaf.is-invalid {
	border-color: var(--fxr-text-danger, #ef4444) !important;
	background-color: var(--fxr-danger-soft, #fef2f2) !important;
	box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.1);
}

.node-errors {
	padding: 2px 4px;
}
</style>
