<template>
	<div class="wait-node-config">
		<div class="form-row">
			<div class="form-group col-md-6">
				<DataControl
					:ref="setControlRef"
					fieldname="config.value"
					:df="{
						fieldtype: 'Float',
						label: __('Delay Value'),
						reqd: 1,
					}"
					:modelValue="getJsonConfig('value', 1)"
					:showValidation="showValidation"
					@update:modelValue="$emit('update-field', 'value', parseFloat($event))"
				/>
			</div>
			<div class="form-group col-md-6">
				<SelectControl
					:ref="setControlRef"
					fieldname="config.unit"
					:df="{
						fieldtype: 'Select',
						label: __('Unit'),
						options: 'Seconds\nMinutes\nHours\nDays',
						reqd: 1,
					}"
					:modelValue="getJsonConfig('unit', 'Minutes')"
					:showValidation="showValidation"
					@update:modelValue="$emit('update-field', 'unit', $event)"
				/>
			</div>
		</div>
		<div class="alert alert-info py-2 px-3 small mt-2">
			<i class="fa fa-info-circle mr-1"></i>
			{{ __("Rule execution will pause for the specified duration.") }}
		</div>
	</div>
</template>

<script setup>
import { ref, onBeforeUpdate } from "vue";
import DataControl from "../../controls/DataControl.vue";
import SelectControl from "../../controls/SelectControl.vue";

const props = defineProps({
	nodeData: Object,
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update-field"]);
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

function getJsonConfig(key, defaultVal = "") {
	const configStr = props.nodeData?.config;
	const config = flexirule.utils.safe_json_parse(configStr, {});

	// Legacy migration: if key is 'value' but only 'duration' exists
	if (key === "value" && config.duration !== undefined && config.value === undefined) {
		return config.duration;
	}

	return config[key] !== undefined ? config[key] : defaultVal;
}

async function validate() {
	const results = await Promise.all(
		(controlRefs.value || []).map((ctrl) => {
			if (ctrl && typeof ctrl.validate === "function") {
				return ctrl.validate();
			}
			return { valid: true };
		})
	);
	const errors = results.flatMap((r) => r.errors || []);

	const value = getJsonConfig("value", 1);
	if (value <= 0) {
		errors.push(__("Delay value must be greater than 0"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
