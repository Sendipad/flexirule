<template>
	<div class="source-picker-popover card shadow-lg border">
		<!-- Search Header -->
		<div class="p-2 border-bottom">
			<div class="input-group input-group-sm">
				<div class="input-group-prepend">
					<span class="input-group-text bg-transparent border-right-0">
						<i class="fa fa-search text-muted"></i>
					</span>
				</div>
				<input
					ref="searchInputRef"
					type="text"
					class="form-control border-left-0"
					v-model="searchQuery"
					:placeholder="__('Search fields and values...')"
					@keydown.esc.stop="$emit('close')"
					@keydown.down.prevent="focusNextItem"
					@keydown.up.prevent="focusPrevItem"
				/>
				<div class="input-group-append" v-if="searchQuery">
					<button
						class="btn btn-outline-secondary"
						type="button"
						@click="searchQuery = ''"
					>
						<i class="fa fa-times"></i>
					</button>
				</div>
			</div>
		</div>

		<!-- Categories & Options List -->
		<div class="source-options-list p-1">
			<div v-if="filteredGroups.length === 0" class="text-muted small text-center p-3">
				{{ __("No matching fields or values found") }}
			</div>

			<div v-for="group in filteredGroups" :key="group.name" class="source-group mb-2">
				<div
					class="group-header px-2 py-1 small font-weight-bold text-uppercase text-secondary"
				>
					<i :class="group.icon" class="mr-1"></i>
					{{ group.label }}
				</div>
				<div class="group-items">
					<div
						v-for="item in group.items"
						:key="item.value"
						class="source-item px-2 py-1 rounded small d-flex align-items-center justify-content-between"
						:class="{ 'is-selected': isItemSelected(item) }"
						@click="selectItem(item)"
					>
						<div class="item-main d-flex align-items-center text-truncate">
							<span class="item-label font-weight-medium text-truncate mr-2">
								{{ item.friendlyLabel || item.label || item.value }}
							</span>
							<span
								v-if="item.fieldtype"
								class="badge badge-light text-muted small mr-1"
							>
								{{ item.fieldtype }}
							</span>
						</div>
						<span class="item-path text-muted font-monospace small">
							{{ item.value }}
						</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div
			class="p-2 border-top bg-light d-flex align-items-center justify-content-between small text-muted"
		>
			<span><kbd class="small">@</kbd> {{ __("or click to select") }}</span>
			<button
				type="button"
				class="btn btn-link btn-xs text-secondary p-0"
				@click="$emit('close')"
			>
				{{ __("Close") }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from "vue";

const props = defineProps({
	options: { type: Array, default: () => [] },
	currentValue: { type: [Object, String], default: null },
});

const emit = defineEmits(["select", "close"]);

const searchQuery = ref("");
const searchInputRef = ref(null);

onMounted(() => {
	nextTick(() => {
		searchInputRef.value?.focus();
	});
});

function isItemSelected(item) {
	if (!props.currentValue) return false;
	if (typeof props.currentValue === "string") {
		return props.currentValue === item.value;
	}
	if (props.currentValue.mode === "variable") {
		const path = props.currentValue.path || {};
		const scope = path.scope || "doc";
		const segs = path.segments || [];
		const pathStr = segs.length ? `${scope}.${segs.join(".")}` : scope;
		return item.value === pathStr || item.value === segs.join(".");
	}
	return false;
}

function selectItem(item) {
	emit("select", item);
}

const categorizedOptions = computed(() => {
	const raw = props.options || [];
	const docItems = [];
	const oldDocItems = [];
	const stepItems = [];
	const contextItems = [];
	const otherItems = [];

	for (const opt of raw) {
		const val = opt.value || opt;
		const label = opt.label || val;
		const strVal = String(val);

		const item = {
			...opt,
			value: strVal,
			label: label,
			friendlyLabel: cleanFriendlyLabel(label, strVal),
		};

		if (strVal.startsWith("old_doc.")) {
			oldDocItems.push(item);
		} else if (strVal.startsWith("doc.") || (!strVal.includes(".") && !opt.is_context)) {
			docItems.push(item);
		} else if (strVal.startsWith("vars.") || strVal.startsWith("steps.")) {
			stepItems.push(item);
		} else if (
			opt.is_context ||
			strVal.startsWith("rule.") ||
			strVal.startsWith("caller.") ||
			strVal === "doctype"
		) {
			contextItems.push(item);
		} else {
			otherItems.push(item);
		}
	}

	const groups = [];
	if (docItems.length) {
		groups.push({
			name: "doc",
			label: __("This Document"),
			icon: "fa fa-file-text-o",
			items: docItems,
		});
	}
	if (oldDocItems.length) {
		groups.push({
			name: "old_doc",
			label: __("Previous Document (old_doc)"),
			icon: "fa fa-history",
			items: oldDocItems,
		});
	}
	if (stepItems.length) {
		groups.push({
			name: "vars",
			label: __("Predecessor Step Outputs"),
			icon: "fa fa-cubes",
			items: stepItems,
		});
	}
	if (contextItems.length) {
		groups.push({
			name: "context",
			label: __("Rule & Context Details"),
			icon: "fa fa-info-circle",
			items: contextItems,
		});
	}
	if (otherItems.length) {
		groups.push({
			name: "other",
			label: __("Other Approved Sources"),
			icon: "fa fa-sliders",
			items: otherItems,
		});
	}

	return groups;
});

function cleanFriendlyLabel(label, value) {
	if (!label) return value;
	// Remove prefixes like "doc.grand_total (Grand Total)" -> "Grand Total"
	const parenMatch = label.match(/\(([^)]+)\)/);
	if (parenMatch && parenMatch[1]) {
		return parenMatch[1].trim();
	}
	return label.replace(/^(doc|old_doc|vars|caller|rule)\./, "");
}

const filteredGroups = computed(() => {
	const q = searchQuery.value.toLowerCase().trim();
	if (!q) return categorizedOptions.value;

	const result = [];
	for (const group of categorizedOptions.value) {
		const matching = group.items.filter((item) => {
			return (
				item.value.toLowerCase().includes(q) ||
				(item.label && item.label.toLowerCase().includes(q)) ||
				(item.friendlyLabel && item.friendlyLabel.toLowerCase().includes(q)) ||
				(item.fieldtype && item.fieldtype.toLowerCase().includes(q))
			);
		});
		if (matching.length) {
			result.push({
				...group,
				items: matching,
			});
		}
	}
	return result;
});
</script>

<style scoped>
.source-picker-popover {
	width: 320px;
	max-height: 380px;
	background: var(--fxr-bg-surface, #ffffff);
	border-radius: var(--fxr-radius-md, 6px);
	z-index: 15000;
	display: flex;
	flex-direction: column;
}

.source-options-list {
	overflow-y: auto;
	flex: 1;
	max-height: 280px;
}

.group-header {
	font-size: 10px;
	letter-spacing: 0.5px;
	color: var(--fxr-text-secondary, #6b7280);
}

.source-item {
	cursor: pointer;
	transition: background-color var(--fxr-transition-fast, 0.15s ease);
}

.source-item:hover {
	background-color: var(--fxr-surface-2, #f3f4f6);
}

.source-item.is-selected {
	background-color: var(--fxr-accent-soft, #eff6ff);
	color: var(--fxr-accent, #2563eb);
}
</style>
