<template>
	<div class="tg-mention-list" v-if="items.length">
		<div class="tg-mention-header" v-if="triggerChar === '@'">
			<i class="fa fa-at"></i> {{ t("Variables") }}
		</div>
		<div class="tg-mention-header" v-else>
			<i class="fa fa-terminal"></i> {{ t("Logic Commands") }}
		</div>

		<div class="tg-mention-scroller v2-scrollbar">
			<button
				v-for="(item, index) in items"
				:key="item.id || item"
				class="tg-mention-item"
				:class="{ 'is-selected': index === selectedIndex }"
				@mousedown.prevent="selectItem(index)"
			>
				<div class="item-icon" :class="item.type">
					<!-- Emoji icon takes priority over Font-Awesome for command items -->
					<span v-if="item.icon && !item.icon.startsWith('fa')" class="item-emoji">{{
						item.icon
					}}</span>
					<i v-else :class="getIcon(item)"></i>
				</div>
				<div class="item-info">
					<span class="item-label">{{ item.label || item.id || item }}</span>
					<span v-if="item.description" class="item-description">{{
						item.description
					}}</span>
				</div>
			</button>
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
			triggerChar: "@",
		};
	},
	watch: {
		items: {
			immediate: true,
			handler(newItems) {
				this.selectedIndex = 0;
				// Detect trigger from first item if possible
				if (newItems.length > 0) {
					this.triggerChar = newItems[0].type === "logic" ? "/" : "@";
				}
			},
		},
	},
	methods: {
		t(message) {
			const translate = globalThis.__;
			return typeof translate === "function" ? translate(message) : message;
		},
		getIcon(item) {
			if (item.type === "variable") return "fa fa-cube";
			if (item.type === "logic") {
				const iconMap = {
					formula: "fa fa-calculator",
					resolver: "fa fa-bolt",
					formatter: "fa fa-paint-brush",
					normalize: "fa fa-refresh",
					localization: "fa fa-globe",
					condition: "fa fa-code-fork",
					link: "fa fa-link",
					"dynamic-link": "fa fa-cubes",
				};
				return iconMap[item.id] || "fa fa-terminal";
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
	background: var(--tg-bg);
	border: 1px solid var(--tg-border);
	border-radius: 12px;
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
	padding: 6px;
	min-width: 240px;
	overflow: hidden;
	z-index: 1000;
	color: var(--tg-text);
}

.tg-mention-header {
	padding: 10px 12px;
	font-size: 10px;
	font-weight: 800;
	color: var(--tg-text-muted);
	text-transform: uppercase;
	letter-spacing: 0.08em;
	border-bottom: 1px solid var(--tg-border);
	margin-bottom: 6px;
}

.tg-mention-scroller {
	max-height: 280px;
	overflow-y: auto;
}

.tg-mention-item {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 8px 12px;
	width: 100%;
	border: none;
	background: transparent;
	border-radius: 10px;
	cursor: pointer;
	text-align: left;
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	color: var(--tg-text);
}

.tg-mention-item:hover,
.tg-mention-item.is-selected {
	background: color-mix(in srgb, var(--tg-accent) 10%, var(--tg-surface));
	color: var(--tg-text);
}

.tg-mention-item.is-selected {
	box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--tg-accent) 20%, transparent);
}

.item-icon {
	width: 28px;
	height: 28px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 8px;
	font-size: 12px;
	flex-shrink: 0;
}

.item-icon.variable {
	background: var(--fxr-badge-bool);
	color: var(--fxr-badge-bool-text);
}
.item-icon.logic {
	background: var(--fxr-badge-var);
	color: var(--fxr-badge-var-text);
}

.item-info {
	display: flex;
	flex-direction: column;
	min-width: 0;
}

.item-label {
	font-size: 13px;
	font-weight: 600;
	color: var(--tg-text);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-description {
	font-size: 11px;
	color: var(--tg-text-muted);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-emoji {
	font-size: 14px;
	line-height: 1;
}

.tg-mention-empty {
	padding: 16px;
	text-align: center;
	color: #94a3b8;
	font-size: 12px;
}
</style>
