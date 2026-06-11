<script setup>
import { ref, computed, watch } from "vue";
import { BaseEdge, getSmoothStepPath, EdgeLabelRenderer, useVueFlow } from "@vue-flow/core";
import { useStore } from "../stores";
import ActionZone from "./ActionZone.vue";

defineOptions({ inheritAttrs: false });

const props = defineProps({
	id: { type: String, required: true },
	source: { type: String, required: true },
	target: { type: String, required: true },
	sourceX: { type: Number, required: true },
	sourceY: { type: Number, required: true },
	targetX: { type: Number, required: true },
	targetY: { type: Number, required: true },
	sourcePosition: { type: String, required: true },
	targetPosition: { type: String, required: true },
	data: { type: Object, required: false },
	markerEnd: { type: String, required: false },
	style: { type: Object, required: false },
	sourceHandleId: { type: String, required: false },
	targetHandleId: { type: String, required: false },
});

const emit = defineEmits(["insert-node"]);
const store = useStore();
const { onPaneScroll, onPaneContextMenu, onMove } = useVueFlow();

const showPopover = ref(false);
const popoverPosition = ref({ x: 0, y: 0 });
const addButtonRef = ref(null);

const isReturnEdge = computed(() => {
	return (
		props.data?.isReturn ||
		props.targetHandleId === "return" ||
		props.id.includes("return") ||
		props.data?.targetHandle === "return"
	);
});

const isAfterLastEdge = computed(() => {
	return props.data?.afterLast === true;
});

const isLoopBodyEdge = computed(() => {
	return props.data?.loopBody === true;
});

const isHorizontal = computed(() => store.settings?.layout_direction !== "Top to Bottom");

const isEnabled = computed(() => {
	if (!store.settings) return true;
	if (store.settings.enable_edge_insertion === 0) return false;
	return true;
});

const path = computed(() => {
	// Salesforce aesthetic uses SmoothStep for everything to keep lines clean and 90-degree
	const config = {
		sourceX: props.sourceX,
		sourceY: props.sourceY,
		sourcePosition: props.sourcePosition,
		targetX: props.targetX,
		targetY: props.targetY,
		targetPosition: props.targetPosition,
		borderRadius: 24,
		offset: 40,
	};

	if (isReturnEdge.value) {
		// Return edges are pulled away from loop bypass edges.
		config.offset = isHorizontal.value ? 70 : 62;
		config.borderRadius = 18;
	} else if (isAfterLastEdge.value) {
		// Bypass branch should stay clearly separated from loop return/body edges.
		config.offset = isHorizontal.value ? 52 : 70;
		config.borderRadius = 30;
	} else if (isLoopBodyEdge.value) {
		// Keep "For Each" branch tighter to the main direction so it doesn't cross bypass.
		config.offset = isHorizontal.value ? 34 : 34;
		config.borderRadius = 20;
	}

	return getSmoothStepPath(config);
});

function onAddClick(event) {
	event.stopPropagation();
	const rect = event.currentTarget.getBoundingClientRect();
	popoverPosition.value = {
		x: rect.left + rect.width / 2,
		y: rect.top + rect.height / 2,
	};
	showPopover.value = !showPopover.value;
}

// Close popover if canvas moves or scrolls
onPaneScroll(() => (showPopover.value = false));
onPaneContextMenu(() => (showPopover.value = false));
onMove(() => {
	if (showPopover.value) showPopover.value = false;
});

function onActionSelect(selection) {
	showPopover.value = false;
	emit("insert-node", {
		edgeId: props.id,
		actionType: selection.action_type,
		operation: selection.operation,
		process_name: selection.process_name,
		label: selection.label,
	});
}

function onPaste() {
	showPopover.value = false;
	emit("insert-node", {
		edgeId: props.id,
		isPaste: true,
	});
}
</script>

<template>
	<BaseEdge
		:id="id"
		:style="{
			...style,
			strokeWidth: isReturnEdge ? 1.5 : 2,
			stroke: 'var(--fxr-edge-stroke)',
			strokeDasharray: isReturnEdge ? '5,5' : 'none',
			opacity: isReturnEdge ? 0.8 : 1,
		}"
		:path="path[0]"
		:marker-end="markerEnd"
		data-edge-type="add"
	/>
	<EdgeLabelRenderer v-if="isEnabled && !store.is_read_only">
		<div
			:style="{
				pointerEvents: 'all',
				position: 'absolute',
				transform: `translate(-50%, -50%) translate(${path[1]}px,${path[2]}px)`,
				zIndex: 1000,
			}"
			class="nodrag nopan edge-label-container"
		>
			<button
				ref="addButtonRef"
				class="edge-add-button"
				:class="{ active: showPopover }"
				@click="onAddClick"
				:title="__('Insert Action')"
				data-testid="edge-add-button"
			>
				<i class="fa fa-plus"></i>
			</button>

			<Teleport to="body">
				<div class="fxr-builder-active">
					<ActionZone
						v-if="showPopover"
						mode="popover"
						:trigger="addButtonRef"
						:position="popoverPosition"
						@select="onActionSelect"
						@paste="onPaste"
						@close="showPopover = false"
					/>
				</div>
			</Teleport>
		</div>
	</EdgeLabelRenderer>
</template>

<style scoped>
.edge-add-button {
	width: 22px;
	height: 22px;
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border-strong);
	border-radius: 50%;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 8px;
	color: var(--fxr-text-soft);
	box-shadow: var(--fxr-shadow-sm);
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	z-index: 10;
}

.edge-add-button:hover,
.edge-add-button.active {
	transform: scale(1.15);
	border-color: var(--fxr-accent);
	color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-md);
}

.edge-add-button i {
	pointer-events: none;
	transition: transform 0.2s ease;
}

.edge-add-button.active i {
	transform: rotate(45deg);
}
</style>
