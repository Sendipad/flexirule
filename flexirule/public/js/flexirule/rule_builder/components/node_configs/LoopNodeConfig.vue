<template>
	<div class="loop-node-config">
		<div class="form-group">
			<ComboBoxControl
				ref="controlRefs"
				fieldname="config.iterator"
				:df="{ label: __('Iterator (List)'), fieldtype: 'FieldPicker', reqd: 1 }"
				:options="listFields"
				:modelValue="getJsonConfig('iterator')"
				:showValidation="showValidation"
				:trigger="'button'"
				@update:modelValue="$emit('update-json-config', 'iterator', $event)"
			/>
			<div class="help-text text-muted" style="font-size: 11px">
				{{ __("Select a list or table to iterate over.") }}
			</div>
		</div>
		<div class="form-group">
			<ControlFactory
				ref="controlRefs"
				:df="aliasFieldDf"
				:modelValue="nodeData.return_variable"
				:showValidation="showValidation"
				@update:modelValue="updateReturnVariable"
			/>
			<div class="help-text text-muted" style="font-size: 11px">
				{{ __("Variable name for current item (e.g. 'row' or 'item').") }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onBeforeUpdate } from "vue";
import { useStore } from "../../stores";
import ControlFactory from "../../controls/ControlFactory.vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";

const props = defineProps({
	node: Object,
	showValidation: { type: Boolean, default: false },
});

const store = useStore();
const docFields = ref([]);
const loading = ref(false);

const nodeData = computed(() => props.node?.data || {});

const emit = defineEmits(["update-json-config"]);
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

const aliasFieldDf = computed(() => ({
	fieldname: "return_variable",
	fieldtype: "Data",
	label: __("Item Alias"),
	placeholder: "item",
	reqd: 1,
}));

async function loadFields() {
	if (!props.node?.id) return;
	loading.value = true;
	try {
		docFields.value = await store.getAvailableVariables(props.node.id);
	} catch (e) {
		console.error("Failed to load fields for LoopNodeConfig", e);
	} finally {
		loading.value = false;
	}
}

const listFields = computed(() => {
	const fields = docFields.value || [];
	return fields.filter((f) => {
		// 1. Explicit Table types
		if (f.fieldtype === "Table") return true;

		// 2. Variables that have sub-fields (schema-driven objects/lists)
		const prefix = f.value + ".";
		return fields.some((sub) => sub.value.startsWith(prefix));
	});
});

onMounted(loadFields);
watch(() => props.node?.id, loadFields);
// Refresh only when node return_variables or action_types change (not on every drag/resize)
watch(
	() =>
		store.nodes
			?.map((n) => `${n.id}:${n.data?.return_variable}:${n.data?.action_type}`)
			.join(","),
	loadFields
);

function updateReturnVariable(val) {
	if (props.node?.data) {
		props.node.data.return_variable = val;
		const isDraft = !store.nodes.some((n) => n === props.node);
		if (!isDraft) {
			store.mark_dirty();
		}
	}
}

// Migration: If config.alias exists but return_variable is empty, migrate it
watch(
	() => nodeData.value?.config,
	(val) => {
		const config = flexirule.utils.safe_json_parse(val, {});
		if (config.alias && !nodeData.value.return_variable) {
			updateReturnVariable(config.alias);
			// Optional: remove from config to clean up
			emit("update-json-config", "alias", undefined);
		}
	},
	{ immediate: true }
);

function getJsonConfig(key, defaultVal = "") {
	const configStr = nodeData.value?.config || nodeData.value?.method_config;
	const config = flexirule.utils.safe_json_parse(configStr, {});
	return config[key] !== undefined ? config[key] : defaultVal;
}

async function validate() {
	const results = await Promise.all(
		(controlRefs.value || []).map((ref) => {
			if (ref && typeof ref.validate === "function") {
				return ref.validate();
			}
			return { valid: true };
		})
	);
	const errors = results.flatMap((r) => r.errors || []);
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
