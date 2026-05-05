<script setup>
/**
 * MultiSelectControl - Wrapper for Frappe's MultiSelect control
 * Supports both static options (Select) and dynamic links (Link)
 */
import { ref, onMounted, watch, onBeforeUnmount, nextTick } from "vue";

const props = defineProps({
	df: Object,
	modelValue: [Array, String],
	read_only: Boolean,
	get_data: { type: Function, default: null },
});

const emit = defineEmits(["update:modelValue"]);

const wrapper = ref(null);
const control = ref(null);
let is_setting_value = false;

async function make_control() {
	if (!wrapper.value) return;
	wrapper.value.innerHTML = "";

	try {
		let normalizedOptions = props.df?.options;
		if (typeof normalizedOptions === "string") {
			normalizedOptions = normalizedOptions
				.split("\n")
				.map((opt) => opt.trim())
				.filter(Boolean);
		}

		const control_df = {
			...props.df,
			fieldtype: "MultiSelect",
			options: normalizedOptions,
			label: props.df.label,
			read_only: props.read_only,
			get_data: props.get_data || props.df.get_data,
			change: () => {
				if (control.value && !is_setting_value) {
					const val = control.value.get_value();
					const arr = val
						? val
								.split(",")
								.map((s) => s.trim())
								.filter(Boolean)
						: [];
					emit("update:modelValue", arr);
				}
			},
		};

		const ControlClass = frappe.ui.form.ControlMultiSelect;
		control.value = new ControlClass({
			df: control_df,
			parent: $(wrapper.value),
			render_input: true,
			only_input: true,
		});
		control.value.make();

		// Set initial value
		if (props.modelValue) {
			sync_value(props.modelValue);
		}
	} catch (e) {
		console.error("Failed to create MultiSelect control", e);
		wrapper.value.innerHTML = `<div class="text-danger small">${__("Error loading control")}: ${
			e.message
		}</div>`;
	}
}

function sync_value(val) {
	if (!control.value) return;

	let str_value = "";
	if (Array.isArray(val)) {
		str_value = val.join(", ");
	} else if (typeof val === "string") {
		str_value = val;
	}

	if (control.value.get_value() !== str_value) {
		is_setting_value = true;
		control.value.set_value(str_value);
		setTimeout(() => {
			is_setting_value = false;
		}, 50);
	}
}

onMounted(() => {
	nextTick(() => {
		make_control();
	});
});

watch(
	() => props.modelValue,
	(val) => {
		sync_value(val);
	},
	{ deep: true }
);

watch(
	() => [props.df?.options, props.read_only],
	() => {
		make_control();
	}
);

onBeforeUnmount(() => {
	if (control.value && control.value.destroy) {
		// control.value.destroy();
	}
});
</script>

<template>
	<div class="control-wrapper" ref="wrapper"></div>
</template>

<script>
export default {
	name: "MultiSelectControl",
};
</script>

<style scoped>
/* ─── MultiSelectControl – Unified Design ─── */
.control-wrapper {
	min-height: var(--fr-input-height);
}
:deep(.form-group) {
	margin-bottom: 0 !important;
}
:deep(.awesomplete > ul) {
	z-index: var(--fr-z-dropdown, 1050);
}
:deep(.form-control) {
	height: var(--fr-input-height) !important;
	font-size: var(--fr-input-font-size) !important;
	border: 1px solid var(--fr-border) !important;
	border-radius: var(--fr-radius-md) !important;
	transition: border-color var(--fr-transition-fast), box-shadow var(--fr-transition-fast) !important;
}
:deep(.form-control:focus) {
	border-color: var(--fr-border-focus) !important;
	box-shadow: var(--fr-shadow-focus) !important;
}
</style>
