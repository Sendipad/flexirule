<template>
	<div class="loop-node-config">
		<div class="form-group">
			<FieldPickerControl
				:df="{ label: __('Iterator (List)'), fieldtype: 'Link' }"
				:fields="listFields"
				:modelValue="getJsonConfig('iterator')"
				@update:modelValue="$emit('update-json-config', 'iterator', $event)"
			/>
			<div class="help-text text-muted" style="font-size: 11px">
				{{ __("Select a list or table to iterate over.") }}
			</div>
		</div>
		<div class="form-group">
			<label>{{ __("Item Alias") }}</label>
			<input
				type="text"
				class="form-control"
				:value="getJsonConfig('alias')"
				@input="$emit('update-json-config', 'alias', $event.target.value)"
				placeholder="item"
			/>
			<div class="help-text text-muted" style="font-size: 11px">
				{{ __("Variable name for current item (e.g. 'row' or 'item').") }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useStore } from "../../stores";
import FieldPickerControl from "../../controls/FieldPickerControl.vue";

const props = defineProps({
	node: Object,
});

const store = useStore();
const docFields = ref([]);
const loading = ref(false);

const nodeData = computed(() => props.node?.data || {});

defineEmits(["update-json-config"]);

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

function getJsonConfig(key, defaultVal = "") {
	const configStr = nodeData.value?.config || nodeData.value?.method_config;
	const config = flexirule.utils.safe_json_parse(configStr, {});
	return config[key] !== undefined ? config[key] : defaultVal;
}

function validate() {
	const iterator = getJsonConfig("iterator");
	if (!iterator) {
		return { valid: false, message: __("Iterator is required") };
	}
	return { valid: true };
}

defineExpose({ validate });
</script>
