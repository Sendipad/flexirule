<template>
	<div class="d-flex flex-column fxr-gap-2">
		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Target Type") }}</label>
			<select
				v-model="localState.operation"
				class="form-control form-control-sm"
				:disabled="readOnly"
			>
				<option value="text">{{ __("Text (String)") }}</option>
				<option value="integer">{{ __("Integer (Integer)") }}</option>
				<option value="decimal">{{ __("Decimal (Float)") }}</option>
				<option value="boolean">{{ __("Boolean (True/False)") }}</option>
				<option value="date">{{ __("Date") }}</option>
				<option value="datetime">{{ __("Datetime") }}</option>
			</select>
		</div>

		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Source Field / Variable") }}</label>
			<ComboBoxControl
				v-model="localState.field"
				:options="variableOptions"
				:doctype="doctype"
				:read_only="readOnly"
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
