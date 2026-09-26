<template>
	<div class="d-flex flex-column fxr-gap-1">
		<SelectControl
			v-model="modelValue.operation"
			:options="operationOptions"
			:read_only="readOnly"
			:df="{ label: __('Date & Time Operation') }"
		/>
	</div>

	<!-- Render active operation configuration component dynamically from registry -->
	<component
		:is="activeOperationComponent"
		v-if="activeOperationComponent"
		v-model="modelValue.config"
		:doctype="doctype"
		:readOnly="readOnly"
	/>
</template>

<script setup>
import { computed, markRaw } from "vue";
import { __ } from "../utils";
import SelectControl from "../../SelectControl.vue";
import DateTimeCalculateConfig from "./operations/DateTimeCalculateConfig.vue";
import DateTimeDiffConfig from "./operations/DateTimeDiffConfig.vue";
import DateTimeFormatConfig from "./operations/DateTimeFormatConfig.vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			operation: "calculate",
			config: {},
		}),
	},
	doctype: String,
	readOnly: Boolean,
});

/**
 * Extensible Date & Time operations registry.
 * Future operations (extract, convert, combine, round, timezone) can be registered here.
 */
export const DATE_TIME_OPERATIONS = {
	calculate: {
		id: "calculate",
		label: __("Date & Time Formula"),
		component: markRaw(DateTimeCalculateConfig),
	},
	diff: {
		id: "diff",
		label: __("Date & Time Difference"),
		component: markRaw(DateTimeDiffConfig),
	},
	format: {
		id: "format",
		label: __("Format Date & Time"),
		component: markRaw(DateTimeFormatConfig),
	},
};

const operationOptions = computed(() => {
	return Object.values(DATE_TIME_OPERATIONS).map((op) => ({
		value: op.id,
		label: op.label,
	}));
});

const activeOperationComponent = computed(() => {
	const currentOp = props.modelValue.operation || "calculate";
	return DATE_TIME_OPERATIONS[currentOp]?.component || null;
});
</script>
