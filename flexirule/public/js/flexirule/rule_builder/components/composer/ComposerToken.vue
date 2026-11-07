<template>
	<span
		class="composer-token"
		:class="[
			tokenKindClass,
			{ 'is-interactive': interactive && !readOnly, 'is-configured': hasConfig },
		]"
		@click="onClick"
	>
		<i v-if="tokenIcon" :class="tokenIcon" class="composer-token-icon"></i>
		<span class="composer-token-label">{{ displayLabel }}</span>

		<!-- Optional inline flyout toggle or remove button -->
		<button
			v-if="!readOnly && removable"
			type="button"
			class="composer-token-remove"
			@click.stop="$emit('remove')"
			:title="__('Remove token')"
		>
			<i class="fa fa-times"></i>
		</button>
	</span>
</template>

<script setup>
import { computed } from "vue";
import { getResolverIcon } from "./ComposerContextAdapter.js";

const props = defineProps({
	modelValue: { type: Object, default: () => null },
	readOnly: { type: Boolean, default: false },
	interactive: { type: Boolean, default: true },
	removable: { type: Boolean, default: true },
});

const emit = defineEmits(["click", "remove", "configure"]);

const tokenKind = computed(() => {
	const val = props.modelValue;
	if (!val) return "empty";
	if (val.mode === "variable") {
		const scope = val.path?.scope;
		if (scope === "doc" || scope === "old_doc") return "document";
		return "variable";
	}
	if (val.mode === "resolver") return "resolver";
	if (val.mode === "static") return "static";
	if (val.mode === "template") return "template";
	return "custom";
});

const tokenKindClass = computed(() => {
	return `token--${tokenKind.value}`;
});

const tokenIcon = computed(() => {
	const val = props.modelValue;
	if (!val) return null;
	if (val.mode === "variable") {
		const scope = val.path?.scope;
		if (scope === "doc" || scope === "old_doc") return "fa fa-file-text-o";
		return "fa fa-database";
	}
	if (val.mode === "resolver") {
		return getResolverIcon(val.family, val.operation);
	}
	if (val.mode === "static") {
		return null;
	}
	return "fa fa-code";
});

const hasConfig = computed(() => {
	const val = props.modelValue;
	if (val?.mode === "resolver") {
		return Object.keys(val.config || {}).length > 0;
	}
	return false;
});

const displayLabel = computed(() => {
	const val = props.modelValue;
	if (!val) return "";

	if (val.mode === "variable") {
		const scope = val.path?.scope || "doc";
		const segments = Array.isArray(val.path?.segments) ? val.path.segments : [];
		return segments.length > 0 ? `@${scope}.${segments.join(".")}` : `@${scope}`;
	}

	if (val.mode === "resolver") {
		const prefix = `@${val.family}.${val.operation}`;
		// If formula has expression, show compact preview
		if (val.family === "math" && val.operation === "formula" && val.config?.expression) {
			return `${prefix}: ${val.config.expression}`;
		}
		if (val.family === "date_time" && val.config?.token) {
			return `${prefix}: ${val.config.token}`;
		}
		return prefix;
	}

	if (val.mode === "static") {
		if (val.value_type === "list" && Array.isArray(val.value)) {
			return `[${val.value.join(", ")}]`;
		}
		if (val.value_type === "boolean") {
			return val.value ? "true" : "false";
		}
		return String(val.value ?? "");
	}

	return JSON.stringify(val);
});

function onClick(e) {
	if (props.readOnly || !props.interactive) return;
	emit("click", e);
	if (props.modelValue?.mode === "resolver") {
		emit("configure", props.modelValue);
	}
}
</script>

<style scoped>
.composer-token {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	padding: 2px 8px;
	border-radius: 9999px;
	font-size: 12px;
	line-height: 1.4;
	font-weight: 500;
	user-select: none;
	transition: all 0.15s ease;
	border: 1px solid transparent;
}

.composer-token.is-interactive {
	cursor: pointer;
}

.composer-token.is-interactive:hover {
	filter: brightness(0.95);
}

.composer-token-icon {
	font-size: 11px;
	opacity: 0.8;
}

.composer-token-label {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	max-width: 240px;
}

.composer-token-remove {
	border: none;
	background: transparent;
	padding: 0;
	margin-left: 2px;
	font-size: 10px;
	color: inherit;
	opacity: 0.6;
	cursor: pointer;
	display: inline-flex;
	align-items: center;
}

.composer-token-remove:hover {
	opacity: 1;
}

/* ── Semantic Tints ── */
.token--document {
	background: #eef2ff;
	color: #4338ca;
	border-color: #c7d2fe;
}

.token--variable {
	background: #f0fdf4;
	color: #15803d;
	border-color: #bbf7d0;
}

.token--resolver {
	background: #faf5ff;
	color: #7e22ce;
	border-color: #e9d5ff;
}

.token--static {
	background: #f8fafc;
	color: #334155;
	border-color: #e2e8f0;
}

.token--template {
	background: #fffbeb;
	color: #b45309;
	border-color: #fde68a;
}
</style>
