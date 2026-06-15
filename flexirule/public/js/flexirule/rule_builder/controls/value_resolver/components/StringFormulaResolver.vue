<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Operation") }}</label>
		<select class="fxr-select" v-model="modelValue.str_op" :disabled="readOnly">
			<option value="concat">{{ __("Concatenate") }}</option>
			<option value="fmt_money">{{ __("Format Currency") }}</option>
			<option value="uppercase">{{ __("Uppercase") }}</option>
			<option value="lowercase">{{ __("Lowercase") }}</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{
			modelValue.str_op === "fmt_money" ? __("Numeric Field") : __("Value A")
		}}</label>
		<div class="d-flex gap-2">
			<select class="fxr-select flex-1" v-model="modelValue.str_a_type" :disabled="readOnly">
				<option value="field">{{ __("Document Field") }}</option>
				<option value="constant">{{ __("Fixed Text") }}</option>
			</select>
			<select
				v-if="modelValue.str_a_type === 'field'"
				class="fxr-select flex-1"
				v-model="modelValue.str_a"
				:disabled="readOnly"
			>
				<option value="">{{ __("Select field...") }}</option>
				<option
					v-for="opt in modelValue.str_op === 'fmt_money'
						? numericFieldOptions
						: stringFieldOptions"
					:key="opt.value"
					:value="opt.value"
				>
					{{ opt.label }}
				</option>
			</select>
			<input
				v-else
				type="text"
				class="fxr-input flex-1"
				v-model="modelValue.str_a"
				:disabled="readOnly"
				:placeholder="__('Enter text')"
			/>
		</div>
	</div>
	<div
		class="d-flex flex-column fxr-gap-1 mt-2"
		v-if="['concat', 'fmt_money'].includes(modelValue.str_op)"
	>
		<label class="fxr-label-sm">{{
			modelValue.str_op === "fmt_money" ? __("Currency") : __("Value B")
		}}</label>
		<div class="d-flex gap-2">
			<select class="fxr-select flex-1" v-model="modelValue.str_b_type" :disabled="readOnly">
				<option value="field">{{ __("Document Field") }}</option>
				<option value="constant">
					{{
						modelValue.str_op === "fmt_money" ? __("Fixed Currency") : __("Fixed Text")
					}}
				</option>
			</select>
			<select
				v-if="modelValue.str_b_type === 'field'"
				class="fxr-select flex-1"
				v-model="modelValue.str_b"
				:disabled="readOnly"
			>
				<option value="">{{ __("Select field...") }}</option>
				<option v-for="opt in stringFieldOptions" :key="opt.value" :value="opt.value">
					{{ opt.label }}
				</option>
			</select>
			<input
				v-else
				type="text"
				class="fxr-input flex-1"
				v-model="modelValue.str_b"
				:disabled="readOnly"
				:placeholder="modelValue.str_op === 'fmt_money' ? __('e.g. USD') : __('Enter text')"
			/>
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
