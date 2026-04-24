<template>
	<div class="configuration-panel">
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
import { computed, ref } from "vue";
import { useStore } from "../../stores";
import { mapActionTypeToNodeType } from "../../composables/useActionTypeMapper";
import ProcessConfig from "./types/ProcessConfig.vue";
import ConditionConfig from "./types/ConditionConfig.vue";
import LoopConfig from "./types/LoopConfig.vue";
import SwitchConfig from "./types/SwitchConfig.vue";
import SubRuleConfig from "./types/SubRuleConfig.vue";
import WaitConfig from "./types/WaitConfig.vue";
import SetValueConfig from "./types/SetValueConfig.vue";
import NotifyConfig from "./types/NotifyConfig.vue";
import RaiseErrorConfig from "./types/RaiseErrorConfig.vue";
import QueryRecordsConfig from "./types/QueryRecordsConfig.vue";
import DocumentActionConfig from "./types/DocumentActionConfig.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const store = useStore();

const configComponents = {
	process: ProcessConfig,
	condition: ConditionConfig,
	loop: LoopConfig,
	switch: SwitchConfig,
	"sub-rule": SubRuleConfig,
	subrule: SubRuleConfig,
	wait: WaitConfig,
	"set-value": SetValueConfig,
	"set value": SetValueConfig,
	setvalue: SetValueConfig,
	notify: NotifyConfig,
	"raise-error": RaiseErrorConfig,
	"raise error": RaiseErrorConfig,
	raiseerror: RaiseErrorConfig,
	query: QueryRecordsConfig,
	"query-records": QueryRecordsConfig,
	"query records": QueryRecordsConfig,
	queryrecords: QueryRecordsConfig,
	documentaction: DocumentActionConfig,
	"document-action": DocumentActionConfig,
	"document action": DocumentActionConfig,
};

function normalizeKey(value) {
	return String(value || "")
		.toLowerCase()
		.replace(/[_-]+/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}

const configComponent = computed(() => {
	const mappedType = normalizeKey(
		mapActionTypeToNodeType(props.node?.data?.action_type || props.node?.type) || ""
	);
	const rawType = normalizeKey(props.node?.data?.action_type || props.node?.type || "");
	const compactRaw = rawType.replace(/\s+/g, "");
	return (
		configComponents[mappedType] ||
		configComponents[rawType] ||
		configComponents[compactRaw] ||
		null
	);
});

const configRef = ref(null);
const NO_DYNAMIC_CONFIG_TYPES = new Set([
	"entry action",
	"start",
	"stop",
	"raise error",
	"raise-error",
]);

const normalizedActionType = computed(() =>
	String(props.node?.data?.action_type || props.node?.type || "")
		.toLowerCase()
		.trim()
);

const emptyStateMessage = computed(() => {
	const label = props.node?.data?.action_type || props.node?.type || __("Action");
	if (NO_DYNAMIC_CONFIG_TYPES.has(normalizedActionType.value)) {
		return __(
			"Dynamic configuration is not required for '{0}'. Use Setup/Input/Output panels."
		).replace("{0}", label);
	}
	return __("No configuration UI available for '{0}'").replace("{0}", label);
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

defineExpose({
	validate,
});
</script>

<style scoped>
.configuration-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
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
	border-bottom: 1px solid var(--border-color);
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
	flex: 1;
	overflow-y: auto;
	padding: var(--panel-padding, 16px);
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
</style>
