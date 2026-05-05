<!--
  SelectControl - Simple native select for reliability
-->
<script setup>
import { computed } from "vue";
const props = defineProps({
	df: Object,
	modelValue: [String, Number],
	read_only: Boolean,
	no_label: Boolean,
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const options = computed(() => {
	let opts = props.df?.options;

	if (!opts) return [];

	// String options (newline separated)
	if (typeof opts === "string") {
		return opts
			.split("\n")
			.filter(Boolean)
			.map((opt) => ({
				label: __(opt.trim()),
				value: opt.trim(),
			}));
	}

	// Array of strings
	if (Array.isArray(opts) && opts.length && typeof opts[0] === "string") {
		return opts.map((opt) => ({
			label: __(opt),
			value: opt,
		}));
	}

	// Array of objects with label/value
	if (Array.isArray(opts)) {
		return opts.map((opt) => ({
			label: __(opt.label || opt.value),
			value: opt.value,
		}));
	}

	return [];
});

function on_change(event) {
	emit("update:modelValue", event.target.value);
}
</script>

<template>
	<div class="control frappe-control">
		<div
			v-if="df?.label && !no_label && !hideLabel"
			class="control-label label"
			:class="{ reqd: df.reqd }"
		>
			{{ __(df.label) }}
		</div>
		<div class="select-wrapper">
			<select
				class="form-control input-sm"
				:value="modelValue"
				:disabled="read_only || df?.read_only"
				@change="on_change"
			>
				<option v-if="!df?.reqd" value="">{{ __("Select...") }}</option>
				<option v-for="opt in options" :key="opt.value" :value="opt.value">
					{{ opt.label }}
				</option>
			</select>
			<div class="select-icon">
				<svg class="icon icon-sm"><use href="#icon-select"></use></svg>
			</div>
		</div>
		<div v-if="df?.description && !hideDescription" class="description text-muted">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style scoped>
/* ─── SelectControl – Unified Design ─── */
.control-label {
	font-size: var(--fr-text-sm);
	font-weight: var(--fr-weight-medium);
	margin-bottom: var(--fr-space-2);
	color: var(--fr-text-secondary);
}

.control-label.reqd::after {
	content: " *";
	color: var(--fr-text-danger);
}

.select-wrapper {
	position: relative;
}

.select-wrapper select {
	width: 100%;
	appearance: none;
	-webkit-appearance: none;
	-moz-appearance: none;
	padding-right: 28px;
	font-size: var(--fr-input-font-size);
	background: transparent;
	border: 1px solid var(--fr-border);
	height: var(--fr-input-height);
	border-radius: var(--fr-radius-md);
	transition: border-color var(--fr-transition-fast), box-shadow var(--fr-transition-fast);
}

.select-wrapper select:hover:not(:disabled) {
	border-color: var(--fr-border-strong);
}

.select-wrapper select:focus:not(:disabled) {
	border-color: var(--fr-border-focus);
	box-shadow: var(--fr-shadow-focus);
}

.select-icon {
	position: absolute;
	top: 50%;
	right: 4px;
	transform: translateY(-50%);
	pointer-events: none;
	color: var(--fr-text-muted);
}

.select-icon .icon {
	width: 12px;
	height: 12px;
}

.description {
	font-size: var(--fr-text-xs);
	margin-top: var(--fr-space-2);
	color: var(--fr-text-muted);
}
</style>
