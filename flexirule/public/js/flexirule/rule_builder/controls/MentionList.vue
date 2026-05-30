<template>
	<div class="tg-mention-list" v-if="items.length">
		<div class="tg-mention-header" v-if="triggerChar === '@'">
			<i class="fa fa-at"></i> {{ __("Variables") }}
		</div>
		<div class="tg-mention-header" v-else>
			<i class="fa fa-terminal"></i> {{ __("Logic Commands") }}
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
		{{ __("No results found") }}
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
				// Let Tiptap handle Escape to close the suggestion popup
				event.preventDefault();
				event.stopPropagation();
				event.stopImmediatePropagation();
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
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 12px;
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
	padding: 4px;
	min-width: 220px;
	overflow: hidden;
	z-index: 1000;
}

.tg-mention-header {
	padding: 8px 12px;
	font-size: 10px;
	font-weight: 700;
	color: #94a3b8;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	border-bottom: 1px solid #f1f5f9;
	margin-bottom: 4px;
}

.tg-mention-scroller {
	max-height: 240px;
	overflow-y: auto;
}

.tg-mention-item {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 8px 12px;
	width: 100%;
	border: none;
	background: transparent;
	border-radius: 8px;
	cursor: pointer;
	text-align: left;
	transition: all 0.2s;
}

.tg-mention-item:hover,
.tg-mention-item.is-selected {
	background: #f1f5f9;
}

.item-icon {
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 6px;
	font-size: 11px;
}

.item-icon.variable {
	background: #ecfdf5;
	color: #059669;
}
.item-icon.logic {
	background: #f5f3ff;
	color: #7c3aed;
}

.item-info {
	display: flex;
	flex-direction: column;
	min-width: 0;
}

.item-label {
	font-size: 13px;
	font-weight: 600;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-description {
	font-size: 11px;
	color: #64748b;
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
