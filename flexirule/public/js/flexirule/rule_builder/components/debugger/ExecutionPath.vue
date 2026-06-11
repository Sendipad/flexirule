<template>
	<div class="execution-path-container" :class="[layoutDirection]">
		<!-- Header / Controls -->
		<div class="execution-header">
			<div class="title-wrap">
				<i class="fa fa-terminal"></i>
				<span class="title">{{ __("Execution Path") }}</span>
				<span class="badge-steps">{{ steps.length }}</span>
			</div>
			<div class="divider-vertical"></div>
			<button class="btn-clear" @click="clearPath" :title="__('Clear and Close')">
				<i class="fa fa-times"></i>
			</button>
		</div>

		<!-- Steps Scroll Area -->
		<div class="steps-wrapper" ref="stepsWrapper">
			<ExecutionStepCard
				v-for="(step, index) in steps"
				:key="`${step.node_id}-${index}`"
				:step="step"
				:isActive="uiStore.test_selected_step_index === index"
				@click="handleStepClick(index)"
			/>
		</div>

		<!-- Details Panel (Slide up or Drawer) -->
		<transition :name="transitionName">
			<div v-if="uiStore.test_selected_step_index !== null" class="details-panel-overlay">
				<ExecutionStepDetails
					:step="selectedStep"
					:layout="layoutDirection === 'horizontal' ? 'bottom' : 'right'"
					@close="uiStore.test_selected_step_index = null"
				/>
			</div>
		</transition>
	</div>
</template>

<script setup>
import { computed, ref, nextTick, watch } from "vue";
import { useVueFlow } from "@vue-flow/core";
import { useUIStore, useGraphStore } from "../../stores";
import ExecutionStepCard from "./ExecutionStepCard.vue";
import ExecutionStepDetails from "./ExecutionStepDetails.vue";

const props = defineProps({
	layout: {
		type: String, // 'LR' or 'TB'
		default: "LR",
	},
});

const uiStore = useUIStore();
const graphStore = useGraphStore();
const { setCenter } = useVueFlow();
const stepsWrapper = ref(null);

const steps = computed(() => uiStore.test_execution_steps || []);
const selectedStep = computed(() => steps.value[uiStore.test_selected_step_index]);
const layoutDirection = computed(() => (props.layout === "TB" ? "vertical" : "horizontal"));
const transitionName = computed(() =>
	layoutDirection.value === "horizontal" ? "slide-up" : "slide-left"
);

function handleStepClick(index) {
	if (uiStore.test_selected_step_index === index) {
		uiStore.test_selected_step_index = null;
	} else {
		uiStore.test_selected_step_index = index;
		const step = steps.value[index];
		if (step && step.node_id) {
			const node = graphStore.nodes.find((n) => n.id === step.node_id);
			if (node && node.position) {
				// Zoom and center on the node
				setCenter(node.position.x + 100, node.position.y + 50, {
					zoom: 1.2,
					duration: 800,
				});
			}
		}
	}
}

function clearPath() {
	uiStore.clear_test_result();
}

// Auto-scroll to the end when new steps arrive
watch(
	() => steps.value.length,
	() => {
		nextTick(() => {
			if (stepsWrapper.value) {
				if (layoutDirection.value === "horizontal") {
					stepsWrapper.value.scrollLeft = stepsWrapper.value.scrollWidth;
				} else {
					stepsWrapper.value.scrollTop = stepsWrapper.value.scrollHeight;
				}
			}
		});
	}
);
</script>

<style scoped>
.execution-path-container {
	position: absolute;
	display: flex;
	background: var(--fxr-surface-elevated);
	padding: var(--fxr-space-2);
	border-radius: var(--fxr-radius-md);
	border: 1px solid var(--fxr-border-subtle);
	box-shadow: var(--fxr-shadow-md);
	backdrop-filter: blur(12px);
	z-index: 100;
	transition: all 0.3s ease;
}

/* Horizontal Layout (Canvas Bottom) */
.execution-path-container.horizontal {
	left: 50%;
	transform: translateX(-50%);
	bottom: 12px;
	height: 52px;
	flex-direction: row;
	align-items: center;
	gap: var(--fxr-space-3);
	max-width: calc(100% - 40px);
	width: auto;
}

/* Vertical Layout (Canvas Right) */
.execution-path-container.vertical {
	top: 70px;
	right: 12px;
	bottom: 12px;
	width: 200px;
	flex-direction: column;
	gap: var(--fxr-space-2);
}

.execution-header {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-2);
	flex-shrink: 0;
}

.vertical .execution-header {
	justify-content: space-between;
	padding: 2px 4px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	margin-bottom: 4px;
	padding-bottom: 6px;
}

.title-wrap {
	display: flex;
	align-items: center;
	gap: 6px;
	white-space: nowrap;
}

.title-wrap i {
	color: var(--fxr-accent);
	font-size: 12px;
}

.title {
	font-size: 10px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: var(--fxr-text-soft);
}

.badge-steps {
	background: var(--fxr-surface-2);
	color: var(--fxr-text-soft);
	font-size: 9px;
	font-weight: 700;
	padding: 1px 5px;
	border-radius: 4px;
}

.divider-vertical {
	width: 1px;
	height: 16px;
	background-color: var(--fxr-border-subtle);
}

.btn-clear {
	background: none;
	border: none;
	cursor: pointer;
	color: var(--fxr-text-faint);
	padding: 4px;
	border-radius: 4px;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.2s;
}

.btn-clear:hover {
	color: var(--red-500);
	background: var(--fxr-danger-soft);
}

.steps-wrapper {
	flex: 1;
	display: flex;
	gap: 8px;
	overflow-x: auto;
	overflow-y: hidden;
}

.horizontal .steps-wrapper {
	flex-direction: row;
	align-items: center;
	scrollbar-width: none; /* Firefox */
}

.horizontal .steps-wrapper::-webkit-scrollbar {
	display: none; /* Safari and Chrome */
}

.vertical .steps-wrapper {
	flex-direction: column;
	overflow-y: auto;
	overflow-x: hidden;
}

/* Details Panel Overlay Positioning */
.details-panel-overlay {
	position: absolute;
	z-index: 1001;
}

.horizontal .details-panel-overlay {
	bottom: 64px;
	left: 50%;
	transform: translateX(-50%);
	width: 600px;
	max-width: 90vw;
}

.vertical .details-panel-overlay {
	right: 212px;
	top: 0;
	bottom: 0;
}

/* Animations */
.slide-up-enter-active,
.slide-up-leave-active,
.slide-left-enter-active,
.slide-left-leave-active {
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
	transform: translate(-50%, 20px);
	opacity: 0;
}

.slide-left-enter-from,
.slide-left-leave-to {
	transform: translateX(20px);
	opacity: 0;
}
</style>
