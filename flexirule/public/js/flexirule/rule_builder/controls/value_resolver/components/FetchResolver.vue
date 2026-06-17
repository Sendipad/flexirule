<template>
	<div class="fetch-resolver-wrap">
		<!-- Step 1: Source DocType -->
		<CollapsibleSection
			:label="__('1. Source DocType')"
			:initial-collapsed="!!modelValue.linked_doctype"
			:read-only="readOnly"
		>
			<template #header-actions>
				<span v-if="modelValue.linked_doctype" class="fxr-text-xs text-muted truncate ml-2">
					{{ modelValue.linked_doctype }}
				</span>
			</template>
			<ComboBoxControl
				v-model="modelValue.linked_doctype"
				doctype="DocType"
				:read_only="readOnly"
				:placeholder="__('Select Source DocType...')"
				hide-label
				allow-custom-value
			/>
		</CollapsibleSection>

		<!-- Step 2: Source Document -->
		<CollapsibleSection
			:label="__('2. Source Document')"
			:initial-collapsed="!!modelValue.link_field"
			:read-only="readOnly"
			class="mt-1"
		>
			<template #header-actions>
				<span v-if="modelValue.link_field" class="fxr-text-xs text-muted truncate ml-2">
					{{ modelValue.link_field }}
				</span>
			</template>
			<div class="d-flex fxr-gap-2">
				<SelectControl
					style="width: 80px"
					v-model="modelValue.link_source_type"
					:options="sourceTypeOptions"
					:read_only="readOnly"
					no-label
					@change="modelValue.link_field = ''"
				/>
				<ComboBoxControl
					v-if="modelValue.link_source_type !== 'expression'"
					class="flex-1 min-w-0"
					v-model="modelValue.link_field"
					:options="sourceLinkOptions"
					:read_only="readOnly"
					:placeholder="
						modelValue.link_source_type === 'variable'
							? __('Search variable...')
							: __('Select field...')
					"
					:allow-custom-value="modelValue.link_source_type === 'variable'"
					hide-label
				/>
				<DataControl
					v-else
					class="flex-1"
					v-model="modelValue.link_field"
					:read_only="readOnly"
					:placeholder="__('e.g. doc.party')"
					no-label
				/>
			</div>
		</CollapsibleSection>

		<!-- Step 3: Fetch Field -->
		<CollapsibleSection
			:label="__('3. Fetch Field')"
			:initial-collapsed="false"
			:read-only="readOnly"
			class="mt-1 border-bottom-0"
		>
			<template #header-actions>
				<span v-if="modelValue.fetch_field" class="fxr-text-xs text-muted truncate ml-2">
					{{ modelValue.fetch_field }}
				</span>
			</template>
			<ComboBoxControl
				v-model="modelValue.fetch_field"
				:options="fetchFieldOptions"
				:read_only="readOnly || !modelValue.linked_doctype"
				:loading="fetchMetaLoading"
				:placeholder="fetchMetaLoading ? __('Loading...') : __('Select field to fetch...')"
				:allow-custom-value="true"
				hide-label
			/>
		</CollapsibleSection>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useStore } from "../../../stores";
import ComboBoxControl from "../../ComboBoxControl.vue";
import SelectControl from "../../SelectControl.vue";
import DataControl from "../../DataControl.vue";
import CollapsibleSection from "../../CollapsibleSection.vue";
import { __ } from "../utils";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
	variableOptions: {
		type: Array,
		default: () => [],
	},
	context: Object,
});

const store = useStore();
const fetchMetaLoading = ref(false);

const sourceTypeOptions = [
	{ value: "doc_field", label: __("Field") },
	{ value: "variable", label: __("Var") },
	{ value: "expression", label: __("Expr") },
];

const resolverFieldname = computed(() => {
	const fieldname =
		props.context?.fieldname ||
		props.context?.target ||
		props.context?.df?.fieldname ||
		props.context?.df?.value ||
		"value_resolver";
	return String(fieldname)
		.replace(/^doc\./, "")
		.replace(/^vars\./, "");
});

const prioritizedFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];

	const prioritizedTypes = ["Link", "Dynamic Link", "Data", "Select"];

	return [...fields]
		.sort((a, b) => {
			const aPrio = prioritizedTypes.indexOf(a.fieldtype);
			const bPrio = prioritizedTypes.indexOf(b.fieldtype);

			if (aPrio !== -1 && bPrio !== -1) return aPrio - bPrio;
			if (aPrio !== -1) return -1;
			if (bPrio !== -1) return 1;
			return 0;
		})
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
			options: f.options,
			fieldtype: f.fieldtype,
			icon: ["Link", "Dynamic Link"].includes(f.fieldtype) ? "fa fa-link" : "fa fa-columns",
		}));
});

const sourceLinkOptions = computed(() => {
	if (props.modelValue.link_source_type === "variable") {
		const vars = props.variableOptions || [];
		return vars.map((v) => ({
			label: `${v.label || v.value} (vars.${v.value})`,
			value: `vars.${v.value}`,
			options: v.options,
			fieldtype: v.fieldtype,
		}));
	}
	return prioritizedFieldOptions.value;
});

const fetchFieldOptions = computed(() => {
	const linkedDt = props.modelValue.linked_doctype;
	if (!linkedDt) return [];
	return store.get_fields_for_doctype(linkedDt, { valueMode: "fieldname" });
});

watch(
	() => props.modelValue.link_field,
	async (newVal) => {
		if (!newVal) return;

		const opt = sourceLinkOptions.value.find((o) => o.value === newVal);
		if (opt && (opt.options || opt.fieldtype === "Dynamic Link")) {
			let linkedDt = opt.options;
			if (opt.fieldtype === "Dynamic Link") {
				linkedDt = `doc.${opt.options}`;
			}

			if (linkedDt && !props.modelValue.linked_doctype) {
				props.modelValue.linked_doctype = linkedDt;
			}
		}
	}
);

watch(
	() => props.modelValue.linked_doctype,
	async (newVal, oldVal) => {
		if (!newVal) {
			props.modelValue.fetch_field = "";
			return;
		}

		if (newVal !== oldVal) {
			if (!props.modelValue.fetch_field && resolverFieldname.value) {
				props.modelValue.fetch_field = resolverFieldname.value;
			}
		}

		if (newVal && !newVal.startsWith("doc.") && !newVal.startsWith("vars.")) {
			fetchMetaLoading.value = true;
			try {
				await store.fetch_metadata(newVal);
			} finally {
				fetchMetaLoading.value = false;
			}
		}
	}
);
</script>
