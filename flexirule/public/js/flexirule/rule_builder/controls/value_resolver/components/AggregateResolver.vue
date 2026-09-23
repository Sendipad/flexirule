<template>
	<div class="d-flex flex-column fxr-gap-2">
		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Aggregation Operation") }}</label>
			<select
				v-model="localState.agg_op"
				class="form-control form-control-sm"
				:disabled="readOnly"
			>
				<option value="sum">{{ __("Sum") }}</option>
				<option value="avg">{{ __("Average") }}</option>
				<option value="min">{{ __("Minimum") }}</option>
				<option value="max">{{ __("Maximum") }}</option>
				<option value="count">{{ __("Row Count") }}</option>
			</select>
		</div>

		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Child Table / Source") }}</label>
			<ComboBoxControl
				v-model="localState.agg_table"
				:options="variableOptions"
				:doctype="doctype"
				:read_only="readOnly"
			/>
		</div>

		<div v-if="localState.agg_op !== 'count'" class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Numeric Field") }}</label>
			<input
				v-model="localState.agg_field"
				type="text"
				class="form-control form-control-sm"
				placeholder="e.g. amount, qty, rate"
				:disabled="readOnly"
			/>
		</div>
	</div>
</template>

<script setup>
import ComboBoxControl from "../../ComboBoxControl.vue";
import { __ } from "../utils";

const props = defineProps({
	modelValue: { type: Object, default: () => ({}) },
	doctype: { type: String, default: "" },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: () => [] },
});

const localState = props.modelValue;
</script>
