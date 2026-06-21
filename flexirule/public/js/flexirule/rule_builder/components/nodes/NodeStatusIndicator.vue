<script setup>
import { computed } from "vue";

const props = defineProps({
	status: {
		type: String,
		required: true,
		validator: (val) => ["not-configured", "configured", "invalid"].includes(val),
	},
	errors: {
		type: Array,
		default: () => [],
	},
});

const statusMeta = computed(() => {
	switch (props.status) {
		case "invalid":
			return {
				icon: "fa-exclamation-circle",
				label: __("Invalid Configuration"),
				class: "is-invalid",
			};
		case "configured":
			return {
				icon: "fa-check-circle",
				label: __("Configured"),
				class: "is-configured",
			};
		default:
			return {
				icon: "fa-circle-o",
				label: __("Not Configured"),
				class: "not-configured",
			};
	}
});

const tooltipContent = computed(() => {
	if (props.status === "invalid" && props.errors.length > 0) {
		return props.errors.join("\n");
	}
	return statusMeta.value.label;
});
</script>

<template>
	<div class="node-status-indicator" :class="statusMeta.class" :title="tooltipContent">
		<i class="fa" :class="statusMeta.icon"></i>
		<span class="status-label">{{ statusMeta.label }}</span>
	</div>
</template>

<style>
.node-status-indicator {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 10px;
	cursor: pointer;
	color: var(--fxr-text-faint);
	transition: all 0.2s ease;
	--indicator-color: var(--fxr-text-faint);
}

.node-status-indicator.is-configured {
	--indicator-color: var(--fxr-text-success, #198754);
	color: var(--indicator-color);
}

.node-status-indicator.is-invalid {
	--indicator-color: var(--fxr-text-danger, #dc3545);
	color: var(--indicator-color);
	font-weight: 600;
}

.node-status-indicator:hover {
	opacity: 0.8;
}

.stop-node-card .node-status-indicator {
	color: #ffffff !important;
	opacity: 0.8;
}

.stop-node-card .node-status-indicator.is-invalid {
	color: #fff1f2 !important;
}

.stop-node-card .node-status-indicator.is-invalid .status-label {
	text-decoration: underline;
}

.node-status-indicator i {
	font-size: 11px;
}
</style>
