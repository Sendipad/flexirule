<script setup>
import { ref, computed } from "vue";
import { BaseEdge, getSmoothStepPath, EdgeLabelRenderer } from "@vue-flow/core";
import { useStore } from "../stores";
import ActionPopover from "./ActionPopover.vue";

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

const showPopover = ref(false);
const popoverPosition = ref({ x: 0, y: 0 });

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
		x: Math.min(rect.left + rect.width / 2 + 12, window.innerWidth - 320),
		y: Math.max(rect.top - 16, 12),
	};
	showPopover.value = !showPopover.value;
}

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
			stroke: isReturnEdge ? '#94a3b8' : 'var(--border-color, #cbd5e1)',
			strokeDasharray: isReturnEdge ? '5,5' : 'none',
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
				class="edge-add-button"
				:class="{ active: showPopover }"
				@click="onAddClick"
				:title="__('Insert Action')"
				data-testid="edge-add-button"
			>
				<i class="fa fa-plus"></i>
			</button>

			<Teleport to="body">
				<ActionPopover
					v-if="showPopover"
					:active="showPopover"
					:position="popoverPosition"
					@select="onActionSelect"
					@paste="onPaste"
					@close="showPopover = false"
				/>
			</Teleport>
		</div>
	</EdgeLabelRenderer>
</template>

<style scoped>
.edge-add-button {
	width: 22px;
	height: 22px;
	background: #fff;
	border: 1px solid #cbd5e1;
	border-radius: 50%;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 8px;
	color: #64748b;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	z-index: 10;
}

.edge-add-button:hover,
.edge-add-button.active {
	transform: scale(1.15);
	border-color: #3b82f6;
	color: #3b82f6;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.edge-add-button i {
	pointer-events: none;
	transition: transform 0.2s ease;
}

.edge-add-button.active i {
	transform: rotate(45deg);
}
</style>
