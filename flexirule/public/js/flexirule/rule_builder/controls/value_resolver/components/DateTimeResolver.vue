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
import DateTimeCurrentConfig from "./operations/DateTimeCurrentConfig.vue";
import DateTimeCalculateConfig from "./operations/DateTimeCalculateConfig.vue";
import DateTimeDiffConfig from "./operations/DateTimeDiffConfig.vue";
import DateTimeExtractConfig from "./operations/DateTimeExtractConfig.vue";
import DateTimeBoundaryConfig from "./operations/DateTimeBoundaryConfig.vue";
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
 */
const DATE_TIME_OPERATIONS = {
	current: {
		id: "current",
		label: __("Current Value"),
		component: markRaw(DateTimeCurrentConfig),
	},
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
	extract: {
		id: "extract",
		label: __("Extract Component"),
		component: markRaw(DateTimeExtractConfig),
	},
	boundary: {
		id: "boundary",
		label: __("Period Boundary"),
		component: markRaw(DateTimeBoundaryConfig),
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
