<!--
  AutocompleteControl - Robust implementation for Grid integration
-->
<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
const props = defineProps({
	df: Object,
	modelValue: [String, Number],
	read_only: Boolean,
	options: { type: Array, default: null },
	get_options: { type: Function, default: null },
	doc: { type: Object, default: null },
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
	showOnFocus: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const wrapper_ref = ref(null);
let frappe_control = null;
let is_setting_value = false;

onMounted(async () => {
	await nextTick();
	await init_control();
});

onUnmounted(() => {
	destroy_control();
});

function destroy_control() {
	if (frappe_control) {
		if (frappe_control.$input) {
			frappe_control.$input.off("awesomplete-selectcomplete");
			frappe_control.$input.off("awesomplete-open"); // Remove our handler
		}
		if (frappe_control.awesomplete) {
			try {
				const ul = frappe_control.awesomplete.ul;
				frappe_control.awesomplete.destroy();
				// Ensure UL is removed if it was moved to body
				if (ul && ul.parentNode === document.body) {
					document.body.removeChild(ul);
				}
			} catch (e) {
				// Ignore errors during cleanup
			}
		}
	}
	frappe_control = null;
}

async function init_control() {
	if (!wrapper_ref.value) return;

	destroy_control();
	wrapper_ref.value.innerHTML = "";

	const control_df = {
		...props.df,
		fieldtype: "Autocomplete",
		hidden: 0,
		read_only: props.read_only,
		ignore_validation: true,
		change: () => {
			if (frappe_control && !is_setting_value) {
				const value = frappe_control.get_value();
				if (value !== props.modelValue) {
					emit("update:modelValue", value);
				}
			}
		},
	};

	if (props.showOnFocus) {
		control_df.on_focus = () => {
			if (frappe_control && frappe_control.awesomplete) {
				frappe_control.awesomplete.minChars = 0;
				frappe_control.awesomplete.evaluate();
				frappe_control.awesomplete.open();
			}
		};
	}

	const ControlClass = frappe.ui.form.ControlAutocomplete;
	frappe_control = new ControlClass({
		df: control_df,
		parent: $(wrapper_ref.value),
		render_input: true,
		only_input: true,
	});
	frappe_control.make();

	// Fix clipping issues in Grid/Modal by moving dropdown to body
	if (frappe_control.awesomplete) {
		const awesomplete = frappe_control.awesomplete;

		// Move UL to body
		if (awesomplete.ul && awesomplete.ul.parentNode !== document.body) {
			document.body.appendChild(awesomplete.ul);
			awesomplete.ul.classList.add("flexirule-autocomplete-dropdown");
		}

		// Cleanup on destroy is simpler if we track it?
		// Actually awesomplete.destroy() attempts to remove ul from its parent.
		// Since we moved it, we should ensure it's removed correctly in destroy_control.

		// Position update function
		const updatePosition = () => {
			if (!frappe_control || !frappe_control.$input) return;
			const input = frappe_control.$input[0];
			const rect = input.getBoundingClientRect();
			const ul = awesomplete.ul;

			ul.style.position = "fixed";
			ul.style.zIndex = "100010"; // Higher than most modals
			ul.style.top = rect.bottom + 2 + "px"; // 2px margin
			ul.style.left = rect.left + "px";
			ul.style.width = rect.width + "px";
			ul.style.minWidth = "150px";
		};

		// Hook into open event to position
		frappe_control.$input.on("awesomplete-open", updatePosition);

		// Optionally hook into window scroll/resize to close (simpler than repositioning)
		// Or reposition?
		// window.addEventListener('scroll', updatePosition, true); // capture phase for all scrolls
	}

	await set_options();

	if (props.modelValue !== undefined && props.modelValue !== null) {
		is_setting_value = true;
		frappe_control.set_value(props.modelValue);
		setTimeout(() => {
			is_setting_value = false;
		}, 50);
	}

	if (frappe_control.$input) {
		frappe_control.$input.on("awesomplete-selectcomplete", () => {
			if (!is_setting_value) {
				const value = frappe_control.get_value();
				emit("update:modelValue", value);
			}
		});
	}
}

async function set_options() {
	if (!frappe_control) return;
	let opts = [];
	if (typeof props.get_options === "function") {
		try {
			opts = await props.get_options(props.doc);
		} catch (e) {
			opts = [];
		}
	} else if (props.options && Array.isArray(props.options)) {
		opts = props.options;
	} else if (props.df?.options && typeof props.df.options === "string") {
		opts = props.df.options
			.split("\n")
			.filter(Boolean)
			.map((o) => ({ value: o.trim(), label: o.trim() }));
	}

	if (opts.length && frappe_control.set_data) {
		frappe_control.set_data(opts);
	}
}

watch(
	() => props.modelValue,
	(newVal) => {
		if (frappe_control && !is_setting_value && frappe_control.get_value() !== newVal) {
			is_setting_value = true;
			frappe_control.set_value(newVal || "");
			setTimeout(() => {
				is_setting_value = false;
			}, 50);
		}
	}
);

watch(
	() => [props.df?.fieldname, props.df?.fieldtype],
	async () => {
		await init_control();
	}
);

watch(
	() => props.options,
	async () => {
		await set_options();
	},
	{ deep: true }
);
watch(
	() => props.read_only,
	(newVal) => {
		if (frappe_control) {
			if (typeof frappe_control.set_enabled === "function") {
				frappe_control.set_enabled(!newVal);
			} else {
				frappe_control.df.read_only = newVal ? 1 : 0;
				frappe_control.refresh();
			}
		}
	}
);

function onDrop(event) {
	let variable = event.dataTransfer.getData("application/x-flexirule-variable");
	if (variable) {
		event.preventDefault();

		// Sanitize variable name to prevent injection/breaking templates
		if (/[{}"']/.test(variable)) {
			console.warn("FlexiRule: Rejected unsafe variable name drop:", variable);
			return;
		}

		if (frappe_control) {
			// In Autocomplete, we usually replace the whole value with the variable name (no brackets)
			emit("update:modelValue", variable);
		}
	}
}
</script>

<template>
	<div class="fr-control" :class="{ 'no-label': hideLabel }">
		<div v-if="df?.label && !hideLabel" class="fr-label" :class="{ reqd: df.reqd }">
			{{ __(df.label) }}
		</div>
		<div
			ref="wrapper_ref"
			class="autocomplete-input-wrapper"
			@dragover.prevent
			@drop="onDrop"
		></div>
		<div v-if="df?.description && !hideDescription" class="fr-description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style scoped>
.autocomplete-input-wrapper {
	position: relative;
}

.autocomplete-input-wrapper :deep(.form-control) {
	font-size: var(--fr-text-base);
	padding: var(--fr-input-padding-y) var(--fr-input-padding-x);
	height: var(--fr-input-height);
	width: 100%;
	color: var(--fr-text);
	background-color: var(--fr-bg-card);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-md);
	transition: all var(--fr-transition-fast);
}

.autocomplete-input-wrapper :deep(.form-control:focus) {
	border-color: var(--fr-accent);
	box-shadow: var(--fr-shadow-focus);
	outline: none;
}

.autocomplete-input-wrapper :deep(.form-control:hover:not(:disabled):not(:focus)) {
	border-color: var(--fr-border-strong);
}

.autocomplete-input-wrapper :deep(.awesomplete) {
	width: 100%;
	display: block;
}

.autocomplete-input-wrapper :deep(.awesomplete > ul) {
	z-index: var(--fr-z-dropdown);
	max-height: 200px;
	overflow-y: auto;
}

/* Global style for teleported dropdown */
:global(.flexirule-autocomplete-dropdown) {
	z-index: var(--fr-z-dropdown) !important;
	box-shadow: var(--fr-shadow-lg);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-md);
	background: var(--fr-bg-card);
	max-height: 200px;
	overflow-y: auto;
	padding: var(--fr-space-2) 0;
	margin: 0;
	list-style: none;
	position: fixed;
}

:global(.flexirule-autocomplete-dropdown li) {
	padding: var(--fr-space-3) var(--fr-space-5);
	cursor: pointer;
	font-size: var(--fr-text-sm);
	color: var(--fr-text);
	transition: background var(--fr-transition-fast);
}

:global(.flexirule-autocomplete-dropdown li:hover),
:global(.flexirule-autocomplete-dropdown li[aria-selected="true"]) {
	background-color: var(--fr-bg-hover);
	color: var(--fr-accent);
}

:global(.flexirule-autocomplete-dropdown mark) {
	background: transparent;
	font-weight: var(--fr-weight-bold);
	color: inherit;
	padding: 0;
}
</style>
