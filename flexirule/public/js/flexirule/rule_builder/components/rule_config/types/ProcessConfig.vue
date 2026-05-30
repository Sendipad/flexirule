<template>
	<div class="process-config-wrapper">
		<div v-if="error" class="alert alert-danger m-3">
			<i class="fa fa-exclamation-triangle"></i> {{ error }}
		</div>
		<div v-else-if="!engine && needsSetup" class="p-4 text-center text-muted">
			<i class="fa fa-info-circle fa-2x mb-3 d-block"></i>
			<p class="mb-1 fw-bold">{{ __("Process Configuration") }}</p>
			<p class="small">
				{{
					__(
						"Select a Process and Operation in the Setup panel to configure this action."
					)
				}}
			</p>
			<div class="small mt-2 p-2 border rounded bg-light">
				<span v-if="!node.data?.process_name">{{ __("Process: Not selected") }}</span>
				<span v-else>{{ __("Process:") }} {{ node.data.process_name }}</span>
				<br />
				<span v-if="!node.data?.operation">{{ __("Operation: Not selected") }}</span>
				<span v-else>{{ __("Operation:") }} {{ node.data.operation }}</span>
			</div>
		</div>
		<div v-else-if="!engine && !error" class="d-flex justify-content-center p-5">
			<div class="spinner-border text-primary"></div>
		</div>
		<template v-else-if="engine">
			<div class="d-flex justify-content-between align-items-center mb-2 px-3">
				<h6 class="mb-0 fw-bold">{{ __("Process Configuration") }}</h6>
				<div class="btn-group">
					<button
						class="btn btn-xs"
						:class="view === 'form' ? 'btn-primary' : 'btn-default'"
						@click="view = 'form'"
					>
						<i class="fa fa-list"></i> {{ __("Form") }}
					</button>
					<button
						class="btn btn-xs"
						:class="view === 'visual' ? 'btn-primary' : 'btn-default'"
						@click="view = 'visual'"
					>
						<i class="fa fa-exchange"></i> {{ __("Visual") }}
					</button>
				</div>
			</div>

			<div v-show="view === 'form'">
				<SchemaRenderer :fields="engine.normalized_fields" :engine="engine" />
			</div>

			<div v-if="view === 'visual'" class="px-3">
				<TransformControl
					:modelValue="visualMappings"
					:sourceSchema="sourceSchema"
					:targetSchema="targetSchema"
					@update:modelValue="update_visual_mappings"
				/>
			</div>

			<div v-if="engine.normalized_fields.length === 0" class="p-5 text-center text-muted">
				<p>{{ __("No configuration fields found for this operation.") }}</p>
				<div class="small mt-2 p-2 border rounded bg-light text-left">
					<code>Process: {{ node.data?.process_name }}</code
					><br />
					<code>Operation: {{ node.data?.operation }}</code>
				</div>
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

	// Identify fields that were previously mapped to variables
	const previouslyMapped = Object.keys(config).filter((key) => {
		const val = config[key];
		return typeof val === "string" && val.startsWith("{") && val.endsWith("}");
	});

	// Clear them
	previouslyMapped.forEach((key) => delete config[key]);

	// Apply new ones
	mappings.forEach((m) => {
		config[m.target] = `{${m.source}}`;
	});
}

let initCounter = 0;

async function initEngine() {
	if (!props.node?.data?.process_name || !props.node?.data?.operation) {
		// Clear any previous engine so we show guidance instead of stale config
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
</style>
