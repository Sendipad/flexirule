<script setup>
import { Handle, Position } from "@vue-flow/core";

import { computed } from "vue";
import { useStore } from "../../stores";

const props = defineProps(["data", "label", "sourcePosition", "targetPosition"]);
const store = useStore();

const isHorizontal = computed(() => store.settings?.layout_direction !== "Top to Bottom");

const targetPos = computed(
	() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
);
const sourcePos = computed(
	() => props.sourcePosition || (isHorizontal.value ? Position.Right : Position.Bottom)
);
</script>

<template>
	<div class="action-node-refined" :class="{ 'is-vertical': !isHorizontal }">
		<Handle type="target" :position="targetPos" class="handle-target" />
		<div class="node-content">
			<div class="icon-box">
				<span class="icon">⚙️</span>
			</div>
			<div class="text-group">
				<span class="label">{{ label }}</span>
				<span class="subtext">PROCESS</span>
			</div>
		</div>
		<Handle type="source" :position="sourcePos" class="handle-source" />
	</div>
</template>

<style scoped>
.action-node-refined {
	background: #fff;
	width: 200px;
	height: 70px;
	position: relative;
	display: flex;
	align-items: center;
	padding: 0 16px;
	border-radius: 4px 16px 4px 16px;
	border: 1px solid var(--blue-200);
	border-left: 5px solid var(--blue-500);
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	transition: all 0.3s ease;
}

.action-node-refined:hover {
	transform: translateY(-3px);
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.node-content {
	display: flex;
	align-items: center;
	gap: 12px;
	width: 100%;
}

.icon-box {
	width: 34px;
	height: 34px;
	background: var(--blue-50);
	border-radius: 8px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 16px;
}

.text-group {
	display: flex;
	flex-direction: column;
}

.label {
	font-size: 13px;
	font-weight: 700;
	color: var(--text-color);
}
.subtext {
	font-size: 8px;
	font-weight: 800;
	color: var(--blue-600);
	opacity: 0.6;
}

.action-node-refined.is-vertical {
	width: 100px;
	height: 120px;
	flex-direction: column;
	padding: 16px 8px;
	border-left: none;
	border-top: 5px solid var(--blue-500);
}

.is-vertical .node-content {
	flex-direction: column;
	text-align: center;
}

/* Handles */
.handle-target,
.handle-source {
	background: var(--gray-400) !important;
	border: 2px solid white !important;
	width: 10px !important;
	height: 10px !important;
	z-index: 10 !important;
}

.action-node-refined:not(.is-vertical) .handle-target {
	left: -5px !important;
}

.action-node-refined:not(.is-vertical) .handle-source {
	right: -5px !important;
}

.is-vertical .handle-target {
	top: -5px !important;
	left: 50% !important;
	transform: translateX(-50%) !important;
}

.is-vertical .handle-source {
	bottom: -5px !important;
	left: 50% !important;
	transform: translateX(-50%) !important;
}
</style>
