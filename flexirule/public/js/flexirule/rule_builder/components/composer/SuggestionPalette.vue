<template>
	<div
		v-if="isOpen"
		ref="paletteRef"
		class="suggestion-palette"
		:style="paletteStyle"
		tabindex="-1"
		@keydown.down.prevent="onKeyDown"
		@keydown.up.prevent="onKeyUp"
		@keydown.enter.prevent="onKeyEnter"
		@keydown.esc.prevent="close"
	>
		<!-- Palette Header / Search Input -->
		<div class="palette-search-wrap">
			<i class="fa fa-search palette-search-icon"></i>
			<input
				ref="searchInputRef"
				v-model="searchQuery"
				type="text"
				class="palette-search-input"
				:placeholder="__('Type @ to mention, search fields, variables, resolvers...')"
				@input="onSearchInput"
				@keydown.down.prevent="onKeyDown"
				@keydown.up.prevent="onKeyUp"
				@keydown.enter.prevent="onKeyEnter"
				@keydown.esc.prevent="close"
			/>
			<span v-if="searchQuery" class="palette-search-clear" @click="searchQuery = ''">
				<i class="fa fa-times"></i>
			</span>
		</div>

		<!-- Palette Results List -->
		<div ref="listContainerRef" class="palette-list-container">
			<template v-if="groupedItems.length > 0">
				<div v-for="group in groupedItems" :key="group.name" class="palette-group">
					<div class="palette-group-header">
						{{ group.name }}
					</div>
					<div
						v-for="item in group.items"
						:key="item.id"
						:data-item-id="item.id"
						class="palette-item"
						:class="{ 'is-active': activeIndex === getItemFlatIndex(item) }"
						@mouseenter="activeIndex = getItemFlatIndex(item)"
						@click.stop="selectItem(item)"
					>
						<div class="palette-item-icon">
							<i :class="item.icon"></i>
						</div>
						<div class="palette-item-content">
							<div class="palette-item-title-row">
								<span class="palette-item-label">{{ item.displayLabel }}</span>
								<span class="palette-item-mention">{{ item.mentionLabel }}</span>
							</div>
							<div v-if="item.subLabel" class="palette-item-sub">
								{{ item.subLabel }}
							</div>
						</div>
						<div class="palette-item-badge">
							{{ item.value_type || "any" }}
						</div>
					</div>
				</div>
			</template>

			<div v-else class="palette-empty-state">
				<i class="fa fa-info-circle mr-1"></i>
				{{ __("No matching capabilities found") }}
			</div>
		</div>

		<!-- Palette Footer Hints -->
		<div class="palette-footer">
			<span class="palette-hint"><kbd>↑</kbd><kbd>↓</kbd> {{ __("Navigate") }}</span>
			<span class="palette-hint"><kbd>↵</kbd> {{ __("Select") }}</span>
			<span class="palette-hint"><kbd>esc</kbd> {{ __("Close") }}</span>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from "vue";
import { buildContextualSuggestions, groupSuggestions } from "./ComposerContextAdapter.js";

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	docFields: { type: Array, default: () => [] },
	variableOptions: { type: Array, default: () => [] },
	contract: { type: Object, default: () => ({}) },
	isConditionOperand: { type: Boolean, default: false },
	targetFieldtype: { type: String, default: null },
	anchorEl: { type: Object, default: null },
});

const emit = defineEmits(["select", "close"]);

const searchQuery = ref("");
const activeIndex = ref(0);
const paletteRef = ref(null);
const searchInputRef = ref(null);
const listContainerRef = ref(null);

const rawSuggestions = computed(() => {
	return buildContextualSuggestions({
		docFields: props.docFields,
		variableOptions: props.variableOptions,
		contract: props.contract,
		isConditionOperand: props.isConditionOperand,
		targetFieldtype: props.targetFieldtype,
		query: searchQuery.value,
	});
});

const groupedItems = computed(() => {
	return groupSuggestions(rawSuggestions.value);
});

const flatItems = computed(() => {
	const flat = [];
	for (const group of groupedItems.value) {
		for (const item of group.items) {
			flat.push(item);
		}
	}
	return flat;
});

function getItemFlatIndex(item) {
	return flatItems.value.findIndex((x) => x.id === item.id);
}

function selectItem(item) {
	if (!item) return;
	emit("select", item);
	close();
}

function close() {
	searchQuery.value = "";
	activeIndex.value = 0;
	emit("close");
}

function onKeyDown() {
	if (flatItems.value.length === 0) return;
	activeIndex.value = (activeIndex.value + 1) % flatItems.value.length;
	scrollToActive();
}

function onKeyUp() {
	if (flatItems.value.length === 0) return;
	activeIndex.value = (activeIndex.value - 1 + flatItems.value.length) % flatItems.value.length;
	scrollToActive();
}

function onKeyEnter() {
	if (flatItems.value.length > 0 && activeIndex.value >= 0) {
		const item = flatItems.value[activeIndex.value];
		selectItem(item);
	}
}

function onSearchInput() {
	activeIndex.value = 0;
	scrollToActive();
}

function scrollToActive() {
	nextTick(() => {
		const activeEl = listContainerRef.value?.querySelector(".palette-item.is-active");
		if (activeEl) {
			activeEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
		}
	});
}

const paletteStyle = ref({});

function updatePosition() {
	if (!props.anchorEl) {
		paletteStyle.value = {};
		return;
	}
	const rect = props.anchorEl.getBoundingClientRect();
	const left = Math.max(12, Math.min(rect.left, window.innerWidth - 360));

	paletteStyle.value = {
		position: "fixed",
		top: `${rect.bottom + 4}px`,
		left: `${left}px`,
		zIndex: 9999,
	};
}

watch(
	() => props.isOpen,
	(val) => {
		if (val) {
			searchQuery.value = "";
			activeIndex.value = 0;
			nextTick(() => {
				updatePosition();
				searchInputRef.value?.focus();
			});
		}
	}
);

function handleClickOutside(event) {
	if (!props.isOpen) return;
	if (paletteRef.value && !paletteRef.value.contains(event.target)) {
		if (props.anchorEl && props.anchorEl.contains(event.target)) {
			return;
		}
		close();
	}
}

onMounted(() => {
	document.addEventListener("mousedown", handleClickOutside);
	window.addEventListener("resize", updatePosition);
	window.addEventListener("scroll", updatePosition, true);
});

onBeforeUnmount(() => {
	document.removeEventListener("mousedown", handleClickOutside);
	window.removeEventListener("resize", updatePosition);
	window.removeEventListener("scroll", updatePosition, true);
});
</script>

<style scoped>
.suggestion-palette {
	width: 340px;
	max-height: 420px;
	background: #ffffff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	box-shadow:
		0 10px 25px -5px rgba(0, 0, 0, 0.1),
		0 8px 10px -6px rgba(0, 0, 0, 0.1);
	display: flex;
	flex-direction: column;
	overflow: hidden;
	font-family: inherit;
}

.palette-search-wrap {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid #f1f5f9;
	background: #f8fafc;
	gap: 8px;
}

.palette-search-icon {
	color: #94a3b8;
	font-size: 13px;
}

.palette-search-input {
	flex: 1;
	border: none;
	background: transparent;
	font-size: 13px;
	outline: none;
	color: #1e293b;
	padding: 0;
}

.palette-search-clear {
	cursor: pointer;
	color: #94a3b8;
	font-size: 11px;
}

.palette-search-clear:hover {
	color: #475569;
}

.palette-list-container {
	flex: 1;
	overflow-y: auto;
	padding: 4px 0;
	max-height: 320px;
}

.palette-group-header {
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.05em;
	color: #64748b;
	padding: 6px 12px 2px;
	text-transform: uppercase;
}

.palette-item {
	display: flex;
	align-items: center;
	padding: 6px 12px;
	cursor: pointer;
	gap: 10px;
	transition: background-color 0.1s ease;
}

.palette-item:hover,
.palette-item.is-active {
	background-color: #f1f5f9;
}

.palette-item-icon {
	width: 20px;
	height: 20px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #64748b;
	font-size: 12px;
}

.palette-item-content {
	flex: 1;
	min-width: 0;
}

.palette-item-title-row {
	display: flex;
	align-items: baseline;
	gap: 6px;
	overflow: hidden;
}

.palette-item-label {
	font-size: 13px;
	font-weight: 500;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.palette-item-mention {
	font-size: 11px;
	color: #6366f1;
	font-family: monospace;
	white-space: nowrap;
}

.palette-item-sub {
	font-size: 11px;
	color: #94a3b8;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.palette-item-badge {
	font-size: 10px;
	font-family: monospace;
	padding: 1px 6px;
	background: #e2e8f0;
	color: #475569;
	border-radius: 4px;
	text-transform: lowercase;
}

.palette-empty-state {
	padding: 24px 16px;
	text-align: center;
	color: #94a3b8;
	font-size: 12px;
}

.palette-footer {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 12px;
	padding: 6px 12px;
	background: #f8fafc;
	border-top: 1px solid #f1f5f9;
	font-size: 11px;
	color: #94a3b8;
}

.palette-hint kbd {
	background: #e2e8f0;
	color: #334155;
	padding: 1px 4px;
	border-radius: 3px;
	font-size: 10px;
	font-family: inherit;
}
</style>
