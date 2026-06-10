<template>
	<div class="debug-workspace-sidebar" :class="{ 'is-mobile': isMobile }">
		<div class="debug-sidebar-header">
			<div class="header-title">
				<i class="fa fa-bug text-primary"></i>
				<span>{{ __("Debug Session") }}</span>
			</div>
			<div class="header-actions">
				<button
					class="btn btn-xs btn-default"
					@click="exportDebugJSON"
					:title="__('Export Debug JSON')"
				>
					<i class="fa fa-download"></i>
				</button>
				<button class="btn btn-xs btn-default" @click="closeSidebar" :title="__('Close')">
					<i class="fa fa-times"></i>
				</button>
			</div>
		</div>

		<div class="debug-sidebar-content" v-if="uiStore.debug_execution_steps.length">
			<div class="debug-summary-card">
				<div class="summary-info">
					<div class="summary-item">
						<span class="label">{{ __("Status") }}</span>
						<span :class="['status-badge', uiStore.debug_final_status?.toLowerCase()]">
							{{ uiStore.debug_final_status || __("Unknown") }}
						</span>
					</div>
					<div class="summary-item">
						<span class="label">{{ __("Steps") }}</span>
						<span class="value">{{ uiStore.debug_execution_steps.length }}</span>
					</div>
					<div class="summary-item" v-if="totalDuration">
						<span class="label">{{ __("Duration") }}</span>
						<span class="value">{{ totalDuration }}ms</span>
					</div>
				</div>
				<div class="summary-actions mt-3">
					<button
						v-if="uiStore.last_execution_id"
						class="btn btn-xs btn-default btn-block mb-2"
						@click="openExecutionLog"
					>
						<i class="fa fa-external-link mr-1"></i> {{ __("Open Execution Log") }}
					</button>
					<button class="btn btn-xs btn-primary btn-block" @click="runDebug">
						<i class="fa fa-play mr-1"></i> {{ __("Rerun Debug") }}
					</button>
				</div>
			</div>

			<div class="debug-steps-list">
				<div
					v-for="(step, index) in uiStore.debug_execution_steps"
					:key="`${step.node_id}-${step.order}`"
					class="debug-step-item"
					:class="{
						expanded: expandedSteps[index],
						active: uiStore.selected_id === step.node_id,
						'has-error': step.status === 'error',
					}"
				>
					<div class="step-main" @click="toggleStep(index, step.node_id)">
						<div class="step-status-icon">
							<i
								v-if="step.status === 'success'"
								class="fa fa-check-circle text-success"
							></i>
							<i
								v-else-if="step.status === 'error'"
								class="fa fa-times-circle text-danger"
							></i>
							<i v-else class="fa fa-circle-o text-muted"></i>
						</div>
						<div class="step-info">
							<div class="step-name">{{ step.action }}</div>
							<div class="step-meta">
								<span class="step-order">#{{ step.order }}</span>
								<span class="step-duration" v-if="step.duration_ms"
									>{{ step.duration_ms }}ms</span
								>
								<span class="step-offset" v-if="getOffset(step.node_id)"
									>+{{ getOffset(step.node_id) }}ms</span
								>
							</div>
						</div>
						<div class="step-toggle">
							<i
								:class="[
									'fa',
									expandedSteps[index] ? 'fa-chevron-down' : 'fa-chevron-right',
								]"
							></i>
						</div>
					</div>

					<div v-if="expandedSteps[index]" class="step-details">
						<div v-if="step.error" class="step-error-message">
							{{ step.error }}
						</div>

						<div
							v-if="getStepTrace(step.node_id)?.action_type === 'Condition'"
							class="condition-decision-panel"
						>
							<div class="decision-header">
								<span class="decision-title">{{ __("Condition Result") }}</span>
								<span
									:class="[
										'decision-badge',
										getStepTrace(step.node_id).condition_result
											? 'true'
											: 'false',
									]"
								>
									{{
										getStepTrace(step.node_id).condition_result
											? "TRUE"
											: "FALSE"
									}}
								</span>
							</div>
							<div class="decision-body">
								<div class="expr-label">{{ __("Expression") }}</div>
								<div class="expr-code">
									<code>{{
										getStepTrace(step.node_id).condition_expression ||
										__("Inline Condition")
									}}</code>
								</div>
								<div class="next-path-label mt-2">
									{{ __("Next Path:") }}
									<strong>{{
										getStepTrace(step.node_id).condition_result ? "YES" : "NO"
									}}</strong>
								</div>
							</div>
						</div>

						<div class="details-tabs">
							<button
								v-for="tab in availableTabs(step)"
								:key="tab.id"
								class="tab-btn"
								:class="{ active: activeTabs[index] === tab.id }"
								@click="activeTabs[index] = tab.id"
							>
								{{ tab.label }}
								<span
									v-if="tab.id === 'diffs' && getMutationCount(step.node_id)"
									class="tab-badge"
								>
									{{ getMutationCount(step.node_id) }}
								</span>
							</button>
						</div>

						<div class="tab-content">
							<!-- Inputs -->
							<div v-if="activeTabs[index] === 'inputs'" class="data-view">
								<pre v-if="getStepTrace(step.node_id)?.input_snapshot">{{
									formatJSON(getStepTrace(step.node_id).input_snapshot)
								}}</pre>
								<div v-else class="text-muted small">{{ __("No input data") }}</div>
							</div>

							<!-- Outputs -->
							<div v-if="activeTabs[index] === 'outputs'" class="data-view">
								<pre v-if="getStepTrace(step.node_id)?.output_snapshot">{{
									formatJSON(getStepTrace(step.node_id).output_snapshot)
								}}</pre>
								<div v-else class="text-muted small">
									{{ __("No output data") }}
								</div>
							</div>

							<!-- Diffs -->
							<div v-if="activeTabs[index] === 'diffs'" class="diff-view">
								<!-- Variable Mutation Highlighting -->
								<div v-if="hasVarDiff(step.node_id)" class="mutation-summary mb-3">
									<div class="mutation-summary-title">
										{{ __("Variables Changed") }} ({{
											getVarDiffs(step.node_id).length
										}})
									</div>
									<div class="mutation-tags">
										<span
											v-for="diff in getVarDiffs(step.node_id)"
											:key="diff.field"
											class="mutation-tag"
										>
											<i class="fa fa-check text-success mr-1"></i>
											{{ diff.field }}
										</span>
									</div>
								</div>

								<!-- Document Diffs -->
								<div v-if="hasDocDiff(step.node_id)" class="diff-section">
									<div class="diff-title">{{ __("Document Changes") }}</div>
									<div
										v-for="diff in getDocDiffs(step.node_id)"
										:key="diff.field"
										class="diff-row"
									>
										<div class="field-name">{{ diff.field }}</div>
										<div class="diff-values">
											<span class="old-val">{{ formatValue(diff.old) }}</span>
											<i class="fa fa-long-arrow-right mx-2"></i>
											<span class="new-val">{{ formatValue(diff.new) }}</span>
										</div>
									</div>
								</div>

								<!-- Variable Diffs -->
								<div v-if="hasVarDiff(step.node_id)" class="diff-section mt-3">
									<div class="diff-title">{{ __("Variable Details") }}</div>
									<div
										v-for="diff in getVarDiffs(step.node_id)"
										:key="diff.field"
										class="diff-row"
									>
										<div class="field-name">{{ diff.field }}</div>
										<div class="diff-values">
											<span class="old-val">{{ formatValue(diff.old) }}</span>
											<i class="fa fa-long-arrow-right mx-2"></i>
											<span class="new-val">{{ formatValue(diff.new) }}</span>
										</div>
									</div>
								</div>

								<div
									v-if="!hasDocDiff(step.node_id) && !hasVarDiff(step.node_id)"
									class="text-muted small"
								>
									{{ __("No mutations detected in this step") }}
								</div>
							</div>

							<!-- Context -->
							<div v-if="activeTabs[index] === 'context'" class="data-view">
								<div class="context-search mb-2">
									<div class="input-group input-group-sm">
										<div class="input-group-prepend">
											<span class="input-group-text"
												><i class="fa fa-search"></i
											></span>
										</div>
										<input
											type="text"
											class="form-control"
											v-model="contextSearchQuery"
											:placeholder="__('Search context...')"
										/>
									</div>
								</div>
								<div class="context-section">
									<div class="context-title">vars</div>
									<pre>{{ formatJSON(filteredVars(step.node_id)) }}</pre>
								</div>
								<div class="context-section">
									<div class="context-title">doc</div>
									<pre>{{ formatJSON(filteredDoc(step.node_id)) }}</pre>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<div class="debug-empty-state" v-else>
			<div class="empty-icon">
				<i class="fa fa-terminal"></i>
			</div>
			<div class="empty-text">
				{{ __("No active debug session") }}
			</div>
			<div class="empty-hint">
				{{ __("Run 'Debug Rule' to see execution details here.") }}
			</div>
			<button class="btn btn-sm btn-primary mt-4" @click="runDebug">
				{{ __("Debug Rule") }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, watch } from "vue";
import { useUIStore } from "../stores/useUIStore";

const uiStore = useUIStore();
const expandedSteps = reactive({});
const activeTabs = reactive({});
const isMobile = ref(window.innerWidth < 768);
const contextSearchQuery = ref("");

const totalDuration = computed(() => {
	if (!uiStore.debug_execution_steps.length) return 0;
	return uiStore.debug_execution_steps
		.reduce((acc, s) => acc + (s.duration_ms || 0), 0)
		.toFixed(1);
});

function toggleStep(index, nodeId) {
	expandedSteps[index] = !expandedSteps[index];
	if (expandedSteps[index]) {
		uiStore.selected_id = nodeId;
		if (!activeTabs[index]) {
			activeTabs[index] = "inputs";
		}
	}
}

function availableTabs(step) {
	const tabs = [
		{ id: "inputs", label: __("Inputs") },
		{ id: "outputs", label: __("Outputs") },
		{ id: "diffs", label: __("Diffs") },
		{ id: "context", label: __("Context") },
	];
	return tabs;
}

function getStepTrace(nodeId) {
	if (!uiStore.debug_trace || !uiStore.debug_trace.steps) return null;
	return uiStore.debug_trace.steps.find((s) => s.action_id === nodeId);
}

function getOffset(nodeId) {
	if (!uiStore.debug_trace || !uiStore.debug_trace.timeline) return null;
	const entry = uiStore.debug_trace.timeline.find((t) => t.action_id === nodeId);
	return entry ? entry.offset_ms : null;
}

function formatJSON(val) {
	if (!val) return "";
	return JSON.stringify(val, null, 2);
}

function formatValue(val) {
	if (val === null || val === undefined) return "null";
	if (val === "") return '""';
	if (typeof val === "object") {
		if (Array.isArray(val)) return `[${val.length} items]`;
		return "{...}";
	}
	return String(val);
}

function getDocDiffs(nodeId) {
	const trace = getStepTrace(nodeId);
	if (!trace || !trace.doc_before || !trace.doc_after) return [];

	const diffs = [];
	const before = trace.doc_before;
	const after = trace.doc_after;

	const allKeys = new Set([...Object.keys(before), ...Object.keys(after)]);
	for (const key of allKeys) {
		if (["modified", "modified_by"].includes(key)) continue;
		if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) {
			diffs.push({
				field: key,
				old: before[key],
				new: after[key],
			});
		}
	}
	return diffs;
}

function hasDocDiff(nodeId) {
	return getDocDiffs(nodeId).length > 0;
}

function getVarDiffs(nodeId) {
	const trace = getStepTrace(nodeId);
	if (!trace || !trace.vars_before || !trace.vars_after) return [];

	const diffs = [];
	const before = trace.vars_before;
	const after = trace.vars_after;

	const allKeys = new Set([...Object.keys(before), ...Object.keys(after)]);
	for (const key of allKeys) {
		if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) {
			diffs.push({
				field: key,
				old: before[key],
				new: after[key],
			});
		}
	}
	return diffs;
}

function hasVarDiff(nodeId) {
	return getVarDiffs(nodeId).length > 0;
}

function getMutationCount(nodeId) {
	return getDocDiffs(nodeId).length + getVarDiffs(nodeId).length;
}

function filteredVars(nodeId) {
	const vars = getStepTrace(nodeId)?.vars_before || {};
	if (!contextSearchQuery.value) return vars;
	const filtered = {};
	const q = contextSearchQuery.value.toLowerCase();
	Object.keys(vars).forEach((k) => {
		if (k.toLowerCase().includes(q)) filtered[k] = vars[k];
	});
	return filtered;
}

function filteredDoc(nodeId) {
	const doc = getStepTrace(nodeId)?.doc_before || {};
	if (!contextSearchQuery.value) return doc;
	const filtered = {};
	const q = contextSearchQuery.value.toLowerCase();
	Object.keys(doc).forEach((k) => {
		if (k.toLowerCase().includes(q)) filtered[k] = doc[k];
	});
	return filtered;
}

function closeSidebar() {
	uiStore.show_debug_sidebar = false;
}

function runDebug() {
	window.fxrRuleBuilder?.show_debug_dialog?.();
}

function openExecutionLog() {
	if (uiStore.last_execution_id) {
		frappe.set_route("Form", "Rule Execution Log", uiStore.last_execution_id);
	}
}

function exportDebugJSON() {
	const data = {
		execution_id: uiStore.last_execution_id,
		rule: uiStore.debug_context.rule_name,
		timestamp: new Date().toISOString(),
		summary: {
			status: uiStore.debug_final_status,
			total_steps: uiStore.debug_execution_steps.length,
			duration_ms: totalDuration.value,
		},
		trace: uiStore.debug_trace,
	};
	const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = `debug-session-${uiStore.last_execution_id || "export"}.json`;
	a.click();
	URL.revokeObjectURL(url);
}

// Watch for new debug sessions to reset expansion
watch(
	() => uiStore.debug_execution_steps,
	(newSteps) => {
		Object.keys(expandedSteps).forEach((k) => delete expandedSteps[k]);
		Object.keys(activeTabs).forEach((k) => delete activeTabs[k]);

		// Auto expand first step or first error
		if (newSteps && newSteps.length) {
			const firstError = newSteps.findIndex((s) => s.status === "error");
			const indexToExpand = firstError !== -1 ? firstError : 0;
			expandedSteps[indexToExpand] = true;
			activeTabs[indexToExpand] = firstError !== -1 ? "outputs" : "inputs";
		}
	},
	{ deep: true }
);
</script>

<style scoped>
.debug-workspace-sidebar {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: var(--fxr-surface);
	color: var(--fxr-text);
}

.debug-sidebar-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 12px 16px;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.header-title {
	display: flex;
	align-items: center;
	gap: 8px;
	font-weight: 600;
	font-size: 14px;
}

.debug-sidebar-content {
	flex: 1;
	overflow-y: auto;
	padding: 12px;
}

.debug-summary-card {
	background: var(--fxr-surface-soft);
	border-radius: 8px;
	padding: 12px;
	margin-bottom: 16px;
	border: 1px solid var(--fxr-border-subtle);
}

.summary-info {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 8px;
}

.summary-item {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.summary-item .label {
	font-size: 10px;
	text-transform: uppercase;
	color: var(--fxr-text-soft);
	font-weight: 700;
}

.summary-item .value {
	font-size: 13px;
	font-weight: 600;
}

.status-badge {
	font-size: 10px;
	font-weight: 700;
	padding: 2px 8px;
	border-radius: 12px;
	display: inline-block;
	width: fit-content;
}

.status-badge.success {
	background: var(--green-100);
	color: var(--green-700);
}
.status-badge.failed {
	background: var(--red-100);
	color: var(--red-700);
}

.debug-steps-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.debug-step-item {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 8px;
	overflow: hidden;
	transition: all 0.2s ease;
}

.debug-step-item.active {
	border-color: var(--fxr-accent);
	box-shadow: 0 0 0 1px var(--fxr-accent);
}

.debug-step-item.has-error {
	border-color: var(--red-200);
}

.step-main {
	display: flex;
	align-items: center;
	padding: 10px;
	cursor: pointer;
	gap: 12px;
}

.step-main:hover {
	background: var(--fxr-surface-soft);
}

.step-status-icon {
	font-size: 16px;
	display: flex;
	align-items: center;
}

.step-info {
	flex: 1;
	min-width: 0;
}

.step-name {
	font-size: 13px;
	font-weight: 500;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.step-meta {
	display: flex;
	gap: 8px;
	font-size: 10px;
	color: var(--fxr-text-soft);
}

.step-toggle {
	color: var(--fxr-text-faint);
}

.step-details {
	border-top: 1px solid var(--fxr-border-subtle);
	background: #fff;
}

.step-error-message {
	padding: 8px 12px;
	background: var(--red-50);
	color: var(--red-700);
	font-size: 11px;
	border-bottom: 1px solid var(--red-100);
	white-space: pre-wrap;
	word-break: break-all;
}

.condition-decision-panel {
	padding: 10px 12px;
	background: #fdfcf6;
	border-bottom: 1px solid #f9f2d1;
}

.decision-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 8px;
}

.decision-title {
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	color: #856404;
}

.decision-badge {
	font-size: 10px;
	font-weight: 800;
	padding: 2px 8px;
	border-radius: 4px;
}

.decision-badge.true {
	background: #d4edda;
	color: #155724;
}
.decision-badge.false {
	background: #f8d7da;
	color: #721c24;
}

.expr-label {
	font-size: 10px;
	color: var(--fxr-text-soft);
	margin-bottom: 4px;
}

.expr-code code {
	display: block;
	padding: 6px;
	background: #fff;
	border: 1px solid #f9f2d1;
	border-radius: 4px;
	font-family: var(--font-mono);
	font-size: 11px;
	color: #1a1a1a;
}

.details-tabs {
	display: flex;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface-soft);
}

.tab-btn {
	flex: 1;
	border: none;
	background: none;
	padding: 8px 4px;
	font-size: 11px;
	font-weight: 600;
	color: var(--fxr-text-soft);
	cursor: pointer;
	border-bottom: 2px solid transparent;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 4px;
}

.tab-btn:hover {
	color: var(--fxr-text);
}

.tab-btn.active {
	color: var(--fxr-accent);
	border-bottom-color: var(--fxr-accent);
}

.tab-badge {
	background: var(--fxr-accent);
	color: white;
	font-size: 9px;
	padding: 1px 5px;
	border-radius: 10px;
	min-width: 16px;
}

.tab-content {
	padding: 10px;
	max-height: 440px;
	overflow-y: auto;
}

.data-view pre {
	margin: 0;
	font-family: var(--font-mono);
	font-size: 11px;
	background: #f8fafc;
	padding: 8px;
	border-radius: 4px;
	white-space: pre-wrap;
	word-break: break-all;
}

.mutation-summary-title {
	font-size: 11px;
	font-weight: 700;
	color: var(--fxr-text-soft);
	margin-bottom: 6px;
	text-transform: uppercase;
}

.mutation-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
}

.mutation-tag {
	font-size: 10px;
	background: #f1f5f9;
	padding: 2px 8px;
	border-radius: 4px;
	color: #475569;
	font-weight: 500;
}

.diff-section {
	margin-bottom: 12px;
}

.diff-title {
	font-size: 11px;
	font-weight: 700;
	color: var(--fxr-text-soft);
	margin-bottom: 8px;
	text-transform: uppercase;
}

.diff-row {
	display: flex;
	flex-direction: column;
	gap: 4px;
	margin-bottom: 8px;
	padding: 6px;
	background: #f8fafc;
	border-radius: 4px;
}

.field-name {
	font-size: 11px;
	font-weight: 600;
	font-family: var(--font-mono);
	color: var(--fxr-accent);
}

.diff-values {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 4px;
	font-size: 11px;
}

.old-val {
	color: var(--red-600);
	text-decoration: line-through;
	opacity: 0.8;
}

.new-val {
	color: var(--green-600);
	font-weight: 600;
}

.context-section {
	margin-bottom: 12px;
}

.context-title {
	font-size: 10px;
	font-weight: 700;
	font-family: var(--font-mono);
	color: var(--fxr-text-faint);
	margin-bottom: 4px;
}

.debug-empty-state {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 32px;
	text-align: center;
}

.empty-icon {
	font-size: 48px;
	color: var(--fxr-text-faint);
	margin-bottom: 16px;
}

.empty-text {
	font-size: 16px;
	font-weight: 600;
	margin-bottom: 8px;
}

.empty-hint {
	font-size: 13px;
	color: var(--fxr-text-soft);
}
</style>
