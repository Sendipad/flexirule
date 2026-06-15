<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Base Date") }}</label>
		<div class="d-flex fxr-gap-2">
			<select class="fxr-select flex-1" v-model="modelValue.base_type" :disabled="readOnly">
				<option value="today">{{ __("Today") }}</option>
				<option value="doc_field">{{ __("Document Field") }}</option>
			</select>
			<select
				v-if="modelValue.base_type === 'doc_field'"
				class="fxr-select flex-1"
				v-model="modelValue.base_field"
				:disabled="readOnly"
				:class="{ 'is-invalid': !isBaseFieldValid }"
			>
				<option v-for="opt in dateFieldOptions" :key="opt.value" :value="opt.value">
					{{ opt.label }}
				</option>
			</select>
		</div>
		<div v-if="!isBaseFieldValid" class="fxr-text-xs text-danger mt-1">
			<i class="fa fa-exclamation-circle mr-1"></i>
			{{
				__("Field '{0}' not found in {1}").format(
					modelValue.base_field,
					doctype || store.rule_doc?.document_type
				)
			}}
		</div>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Offset") }}</label>
		<div class="d-flex align-items-center fxr-gap-2">
			<select
				class="fxr-select"
				v-model="modelValue.offset_sign"
				style="width: 70px"
				:disabled="readOnly"
			>
				<option value="+">+</option>
				<option value="-">-</option>
			</select>
			<input
				type="number"
				class="fxr-input"
				style="width: 80px"
				v-model.number="modelValue.offset_value"
				min="0"
				:disabled="readOnly"
			/>
			<select class="fxr-select flex-1" v-model="modelValue.offset_unit" :disabled="readOnly">
				<option value="days">{{ __("Days") }}</option>
				<option value="weeks">{{ __("Weeks") }}</option>
				<option value="months">{{ __("Months") }}</option>
				<option value="years">{{ __("Years") }}</option>
				<option value="hours">{{ __("Hours") }}</option>
			</select>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../stores";
import { __, validateField } from "../utils";

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
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

const isBaseFieldValid = computed(() => {
	if (props.modelValue.base_type !== "doc_field") return true;
	if (!props.modelValue.base_field) return true; // Initial state might be empty
	const dt = store.rule_doc?.document_type || props.doctype;
	return validateField(props.modelValue.base_field, dt, store);
});
</script>
