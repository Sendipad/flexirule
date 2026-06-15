<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Format Type") }}</label>
		<select class="fxr-select" v-model="modelValue.fmt_op" :disabled="readOnly">
			<option value="format_date">{{ __("Date/Time Format") }}</option>
			<option value="fmt_money">{{ __("Currency Format") }}</option>
			<option value="format">{{ __("String Template") }}</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Field") }}</label>
		<select class="fxr-select" v-model="modelValue.fmt_field" :disabled="readOnly">
			<option value="">{{ __("Select field...") }}</option>
			<option
				v-for="opt in modelValue.fmt_op === 'fmt_money'
					? numericFieldOptions
					: modelValue.fmt_op === 'format_date'
					? dateFieldOptions
					: stringFieldOptions"
				:key="opt.value"
				:value="opt.value"
			>
				{{ opt.label }}
			</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{
			modelValue.fmt_op === "fmt_money"
				? __("Currency (Field or Code)")
				: modelValue.fmt_op === "format_date"
				? __("Date Format (e.g. YYYY-MM-DD)")
				: __("Template")
		}}</label>
		<input
			type="text"
			class="fxr-input"
			v-model="modelValue.fmt_config"
			:disabled="readOnly"
			:placeholder="modelValue.fmt_op === 'format_date' ? 'YYYY-MM-DD' : ''"
		/>
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

const numericFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});

const stringFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Data", "Text", "Small Text", "Select"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});
</script>
