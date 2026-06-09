<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import ActionZone from "./ActionZone.vue";

const props = defineProps({
	active: Boolean,
	position: Object, // { x, y } in pixels relative to viewport or parent
});

const emit = defineEmits(["select", "close", "paste"]);

const popoverRef = ref(null);

function onClickOutside(e) {
	if (popoverRef.value && !popoverRef.value.contains(e.target)) {
		emit("close");
	}
}

onMounted(() => {
	document.addEventListener("mousedown", onClickOutside);
});

onUnmounted(() => {
	document.removeEventListener("mousedown", onClickOutside);
});
</script>

<template>
	<div
		ref="popoverRef"
		class="action-popover"
		:style="{
			left: position.x + 'px',
			top: position.y + 'px',
		}"
	>
		<div class="popover-header">
			<i class="fa fa-plus-circle"></i>
			<span>{{ __("Add Action") }}</span>
		</div>
		<ActionZone
			@select="emit('select', $event)"
			@paste="emit('paste')"
			@close="emit('close')"
		/>
	</div>
</template>

<style scoped>
.action-popover {
	position: fixed;
	width: 280px;
	max-height: 400px;
	background: #fff;
	background-color: var(--fxr-surface, #ffffff);
	border: 1px solid var(--border-color, #dfe3e8);
	border-radius: 8px;
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
	z-index: 2147483647; /* Maximum possible z-index */
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.popover-header {
	padding: 10px 12px;
	background: #f8f9fa;
	border-bottom: 1px solid #f0f4f7;
	display: flex;
	align-items: center;
	gap: 8px;
	font-weight: 700;
	font-size: 11px;
	color: var(--primary, #3b82f6);
}
</style>
