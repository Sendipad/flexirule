<template>
	<div class="wait-node-config">
		<div class="form-row">
			<div class="form-group col-md-6">
				<DataControl
					:df="{ label: __('Delay Value'), fieldtype: 'Float', reqd: 1 }"
					:modelValue="getJsonConfig('value', 1)"
					@update:modelValue="$emit('update-field', 'value', parseFloat($event))"
				/>
			</div>
			<div class="form-group col-md-6">
				<SelectControl
					:df="{
						label: __('Unit'),
						fieldtype: 'Select',
						options: 'Seconds\nMinutes\nHours\nDays',
						reqd: 1,
					}"
					:modelValue="getJsonConfig('unit', 'Minutes')"
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
import DataControl from "../../controls/DataControl.vue";
import SelectControl from "../../controls/SelectControl.vue";

const props = defineProps({
	nodeData: Object,
});

defineEmits(["update-field"]);

function getJsonConfig(key, defaultVal = "") {
	const configStr = props.nodeData?.config;
	const config = flexirule.utils.safe_json_parse(configStr, {});

	// Legacy migration: if key is 'value' but only 'duration' exists
	if (key === "value" && config.duration !== undefined && config.value === undefined) {
		return config.duration;
	}

	return config[key] !== undefined ? config[key] : defaultVal;
}
</script>
