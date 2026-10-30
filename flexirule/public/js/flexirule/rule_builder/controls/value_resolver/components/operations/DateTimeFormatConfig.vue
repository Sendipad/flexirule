<template>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<ComboBoxControl
			v-model="modelValue.fmt_field"
			:options="dateFieldOptions"
			:read_only="readOnly"
			:df="{ label: __('Date & Time Field') }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<DataControl
			v-model="modelValue.fmt_config"
			:read_only="readOnly"
			:df="{
				label: __('Format Template'),
				placeholder: 'e.g. YYYY-MM-DD or DD/MM/YYYY HH:mm:ss',
			}"
		/>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useMetaStore, useRuleStore } from "../../../../stores";
import { __ } from "../../utils";
import ComboBoxControl from "../../../ComboBoxControl.vue";
import DataControl from "../../../DataControl.vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			fmt_field: "",
			fmt_config: "YYYY-MM-DD",
		}),
	},
	doctype: String,
	readOnly: Boolean,
});

const metaStore = useMetaStore();
const ruleStore = useRuleStore();

const dateFieldOptions = computed(() => {
	const dt = ruleStore.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = metaStore.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) =>
			[
				"Date",
				"Datetime",
				"Time",
				"Data",
				"Text",
				"Small Text",
				"Long Text",
				"Code",
				"Select",
			].includes(f.fieldtype)
		)
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});
</script>
