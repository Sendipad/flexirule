<template>
	<div class="d-flex flex-column fxr-gap-2">
		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Text Operation") }}</label>
			<select v-model="localState.operation" class="form-control form-control-sm" :disabled="readOnly">
				<option value="concat">{{ __("Concatenate") }}</option>
				<option value="trim">{{ __("Trim Whitespace") }}</option>
				<option value="upper">{{ __("Uppercase") }}</option>
				<option value="lower">{{ __("Lowercase") }}</option>
				<option value="title">{{ __("Title Case") }}</option>
				<option value="slug">{{ __("URL Slug") }}</option>
				<option value="snake">{{ __("Snake Case") }}</option>
				<option value="replace">{{ __("Replace Text") }}</option>
				<option value="format_date">{{ __("Format Date") }}</option>
				<option value="fmt_money">{{ __("Format Currency") }}</option>
				<option value="pattern">{{ __("Format Pattern") }}</option>
			</select>
		</div>

		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Source Text / Field A") }}</label>
			<ComboBoxControl
				v-model="localState.field_a"
				:options="variableOptions"
				:doctype="doctype"
				:read_only="readOnly"
			/>
		</div>

		<div v-if="['concat', 'replace'].includes(localState.operation)" class="form-group mb-0">
			<label class="fxr-label-sm">{{ localState.operation === 'concat' ? __('Text / Field B') : __('Search Text') }}</label>
			<ComboBoxControl
				v-model="localState.field_b"
				:options="variableOptions"
				:doctype="doctype"
				:read_only="readOnly"
			/>
		</div>

		<div v-if="['replace', 'format_date', 'fmt_money', 'pattern'].includes(localState.operation)" class="form-group mb-0">
			<label class="fxr-label-sm">
				{{ localState.operation === 'replace' ? __('Replace With') : localState.operation === 'fmt_money' ? __('Currency Code / Field') : __('Format Pattern / String') }}
			</label>
			<input
				v-model="localState.fmt_config"
				type="text"
				class="form-control form-control-sm"
				:placeholder="localState.operation === 'format_date' ? 'YYYY-MM-DD' : localState.operation === 'fmt_money' ? 'USD' : ''"
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
