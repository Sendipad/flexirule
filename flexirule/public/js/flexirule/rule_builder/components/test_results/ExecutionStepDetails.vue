<template>
	<div class="execution-step-details" :class="[layout, { 'is-error': step.status === 'error' }]">
		<div class="details-header">
			<div class="header-left">
				<span class="step-badge">#{{ step.order }}</span>
				<h5>{{ step.action }}</h5>
			</div>
			<button class="btn-close" @click="$emit('close')">&times;</button>
		</div>

		<div class="details-content">
			<!-- Error Section -->
			<div v-if="step.error" class="detail-section error-section">
				<div class="section-title text-danger">
					<i class="fa fa-exclamation-triangle"></i> {{ __("Error Details") }}
				</div>
				<pre class="error-pre">{{ step.error }}</pre>
			</div>

			<!-- Evaluation Details -->
			<div v-if="hasEvaluation" class="detail-section">
				<div class="section-title">{{ __("Evaluation Details") }}</div>
				<div class="evaluation-box">
					<div
						v-if="step.type === 'Condition' || step.type === 'Switch'"
						class="eval-row"
					>
						<span class="eval-label">{{ __("Result") }}:</span>
						<span :class="['eval-value', step.result ? 'text-success' : 'text-danger']">
							{{ step.result ? __("True") : __("False") }}
						</span>
					</div>
					<div
						v-if="step.input && (step.input.expression || step.input.condition_json)"
						class="eval-row"
					>
						<span class="eval-label">{{ __("Expression") }}:</span>
						<code class="eval-code">{{
							step.input.expression || step.input.condition_json
						}}</code>
					</div>
				</div>
			</div>

			<!-- Context Changes -->
			<div v-if="hasChanges" class="detail-section">
				<div class="section-title">{{ __("Context Changes") }}</div>
				<div class="context-diff">
					<div v-for="(change, key) in step.context_diff" :key="key" class="diff-item">
						<span class="diff-key">{{ key }}:</span>
						<span class="diff-old">{{ formatData(change.from) }}</span>
						<i class="fa fa-long-arrow-right"></i>
						<span class="diff-new">{{ formatData(change.to) }}</span>
					</div>
				</div>
			</div>

			<!-- Payload Data -->
			<div class="detail-section">
				<div class="section-title collapsible-trigger" @click="showPayload = !showPayload">
					{{ __("Payload Data") }}
					<i :class="['fa', showPayload ? 'fa-chevron-down' : 'fa-chevron-right']"></i>
				</div>
				<div v-if="showPayload" class="payload-container">
					<div v-if="step.input" class="payload-group">
						<label>{{ __("Input") }}</label>
						<pre>{{ formatData(step.input) }}</pre>
					</div>
					<div v-if="step.output || step.result" class="payload-group">
						<label>{{ __("Output / Result") }}</label>
						<pre>{{ formatData(step.output || step.result) }}</pre>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
	step: {
		type: Object,
		required: true,
	},
	layout: {
		type: String, // 'bottom' or 'right'
		default: "bottom",
	},
});

defineEmits(["close"]);

const showPayload = ref(false);

const hasEvaluation = computed(() => {
	const isEvalType = props.step.type === "Condition" || props.step.type === "Switch";
	const hasExpression = props.step.input?.expression || props.step.input?.condition_json;
	const hasResult = props.step.result !== undefined;
	return isEvalType && (hasExpression || hasResult);
});

const hasChanges = computed(() => {
	return props.step.context_diff && Object.keys(props.step.context_diff).length > 0;
});

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
.execution-step-details {
	display: flex;
	flex-direction: column;
	background: var(--fxr-surface);
	border: 1px solid var(--fxr-border);
	box-shadow: var(--fxr-shadow-lg);
	z-index: 1000;
	overflow: hidden;
}

[data-theme="dark"] .execution-step-details {
	background: var(--fxr-bg-card);
	border-color: rgba(255, 255, 255, 0.1);
}

.execution-step-details.bottom {
	border-radius: var(--fxr-radius-lg) var(--fxr-radius-lg) 0 0;
	max-height: 50vh;
	width: 100%;
}

.execution-step-details.right {
	border-radius: var(--fxr-radius-lg) 0 0 var(--fxr-radius-lg);
	height: 100%;
	width: 320px;
}

.details-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 12px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface-2);
}

.header-left {
	display: flex;
	align-items: center;
	gap: 10px;
}

.header-left h5 {
	margin: 0;
	font-size: 14px;
	font-weight: 700;
}

.step-badge {
	background: var(--fxr-accent);
	color: #fff;
	font-size: 10px;
	font-weight: 800;
	padding: 2px 8px;
	border-radius: 10px;
}

.btn-close {
	background: none;
	border: none;
	font-size: 20px;
	line-height: 1;
	cursor: pointer;
	color: var(--fxr-text-soft);
}

.details-content {
	flex: 1;
	overflow-y: auto;
	padding: 12px;
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.detail-section {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.section-title {
	font-size: 11px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: var(--fxr-text-soft);
	display: flex;
	align-items: center;
	gap: 6px;
}

.collapsible-trigger {
	cursor: pointer;
	user-select: none;
}

.collapsible-trigger:hover {
	color: var(--fxr-accent);
}

.error-pre {
	background: var(--red-50);
	color: var(--red-700);
	padding: 12px;
	border-radius: var(--fxr-radius-md);
	font-size: 11px;
	white-space: pre-wrap;
	border: 1px solid var(--red-100);
}

[data-theme="dark"] .error-pre {
	background: rgba(220, 38, 38, 0.1);
	border-color: rgba(220, 38, 38, 0.2);
}

.evaluation-box {
	background: var(--fxr-surface-2);
	padding: 12px;
	border-radius: var(--fxr-radius-md);
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.eval-row {
	display: flex;
	gap: 8px;
	font-size: 12px;
}

.eval-label {
	font-weight: 600;
	color: var(--fxr-text-soft);
}

.eval-code {
	font-family: var(--font-mono);
	background: var(--fxr-surface-soft);
	padding: 2px 4px;
	border-radius: 4px;
	word-break: break-all;
}

.payload-container {
	display: flex;
	flex-direction: column;
	gap: 12px;
	padding-left: 8px;
	border-left: 2px solid var(--fxr-border-subtle);
}

.payload-group label {
	font-size: 10px;
	font-weight: 700;
	color: var(--fxr-text-faint);
	margin-bottom: 4px;
	display: block;
}

.payload-group pre {
	margin: 0;
	font-size: 11px;
	background: var(--fxr-surface-soft);
	padding: 10px;
	border-radius: var(--fxr-radius-md);
	max-height: 200px;
	overflow: auto;
}

.context-diff {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.diff-item {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 12px;
	background: var(--fxr-surface-2);
	padding: 6px 10px;
	border-radius: 6px;
}

.diff-key {
	font-weight: 700;
	color: var(--fxr-text-soft);
}

.diff-old {
	color: var(--red-600);
	text-decoration: line-through;
	opacity: 0.7;
}

.diff-new {
	color: var(--green-600);
	font-weight: 600;
}
</style>
