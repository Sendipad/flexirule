<template>
	<div
		class="value-resolver-control fxr-control"
		ref="controlRef"
		:data-fxr-fieldname="resolverFieldname"
	>
		<!-- Token UI -->
		<div
			v-if="viewMode === 'popover'"
			ref="tokenRef"
			class="fxr-token"
			:class="{ 'is-active': showPopover, 'is-invalid': !isValid }"
			tabindex="0"
			@click="togglePopover"
			@keydown="handleParentKeydown"
			v-tippy="validationTooltip"
		>
			<div class="fxr-token__content">
				<i :class="activeStrategy?.icon" class="text-muted mr-1"></i>
				<span class="fxr-token__text">{{ previewText }}</span>
			</div>
			<i class="fa fa-chevron-down fxr-token__caret"></i>
		</div>

		<!-- Main Content Wrapper -->
		<Teleport to="body" :disabled="viewMode === 'inline'">
			<div
				v-if="viewMode === 'inline' || showPopover"
				ref="popoverRef"
				:class="
					viewMode === 'inline'
						? 'fxr-inline-builder'
						: 'fxr-popover value-resolver-popover'
				"
				:style="viewMode === 'inline' ? {} : popoverStyle"
				:data-fxr-fieldname="resolverFieldname"
			>
				<div v-if="viewMode !== 'inline'" class="fxr-popover__header">
					<span class="fxr-label-sm mb-0">{{ __(popoverTitle) }}</span>
					<button class="fxr-btn fxr-btn--icon fxr-btn--sm" @click="closePopover">
						<i class="fa fa-times"></i>
					</button>
				</div>
				<div :class="viewMode === 'inline' ? 'fxr-inline-body' : 'fxr-popover__body'">
					<!-- Category Selector -->
					<div class="d-flex flex-column fxr-gap-1">
						<label class="fxr-label-sm">{{ __("Formula Type") }}</label>
						<select
							ref="kindSelectRef"
							class="fxr-select"
							v-model="activeKind"
							:disabled="readOnly"
							data-fxr-fieldname="value_resolver.kind"
						>
							<option
								v-for="cat in availableStrategies"
								:key="cat.kind"
								:value="cat.kind"
							>
								{{ cat.label }}
							</option>
						</select>
					</div>

					<hr class="my-2 border-top" />

					<!-- Dynamic Strategy Component -->
					<component
						v-if="activeStrategy?.component"
						:is="activeStrategy.component"
						v-model="localState"
						:doctype="doctype"
						:readOnly="readOnly"
						:context="context"
						:variableOptions="variableOptions"
					/>
				</div>
				<div :class="viewMode === 'inline' ? 'fxr-inline-footer' : 'fxr-popover__footer'">
					<div class="fxr-preview-snippet">
						<code>{{ expressionSnippet }}</code>
					</div>
					<div v-if="errors.length" class="fxr-validation-errors mt-2">
						<div v-for="err in errors" :key="err" class="text-danger fxr-text-xs">
							<i class="fa fa-exclamation-triangle mr-1"></i> {{ err }}
						</div>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useFloatingDropdown } from "../composables/useFloatingDropdown";
import { useKeyboardRegistry } from "../composables/useKeyboardRegistry";
import { useValueResolver } from "./value_resolver/useValueResolver";
import "./value_resolver/index"; // Initialize strategies
import { __ } from "./value_resolver/utils";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({}),
	},
	doctype: {
		type: String,
		default: "",
	},
	context: {
		type: Object,
		default: () => ({}),
	},
	variableOptions: {
		type: Array,
		default: () => [],
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
	/** Restrict which formula categories are available */
	allowedKinds: {
		type: Array,
		default: null,
	},
	/** 'popover' (default) or 'inline' */
	viewMode: {
		type: String,
		default: "popover",
	},
});

const emit = defineEmits(["update:modelValue"]);

const tokenRef = ref(null);
const kindSelectRef = ref(null);
const { registerShortcut } = useKeyboardRegistry();
const unregisterEsc = ref(null);

const {
	localState,
	activeKind,
	activeStrategy,
	availableStrategies,
	isValid,
	errors,
	syncFromProps,
} = useValueResolver(props, emit);

const {
	triggerRef: controlRef,
	dropdownRef: popoverRef,
	isOpen: showPopover,
	dropdownStyle: popoverStyle,
	openDropdown,
	closeDropdown,
	toggleDropdown: baseTogglePopover,
	updatePosition,
	cleanup: cleanupFloatingDropdown,
} = useFloatingDropdown({
	minWidth: 280,
	maxWidth: 400,
	maxHeight: 500,
	matchTriggerWidth: false,
});

const resolverFieldname = computed(() => {
	const fieldname =
		props.context?.fieldname ||
		props.context?.target ||
		props.context?.df?.fieldname ||
		props.context?.df?.value ||
		"value_resolver";
	return String(fieldname)
		.replace(/^doc\./, "")
		.replace(/^vars\./, "");
});

watch(() => props.modelValue, syncFromProps, { deep: true });
watch(() => props.doctype, syncFromProps);

onMounted(() => {
	syncFromProps();
	document.addEventListener("mousedown", handleClickOutside);
});

onBeforeUnmount(() => {
	document.removeEventListener("mousedown", handleClickOutside);
	if (unregisterEsc.value) unregisterEsc.value();
	cleanupFloatingDropdown();
});

const handleClickOutside = (e) => {
	if (!showPopover.value) return;
	if (controlRef.value?.contains(e.target)) return;
	if (popoverRef.value?.contains(e.target)) return;

	const target = e.target;
	if (target.closest(".fxr-dropdown") || target.closest(".tippy-box")) {
		return;
	}

	closePopover();
};

const handleParentKeydown = (e) => {
	if (props.readOnly) return;
	if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
		e.preventDefault();
		if (!showPopover.value) open();
	}
};

const togglePopover = () => {
	if (props.readOnly) return;
	if (showPopover.value) closePopover();
	else open();
};

const open = async () => {
	if (props.readOnly || showPopover.value) return;
	openDropdown();

	await nextTick();
	if (kindSelectRef.value) {
		kindSelectRef.value.focus();
	}

	unregisterEsc.value = registerShortcut({
		key: "Escape",
		priority: 20,
		callback: () => closePopover(),
	});
};

const closePopover = () => {
	if (!showPopover.value) return;
	closeDropdown();
	if (unregisterEsc.value) {
		unregisterEsc.value();
		unregisterEsc.value = null;
	}

	nextTick(() => {
		tokenRef.value?.focus();
	});
};

defineExpose({
	open,
	close: closePopover,
	focus: () => tokenRef.value?.focus(),
});

const popoverTitle = computed(() => {
	return activeStrategy.value?.label || __("Configure Formula");
});

const previewText = computed(() => {
	return activeStrategy.value?.compileToLabel(localState.value) || __("Configure");
});

const expressionSnippet = computed(() => {
	return activeStrategy.value?.compileToCode(localState.value) || "";
});

const validationTooltip = computed(() => {
	if (isValid.value) return null;
	return {
		content: errors.value.join(", "),
		theme: "error",
		placement: "top",
	};
});

// Update position when local state changes (e.g. dynamic fields appear)
watch(
	localState,
	() => {
		if (showPopover.value) {
			nextTick(() => updatePosition());
		}
	},
	{ deep: true }
);
</script>

<style scoped>
.fxr-preview-snippet {
	font-family: var(--fxr-font-mono);
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
	text-align: center;
	word-break: break-all;
}

.fxr-inline-builder {
	display: flex;
	flex-direction: column;
	width: 100%;
}

.fxr-inline-body {
	padding: var(--fxr-space-1) 0;
}

.fxr-inline-footer {
	margin-top: var(--fxr-space-4);
	padding-top: var(--fxr-space-2);
	border-top: 1px solid var(--fxr-border);
}

hr.border-top {
	border-color: var(--fxr-border);
	opacity: 0.5;
	margin: var(--fxr-space-2) 0;
}

.fxr-token.is-invalid {
	border-color: var(--red-400, #f87171);
	background: var(--red-50, #fef2f2);
}
</style>

<style>
.value-resolver-popover {
	padding: 10px;
	width: 280px;
	overflow-y: auto;
}
.value-resolver-popover .fxr-popover__header {
	padding-bottom: 8px;
	margin-bottom: 8px;
	border-bottom: 1px solid var(--fxr-border, #e2e8f0);
}
.value-resolver-popover .fxr-popover__body {
	padding: 0;
}
.value-resolver-popover .fxr-select,
.value-resolver-popover .fxr-input {
	padding: 2px 6px;
	min-height: 28px;
	font-size: 11px;
}
.value-resolver-popover label.fxr-label-sm {
	margin-bottom: 2px;
	font-size: 10px;
}
.value-resolver-popover hr.border-top {
	margin: 8px 0 !important;
}
</style>
