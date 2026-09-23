<template>
	<div class="d-flex flex-column fxr-gap-2">
		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Operation") }}</label>
			<select v-model="localState.operation" class="form-control form-control-sm" :disabled="readOnly">
				<option value="add">{{ __("Add Offset") }}</option>
				<option value="subtract">{{ __("Subtract Offset") }}</option>
				<option value="diff">{{ __("Date Difference") }}</option>
			</select>
		</div>

		<!-- Add / Subtract Mode -->
		<template v-if="['add', 'subtract'].includes(localState.operation)">
			<div class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("Base Date") }}</label>
				<select v-model="localState.base_type" class="form-control form-control-sm mb-1" :disabled="readOnly">
					<option value="today">{{ __("Today") }}</option>
					<option value="doc_field">{{ __("Field") }}</option>
				</select>
				<ComboBoxControl
					v-if="localState.base_type === 'doc_field'"
					v-model="localState.base_field"
					:options="variableOptions"
					:doctype="doctype"
					:read_only="readOnly"
				/>
			</div>

			<div class="row g-2">
				<div class="col-6">
					<label class="fxr-label-sm">{{ __("Offset Amount") }}</label>
					<input
						v-model.number="localState.offset_value"
						type="number"
						class="form-control form-control-sm"
						:disabled="readOnly"
					/>
				</div>
				<div class="col-6">
					<label class="fxr-label-sm">{{ __("Unit") }}</label>
					<select v-model="localState.offset_unit" class="form-control form-control-sm" :disabled="readOnly">
						<option value="days">{{ __("Days") }}</option>
						<option value="months">{{ __("Months") }}</option>
						<option value="years">{{ __("Years") }}</option>
					</select>
				</div>
			</div>
		</template>

		<!-- Diff Mode -->
		<template v-if="localState.operation === 'diff'">
			<div class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("Start Date") }}</label>
				<select v-model="localState.diff_start_type" class="form-control form-control-sm mb-1" :disabled="readOnly">
					<option value="today">{{ __("Today") }}</option>
					<option value="doc_field">{{ __("Field") }}</option>
				</select>
				<ComboBoxControl
					v-if="localState.diff_start_type === 'doc_field'"
					v-model="localState.diff_start_field"
					:options="variableOptions"
					:doctype="doctype"
					:read_only="readOnly"
				/>
			</div>

			<div class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("End Date") }}</label>
				<select v-model="localState.diff_end_type" class="form-control form-control-sm mb-1" :disabled="readOnly">
					<option value="today">{{ __("Today") }}</option>
					<option value="doc_field">{{ __("Field") }}</option>
				</select>
				<ComboBoxControl
					v-if="localState.diff_end_type === 'doc_field'"
					v-model="localState.diff_end_field"
					:options="variableOptions"
					:doctype="doctype"
					:read_only="readOnly"
				/>
			</div>

			<div class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("Difference Unit") }}</label>
				<select v-model="localState.diff_unit" class="form-control form-control-sm" :disabled="readOnly">
					<option value="days">{{ __("Days") }}</option>
					<option value="months">{{ __("Months") }}</option>
					<option value="years">{{ __("Years") }}</option>
				</select>
			</div>
		</template>
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
