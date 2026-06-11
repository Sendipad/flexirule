<template>
	<div class="execution-path-container" :class="[layoutDirection]">
		<!-- Header / Controls -->
		<div class="execution-header">
			<div class="title-wrap">
				<i class="fa fa-terminal"></i>
				<span class="title">{{ __("Execution Path") }}</span>
				<span class="badge badge-secondary ml-2">{{ steps.length }} {{ __("steps") }}</span>
			</div>
			<div class="actions">
				<button class="btn-clear" @click="clearPath" :title="__('Clear and Close')">
					<i class="fa fa-times"></i>
				</button>
			</div>
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
			if (node) {
				// Zoom and center on the node
				const { zoomTo, setCenter } = useVueFlow();
				// Note: useVueFlow composable needs to be called in setup or passed from parent.
				// In this component, we can use events or a shared vueflow instance if available.
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
				const scrollOptions = { behavior: "smooth" };
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
	background: rgba(255, 255, 255, 0.8);
	backdrop-filter: blur(12px);
	border: 1px solid var(--fxr-border-subtle);
	box-shadow: var(--fxr-shadow-lg);
	z-index: 100;
	transition: all 0.3s ease;
}

[data-theme="dark"] .execution-path-container {
	background: rgba(27, 31, 35, 0.8);
}

/* Horizontal Layout (Canvas Bottom) */
.execution-path-container.horizontal {
	left: 10px;
	right: 10px;
	bottom: 10px;
	height: 80px;
	border-radius: var(--fxr-radius-md);
	flex-direction: column;
	padding: 6px 10px;
}

/* Vertical Layout (Canvas Right) */
.execution-path-container.vertical {
	top: 70px;
	right: 10px;
	bottom: 10px;
	width: 200px;
	border-radius: var(--fxr-radius-md);
	flex-direction: column;
	padding: 10px 6px;
}

.execution-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 4px;
	padding: 0 4px;
}

.title-wrap {
	display: flex;
	align-items: center;
	gap: 6px;
}

.title-wrap i {
	color: var(--fxr-accent);
	font-size: 12px;
}

.title {
	font-size: 11px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: var(--fxr-text-soft);
}

.btn-clear {
	background: none;
	border: none;
	cursor: pointer;
	color: var(--fxr-text-faint);
	padding: 2px 6px;
	border-radius: 4px;
	transition: all 0.2s;
}

.btn-clear:hover {
	color: var(--red-500);
	background: var(--red-50);
}

.steps-wrapper {
	flex: 1;
	display: flex;
	gap: 10px;
	overflow: auto;
}

.horizontal .steps-wrapper {
	flex-direction: row;
	align-items: center;
	padding-bottom: 4px;
}

.vertical .steps-wrapper {
	flex-direction: column;
	padding-right: 4px;
}

/* Scrollbar styling */
.steps-wrapper::-webkit-scrollbar {
	width: 4px;
	height: 4px;
}

.steps-wrapper::-webkit-scrollbar-thumb {
	background: var(--fxr-border-strong);
	border-radius: 4px;
}

/* Details Panel Overlay Positioning */
.details-panel-overlay {
	position: absolute;
	z-index: 1001;
}

.horizontal .details-panel-overlay {
	bottom: 110px;
	left: 0;
	right: 0;
}

.vertical .details-panel-overlay {
	right: 250px;
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
	transform: translateY(20px);
	opacity: 0;
}

.slide-left-enter-from,
.slide-left-leave-to {
	transform: translateX(20px);
	opacity: 0;
}
</style>
