<template>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<SelectControl
			v-model="modelValue.token"
			:options="currentTokenOptions"
			:read_only="readOnly"
			:df="{ label: __('Current Value Type') }"
		/>
	</div>
</template>

<script setup>
import { __ } from "../../utils";
import SelectControl from "../../../SelectControl.vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			token: "date",
		}),
	},
	doctype: String,
	readOnly: Boolean,
});

const currentTokenOptions = [
	{ value: "date", label: __("Current Date (Today)") },
	{ value: "datetime", label: __("Current Date & Time (Now)") },
	{ value: "time", label: __("Current Time") },
];
</script>
