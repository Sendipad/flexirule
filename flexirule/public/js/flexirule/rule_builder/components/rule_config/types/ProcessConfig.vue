<template>
	<div class="process-config-wrapper">
		<div v-if="error" class="error-alert m-4">
			<i class="fa fa-exclamation-triangle"></i>
			<div class="error-content">
				<span class="error-title">{{ __("Configuration Error") }}</span>
				<span class="error-msg">{{ error }}</span>
			</div>
		</div>

		<div v-else-if="!engine && needsSetup" class="empty-mode-state">
			<i class="fa fa-cogs opacity-20 mb-3" style="font-size: 32px"></i>
			<h6 class="fw-bold">{{ __("Process Configuration") }}</h6>
			<p class="text-muted small">
				{{
					__(
						"Select a Process and Operation in the Setup panel to configure this action."
					)
				}}
			</p>
			<div class="setup-summary mt-4">
				<div class="summary-item">
					<span class="label">{{ __("Process") }}</span>
					<span class="value">{{ node.data?.process_name || __("Not selected") }}</span>
				</div>
				<div class="summary-item">
					<span class="label">{{ __("Operation") }}</span>
					<span class="value">{{ node.data?.operation || __("Not selected") }}</span>
				</div>
			</div>
		</div>

		<div v-else-if="!engine && !error" class="d-flex justify-content-center p-5">
			<div class="spinner-border text-primary opacity-50"></div>
		</div>

		<template v-else-if="engine">
			<div class="config-header px-4 py-3">
				<div class="d-flex align-items-center gap-3">
					<div class="header-icon-box">
						<i class="fa fa-terminal"></i>
					</div>
					<div>
						<h6 class="mb-0 fw-bold">{{ __("Operation Settings") }}</h6>
						<p class="text-muted extra-small mb-0">
							{{ engine.process_name }} › {{ engine.operation_name }}
						</p>
					</div>
				</div>
				<div class="view-toggle">
					<button
						class="toggle-btn"
						:class="{ active: view === 'form' }"
						@click="view = 'form'"
						:title="__('Form View')"
					>
						<i class="fa fa-list"></i>
					</button>
					<button
						class="toggle-btn"
						:class="{ active: view === 'visual' }"
						@click="view = 'visual'"
						:title="__('Visual Mapper')"
					>
						<i class="fa fa-exchange"></i>
					</button>
				</div>
			</div>

			<div v-show="view === 'form'" class="form-container">
				<SchemaRenderer :fields="engine.normalized_fields" :engine="engine" />
			</div>

			<div v-if="view === 'visual'" class="visual-container px-4">
				<TransformControl
					:modelValue="visualMappings"
					:sourceSchema="sourceSchema"
					:targetSchema="targetSchema"
					@update:modelValue="update_visual_mappings"
				/>
			</div>

			<div v-if="engine.normalized_fields.length === 0" class="empty-state py-5">
				<i class="fa fa-info-circle opacity-20 mb-3" style="font-size: 32px"></i>
				<p class="text-muted">
					{{ __("No configuration fields found for this operation.") }}
				</p>
			</div>
		</template>
	</div>
</template>

<script setup>
import { onMounted, ref, reactive, watch, computed } from "vue";
import ProcessEngine from "../engines/ProcessEngine.js";
import SchemaRenderer from "../SchemaRenderer.vue";
import { useStore } from "../../../stores";
import TransformControl from "../../../controls/TransformControl.vue";

const props = defineProps({
	node: Object,
});

const store = useStore();
const engine = ref(null);
const error = ref(null);
const view = ref("form");

const needsSetup = computed(() => {
	return !props.node?.data?.process_name || !props.node?.data?.operation;
});

const sourceSchema = computed(() => {
	const vars = engine.value?.available_variables || [];
	return vars.map((v) => ({
		label: v.label || v.value,
		value: v.value,
		fieldtype: v.fieldtype || "Data",
	}));
});

const targetSchema = computed(() => {
	const fields = engine.value?.normalized_fields || [];
	return fields.map((f) => ({
		label: f.label || f.fieldname,
		value: f.fieldname,
		fieldtype: f.fieldtype,
	}));
});

const visualMappings = computed(() => {
	const config = engine.value?.config || {};
	const mappings = [];

	Object.entries(config).forEach(([key, val]) => {
		if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
			const path = val.slice(1, -1);
			mappings.push({
				source: path,
				target: key,
				source_label: path,
				target_label: key,
			});
		}
	});

	return mappings;
});

function update_visual_mappings(mappings) {
	const config = engine.value.config;

	const previouslyMapped = Object.keys(config).filter((key) => {
		const val = config[key];
		return typeof val === "string" && val.startsWith("{") && val.endsWith("}");
	});

	previouslyMapped.forEach((key) => delete config[key]);

	mappings.forEach((m) => {
		config[m.target] = `{${m.source}}`;
	});
}

let initCounter = 0;

async function initEngine() {
	if (!props.node?.data?.process_name || !props.node?.data?.operation) {
		if (engine.value && typeof engine.value.dispose === "function") {
			engine.value.dispose();
		}
		engine.value = null;
		error.value = null;
		return;
	}

	error.value = null;
	const currentInitId = ++initCounter;

	if (engine.value && typeof engine.value.dispose === "function") {
		engine.value.dispose();
	}
	engine.value = null;

	try {
		let configValue = props.node.data.config || {};
		if (typeof configValue === "string") {
			try {
				configValue = JSON.parse(configValue);
			} catch (e) {
				configValue = {};
			}
		}

		const config = reactive(configValue);

		const newEngine = new ProcessEngine({
			process_name: props.node.data.process_name,
			operation_name: props.node.data.operation,
			config: config,
			document_type: store.rule_doc?.document_type,
			doc_meta: store.raw_meta,
			available_variables: await store.getAvailableVariables(props.node.id),
		});

		await newEngine.init();

		if (currentInitId !== initCounter) return;

		engine.value = newEngine;
		props.node.data.config = config;
	} catch (err) {
		if (currentInitId === initCounter) {
			console.error("ProcessConfig: Engine initialization failed", err);
			error.value = err.message || "Unknown error during initialization";
		}
	}
}

onMounted(() => {
	initEngine();
});

watch(
	() => [props.node.data?.process_name, props.node.data?.operation],
	() => {
		initEngine();
	}
);

async function validate() {
	if (!engine.value) return { valid: true };
	return await engine.value.validate();
}

defineExpose({
	validate,
});
</script>

<style scoped>
.process-config-wrapper {
	min-height: 200px;
}

.empty-mode-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	padding: 40px 20px;
}

.setup-summary {
	background: var(--fr-bg-muted);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	padding: 16px;
	width: 100%;
	max-width: 400px;
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.summary-item {
	display: flex;
	justify-content: space-between;
	align-items: center;
	font-size: 13px;
}

.summary-item .label {
	color: var(--fr-text-muted);
	font-weight: 500;
}

.summary-item .value {
	color: var(--fr-text);
	font-weight: 600;
}

.config-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	border-bottom: 1px solid var(--fr-border-subtle);
}

.header-icon-box {
	width: 36px;
	height: 36px;
	background: var(--fr-primary-subtle);
	color: var(--fr-primary);
	border-radius: var(--fr-radius-md);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 16px;
}

.view-toggle {
	display: flex;
	background: var(--fr-bg-muted);
	padding: 3px;
	border-radius: 8px;
}

.toggle-btn {
	width: 32px;
	height: 32px;
	border: none;
	background: transparent;
	color: var(--fr-text-muted);
	border-radius: 6px;
	cursor: pointer;
	transition: all 0.2s;
	display: flex;
	align-items: center;
	justify-content: center;
}

.toggle-btn.active {
	background: var(--fr-bg-surface);
	color: var(--fr-primary);
	box-shadow: var(--fr-shadow-sm);
}

.form-container {
	padding: 20px;
}

.extra-small {
	font-size: 11px;
}

.error-alert {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	padding: 16px;
	background: #fef2f2;
	border: 1px solid #fecaca;
	border-radius: var(--fr-radius-lg);
	color: #b91c1c;
}

.error-content {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.error-title {
	font-weight: 700;
	font-size: 14px;
}

.error-msg {
	font-size: 13px;
	line-height: 1.4;
}

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
}
</style>
