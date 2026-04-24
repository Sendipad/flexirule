<template>
	<div class="resizable-container" :class="{ 'is-resizing': resizing, 'is-mobile': isMobile }">
		<!-- Mobile Toggles -->
		<div v-if="isMobile" class="panel-toggles">
			<button
				v-for="(panel, index) in panels"
				:key="index"
				class="btn btn-xs"
				:class="activePanel === index ? 'btn-primary' : 'btn-default'"
				@click="activePanel = index"
			>
				{{ panel.label }}
			</button>
		</div>

		<div class="panels-wrapper" ref="wrapper">
			<slot></slot>
		</div>
	</div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";

const resizing = ref(false);
const isMobile = ref(false);
const activePanel = ref(1); // Default to middle panel on mobile
const wrapper = ref(null);

const panels = [{ label: __("Inputs") }, { label: __("Config") }, { label: __("Outputs") }];

let resizerListeners = [];

function checkMobile() {
	isMobile.value = window.innerWidth <= 992;
}

function handleResize() {
	checkMobile();
	if (isMobile.value) {
		applyMobileLayout();
	} else {
		applyDesktopLayout();
	}
}

function applyMobileLayout() {
	const children = wrapper.value?.children;
	if (!children) return;

	let panelIndex = 0;
	Array.from(children).forEach((child) => {
		if (child.classList.contains("panel-resizer")) {
			child.style.display = "none";
		} else if (child.classList.contains("resizable-panel")) {
			child.style.display = panelIndex === activePanel.value ? "block" : "none";
			child.style.width = "100%";
			child.style.flex = "1";
			panelIndex++;
		}
	});
}

function applyDesktopLayout() {
	const children = wrapper.value?.children;
	if (!children) return;

	Array.from(children).forEach((child) => {
		if (child.classList.contains("panel-resizer")) {
			child.style.display = "block";
		} else if (child.classList.contains("resizable-panel")) {
			child.style.display = "block";
			// Do NOT force specific flex/width styles here, let CSS handle initial layout
			// Only apply styles if resizing happened?
			// Or ensure we don't break the flex-basis logic.

			// Previous logic forced flex:1 on middle, which broke 20/60/20 ratio.
			// We'll remove inline styles that might have been set by mobile layout.
			child.style.width = "";
			child.style.flex = "";
		}
	});
}

function initResizers() {
	if (!wrapper.value) return;
	const resizers = wrapper.value.querySelectorAll(".panel-resizer");

	resizers.forEach((resizer) => {
		const onMouseDown = (e) => {
			if (isMobile.value) return;

			resizing.value = true;
			const leftPanel = resizer.previousElementSibling;
			const startX = e.clientX;
			const startWidth = leftPanel.offsetWidth;

			const onMouseMove = (moveEvent) => {
				const dx = moveEvent.clientX - startX;
				let newWidth = startWidth + dx;

				// Constraints
				const minWidth = 200;
				const maxWidth = wrapper.value.offsetWidth * 0.6;

				if (newWidth < minWidth) newWidth = minWidth;
				if (newWidth > maxWidth) newWidth = maxWidth;

				leftPanel.style.width = `${newWidth}px`;
				leftPanel.style.flex = "none";
			};

			const onMouseUp = () => {
				resizing.value = false;
				document.removeEventListener("mousemove", onMouseMove);
				document.removeEventListener("mouseup", onMouseUp);
				document.body.style.cursor = "";
			};

			document.addEventListener("mousemove", onMouseMove);
			document.addEventListener("mouseup", onMouseUp);
			document.body.style.cursor = "col-resize";
		};

		resizer.addEventListener("mousedown", onMouseDown);
		resizerListeners.push({ resizer, onMouseDown });
	});
}

onMounted(() => {
	checkMobile();
	window.addEventListener("resize", handleResize);
	nextTick(() => {
		initResizers();
		handleResize();
	});
});

onUnmounted(() => {
	window.removeEventListener("resize", handleResize);
	resizerListeners.forEach(({ resizer, onMouseDown }) => {
		resizer.removeEventListener("mousedown", onMouseDown);
	});
});

// Watch for activePanel changes on mobile
watch(activePanel, () => {
	if (isMobile.value) applyMobileLayout();
});
</script>

<style scoped>
.resizable-container {
	display: flex;
	flex-direction: column;
	width: 100%;
	height: 100%;
	overflow: hidden;
	position: relative;
}

.panels-wrapper {
	display: flex;
	flex: 1;
	width: 100%;
	height: 100%;
	overflow: hidden;
}

.panel-toggles {
	display: flex;
	padding: 10px;
	gap: 8px;
	background: #fcfcfc;
	border-bottom: 1px solid var(--border-color);
	justify-content: center;
}

.resizable-container.is-resizing {
	cursor: col-resize;
}

:deep(.panel-resizer) {
	width: 4px;
	cursor: col-resize;
	background: transparent;
	transition: background 0.2s;
	z-index: 10;
	position: relative;
}

:deep(.panel-resizer:hover),
:deep(.panel-resizer.active) {
	background: var(--primary);
}

:deep(.panel-resizer::after) {
	content: "";
	position: absolute;
	left: -4px;
	top: 0;
	bottom: 0;
	width: 12px;
}

@media (max-width: 992px) {
	.panels-wrapper {
		flex-direction: column;
	}
}
</style>
