<template>
	<div class="date-resolver d-flex flex-column fxr-gap-2">
		<!-- Operation Selector -->
		<div class="d-flex flex-column fxr-gap-1">
			<label class="fxr-label-sm">{{ __("Operation") }}</label>
			<SelectControl
				v-model="modelValue.operation"
				:options="operationOptions"
				:read_only="readOnly"
				no-label
			/>
		</div>

		<!-- Date Formula / Calculate Mode -->
		<template v-if="modelValue.operation === 'calculate'">
			<div class="d-flex flex-column fxr-gap-1 mt-1">
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
						frappe.utils.format(
							__("Field '{0}' not found in {1}"),
							modelValue.base_field,
							doctype || store.rule_doc?.document_type
						)
					}}
				</div>
			</div>
			<div class="d-flex flex-column fxr-gap-1 mt-1">
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

		<!-- Date Difference Mode -->
		<template v-else-if="modelValue.operation === 'diff'">
			<div class="d-flex flex-column fxr-gap-1 mt-1">
				<label class="fxr-label-sm">{{ __("Start Date") }}</label>
				<div class="d-flex fxr-gap-2">
					<SelectControl
						class="flex-1"
						v-model="modelValue.diff_start_type"
						:options="baseTypeOptions"
						:read_only="readOnly"
						no-label
					/>
					<ComboBoxControl
						v-if="modelValue.diff_start_type === 'doc_field'"
						class="flex-1"
						v-model="modelValue.diff_start_field"
						:options="dateFieldOptions"
						:read_only="readOnly"
						no-label
						:placeholder="__('Select field...')"
					/>
				</div>
			</div>
			<div class="d-flex flex-column fxr-gap-1 mt-1">
				<label class="fxr-label-sm">{{ __("End Date") }}</label>
				<div class="d-flex fxr-gap-2">
					<SelectControl
						class="flex-1"
						v-model="modelValue.diff_end_type"
						:options="baseTypeOptions"
						:read_only="readOnly"
						no-label
					/>
					<ComboBoxControl
						v-if="modelValue.diff_end_type === 'doc_field'"
						class="flex-1"
						v-model="modelValue.diff_end_field"
						:options="dateFieldOptions"
						:read_only="readOnly"
						no-label
						:placeholder="__('Select field...')"
					/>
				</div>
			</div>
			<div class="d-flex flex-column fxr-gap-1 mt-1">
				<SelectControl
					v-model="modelValue.diff_unit"
					:options="diffUnitOptions"
					:read_only="readOnly"
					:df="{ label: __('Result Unit') }"
				/>
			</div>
		</template>

		<!-- Format Mode -->
		<template v-else-if="modelValue.operation === 'format'">
			<div class="d-flex flex-column fxr-gap-1 mt-1">
				<ComboBoxControl
					v-model="modelValue.fmt_field"
					:options="dateFieldOptions"
					:read_only="readOnly"
					:df="{ label: __('Date Field') }"
				/>
			</div>
			<div class="d-flex flex-column fxr-gap-1 mt-1">
				<DataControl
					v-model="modelValue.fmt_config"
					:read_only="readOnly"
					:df="{
						label: __('Date Format (e.g. YYYY-MM-DD)'),
						placeholder: 'YYYY-MM-DD',
					}"
				/>
			</div>
		</template>
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
	modelValue: {
		type: Object,
		default: () => ({
			operation: "calculate",
			base_type: "today",
			base_field: "",
			offset_sign: "+",
			offset_value: 0,
			offset_unit: "days",
			diff_start_type: "today",
			diff_start_field: "",
			diff_end_type: "doc_field",
			diff_end_field: "",
			diff_unit: "days",
			fmt_field: "",
			fmt_config: "YYYY-MM-DD",
		}),
	},
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();

const operationOptions = [
	{ value: "calculate", label: __("Date Formula (calculate)") },
	{ value: "diff", label: __("Date Difference (diff)") },
	{ value: "format", label: __("Format (format)") },
];

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
			let realLabel = f.label || f.fieldname;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

const isBaseFieldValid = computed(() => {
	if (props.modelValue.operation !== "calculate") return true;
	if (props.modelValue.base_type !== "doc_field") return true;
	if (!props.modelValue.base_field) return true;
	const dt = store.rule_doc?.document_type || props.doctype;
	return validateField(props.modelValue.base_field, dt, store);
});
</script>
