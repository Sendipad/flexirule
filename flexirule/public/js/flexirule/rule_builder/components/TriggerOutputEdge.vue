<script setup>
import { computed } from "vue";
import {
	BaseEdge,
	EdgeLabelRenderer,
	getBezierPath,
	getSmoothStepPath,
	useVueFlow,
} from "@vue-flow/core";
import { useRuleStore } from "../stores/useRuleStore";

const props = defineProps({
	id: { type: String, required: true },
	sourceX: { type: Number, required: true },
	sourceY: { type: Number, required: true },
	targetX: { type: Number, required: true },
	targetY: { type: Number, required: true },
	sourcePosition: { type: String, required: true },
	targetPosition: { type: String, required: true },
	data: { type: Object, required: false },
	markerEnd: { type: String, required: false },
	style: { type: Object, required: false },
});

const ruleStore = useRuleStore();

const isHorizontal = computed(() => ruleStore.settings?.layout_direction !== "Top to Bottom");

const path = computed(() => {
	const config = {
		sourceX: props.sourceX,
		sourceY: props.sourceY,
		sourcePosition: props.sourcePosition,
		targetX: props.targetX,
		targetY: props.targetY,
		targetPosition: props.targetPosition,
	};

	if (isHorizontal.value) {
		return getBezierPath(config);
	} else {
		return getSmoothStepPath({ ...config, borderRadius: 24 });
	}
});

const permissionFlags = computed(() => {
	const perms = props.data?.permissions;
	if (!Array.isArray(perms) || !perms.length) return ["All"];
	return perms.filter((p) => p.role).map((p) => p.role);
});

function openConfig() {
	ruleStore.open_config("start");
}
</script>

<template>
	<BaseEdge
		:id="id"
		:path="path[0]"
		:marker-end="markerEnd"
		:style="{
			...style,
			stroke: 'var(--vf-connection-path, var(--fxr-edge-stroke))',
			strokeWidth: 2.5,
		}"
	/>
	<EdgeLabelRenderer>
		<div
			:style="{
				pointerEvents: 'all',
				position: 'absolute',
				transform: `translate(-50%, -50%) translate(${path[1]}px,${path[2]}px)`,
				zIndex: 1000,
			}"
			class="nodrag nopan permission-pills-container"
		>
			<div class="permission-pills" :class="{ 'is-horizontal': isHorizontal }">
				<span
					v-for="(role, index) in permissionFlags"
					:key="role"
					class="permission-pill"
					:class="{ primary: index === 0, secondary: index > 0 }"
					@click.stop="openConfig"
				>
					<i :class="['fa', index === 0 ? 'fa-shield' : 'fa-users']"></i>
					{{ role }}
				</span>
			</div>
		</div>
	</EdgeLabelRenderer>
</template>

<style scoped>
.permission-pills {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 4px;
}

.permission-pills.is-horizontal {
	flex-direction: row;
}

.permission-pill {
	font-size: 10px;
	font-weight: 700;
	background-color: var(--fxr-surface-elevated);
	color: var(--fxr-text-strong);
	border: 1px solid var(--fxr-border-subtle);
	padding: 3px 10px;
	border-radius: 12px;
	white-space: nowrap;
	box-shadow: var(--fxr-shadow-sm);
	display: flex;
	align-items: center;
	gap: 6px;
	cursor: pointer;
	transition: all 0.2s;
	background-clip: padding-box;
}

.permission-pill:hover {
	transform: scale(1.05);
	border-color: var(--fxr-accent);
	background-color: var(--fxr-surface-2);
}

.permission-pill i {
	font-size: 10px;
	color: var(--fxr-accent);
}

.permission-pill.secondary {
	font-size: 9px;
	padding: 2px 8px;
	opacity: 0.9;
}
</style>
