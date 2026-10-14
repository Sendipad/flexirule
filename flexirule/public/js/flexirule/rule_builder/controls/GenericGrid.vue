<template>
	<div class="fxr-generic-grid" :style="gridStyle">
		<slot />
	</div>
</template>

<script setup>
import { computed } from "vue";

/**
 * Responsive grid wrapper for layouts whose item count is not fixed.
 * Columns are created automatically from available width and collapse naturally
 * when the container cannot fit another column.
 */
const props = defineProps({
	minColumnWidth: { type: String, default: "240px" },
	gap: { type: String, default: "var(--fxr-space-3, 12px)" },
});

const gridStyle = computed(() => ({
	"--fxr-generic-grid-min-column-width": props.minColumnWidth,
	"--fxr-generic-grid-gap": props.gap,
}));
</script>

<style scoped>
.fxr-generic-grid {
	display: grid;
	grid-template-columns: repeat(
		auto-fit,
		minmax(min(100%, var(--fxr-generic-grid-min-column-width, 240px)), 1fr)
	);
	gap: var(--fxr-generic-grid-gap, var(--fxr-space-3, 12px));
	align-items: start;
	min-width: 0;
}

.fxr-generic-grid > * {
	min-width: 0;
}
</style>
