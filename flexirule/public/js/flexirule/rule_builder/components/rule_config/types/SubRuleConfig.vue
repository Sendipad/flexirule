<template>
	<div class="sub-rule-config">
		<div class="fxr-stack fxr-stack--gap-4">
			<div class="fxr-card">
				<div class="fxr-card-header">
					<span class="fxr-label-sm">{{ __("Target Rule") }}</span>
				</div>
				<div class="fxr-card-body">
					<ControlFactory
						:df="ruleField"
						:modelValue="node.data.rule"
						@update:modelValue="onRuleChange"
					/>
				</div>
			</div>

			<div class="fxr-card" v-if="node.data.rule">
				<div class="fxr-card-header d-flex align-items-center justify-content-between">
					<span class="fxr-label-sm">{{ __("Input Arguments") }}</span>
					<button
						v-if="!readOnly"
						class="fxr-btn btn-xs"
						@click="autoMap"
						:title="__('Map from current context')"
					>
						<i class="fa fa-magic"></i> {{ __("Auto Map") }}
					</button>
				</div>
				<div class="fxr-card-body">
					<div v-if="loading" class="text-center py-4">
						<div class="spinner-border spinner-border-sm text-primary opacity-50"></div>
					</div>
					<div v-else-if="!ruleArguments.length" class="empty-state compact">
						<p>{{ __("This rule has no input arguments defined.") }}</p>
					</div>
					<div v-else class="fxr-stack fxr-stack--gap-3">
						<div
							v-for="arg in ruleArguments"
							:key="arg.fieldname"
							class="argument-row fxr-row fxr-row--gap-4"
						>
							<div class="arg-info flex-1">
								<span class="arg-label">{{ arg.label || arg.fieldname }}</span>
								<span class="arg-type">{{ arg.fieldtype }}</span>
							</div>
							<div class="arg-input flex-2">
								<FlexValueControl
									:modelValue="config.arguments?.[arg.fieldname]"
									:context="{ df: arg }"
									:read_only="readOnly"
									:engine="store"
									@update:modelValue="updateArg(arg.fieldname, $event)"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import FlexValueControl from "../../../controls/FlexValueControl.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { config, update_action_field, store } = useActionConfig(props);
const ruleArguments = ref([]);
const loading = ref(false);

const ruleField = {
	fieldname: "rule",
	fieldtype: "Link",
	label: __("Sub-Rule"),
	options: "Rule",
	get_query: () => {
		const parentDocType = store.rule_doc?.document_type;
		const filters = {
			trigger_type: "Callable Event",
			exposed_as_subrule: 1,
			is_active: 1,
			name: ["!=", store.rule_name || ""],
		};
		if (parentDocType) {
			filters.document_type = ["in", [parentDocType, ""]];
		}
		return { filters };
	},
};

async function fetchRuleArgs(ruleName) {
	if (!ruleName) {
		ruleArguments.value = [];
		return;
	}
	loading.value = true;
	try {
		const args = await frappe.xcall("flexirule.ruleflow.doctype.rule.rule.get_rule_arguments", {
			rule_name: ruleName,
		});
		ruleArguments.value = args || [];
	} catch (e) {
		ruleArguments.value = [];
	} finally {
		loading.value = false;
	}
}

function onRuleChange(val) {
	update_action_field("rule", val);
	fetchRuleArgs(val);
}

function updateArg(fieldname, value) {
	if (!config.arguments) config.arguments = {};
	config.arguments[fieldname] = value;
	update_action_field("config", JSON.stringify(config));
}

function autoMap() {
	if (!config.arguments) config.arguments = {};
	ruleArguments.value.forEach((arg) => {
		if (!config.arguments[arg.fieldname]) {
			config.arguments[arg.fieldname] = `{{ doc.${arg.fieldname} }}`;
		}
	});
	update_action_field("config", JSON.stringify(config));
}

onMounted(() => {
	if (props.node.data?.rule) {
		fetchRuleArgs(props.node.data.rule);
	}
});

watch(
	() => props.node.data?.rule,
	(newVal) => {
		fetchRuleArgs(newVal);
	}
);
</script>

<style scoped>
.sub-rule-config {
	display: flex;
	flex-direction: column;
}

.argument-row {
	padding: 10px 0;
	border-bottom: 1px solid var(--fr-border-subtle);
}

.argument-row:last-child {
	border-bottom: none;
}

.arg-info {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.arg-label {
	font-size: 13px;
	font-weight: 600;
	color: var(--fr-text);
}

.arg-type {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	color: var(--fr-text-muted);
}

.flex-1 {
	flex: 1;
}
.flex-2 {
	flex: 2;
}

.empty-state.compact {
	padding: 24px;
	text-align: center;
	background: var(--fr-bg-muted);
	border: 1px dashed var(--fr-border);
	border-radius: var(--fr-radius-lg);
	color: var(--fr-text-muted);
	font-size: 13px;
}
</style>
