<template>
	<div class="d-flex flex-column fxr-gap-1">
		<SelectControl
			v-model="modelValue.operation"
			:options="operationOptions"
			:read_only="readOnly"
			:df="{ label: __('Date Operation') }"
		/>
	</div>

	<!-- Operation: Calculate (Date Formula) -->
	<template v-if="modelValue.operation === 'calculate'">
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<label class="fxr-label-sm">{{ __("Base Date") }}</label>
			<div class="d-flex fxr-gap-2">
				<SelectControl
					class="flex-1"
					v-model="modelValue.config.base_type"
					:options="baseTypeOptions"
					:read_only="readOnly"
					no-label
				/>
				<ComboBoxControl
					v-if="modelValue.config.base_type === 'doc_field'"
					class="flex-1"
					v-model="modelValue.config.base_field"
					:options="dateFieldOptions"
					:read_only="readOnly"
					no-label
					:placeholder="__('Select field...')"
				/>
			</div>
			<div v-if="!isBaseFieldValid" class="fxr-text-xs text-danger mt-1">
				<i class="fa fa-exclamation-circle mr-1"></i>
				{{
					frappe.utils.format(
						__("Field '{0}' not found in {1}"),
						modelValue.config.base_field,
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
					v-model="modelValue.config.offset_sign"
					:options="signOptions"
					:read_only="readOnly"
					no-label
				/>
				<DataControl
					style="width: 80px"
					v-model="modelValue.config.offset_value"
					:df="{ fieldtype: 'Int' }"
					:read_only="readOnly"
					no-label
				/>
				<SelectControl
					class="flex-1"
					v-model="modelValue.config.offset_unit"
					:options="unitOptions"
					:read_only="readOnly"
					no-label
				/>
			</div>
		</div>
	</template>

	<!-- Operation: Diff (Date Difference) -->
	<template v-else-if="modelValue.operation === 'diff'">
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<label class="fxr-label-sm">{{ __("Start Date") }}</label>
			<div class="d-flex fxr-gap-2">
				<SelectControl
					class="flex-1"
					v-model="modelValue.config.diff_start_type"
					:options="baseTypeOptions"
					:read_only="readOnly"
					no-label
				/>
				<ComboBoxControl
					v-if="modelValue.config.diff_start_type === 'doc_field'"
					class="flex-1"
					v-model="modelValue.config.diff_start_field"
					:options="dateFieldOptions"
					:read_only="readOnly"
					no-label
					:placeholder="__('Select field...')"
				/>
			</div>
		</div>
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<label class="fxr-label-sm">{{ __("End Date") }}</label>
			<div class="d-flex fxr-gap-2">
				<SelectControl
					class="flex-1"
					v-model="modelValue.config.diff_end_type"
					:options="baseTypeOptions"
					:read_only="readOnly"
					no-label
				/>
				<ComboBoxControl
					v-if="modelValue.config.diff_end_type === 'doc_field'"
					class="flex-1"
					v-model="modelValue.config.diff_end_field"
					:options="dateFieldOptions"
					:read_only="readOnly"
					no-label
					:placeholder="__('Select field...')"
				/>
			</div>
		</div>
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<SelectControl
				v-model="modelValue.config.diff_unit"
				:options="diffUnitOptions"
				:read_only="readOnly"
				:df="{ label: __('Result Unit') }"
			/>
		</div>
	</template>

	<!-- Operation: Format (Format Date) -->
	<template v-else-if="modelValue.operation === 'format'">
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<ComboBoxControl
				v-model="modelValue.config.fmt_field"
				:options="dateFieldOptions"
				:read_only="readOnly"
				:df="{ label: __('Date Field') }"
				:placeholder="__('Select date field...')"
			/>
		</div>
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<DataControl
				v-model="modelValue.config.fmt_config"
				:read_only="readOnly"
				:df="{
					label: __('Format String'),
					placeholder: 'e.g. YYYY-MM-DD or dd/mm/yyyy',
				}"
			/>
		</div>
	</template>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../stores";
import { __, validateField } from "../utils";
import SelectControl from "../../SelectControl.vue";
import ComboBoxControl from "../../ComboBoxControl.vue";
import DataControl from "../../DataControl.vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			operation: "calculate",
			config: {},
		}),
	},
	doctype: String,
	readOnly: Boolean,
	context: Object,
});

const store = useStore();

const operationOptions = computed(() => [
	{ value: "calculate", label: __("Date Formula") },
	{ value: "diff", label: __("Date Difference") },
	{ value: "format", label: __("Format Date") },
]);

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

const diffUnitOptions = [
	{ value: "days", label: __("Days") },
	{ value: "months", label: __("Months") },
	{ value: "years", label: __("Years") },
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
	if (props.modelValue.config?.base_type !== "doc_field") return true;
	if (!props.modelValue.config?.base_field) return true;
	const dt = store.rule_doc?.document_type || props.doctype;
	return validateField(props.modelValue.config.base_field, dt, store);
});
</script>
