<template>
	<div class="test-results-view">
		<div v-if="!selectedStep" class="steps-list">
			<div
				v-for="(step, index) in uiStore.test_execution_steps"
				:key="index"
				class="step-item"
				:class="[`status-${step.status}`]"
				@click="selectStep(index)"
			>
				<div class="step-order">#{{ step.order }}</div>
				<div class="step-info">
					<div class="step-action">{{ step.action }}</div>
					<div class="step-meta">
						<span class="step-type">{{ step.type }}</span>
						<span v-if="step.duration_ms" class="step-duration">{{ step.duration_ms }}ms</span>
					</div>
				</div>
				<i class="fa fa-chevron-right step-chevron"></i>
			</div>
		</div>

		<div v-else class="step-details">
			<button class="btn btn-xs btn-default mb-3" @click="uiStore.test_selected_step_index = null">
				<i class="fa fa-arrow-left"></i> {{ __("Back to Steps") }}
			</button>

			<div class="detail-header mb-3">
				<h5>{{ selectedStep.action }}</h5>
				<div :class="['status-badge', selectedStep.status]">
					{{ selectedStep.status }}
				</div>
			</div>

			<div v-if="selectedStep.error" class="error-box mb-3">
				<label>{{ __("Error") }}</label>
				<pre>{{ selectedStep.error }}</pre>
			</div>

			<div v-if="selectedStep.input" class="data-section mb-3">
				<label>{{ __("Input") }}</label>
				<pre>{{ formatData(selectedStep.input) }}</pre>
			</div>

			<div v-if="selectedStep.output || selectedStep.result" class="data-section mb-3">
				<label>{{ __("Output") }}</label>
				<pre>{{ formatData(selectedStep.output || selectedStep.result) }}</pre>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useUIStore } from "../../stores";

const uiStore = useUIStore();

const selectedStep = computed(() => {
	if (uiStore.test_selected_step_index === null) return null;
	return uiStore.test_execution_steps[uiStore.test_selected_step_index];
});

function selectStep(index) {
	uiStore.test_selected_step_index = index;
}

function formatData(data) {
	if (typeof data === "string") {
		try {
			return JSON.stringify(JSON.parse(data), null, 2);
		} catch (e) {
			return data;
		}
	}
	return JSON.stringify(data, null, 2);
}
</script>

<style scoped>
.test-results-view {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.step-item {
	display: flex;
	align-items: center;
	padding: 10px;
	border-radius: 8px;
	background: var(--fxr-surface-2);
	margin-bottom: 8px;
	cursor: pointer;
	transition: background 0.2s;
	border: 1px solid var(--fxr-border-subtle);
}

.step-item:hover {
	background: var(--fxr-border-subtle);
}

.step-order {
	font-weight: bold;
	margin-right: 12px;
	color: var(--fxr-text-soft);
	font-size: 12px;
}

.step-info {
	flex: 1;
}

.step-action {
	font-weight: 600;
	font-size: 13px;
}

.step-meta {
	font-size: 11px;
	color: var(--fxr-text-soft);
	display: flex;
	gap: 8px;
}

.status-success {
	border-left: 4px solid var(--green-500);
}

.status-error {
	border-left: 4px solid var(--red-500);
	background: var(--red-50);
}

.step-chevron {
	color: var(--fxr-text-faint);
	font-size: 12px;
}

.detail-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.status-badge {
	font-size: 10px;
	padding: 2px 8px;
	border-radius: 10px;
	text-transform: uppercase;
	font-weight: bold;
}

.status-badge.success {
	background: var(--green-100);
	color: var(--green-700);
}

.status-badge.error {
	background: var(--red-100);
	color: var(--red-700);
}

.error-box pre {
	background: var(--red-50);
	color: var(--red-700);
	padding: 10px;
	border-radius: 4px;
	font-size: 11px;
	white-space: pre-wrap;
}

.data-section label {
	font-size: 12px;
	font-weight: bold;
	color: var(--fxr-text-soft);
	display: block;
	margin-bottom: 4px;
}

.data-section pre {
	background: var(--fxr-surface-2);
	padding: 10px;
	border-radius: 4px;
	font-size: 11px;
	max-height: 300px;
	overflow: auto;
}
</style>
