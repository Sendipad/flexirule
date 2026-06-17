<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Base Date") }}</label>
		<div class="d-flex fxr-gap-2">
			<SelectControl
				class="flex-1"
				v-model="modelValue.base_type"
				:options="baseTypeOptions"
				:read_only="readOnly"
				no-label
			/>
			<ComboBoxControl
				v-if="modelValue.base_type === 'doc_field'"
				class="flex-1"
				v-model="modelValue.base_field"
				:options="dateFieldOptions"
				:read_only="readOnly"
				no-label
				:placeholder="__('Select field...')"
			/>
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
			<SelectControl
				style="width: 70px"
				v-model="modelValue.offset_sign"
				:options="signOptions"
				:read_only="readOnly"
				no-label
			/>
			<DataControl
				style="width: 80px"
				v-model="modelValue.offset_value"
				:df="{ fieldtype: 'Int' }"
				:read_only="readOnly"
				no-label
			/>
			<SelectControl
				class="flex-1"
				v-model="modelValue.offset_unit"
				:options="unitOptions"
				:read_only="readOnly"
				no-label
			/>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../stores";
import { __, validateField } from "../utils";
import SelectControl from "../../SelectControl.vue";
import ComboBoxControl from "../../ComboBoxControl.vue";
import DataControl from "../../DataControl.vue";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();

const baseTypeOptions = [
	{ value: "today", label: __("Today") },
	{ value: "doc_field", label: __("Document Field") },
];

const signOptions = [
	{ value: "+", label: "+" },
	{ value: "-", label: "-" },
];

const unitOptions = [
	{ value: "days", label: __("Days") },
	{ value: "weeks", label: __("Weeks") },
	{ value: "months", label: __("Months") },
	{ value: "years", label: __("Years") },
	{ value: "hours", label: __("Hours") },
];

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
