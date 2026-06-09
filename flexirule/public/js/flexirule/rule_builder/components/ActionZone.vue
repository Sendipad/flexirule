<script setup>
import { ref, onMounted, nextTick } from "vue";
import { useActionSearch } from "../composables/useActionSearch";

const props = defineProps({
	placeholder: {
		type: String,
		default: () => (window.__ ? __("Search actions or type Action: operation") : "Search actions or type Action: operation"),
	},
	showPaste: {
		type: Boolean,
		default: true,
	},
	autoFocus: {
		type: Boolean,
		default: true,
	}
});

const emit = defineEmits(["select", "paste", "close"]);

const {
	searchQuery,
	filteredResults,
	canPaste,
	loadProcessOperations,
	checkClipboard,
} = useActionSearch();

const selectedIndex = ref(-1);
const searchInputRef = ref(null);
const zoneRef = ref(null);

function selectItem(item) {
	if (item.type === "header") return;
	if (item.type === "scope_action") {
		searchQuery.value = `${item.value}: `;
		selectedIndex.value = -1;
		nextTick(() => searchInputRef.value?.focus());
		return;
	}
	if (item.type === "paste_discovery") {
		emit("paste");
		return;
	}

	const selection = {
		action_type: item.value || "Process",
		operation: item.operation || null,
		process_name: item.process_name || null,
		label: item.label || item.value || "Process",
	};
	emit("select", selection);
}

function nextSelectableIndex(startIndex, direction) {
	const total = filteredResults.value.length;
	if (!total) return -1;
	let index = startIndex;
	for (let step = 0; step < total; step++) {
		index = (index + direction + total) % total;
		if (filteredResults.value[index]?.type !== "header") return index;
	}
	return -1;
}

function onKeydown(e) {
	if (e.key === "Escape") emit("close");
	if (!filteredResults.value.length) return;

	if (e.key === "ArrowDown") {
		e.preventDefault();
		selectedIndex.value = nextSelectableIndex(selectedIndex.value, 1);
		scrollToActive();
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		selectedIndex.value = nextSelectableIndex(selectedIndex.value, -1);
		scrollToActive();
	} else if (e.key === "Enter" && selectedIndex.value !== -1) {
		e.preventDefault();
		selectItem(filteredResults.value[selectedIndex.value]);
	}
}

function scrollToActive() {
	nextTick(() => {
		const activeItem = zoneRef.value?.querySelector(".result-item.active");
		if (activeItem) {
			activeItem.scrollIntoView({ block: "nearest" });
		}
	});
}

function onPasteClick() {
	emit("paste");
}

onMounted(() => {
	loadProcessOperations();
	checkClipboard();
	if (props.autoFocus) {
		setTimeout(() => searchInputRef.value?.focus(), 100);
	}
});

defineExpose({
	focus: () => searchInputRef.value?.focus(),
	clear: () => (searchQuery.value = ""),
});
</script>

<template>
	<div ref="zoneRef" class="action-zone" @keydown="onKeydown">
		<div class="popover-search">
			<i class="fa fa-search"></i>
			<input
				ref="searchInputRef"
				type="text"
				v-model="searchQuery"
				:placeholder="placeholder"
				class="form-control"
				autocomplete="off"
			/>
		</div>
		<div class="popover-body" @wheel.stop>
			<!-- Pinned Paste Option -->
			<div
				v-if="showPaste && canPaste"
				class="result-item is-option paste-option"
				@mousedown.prevent="onPasteClick"
			>
				<div class="item-icon" style="color: var(--blue-500, #3b82f6)">
					<i class="fa fa-paste"></i>
				</div>
				<div class="item-content">
					<div class="item-label">{{ __("Paste Action") }}</div>
					<div class="item-desc">{{ __("Insert from clipboard") }}</div>
				</div>
			</div>

			<div v-if="!filteredResults.length && (!showPaste || !canPaste)" class="no-results">
				{{ __("No matching actions found") }}
			</div>

			<div
				v-for="(item, idx) in filteredResults"
				:key="idx"
				:class="[
					'result-item',
					item.type === 'header' ? 'is-header' : 'is-option',
					{ active: idx === selectedIndex },
				]"
				@mousedown.prevent="selectItem(item)"
				@mouseover="selectedIndex = idx"
			>
				<template v-if="item.type === 'header'">
					{{ item.label }}
				</template>
				<template v-else>
					<div class="item-icon" :style="{ color: item.color }">
						<i :class="['fa', item.icon?.replace('fa ', '') || 'fa-cog']"></i>
					</div>
					<div class="item-content">
						<div class="item-label">{{ item.label }}</div>
						<div v-if="item.description" class="item-desc">{{ item.description }}</div>
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<style scoped>
.action-zone {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: inherit;
}

.popover-search {
	padding: 8px;
	position: relative;
	border-bottom: 1px solid #f0f4f7;
}

.popover-search i {
	position: absolute;
	left: 16px;
	top: 50%;
	transform: translateY(-50%);
	color: #adb5bd;
	font-size: 10px;
}

.popover-search input {
	padding-left: 28px !important;
	height: 32px;
	font-size: 12px;
	border-radius: 4px;
	border: 1px solid var(--border-color, #dfe3e8);
}

.popover-body {
	flex: 1;
	overflow-y: auto;
	padding: 4px 0;
}

.result-item {
	padding: 8px 12px;
	cursor: pointer;
}

.is-header {
	font-size: 10px;
	font-weight: 700;
	color: #94a3b8;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	padding: 12px 12px 4px;
	cursor: default;
	background: #fff;
	background-color: var(--fxr-surface, #ffffff);
	position: sticky;
	top: 0;
	z-index: 1;
}

.is-option {
	display: flex;
	align-items: center;
	gap: 10px;
	transition: background 0.1s;
}

.is-option:hover,
.is-option.active {
	background: #f1f5f9;
}

.item-icon {
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
}

.item-content {
	flex: 1;
	min-width: 0;
}

.item-label {
	font-size: 12px;
	font-weight: 500;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-desc {
	font-size: 10px;
	color: #64748b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.no-results {
	padding: 20px;
	text-align: center;
	color: #94a3b8;
	font-size: 12px;
}

.paste-option {
	border-bottom: 1px solid #f1f5f9;
	background: #f8fafc;
}

.paste-option:hover {
	background: #f1f5f9;
}

/* Custom Scrollbar */
.popover-body::-webkit-scrollbar {
	width: 6px;
}
.popover-body::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 3px;
}
</style>
