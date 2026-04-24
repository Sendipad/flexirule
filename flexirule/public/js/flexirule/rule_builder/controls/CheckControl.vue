<script setup>
import { ref, useSlots } from "vue";
const props = defineProps(["df", "modelValue", "read_only", "hideLabel"]);
defineEmits(["update:modelValue"]);
let slots = useSlots();
const showTooltip = ref(false);
</script>

<template>
	<div
		class="control frappe-control checkbox"
		:class="{ editable: slots.label, 'no-label': hideLabel }"
		@mouseenter="showTooltip = true"
		@mouseleave="showTooltip = false"
		@focusin="showTooltip = true"
		@focusout="showTooltip = false"
	>
		<!-- checkbox -->
		<label v-if="slots.label" class="field-controls">
			<div class="checkbox">
				<input type="checkbox" disabled />
				<slot name="label" />
			</div>
			<slot name="actions" />
		</label>
		<label v-else class="checkbox-label-container">
			<input
				type="checkbox"
				:checked="modelValue"
				:disabled="read_only"
				@change="(event) => $emit('update:modelValue', event.target.checked)"
			/>
			<span v-if="df?.label && !hideLabel" class="label-area" :class="{ reqd: df.reqd }">{{
				__(df.label)
			}}</span>
		</label>

		<!-- Tooltip Popup for Grid / Hidden Label Mode -->
		<div v-if="hideLabel && showTooltip && (df.label || df.description)" class="check-tooltip">
			<div class="tooltip-header" v-if="df.label">{{ __(df.label) }}</div>
			<div class="tooltip-body" v-if="df.description">{{ __(df.description) }}</div>
		</div>

		<!-- standard description -->
		<div v-if="df.description && !hideLabel" class="mt-2 description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style lang="scss" scoped>
label,
input {
	margin-bottom: 0 !important;
	cursor: pointer;
}

.checkbox-label-container {
	display: flex;
	align-items: center;
	width: 100%;
	height: 100%;
	justify-content: flex-start; /* Align left usually, or center for grid? */
}

.control.no-label {
	display: flex;
	justify-content: center; /* Center checkbox in grid cell */
	align-items: center;
	height: 100%;
	position: relative;
	margin: 0;
	min-height: 24px;
}

.control.no-label label {
	width: auto;
	padding: 4px;
	display: flex;
	justify-content: center;
}

.check-tooltip {
	position: absolute;
	bottom: 100%;
	left: 50%;
	transform: translateX(-50%);
	background: #333;
	color: #fff;
	padding: 8px 12px;
	border-radius: 4px;
	font-size: 12px;
	z-index: 1000;
	min-width: 150px;
	max-width: 250px;
	box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	pointer-events: none;
	margin-bottom: 6px;
}

.check-tooltip::after {
	content: "";
	position: absolute;
	top: 100%;
	left: 50%;
	margin-left: -5px;
	border-width: 5px;
	border-style: solid;
	border-color: #333 transparent transparent transparent;
}

.tooltip-header {
	font-weight: 600;
	margin-bottom: 4px;
	border-bottom: 1px solid #555;
	padding-bottom: 4px;
}

label .checkbox {
	display: flex;
	align-items: center;

	input {
		background-color: var(--fg-color);
		box-shadow: none;
		border: 1px solid var(--gray-400);
		pointer-events: none;
	}
}
</style>
