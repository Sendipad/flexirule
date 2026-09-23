<template>
	<div class="d-flex flex-column fxr-gap-2">
		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Math Operation") }}</label>
			<select
				v-model="localState.operation"
				class="form-control form-control-sm"
				:disabled="readOnly"
			>
				<option value="+">{{ __("+ Add") }}</option>
				<option value="-">{{ __("− Subtract") }}</option>
				<option value="*">{{ __("× Multiply") }}</option>
				<option value="/">{{ __("÷ Divide") }}</option>
				<option value="min">{{ __("Minimum (Min)") }}</option>
				<option value="max">{{ __("Maximum (Max)") }}</option>
				<option value="round">{{ __("Round") }}</option>
			</select>
		</div>

		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Value A (Field)") }}</label>
			<ComboBoxControl
				v-model="localState.field_a"
				:options="variableOptions"
				:doctype="doctype"
				:read_only="readOnly"
			/>
		</div>

		<template v-if="localState.operation !== 'round'">
			<div class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("Value B Type") }}</label>
				<select
					v-model="localState.field_b_type"
					class="form-control form-control-sm"
					:disabled="readOnly"
				>
					<option value="field">{{ __("Field / Variable") }}</option>
					<option value="constant">{{ __("Constant Number") }}</option>
				</select>
			</div>

			<div v-if="localState.field_b_type === 'field'" class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("Value B (Field)") }}</label>
				<ComboBoxControl
					v-model="localState.field_b"
					:options="variableOptions"
					:doctype="doctype"
					:read_only="readOnly"
				/>
			</div>

			<div v-else class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("Value B (Constant)") }}</label>
				<input
					v-model.number="localState.constant_b"
					type="number"
					step="any"
					class="form-control form-control-sm"
					:disabled="readOnly"
				/>
			</div>
		</template>

		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Precision (Decimals)") }}</label>
			<input
				v-model.number="localState.precision"
				type="number"
				min="0"
				max="6"
				class="form-control form-control-sm"
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
