<template>
	<div
		class="value-resolver-control fxr-control"
		ref="controlRef"
		v-fxr-fieldname="resolverFieldname"
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
				<span class="fxr-token__icon-wrap" aria-hidden="true">
					<i :class="activeStrategy?.icon || 'fa fa-bolt'" class="token-prefix-icon"></i>
				</span>
				<span class="fxr-token__details">
					<span class="fxr-token__kind">{{ activeStrategy?.label || __('Resolver') }}</span>
					<span class="fxr-token__text" :title="previewText">{{ previewText }}</span>
				</span>
			</div>
			<i class="fa fa-chevron-down fxr-token__caret" aria-hidden="true"></i>
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
				@keydown="handlePopoverKeydown"
			>
				<div :class="viewMode === 'inline' ? 'fxr-inline-body' : 'fxr-popover__body'">
					<!-- Category Selector -->
					<div class="d-flex flex-column fxr-gap-1">
						<div class="d-flex align-items-center justify-content-between">
							<label class="fxr-label-sm mb-0">{{ __("Formula Type") }}</label>
							<button
								v-if="viewMode !== 'inline'"
								class="resolver-close-btn"
								@click="closePopover"
								:title="__('Close')"
							>
								<i class="fa fa-times"></i>
							</button>
						</div>
						<ComboBoxControl
							ref="kindSelectRef"
							v-model="activeKind"
							:options="availableStrategies"
							:read_only="readOnly"
							:trigger="'button'"
							:hideLabel="true"
							class="kind-selector-dropdown"
							:dropdownMinWidth="120"
							:dropdownMaxWidth="280"
							:map="{ value: 'kind', label: 'label', icon: 'icon' }"
						/>
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
				<div
					:class="viewMode === 'inline' ? 'fxr-inline-footer' : 'fxr-popover__footer'"
					class="mt-3"
				>
					<div class="fxr-preview-snippet mb-2">
						<code>{{ expressionSnippet }}</code>
					</div>
					<div v-if="activeStrategy?.description" class="fxr-strategy-help mb-2">
						<i class="fa fa-info-circle mr-1 text-muted"></i>
						<span>{{ __(activeStrategy.description) }}</span>
					</div>
					<div v-if="errors.length" class="fxr-validation-errors">
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
import { deepClone } from "../utils/serialization";
import { useFloatingDropdown } from "../composables/useFloatingDropdown";
import { useKeyboardRegistry } from "../composables/useKeyboardRegistry";
import { useFocusTrap } from "../composables/useFocusTrap";
import ComboBoxControl from "./ComboBoxControl.vue";
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
const { handleTab } = useFocusTrap();
const unregisterEsc = ref(null);
const backupState = ref(null);

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
	zIndex: 15000,
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
	if (
		target.closest(".fxr-dropdown") ||
		target.closest(".tippy-box") ||
		target.closest(".fxr-modal-overlay") ||
		target.closest(".fxr-modal-card")
	) {
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

const handlePopoverKeydown = (e) => {
	if (e.key === "Tab") {
		handleTab(e, popoverRef.value);
	}
};

const togglePopover = () => {
	if (props.readOnly) return;
	if (showPopover.value) closePopover();
	else open();
};

const open = async () => {
	if (props.readOnly || showPopover.value) return;

	// Backup state for cancel support
	backupState.value = {
		kind: activeKind.value,
		config: deepClone(localState.value),
	};

	openDropdown();

	await nextTick();
	if (kindSelectRef.value) {
		kindSelectRef.value.focus();
	}

	unregisterEsc.value = registerShortcut({
		key: "Escape",
		priority: 20,
		callback: () => cancelPopover(),
	});
};

const cancelPopover = () => {
	if (!showPopover.value) return;

	// Restore backup state
	if (backupState.value) {
		activeKind.value = backupState.value.kind;
		localState.value = backupState.value.config;
	}

	closePopover();
};

const closePopover = () => {
	if (!showPopover.value) return;
	closeDropdown();
	backupState.value = null;

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
	validate: () => ({ valid: isValid.value, errors: errors.value }),
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
hr.border-top {
	border-color: var(--fxr-border);
	opacity: 0.5;
	margin: var(--fxr-space-2) 0;
}

.token-prefix-icon {
	color: var(--fxr-accent-icon, var(--fxr-accent));
	font-size: 12px;
	opacity: 0.85;
}

.kind-selector-dropdown :deep(.combobox-wrapper) {
	width: 100%;
}

.resolver-close-btn {
	background: var(--fxr-bg-muted);
	color: var(--fxr-text-muted);
	border: none;
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 6px;
	cursor: pointer;
	transition: all 0.2s ease;
	margin-top: -4px;
	margin-right: -4px;
}

.resolver-close-btn:hover {
	background: var(--fxr-danger-soft);
	color: var(--fxr-text-danger);
	transform: rotate(90deg);
}

.fxr-token {
	display: flex;
	align-items: center;
	gap: 8px;
	min-width: 0;
	max-width: 100%;
	min-height: 30px;
	padding: 3px 8px 3px 5px;
	border: 1px solid var(--fxr-border);
	border-radius: 8px;
	background: var(--fxr-bg-input, var(--fxr-bg));
	color: var(--fxr-text);
	box-shadow: 0 1px 2px rgb(15 23 42 / 4%);
	transition: border-color 150ms ease, background-color 150ms ease, box-shadow 150ms ease;
}
.fxr-token:hover,
.fxr-token.is-active {
	border-color: var(--fxr-accent);
	background: var(--fxr-bg-muted, var(--fxr-bg-input));
}
.fxr-token:focus-visible {
	outline: 2px solid var(--fxr-accent);
	outline-offset: 2px;
}
.fxr-token__content {
	display: flex;
	align-items: center;
	gap: 8px;
	flex: 1;
	min-width: 0;
}
.fxr-token__icon-wrap {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex: 0 0 26px;
	width: 26px;
	height: 26px;
	border-radius: 6px;
	background: var(--fxr-accent-soft, var(--fxr-bg-muted));
}
.fxr-token__icon-wrap .token-prefix-icon {
	margin: 0;
	font-size: 12px;
	color: var(--fxr-accent);
}
.fxr-token__details {
	display: flex;
	flex-direction: column;
	gap: 1px;
	min-width: 0;
	flex: 1;
	line-height: 1.2;
}
.fxr-token__kind {
	font-size: 10px;
	font-weight: 700;
	letter-spacing: .035em;
	text-transform: uppercase;
	color: var(--fxr-text-muted);
}
.fxr-token__text {
	display: block;
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 12px;
	font-weight: 600;
	color: var(--fxr-text);
}
.fxr-token__caret {
	flex: 0 0 auto;
	font-size: 10px;
	color: var(--fxr-text-muted);
	transition: transform 150ms ease;
}
.fxr-token.is-active .fxr-token__caret {
	transform: rotate(180deg);
}
.fxr-token.is-invalid {
	border-color: var(--fxr-danger, #dc2626);
	background: var(--fxr-danger-soft, #fef2f2);
}
@media (prefers-reduced-motion: reduce) {
	.fxr-token,
	.fxr-token__caret {
		transition: none;
	}
}

/* Ensure the category selector doesn't overflow its parent popover */
.value-resolver-popover {
	max-width: min(400px, 95vw);
	padding: var(--spacing-md);
}
</style>
