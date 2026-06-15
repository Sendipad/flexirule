<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Start Date") }}</label>
		<div class="d-flex fxr-gap-2">
			<select
				class="fxr-select flex-1"
				v-model="modelValue.diff_start_type"
				:disabled="readOnly"
			>
				<option value="today">{{ __("Today") }}</option>
				<option value="doc_field">{{ __("Document Field") }}</option>
			</select>
			<select
				v-if="modelValue.diff_start_type === 'doc_field'"
				class="fxr-select flex-1"
				v-model="modelValue.diff_start_field"
				:disabled="readOnly"
			>
				<option v-for="opt in dateFieldOptions" :key="opt.value" :value="opt.value">
					{{ opt.label }}
				</option>
			</select>
		</div>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("End Date") }}</label>
		<div class="d-flex fxr-gap-2">
			<select
				class="fxr-select flex-1"
				v-model="modelValue.diff_end_type"
				:disabled="readOnly"
			>
				<option value="today">{{ __("Today") }}</option>
				<option value="doc_field">{{ __("Document Field") }}</option>
			</select>
			<select
				v-if="modelValue.diff_end_type === 'doc_field'"
				class="fxr-select flex-1"
				v-model="modelValue.diff_end_field"
				:disabled="readOnly"
			>
				<option v-for="opt in dateFieldOptions" :key="opt.value" :value="opt.value">
					{{ opt.label }}
				</option>
			</select>
		</div>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Result Unit") }}</label>
		<select class="fxr-select" v-model="modelValue.diff_unit" :disabled="readOnly">
			<option value="days">{{ __("Days") }}</option>
			<option value="months">{{ __("Months") }}</option>
			<option value="years">{{ __("Years") }}</option>
		</select>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../stores";
import { __ } from "../utils";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();

const dateFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Date", "Datetime"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});
</script>
