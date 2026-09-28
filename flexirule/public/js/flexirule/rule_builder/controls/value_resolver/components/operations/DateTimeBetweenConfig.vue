<template>
	<div class="d-flex flex-column fxr-gap-2 mt-2">
		<div class="dual-value-wrapper">
			<div class="value-input-item">
				<label class="fxr-label-sm mb-1">{{ __("From") }}</label>
				<FlexValueControl
					:modelValue="fromValue"
					:context="{
						df: valueFieldSchema,
						operator: '>=',
						referenceDoctype: doctype,
					}"
					:engine="store"
					:doc="store?.rule_doc"
					:variableOptions="variableOptions"
					:readOnly="readOnly"
					:disabled="readOnly"
					@update:modelValue="updateFromValue"
				/>
			</div>
			<span class="between-sep align-self-end mb-2">{{ __("and") }}</span>
			<div class="value-input-item">
				<label class="fxr-label-sm mb-1">{{ __("To") }}</label>
				<FlexValueControl
					:modelValue="toValue"
					:context="{
						df: valueFieldSchema,
						operator: '<=',
						referenceDoctype: doctype,
					}"
					:engine="store"
					:doc="store?.rule_doc"
					:variableOptions="variableOptions"
					:readOnly="readOnly"
					:disabled="readOnly"
					@update:modelValue="updateToValue"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../../stores";
import { __ } from "../../utils";
import FlexValueControl from "../../../FlexValueControl.vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			from: { mode: "static", value: "" },
			to: { mode: "static", value: "" },
		}),
	},
	doctype: String,
	context: Object,
	variableOptions: Array,
	readOnly: Boolean,
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();

const valueFieldSchema = computed(() => {
	const df = props.context?.df || {};
	return {
		...df,
		reqd: 1,
	};
});

function ensureStructured(val) {
	if (val && typeof val === "object" && val.mode) return val;
	return { mode: "static", value: val ?? "" };
}

const fromValue = computed(() => ensureStructured(props.modelValue?.from));
const toValue = computed(() => ensureStructured(props.modelValue?.to));

function updateFromValue(val) {
	emit("update:modelValue", {
		...props.modelValue,
		from: ensureStructured(val),
	});
}

function updateToValue(val) {
	emit("update:modelValue", {
		...props.modelValue,
		to: ensureStructured(val),
	});
}
</script>

<style scoped>
.dual-value-wrapper {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-3);
	width: 100%;
}

.value-input-item {
	flex: 1;
	min-width: 0;
}

.between-sep {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
	font-weight: var(--fxr-weight-semibold);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	flex-shrink: 0;
}
</style>
