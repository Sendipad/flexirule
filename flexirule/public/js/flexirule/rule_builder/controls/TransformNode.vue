<template>
	<div
		class="transform-node-wrapper"
		:data-path="node.path"
		:data-type="type"
		:class="{ 'is-leaf': node.isLeaf, 'is-mapped': isMapped }"
	>
		<div class="node-row" @click="onRowClick">
			<div v-if="!node.isLeaf" class="toggle-icon">
				<i :class="isOpen ? 'fa fa-caret-down' : 'fa fa-caret-right'"></i>
			</div>
			<div v-else class="leaf-spacer"></div>

			<div class="node-icon">
				<i :class="nodeIcon"></i>
			</div>

			<div class="node-label">
				<span class="label-text">{{ node.label }}</span>
				<span v-if="node.fieldtype" class="fieldtype">{{ node.fieldtype }}</span>
			</div>

			<!-- Connection Anchor -->
			<div
				class="anchor"
				:class="{ 'anchor-mapped': isMapped }"
				@mousedown.stop="onAnchorMouseDown"
				@mouseup.stop="onAnchorMouseUp"
			></div>
		</div>

		<div v-if="isOpen && node.children.length" class="node-children">
			<TransformNode
				v-for="child in node.children"
				:key="child.path"
				:node="child"
				:type="type"
				:is-mapped="isChildMapped(child.path)"
				@connect="$emit('connect', $event)"
				@toggle="$emit('toggle', $event)"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, inject } from "vue";

const props = defineProps({
	node: Object,
	type: String, // 'source' or 'target'
	isMapped: Boolean,
	isExpanded: Boolean,
});

const emit = defineEmits(["connect", "toggle"]);

const expandedNodes = inject("expandedNodes", ref(new Set()));
const localOpen = ref(false);
const isOpen = computed(
	() => props.isExpanded || localOpen.value || expandedNodes.value.has(props.node.path)
);

const nodeIcon = computed(() => {
	if (!props.node.isLeaf) return isOpen.value ? "fa fa-folder-open-o" : "fa fa-folder-o";
	switch (props.node.fieldtype) {
		case "Data":
			return "fa fa-font";
		case "Int":
		case "Float":
		case "Currency":
			return "fa fa-hashtag";
		case "Date":
		case "Datetime":
			return "fa fa-calendar";
		case "Table":
			return "fa fa-table";
		case "Link":
			return "fa fa-link";
		case "Check":
			return "fa fa-check-square-o";
		default:
			return "fa fa-circle-o";
	}
});

function onRowClick() {
	if (!props.node.isLeaf) {
		localOpen.value = !localOpen.value;
		emit("toggle", props.node);
	}
}

function onAnchorMouseDown() {
	if (props.type === "source" && props.node.isLeaf) {
		emit("connect", props.node);
	}
}

function onAnchorMouseUp() {
	if (props.type === "target" && props.node.isLeaf) {
		emit("connect", props.node);
	}
}

const mappings = inject("mappings", ref([]));

function isChildMapped(path) {
	if (props.type === "source") {
		return mappings.value.some((m) => m.source === path);
	}
	return mappings.value.some((m) => m.target === path);
}
</script>

<style scoped>
.transform-node-wrapper {
	user-select: none;
}

.node-row {
	display: flex;
	align-items: center;
	padding: 6px 12px;
	border-radius: 6px;
	cursor: pointer;
	position: relative;
	gap: 10px;
	transition: all 0.2s;
}

.node-row:hover {
	background-color: var(--fxr-bg-hover);
}

.transform-node-wrapper.is-mapped .node-row {
	background-color: var(--fxr-accent-soft);
}

.toggle-icon {
	width: 14px;
	color: var(--fxr-text-muted);
	font-size: 11px;
}

.leaf-spacer {
	width: 14px;
}

.node-icon {
	width: 18px;
	text-align: center;
	color: var(--fxr-text-soft);
	font-size: 14px;
}

.node-label {
	flex: 1;
	display: flex;
	align-items: center;
	gap: 8px;
	min-width: 0;
}

.label-text {
	font-size: 12.5px;
	font-weight: 500;
	color: var(--fxr-text-secondary);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.fieldtype {
	font-size: 9px;
	color: var(--fxr-text-muted);
	text-transform: uppercase;
	font-weight: 700;
	background-color: var(--fxr-surface-soft);
	padding: 1px 4px;
	border-radius: 3px;
	border: 1px solid var(--fxr-border-subtle);
}

.node-children {
	margin-left: 20px;
	border-left: 1px dashed var(--fxr-border-strong);
}

/* Anchors */
.anchor {
	width: 12px;
	height: 12px;
	border: 2px solid var(--fxr-border-strong);
	background-color: var(--fxr-bg-card);
	border-radius: 50%;
	transition: all 0.2s;
	z-index: 20;
	box-shadow: 0 0 0 2px var(--fxr-bg-card);
}

.transform-node-wrapper[data-type="source"] .anchor {
	margin-right: -13px;
}

.transform-node-wrapper[data-type="target"] .anchor {
	margin-left: -13px;
	order: -1;
}

.is-leaf .anchor {
	border-color: var(--fxr-text-muted);
}

.anchor:hover {
	transform: scale(1.3);
	border-color: var(--fxr-accent);
}

.anchor-mapped {
	background-color: var(--fxr-accent);
	border-color: var(--fxr-accent);
}

.is-mapped .label-text {
	color: var(--fxr-accent);
	font-weight: 700;
}
</style>
