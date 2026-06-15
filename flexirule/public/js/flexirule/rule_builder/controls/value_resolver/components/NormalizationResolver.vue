<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Operation") }}</label>
		<select class="fxr-select" v-model="modelValue.norm_op" :disabled="readOnly">
			<option value="trim">{{ __("Trim Whitespace") }}</option>
			<option value="slug">{{ __("Slugify") }}</option>
			<option value="title">{{ __("Title Case") }}</option>
			<option value="upper">{{ __("Uppercase") }}</option>
			<option value="lower">{{ __("Lowercase") }}</option>
			<option value="snake">{{ __("Snake Case") }}</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Field") }}</label>
		<select class="fxr-select" v-model="modelValue.norm_field" :disabled="readOnly">
			<option value="">{{ __("Select field...") }}</option>
			<option v-for="opt in stringFieldOptions" :key="opt.value" :value="opt.value">
				{{ opt.label }}
			</option>
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
