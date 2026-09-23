<template>
	<div class="d-flex flex-column fxr-gap-2">
		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Lookup Operation") }}</label>
			<select v-model="localState.operation" class="form-control form-control-sm" :disabled="readOnly">
				<option value="get">{{ __("Fetch Field Value") }}</option>
				<option value="exists">{{ __("Check Record Exists") }}</option>
			</select>
		</div>

		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Local Link Field") }}</label>
			<ComboBoxControl
				v-model="localState.link_field"
				:options="variableOptions"
				:doctype="doctype"
				:read_only="readOnly"
			/>
		</div>

		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Linked DocType") }}</label>
			<input
				v-model="localState.linked_doctype"
				type="text"
				class="form-control form-control-sm"
				placeholder="e.g. Customer, Item"
				:disabled="readOnly"
			/>
		</div>

		<div v-if="localState.operation === 'get'" class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Target Field to Fetch") }}</label>
			<input
				v-model="localState.fetch_field"
				type="text"
				class="form-control form-control-sm"
				placeholder="e.g. customer_group, item_name"
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
