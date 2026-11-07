<template>
	<div class="tg-mention-list" v-if="items.length">
		<div class="tg-mention-scroller v2-scrollbar">
			<template v-for="(group, gIdx) in groupedItems" :key="group.category || gIdx">
				<div class="tg-mention-header" v-if="group.label">
					<i :class="group.icon || 'fa fa-folder-o'"></i> {{ group.label }}
				</div>
				<button
					v-for="item in group.items"
					:key="item.id || item.value || item"
					class="tg-mention-item"
					:class="{
						'is-selected': item._globalIndex === selectedIndex,
						'is-incompatible': item.isCompatible === false,
					}"
					@mousedown.prevent="selectItem(item._globalIndex)"
				>
					<div class="item-icon" :class="item.sourceType || item.type">
						<span v-if="item.icon && !item.icon.startsWith('fa')" class="item-emoji">{{
							item.icon
						}}</span>
						<i v-else :class="getIcon(item)"></i>
					</div>
					<div class="item-info">
						<div class="d-flex align-items-center justify-content-between">
							<span class="item-label">{{
								item.primaryLabel || item.label || item.id || item
							}}</span>
							<span v-if="item.fieldtype" class="item-badge">{{
								item.fieldtype
							}}</span>
						</div>
						<div class="d-flex align-items-center justify-content-between mt-0.5">
							<span v-if="item.secondaryText" class="item-secondary font-monospace">{{
								item.secondaryText
							}}</span>
							<span v-else-if="item.description" class="item-description">{{
								item.description
							}}</span>
						</div>
					</div>
				</button>
			</template>
		</div>
	</div>
	<div v-else class="tg-mention-list tg-mention-empty">
		{{ t("No results found") }}
	</div>
</template>

<script>
export default {
	props: {
		items: { type: Array, required: true },
		command: { type: Function, required: true },
	},
	data() {
		return {
			selectedIndex: 0,
		};
	},
	computed: {
		groupedItems() {
			const groups = [];
			const map = new Map();
			let globalIdx = 0;

			for (const rawItem of this.items) {
				const item = { ...rawItem, _globalIndex: globalIdx++ };
				const cat = item.category || (item.type === "logic" ? "commands" : "other");
				let group = map.get(cat);
				if (!group) {
					let catLabel = item.categoryLabel;
					let catIcon = "fa fa-folder-o";
					if (!catLabel) {
						if (cat === "fields") {
							catLabel = this.t("Document Fields");
							catIcon = "fa fa-file-text-o";
						} else if (cat === "variables") {
							catLabel = this.t("Variables");
							catIcon = "fa fa-cube";
						} else if (cat === "resolvers") {
							catLabel = this.t("Resolvers");
							catIcon = "fa fa-bolt";
						} else if (cat === "commands") {
							catLabel = this.t("Commands");
							catIcon = "fa fa-terminal";
						} else {
							catLabel = this.t("Other");
						}
					}
					group = {
						category: cat,
						label: catLabel,
						icon: item.categoryIcon || catIcon,
						items: [],
					};
					map.set(cat, group);
					groups.push(group);
				}
				group.items.push(item);
			}
			return groups;
		},
	},
	watch: {
		items: {
			immediate: true,
			handler() {
				this.selectedIndex = 0;
			},
		},
	},
	methods: {
		t(message) {
			const translate = globalThis.__;
			return typeof translate === "function" ? translate(message) : message;
		},
		getIcon(item) {
			if (item.icon) return item.icon;
			if (item.sourceType === "field") return "fa fa-file-text-o";
			if (item.sourceType === "variable" || item.type === "variable") return "fa fa-cube";
			if (item.sourceType === "resolver") return "fa fa-bolt";
			if (item.type === "logic") {
				return "fa fa-terminal";
			}
			return "fa fa-cube";
		},
		onKeyDown({ event }) {
			if (event.key === "ArrowUp") {
				this.upHandler();
				return true;
			}
			if (event.key === "ArrowDown") {
				this.downHandler();
				return true;
			}
			if (event.key === "Enter" || event.key === "Tab") {
				this.enterHandler();
				return true;
			}
			if (event.key === "Escape") {
				return false;
			}
			return false;
		},
		upHandler() {
			this.selectedIndex = (this.selectedIndex + this.items.length - 1) % this.items.length;
			this.scrollToActive();
		},
		downHandler() {
			this.selectedIndex = (this.selectedIndex + 1) % this.items.length;
			this.scrollToActive();
		},
		scrollToActive() {
			this.$nextTick(() => {
				const container = this.$el.querySelector(".tg-mention-scroller");
				const item = container?.querySelector(".is-selected");
				if (container && item) {
					const containerRect = container.getBoundingClientRect();
					const itemRect = item.getBoundingClientRect();

					if (itemRect.top < containerRect.top) {
						container.scrollTop -= containerRect.top - itemRect.top;
					} else if (itemRect.bottom > containerRect.bottom) {
						container.scrollTop += itemRect.bottom - containerRect.bottom;
					}
				}
			});
		},
		enterHandler() {
			this.selectItem(this.selectedIndex);
		},
		selectItem(index) {
			const item = this.items[index];
			if (item) {
				this.command(item);
			}
		},
	},
};
</script>

<style scoped>
.tg-mention-list {
	background: var(--tg-bg, #ffffff);
	border: 1px solid var(--tg-border, #e2e8f0);
	border-radius: 8px;
	box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
	padding: 4px;
	min-width: 280px;
	max-width: 380px;
	overflow: hidden;
	z-index: 15000;
	color: var(--tg-text, #1e293b);
}

.tg-mention-header {
	padding: 6px 8px 4px 8px;
	font-size: 10px;
	font-weight: 700;
	color: var(--tg-text-muted, #64748b);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	display: flex;
	align-items: center;
	gap: 6px;
	border-top: 1px solid var(--tg-border, #f1f5f9);
	margin-top: 4px;
}
.tg-mention-header:first-child {
	border-top: none;
	margin-top: 0;
}

.tg-mention-scroller {
	max-height: 280px;
	overflow-y: auto;
}

.tg-mention-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 8px;
	width: 100%;
	border: none;
	background: transparent;
	border-radius: 6px;
	cursor: pointer;
	text-align: left;
	transition: background-color 0.15s ease;
	color: var(--tg-text, #1e293b);
}

.tg-mention-item:hover,
.tg-mention-item.is-selected {
	background: var(--fxr-accent-soft, #eff6ff);
	color: var(--fxr-accent, #2563eb);
}

.tg-mention-item.is-incompatible {
	opacity: 0.6;
}

.item-icon {
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 6px;
	font-size: 11px;
	flex-shrink: 0;
}

.item-icon.field {
	background: var(--fxr-badge-primary, #e0f2fe);
	color: var(--fxr-badge-primary-text, #0369a1);
}
.item-icon.variable {
	background: var(--fxr-badge-bool, #dcfce7);
	color: var(--fxr-badge-bool-text, #15803d);
}
.item-icon.resolver {
	background: var(--fxr-badge-resolver, #fef3c7);
	color: var(--fxr-badge-resolver-text, #b45309);
}
.item-icon.logic {
	background: var(--fxr-badge-var, #f3e8ff);
	color: var(--fxr-badge-var-text, #7e22ce);
}

.item-info {
	display: flex;
	flex-direction: column;
	min-width: 0;
	flex: 1;
}

.item-label {
	font-size: 12px;
	font-weight: 600;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-secondary {
	font-size: 10px;
	color: var(--tg-text-muted, #64748b);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-badge {
	font-size: 9px;
	padding: 1px 4px;
	border-radius: 3px;
	background: var(--fxr-surface-2, #f1f5f9);
	color: var(--tg-text-muted, #64748b);
	font-weight: 600;
	margin-left: 4px;
}

.item-description {
	font-size: 11px;
	color: var(--tg-text-muted, #64748b);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-emoji {
	font-size: 13px;
	line-height: 1;
}

.tg-mention-empty {
	padding: 16px;
	text-align: center;
	color: #94a3b8;
	font-size: 12px;
}
</style>
