<template>
	<div
		class="transform-control fxr-control"
		ref="containerRef"
		:class="{ 'has-error': showValidation && !isValid }"
		v-fxr-fieldname="df?.fieldname || fieldname || null"
	>
		<div v-if="df?.label" class="fxr-label" :class="{ reqd: df?.reqd }">
			{{ __(df.label) }}
		</div>

		<div class="transform-header">
			<div class="header-left">
				<label class="rm-label-sm">{{ __("Source Data") }}</label>
				<div class="search-box">
					<i class="fa fa-search"></i>
					<input
						type="text"
						v-model="sourceSearch"
						:placeholder="__('Search source...')"
						class="form-control input-xs"
					/>
				</div>
			</div>
			<div class="header-center">
				<button class="btn btn-xs btn-default magic-btn" @click="autoMap">
					<i class="fa fa-magic"></i> {{ __("Auto-map") }}
				</button>
			</div>
			<div class="header-right">
				<label class="rm-label-sm">{{ __("Target Data") }}</label>
				<div class="search-box">
					<i class="fa fa-search"></i>
					<input
						type="text"
						v-model="targetSearch"
						:placeholder="__('Search target...')"
						class="form-control input-xs"
					/>
				</div>
			</div>
		</div>

		<div class="transform-body" ref="bodyRef">
			<!-- SVG Overlay for Lines -->
			<svg class="mapping-lines-svg" :style="svgStyle">
				<path
					v-for="(line, idx) in mappingLines"
					:key="idx"
					:d="line.path"
					class="mapping-line"
					:class="{ active: activeLine === idx }"
					@click="selectMapping(line.mapping)"
				/>
			</svg>

			<!-- Source Column -->
			<div class="transform-col source-col" @scroll="updateLines">
				<div v-for="node in filteredSourceTree" :key="node.path" class="tree-node">
					<TransformNode
						:node="node"
						type="source"
						:is-mapped="isSourceMapped(node.path)"
						:is-expanded="isExpanded(node.path)"
						@connect="onSourceConnect"
						@toggle="toggleNode"
					/>
				</div>
			</div>

			<!-- Target Column -->
			<div class="transform-col target-col" @scroll="updateLines">
				<div v-for="node in filteredTargetTree" :key="node.path" class="tree-node">
					<TransformNode
						:node="node"
						type="target"
						:is-mapped="isTargetMapped(node.path)"
						:is-expanded="isExpanded(node.path)"
						@connect="onTargetConnect"
						@toggle="toggleNode"
					/>
				</div>
			</div>
		</div>

		<!-- Mapping Details / Expression Editor -->
		<div v-if="selectedMapping" class="mapping-details">
			<div class="details-header">
				<h6>{{ __("Edit Mapping") }}</h6>
				<button
					class="btn btn-xs btn-link text-danger"
					@click="removeMapping(selectedMapping)"
				>
					<i class="fa fa-trash"></i>
				</button>
			</div>
			<div class="details-body">
				<div class="mapping-path">
					<code>{{ selectedMapping.source }}</code>
					<i class="fa fa-arrow-right mx-2"></i>
					<code>{{ selectedMapping.target }}</code>
				</div>
				<!-- Future: Add expression editor here -->
			</div>
		</div>

		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{
				__("{0} requires at least one mapping").replace("{0}", df?.label || __("Transform"))
			}}
		</div>

		<div v-if="df?.description" class="fxr-description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from "vue";
import TransformNode from "./TransformNode.vue";
import { useTransformMapper } from "../composables/useTransformMapper.js";

const props = defineProps({
	df: { type: Object, default: null },
	fieldname: String,
	modelValue: { type: Array, default: () => [] },
	sourceSchema: { type: Array, default: () => [] }, // Flat list with dot notation
	targetSchema: { type: Array, default: () => [] }, // Flat list with dot notation
	readOnly: Boolean,
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const bodyRef = ref(null);
const {
	sourceSearch,
	targetSearch,
	activeLine,
	selectedMapping,
	mappingLines,
	svgStyle,
	filteredSourceTree,
	filteredTargetTree,
	mappings,
	updateLines,
	toggleNode,
	isExpanded,
	isSourceMapped,
	isTargetMapped,
	autoExpandMapped,
	autoMap,
} = useTransformMapper(props, emit, bodyRef);

// ── Mapping UX Logic ──────────────────────────────────────────────────────

const connectingSource = ref(null);

function onSourceConnect(node) {
	connectingSource.value = node;
}

function onTargetConnect(node) {
	if (!connectingSource.value) return;

	const newMapping = {
		source: connectingSource.value.path,
		target: node.path,
		source_label: connectingSource.value.label,
		target_label: node.label,
	};

	// Remove existing mapping for this target if it exists
	const filtered = mappings.value.filter((m) => m.target !== node.path);
	mappings.value = [...filtered, newMapping];
	connectingSource.value = null;
	updateLines();
}

function removeMapping(mapping) {
	mappings.value = mappings.value.filter((m) => m !== mapping);
	selectedMapping.value = null;
	updateLines();
}

function selectMapping(mapping) {
	selectedMapping.value = mapping;
}

const isValid = computed(() => {
	if (props.df?.reqd) {
		return mappings.value.length > 0;
	}
	return true;
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(
			__("{0} requires at least one mapping").replace(
				"{0}",
				props.df?.label || __("Transform")
			)
		);
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

// ── Lifecycle ─────────────────────────────────────────────────────────────

let resizeObserver = null;
let mutationObserver = null;

onMounted(() => {
	autoExpandMapped();
	nextTick(() => {
		updateLines();
		resizeObserver = new ResizeObserver(updateLines);
		if (bodyRef.value) resizeObserver.observe(bodyRef.value);

		mutationObserver = new MutationObserver(updateLines);
		if (bodyRef.value) {
			mutationObserver.observe(bodyRef.value, { childList: true, subtree: true });
		}
	});
});

onUnmounted(() => {
	if (resizeObserver) resizeObserver.disconnect();
	if (mutationObserver) mutationObserver.disconnect();
});

watch(
	() => [props.modelValue, sourceSearch.value, targetSearch.value],
	() => {
		nextTick(updateLines);
	},
	{ deep: true }
);
</script>

<style scoped>
.transform-control {
	display: flex;
	flex-direction: column;
	height: 600px;
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 12px;
	position: relative;
	overflow: hidden;
	box-shadow: var(--fxr-shadow-md);
}

.transform-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 16px 20px;
	background-color: var(--fxr-surface-2);
	backdrop-filter: blur(8px);
	border-bottom: 1px solid var(--fxr-border-subtle);
	gap: 24px;
}

.header-left,
.header-right {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.search-box {
	position: relative;
}

.search-box i {
	position: absolute;
	left: 10px;
	top: 50%;
	transform: translateY(-50%);
	color: #94a3b8;
	font-size: 12px;
}

.search-box input {
	padding-left: 28px;
	border-radius: 6px;
	background-color: var(--fxr-bg-input);
	border: 1px solid var(--fxr-border);
	color: var(--fxr-text);
	transition: all 0.2s;
}

.search-box input:focus {
	border-color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-focus);
}

.transform-body {
	flex: 1;
	display: flex;
	position: relative;
	overflow: hidden;
	background-color: var(--fxr-surface-soft);
}

.mapping-lines-svg {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	pointer-events: none;
	z-index: 5;
}

.mapping-line {
	fill: none;
	stroke: var(--fxr-border-strong);
	stroke-width: 2.5;
	pointer-events: stroke;
	cursor: pointer;
	transition:
		stroke 0.2s,
		stroke-width 0.2s;
}

.mapping-line:hover,
.mapping-line.active {
	stroke: var(--fxr-accent);
	stroke-width: 4;
	filter: drop-shadow(0 0 4px var(--fxr-accent-light));
}

.transform-col {
	flex: 1;
	overflow-y: auto;
	padding: 16px;
	z-index: 10;
	scrollbar-width: thin;
}

.source-col {
	border-right: 1px solid var(--fxr-border-subtle);
}

.tree-node {
	margin-bottom: 4px;
}

.mapping-details {
	padding: 16px 20px;
	background-color: var(--fxr-surface-2);
	border-top: 1px solid var(--fxr-border-subtle);
	animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
	from {
		transform: translateY(100%);
	}
	to {
		transform: translateY(0);
	}
}

.details-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 10px;
}

.details-header h6 {
	margin: 0;
	font-size: 13px;
	font-weight: 700;
	color: var(--fxr-text-strong);
}

.mapping-path {
	display: flex;
	align-items: center;
	font-size: 12px;
	background-color: var(--fxr-bg-card);
	padding: 8px 12px;
	border-radius: 6px;
	border: 1px solid var(--fxr-border-subtle);
}

.rm-label-sm {
	font-size: 11px;
	font-weight: 700;
	color: var(--fxr-text-soft);
	text-transform: uppercase;
	letter-spacing: 0.05em;
}

.magic-btn {
	color: var(--fxr-accent);
	border-color: var(--fxr-accent-border);
	background-color: var(--fxr-bg-card);
	padding: 6px 12px;
	font-weight: 600;
	transition: all 0.2s;
}

.magic-btn:hover {
	background-color: var(--fxr-accent-soft);
	border-color: var(--fxr-accent);
	transform: translateY(-1px);
}
</style>
