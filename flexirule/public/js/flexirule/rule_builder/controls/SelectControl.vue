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
.control-label {
	font-size: 11px;
	font-weight: 500;
	margin-bottom: 4px;
	color: var(--text-muted);
}

.control-label.reqd::after {
	content: " *";
	color: var(--red-500);
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
	font-size: 13px;
	background: transparent;
	border: 1px solid transparent;
}

.select-icon {
	position: absolute;
	top: 50%;
	right: 4px;
	transform: translateY(-50%);
	pointer-events: none;
	color: var(--text-muted);
}

.select-icon .icon {
	width: 12px;
	height: 12px;
}

.description {
	font-size: 10px;
	margin-top: 4px;
}
</style>
