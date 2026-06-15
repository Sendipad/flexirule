<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Field A") }}</label>
		<select
			class="fxr-select"
			v-model="modelValue.field_a"
			:disabled="readOnly"
			:class="{ 'is-invalid': !isFieldAValid }"
		>
			<option value="">{{ __("Select field...") }}</option>
			<option v-for="opt in numericFieldOptions" :key="opt.value" :value="opt.value">
				{{ opt.label }}
			</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Operator") }}</label>
		<select class="fxr-select" v-model="modelValue.math_op" :disabled="readOnly">
			<option value="+">{{ __("Add (+)") }}</option>
			<option value="-">{{ __("Subtract (-)") }}</option>
			<option value="*">{{ __("Multiply (×)") }}</option>
			<option value="/">{{ __("Divide (÷)") }}</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Field B / Value") }}</label>
		<div class="d-flex fxr-gap-2">
			<select
				class="fxr-select flex-1"
				v-model="modelValue.field_b_type"
				:disabled="readOnly"
			>
				<option value="field">{{ __("Document Field") }}</option>
				<option value="constant">{{ __("Fixed Value") }}</option>
			</select>
			<select
				v-if="modelValue.field_b_type === 'field'"
				class="fxr-select flex-1"
				v-model="modelValue.field_b"
				:disabled="readOnly"
				:class="{ 'is-invalid': !isFieldBValid }"
			>
				<option value="">{{ __("Select field...") }}</option>
				<option v-for="opt in numericFieldOptions" :key="opt.value" :value="opt.value">
					{{ opt.label }}
				</option>
			</select>
			<input
				v-else
				type="number"
				step="any"
				class="fxr-input flex-1"
				v-model.number="modelValue.constant_b"
				:disabled="readOnly"
				:placeholder="__('Enter value')"
			/>
		</div>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Round To") }}</label>
		<div class="d-flex align-items-center fxr-gap-2">
			<input
				type="number"
				class="fxr-input"
				style="width: 80px"
				v-model.number="modelValue.precision"
				min="0"
				max="9"
				:disabled="readOnly"
			/>
			<span class="text-muted fxr-text-xs">{{ __("decimal places") }}</span>
		</div>
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

const numericFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
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

const isFieldAValid = computed(() => {
	if (!props.modelValue.field_a) return true; // Optional or handled by overall validation
	return numericFieldOptions.value.some((opt) => opt.value === props.modelValue.field_a);
});

const isFieldBValid = computed(() => {
	if (props.modelValue.field_b_type !== "field") return true;
	if (!props.modelValue.field_b) return true;
	return numericFieldOptions.value.some((opt) => opt.value === props.modelValue.field_b);
});
</script>
