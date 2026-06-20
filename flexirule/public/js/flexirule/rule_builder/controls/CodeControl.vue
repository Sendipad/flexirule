<!-- Used as Code, HTML Editor, Markdown Editor & JSON Control -->
<script setup>
import { computed, onMounted, ref, useSlots, watch } from "vue";
const props = defineProps({
	df: Object,
	read_only: Boolean,
	modelValue: [String, Number],
	showValidation: { type: Boolean, default: false },
});
let emit = defineEmits(["update:modelValue"]);
let slots = useSlots();

let code = ref(null);
let code_control = ref(null);
let update_control = ref(true);

let content = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

onMounted(() => {
	if (code.value) {
		code_control.value = frappe.ui.form.make_control({
			parent: code.value,
			df: {
				...props.df,
				fieldtype: "Code",
				hidden: 0,
				read_only: props.read_only,
				change: () => {
					if (update_control.value) {
						content.value = code_control.value.get_value();
					}
					update_control.value = true;
				},
			},
			value: content.value,
			disabled: Boolean(slots.label) || props.read_only,
			render_input: true,
			only_input: Boolean(slots.label),
		});
	}
});

watch(
	() => content.value,
	(value) => {
		update_control.value = false;
		code_control.value?.set_value(value);
	}
);

watch(
	() => props.df.max_height,
	(value) => {
		if (code_control.value) {
			code_control.value.ace_editor_target.css("max-height", value);
		}
	}
);

function copyCode() {
	if (!content.value) return;
	frappe.utils.copy_to_clipboard(content.value);
}

const isValid = computed(() => {
	if (!props.df?.reqd) return true;
	return props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "";
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("{0} is required").replace("{0}", props.df?.label || __("Field")));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<template>
	<div
		v-if="slots.label"
		class="control fxr-control"
		:class="{
			editable: slots.label,
			'has-error': showValidation && !isValid,
		}"
		v-field-inspect="{ name: df?.fieldname || fieldname, label: df?.label }"
	>
		<div class="field-controls">
			<slot name="label" />
			<div class="d-flex align-items-center gap-2">
				<slot name="actions" />
				<button
					v-if="read_only"
					class="btn btn-xs btn-default"
					@click="copyCode"
					:title="__('Copy to Clipboard')"
				>
					<i class="fa fa-copy"></i>
				</button>
			</div>
		</div>
		<div ref="code"></div>
		<div v-if="df.description" class="mt-2 description">{{ __(df.description) }}</div>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} is required").replace("{0}", df?.label || __("Field")) }}
		</div>
	</div>
	<div
		v-else
		class="control fxr-control"
		:class="{ 'has-error': showValidation && !isValid }"
		ref="code"
		v-field-inspect="{ name: df?.fieldname || fieldname, label: df?.label }"
	></div>
</template>
