<template>
	<div class="d-flex flex-column fxr-gap-1">
		<SelectControl
			v-model="modelValue.operation"
			:options="operationOptions"
			:read_only="readOnly"
			:df="{ label: __('Text Operation') }"
		/>
	</div>

	<!-- Operation: Combine -->
	<template v-if="modelValue.operation === 'combine'">
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<label class="fxr-label-sm">{{ __("Value A") }}</label>
			<div class="d-flex gap-2">
				<SelectControl
					class="flex-1"
					v-model="modelValue.config.str_a_type"
					:options="typeOptions"
					:read_only="readOnly"
					no-label
				/>
				<ComboBoxControl
					v-if="modelValue.config.str_a_type === 'field'"
					class="flex-1"
					v-model="modelValue.config.str_a"
					:options="stringFieldOptions"
					:read_only="readOnly"
					no-label
					:placeholder="__('Select field...')"
				/>
				<DataControl
					v-else
					class="flex-1"
					v-model="modelValue.config.str_a"
					:read_only="readOnly"
					no-label
					:placeholder="__('Enter text')"
				/>
			</div>
		</div>
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<label class="fxr-label-sm">{{ __("Value B") }}</label>
			<div class="d-flex gap-2">
				<SelectControl
					class="flex-1"
					v-model="modelValue.config.str_b_type"
					:options="typeOptions"
					:read_only="readOnly"
					no-label
				/>
				<ComboBoxControl
					v-if="modelValue.config.str_b_type === 'field'"
					class="flex-1"
					v-model="modelValue.config.str_b"
					:options="stringFieldOptions"
					:read_only="readOnly"
					no-label
					:placeholder="__('Select field...')"
				/>
				<DataControl
					v-else
					class="flex-1"
					v-model="modelValue.config.str_b"
					:read_only="readOnly"
					no-label
					:placeholder="__('Enter text')"
				/>
			</div>
		</div>
	</template>

	<!-- Operation: Case -->
	<template v-else-if="modelValue.operation === 'case'">
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<ComboBoxControl
				v-model="modelValue.config.field"
				:options="stringFieldOptions"
				:read_only="readOnly"
				:df="{ label: __('Target Field') }"
			/>
		</div>
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<SelectControl
				v-model="modelValue.config.case_mode"
				:options="caseOptions"
				:read_only="readOnly"
				:df="{ label: __('Case Mode') }"
			/>
		</div>
	</template>

	<!-- Operation: Normalize -->
	<template v-else-if="modelValue.operation === 'normalize'">
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<ComboBoxControl
				v-model="modelValue.config.norm_field"
				:options="stringFieldOptions"
				:read_only="readOnly"
				:df="{ label: __('Target Field') }"
			/>
		</div>
		<div class="d-flex flex-column fxr-gap-1 mt-3">
			<SelectControl
				v-model="modelValue.config.norm_profile"
				:options="profileOptions"
				:read_only="readOnly"
				:df="{ label: __('Normalization Profile') }"
			/>
		</div>
		<div class="d-flex flex-column fxr-gap-1 mt-3">
			<div class="d-flex align-items-center justify-content-between">
				<label class="fxr-label-sm mb-0">{{ __("Pipeline Operations") }}</label>
				<span v-if="!isCustomProfile" class="fxr-text-xs text-muted">
					{{ __("Read-only for selected profile") }}
				</span>
			</div>
			<MultiSelectList
				v-model="modelValue.config.norm_pipeline"
				:options="normOperationOptions"
				:read_only="readOnly || !isCustomProfile"
				displayMode="badges"
				:placeholder="__('Select operations...')"
			/>
		</div>
	</template>

	<!-- Operation: Format -->
	<template v-else-if="modelValue.operation === 'format'">
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<ComboBoxControl
				v-model="modelValue.config.fmt_field"
				:options="stringFieldOptions"
				:read_only="readOnly"
				:df="{ label: __('Field') }"
			/>
		</div>
		<div class="d-flex flex-column fxr-gap-1 mt-2">
			<DataControl
				v-model="modelValue.config.fmt_config"
				:read_only="readOnly"
				:df="{
					label: __('Template String'),
					placeholder: 'e.g. Hello {0}',
				}"
			/>
		</div>
	</template>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useStore } from "../../../stores";
import { __ } from "../utils";
import SelectControl from "../../SelectControl.vue";
import ComboBoxControl from "../../ComboBoxControl.vue";
import DataControl from "../../DataControl.vue";
import MultiSelectList from "../../MultiSelectList.vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			operation: "combine",
			config: {},
		}),
	},
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();
const availableOperations = ref([]);
const availableProfiles = ref([]);

const operationOptions = [
	{ value: "combine", label: __("Combine Text") },
	{ value: "case", label: __("Change Case") },
	{ value: "normalize", label: __("Normalize") },
	{ value: "format", label: __("Template Format") },
];

const typeOptions = [
	{ value: "field", label: __("Document Field") },
	{ value: "constant", label: __("Fixed Text") },
];

const caseOptions = [
	{ value: "uppercase", label: __("Uppercase") },
	{ value: "lowercase", label: __("Lowercase") },
	{ value: "titlecase", label: __("Title Case") },
	{ value: "slug", label: __("Slug") },
	{ value: "snake", label: __("Snake Case") },
];

const isCustomProfile = computed(
	() => (props.modelValue.config?.norm_profile || "Custom") === "Custom"
);

const profileOptions = computed(() => {
	const opts = [{ value: "Custom", label: __("Custom Pipeline") }];
	availableProfiles.value.forEach((p) => {
		opts.push({ value: p, label: p });
	});
	return opts;
});

const formatOpLabel = (op) => {
	if (!op) return "";
	return op
		.replace(/_/g, " ")
		.replace(/\b\w/g, (l) => l.toUpperCase())
		.replace("Normalize", "Norm.")
		.replace("Extra Spaces", "Spaces");
};

const normOperationOptions = computed(() => {
	return availableOperations.value.map((op) => ({
		value: op,
		label: formatOpLabel(op),
	}));
});

const stringFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) =>
			["Data", "Text", "Small Text", "Select", "Phone", "Autocomplete"].includes(f.fieldtype)
		)
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});

const fetchMetadata = async () => {
	try {
		if (window.frappe?.call) {
			const res = await frappe.call("flexirule.ruleflow.api.normalize_test_value", {
				input_value: "",
			});
			if (res.message) {
				availableOperations.value = res.message.available_operations || [];
				availableProfiles.value = res.message.available_profiles || [];
			}
		}
	} catch (e) {
		console.error("Failed to fetch normalization metadata", e);
	}
};

onMounted(() => {
	fetchMetadata();
});
</script>
