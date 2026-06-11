<template>
	<div class="configuration-panel fxr-accent-scope" :style="panelStyleVars">
		<div v-if="node" class="panel-content">
			<div class="panel-header" v-if="!store.use_modern_layout">
				<div class="header-text">
					<h4>{{ __("Dynamic Configuration") }}</h4>
					<p class="text-muted small">
						{{ node.data?.action_type || node.type }}
					</p>
				</div>
			</div>
			<div class="panel-sections">
				<!-- Core Action Specific UI -->
				<component
					:is="configComponent"
					v-if="configComponent"
					ref="configRef"
					:node="node"
					:read_only="readOnly"
					@update:field="on_update_field"
				/>
				<div v-else class="empty-config text-center">
					<i class="fa fa-sliders fa-3x text-muted mb-3"></i>
					<p class="text-muted">{{ emptyStateMessage }}</p>
				</div>
			</div>
		</div>
		<div v-else class="panel-content empty-state text-center">
			<p class="text-muted">{{ __("Select an action node to configure") }}</p>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, nextTick } from "vue";
import { useStore } from "../../stores";
import { mapActionTypeToNodeType } from "../../composables/useActionTypeMapper";
import { getContract } from "../../../core/contracts.js";

import AssignmentConfig from "./types/AssignmentConfig.vue";
import ConditionStep from "./types/ConditionStep.vue";
import DocumentActionConfig from "./types/DocumentActionConfig.vue";
import LoopConfig from "./types/LoopConfig.vue";
import NotifyConfig from "./types/NotifyConfig.vue";
import ProcessConfig from "./types/ProcessConfig.vue";
import QueryRecordsConfig from "./types/QueryRecordsConfig.vue";
import RaiseErrorConfig from "./types/RaiseErrorConfig.vue";
import SubRuleConfig from "./types/SubRuleConfig.vue";
import SwitchConfig from "./types/SwitchConfig.vue";
import WaitConfig from "./types/WaitConfig.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();

const componentRegistry = {
	AssignmentConfig,
	ConditionStep,
	DocumentActionConfig,
	LoopConfig,
	NotifyConfig,
	ProcessConfig,
	QueryRecordsConfig,
	RaiseErrorConfig,
	SubRuleConfig,
	SwitchConfig,
	WaitConfig,
};

const staticComponentMap = {
	Condition: "ConditionStep",
	Process: "ProcessConfig",
	Loop: "LoopConfig",
	Switch: "SwitchConfig",
	"Sub-Rule": "SubRuleConfig",
	Wait: "WaitConfig",
	Assignment: "AssignmentConfig",
	Notify: "NotifyConfig",
	"Raise Error": "RaiseErrorConfig",
	"Query Records": "QueryRecordsConfig",
	"Document Action": "DocumentActionConfig",
};

const configComponent = computed(() => {
	const actionType = props.node?.data?.action_type || props.node?.type;
	if (!actionType) return null;

	const contract = getContract(actionType);

	// Fallback to static mapping if the contract is missing config_component (e.g. stale cache)
	let componentName = contract?.config_component;
	if (!componentName && staticComponentMap[actionType]) {
		componentName = staticComponentMap[actionType];
	}

	if (!componentName || !componentRegistry[componentName]) return null;

	return componentRegistry[componentName];
});

const configRef = ref(null);

const normalizedActionType = computed(() =>
	String(props.node?.data?.action_type || props.node?.type || "")
		.toLowerCase()
		.trim()
);

const emptyStateMessage = computed(() => {
	const label = props.node?.data?.action_type || props.node?.type || __("Action");
	const contract = getContract(props.node?.data?.action_type || props.node?.type);

	if (contract && contract.configurable === false) {
		return __(
			"Dynamic configuration is not required for '{0}'. Use Setup/Input/Output panels."
		).replace("{0}", label);
	}
	return __("No configuration UI available for '{0}'").replace("{0}", label);
});

const panelStyleVars = computed(() => {
	const actionType = props.node?.data?.action_type || props.node?.type;
	const color = getContract(actionType)?.css?.color || "var(--fxr-accent)";
	return {
		"--fxr-node-accent": color,
		"--fxr-node-accent-light": `color-mix(in srgb, ${color} 12%, var(--fxr-surface))`,
	};
});

function on_update_field(fieldname, value) {
	if (!props.node?.data) return;
	props.node.data[fieldname] = value;
	store.mark_dirty();
}

async function validate() {
	if (configRef.value && typeof configRef.value.validate === "function") {
		return await configRef.value.validate();
	}
	return { valid: true };
}

function focusFirst() {
	nextTick(() => {
		const sections = document.querySelector(".panel-sections");
		if (sections) {
			const first = sections.querySelector("button, input, select, textarea, [tabindex='0']");
			first?.focus();
		}
	});
}

defineExpose({
	validate,
	focusFirst,
});
</script>

<style scoped>
.configuration-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
	background-color: var(--fxr-bg-page);
}

.panel-content {
	flex: 1;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	min-height: 0;
}

.panel-header {
	padding: 20px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.panel-header h4 {
	margin: 0 0 4px 0;
	font-size: 15px;
	font-weight: 600;
}

.panel-sections {
	flex: 0 1 auto;
	overflow-y: auto;
	padding: var(--panel-padding, 8px);
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.empty-config {
	height: 200px;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
}

.empty-state {
	display: flex;
	align-items: center;
	justify-content: center;
	flex: 1;
	padding: 20px;
}

@media (max-width: 768px) {
	.panel-sections {
		padding: var(--fxr-space-4);
		gap: var(--fxr-space-4);
	}
}
</style>
