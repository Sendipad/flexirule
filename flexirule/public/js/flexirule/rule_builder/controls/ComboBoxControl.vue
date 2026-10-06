<template>
	<div
		class="fxr-control"
		:class="{
			'no-label': hideLabel,
			'has-error': showValidation && !isValid,
		}"
		v-fxr-fieldname="df?.fieldname || fieldname || null"
	>
		<div
			class="fxr-input-group"
			:class="{
				'has-floating-label': df?.label && !hideLabel,
				'has-value': modelValue !== undefined && modelValue !== null && modelValue !== '',
			}"
		>
			<label v-if="df?.label && !hideLabel" class="fxr-label" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</label>

			<div class="combobox-container" ref="wrapperRef" @focusout="onFocusOut">
				<div
					class="combobox-wrapper"
					:class="{
						'is-focused': isDropdownOpen,
						'is-button-mode': trigger === 'button',
					}"
				>
					<div class="combobox-input-group">
						<!-- Prefix Slot / Selected Icon -->
						<div v-if="selectedOption?.icon || $slots.prefix" class="selection-icon">
							<slot name="prefix" v-bind="{ selectedOption }">
								<i v-if="selectedOption?.icon" :class="selectedOption.icon"></i>
							</slot>
						</div>

						<!-- Trigger: Button Mode -->
						<button
							v-if="trigger === 'button'"
							class="combobox-button-trigger"
							@click.prevent="toggleDropdown"
							@keydown="onKeydown"
							:disabled="read_only"
						>
							<span class="selected-label truncate">
								{{ displayValue || placeholder || __("Select option") }}
							</span>
							<i
								class="fa fa-chevron-down ml-2 text-xs opacity-50 transition-transform"
								:class="{ 'rotate-180': isDropdownOpen }"
							></i>
						</button>

						<!-- Trigger: Input Mode -->
						<input
							v-else
							ref="mainInputRef"
							type="text"
							class="combobox-input"
							:value="isDropdownOpen ? query : displayValue"
							@input="onInput"
							@focus="onFocus"
							@keydown="onKeydown"
							:placeholder="__(placeholder || df?.placeholder || '')"
							autocomplete="off"
							:disabled="read_only"
						/>

						<!-- Clear Button -->
						<button
							v-if="trigger === 'input' && modelValue && !read_only"
							class="combobox-trigger clear-btn"
							@click.prevent="onSelect('')"
							title="Clear"
							tabindex="-1"
						>
							<i class="fa fa-times"></i>
						</button>

						<!-- Open Link Button — excluded from keyboard tab flow -->
						<button
							v-if="
								(df?.fieldtype === 'Link' || df?.fieldtype === 'Dynamic Link') &&
								modelValue
							"
							class="combobox-trigger open-link-btn"
							title="Open in new tab"
							tabindex="-1"
							@click.stop.prevent="openLink"
						>
							<i class="fa fa-external-link"></i>
						</button>

						<!-- Dropdown Chevron -->
						<button
							v-if="trigger === 'input'"
							class="combobox-trigger"
							@click.prevent="toggleDropdown"
							:disabled="read_only"
							tabindex="-1"
						>
							<i
								class="fa fa-chevron-down transition-transform"
								:class="{ 'rotate-180': isDropdownOpen }"
							></i>
						</button>
					</div>
				</div>

				<Teleport to="body">
					<transition name="dropdown-fade">
						<div
							v-if="isDropdownOpen"
							class="fxr-dropdown"
							:class="{ 'has-search': trigger === 'button' && !hideSearch }"
							:style="dropdownStyle"
							ref="optionsRef"
							tabindex="-1"
							@mousedown.prevent
							@keydown="onKeydown"
						>
							<!-- Breadcrumbs navigation header -->
							<div v-if="navStack && navStack.length > 0" class="nav-breadcrumbs-bar">
								<button
									v-if="navStack.length > 1"
									class="nav-back-btn"
									type="button"
									title="Back"
									@click.stop.prevent="onBack(navStack.length - 2)"
								>
									<i class="fa fa-arrow-left"></i>
								</button>
								<div class="breadcrumbs-list truncate">
									<template v-for="(item, idx) in navStack" :key="idx">
										<span v-if="idx > 0" class="breadcrumb-separator">/</span>
										<button
											type="button"
											v-if="idx < navStack.length - 1"
											class="breadcrumb-link"
											@click.stop.prevent="onBack(idx)"
										>
											{{ __(item.label) }}
										</button>
										<span v-else class="breadcrumb-current">{{
											__(item.label)
										}}</span>
									</template>
								</div>
							</div>

							<!-- Search box inside popover for button mode -->
							<div v-if="trigger === 'button' && !hideSearch" class="popover-search">
								<i class="fa fa-search text-muted mr-2"></i>
								<input
									ref="popoverSearchInput"
									class="popover-search-input"
									:value="query"
									@input="onInput"
									@keydown="onKeydown"
									:placeholder="__('Search...')"
									autocomplete="off"
								/>
							</div>

							<div v-if="loading" class="fxr-dropdown-item text-center text-muted">
								<i class="fa fa-spinner fa-spin mr-2"></i>
								{{ __("Loading...") }}
							</div>

							<div
								v-else-if="
									(filteredOptions || []).length === 0 &&
									query !== '' &&
									!allowCustomValue
								"
								class="fxr-dropdown-item text-center text-muted"
							>
								{{ __("No results found") }}
							</div>

							<!-- Create New Option -->
							<div
								v-if="canAcceptCustom && query !== '' && !exactMatch"
								class="fxr-dropdown-item is-create"
								:class="{ active: activeIndex === -2 }"
								@click="onSelect(query)"
								@mouseover="activeIndex = -2"
							>
								<div class="option-content">
									<div class="option-icon"><i class="fa fa-plus"></i></div>
									<div class="option-text">
										<div class="option-label text-primary font-medium">
											{{ __("Create '{0}'", [query]) }}
										</div>
									</div>
								</div>
							</div>

							<div
								v-for="(option, idx) in filteredOptions"
								:key="option.value || idx"
								class="fxr-dropdown-item"
								:class="{
									active: idx === activeIndex,
									selected: isOptionSelected(option.value),
									'is-compact': hideLabel,
								}"
								@click="onSelect(option.value)"
								@mouseover="activeIndex = idx"
							>
								<div class="option-content">
									<div v-if="option.icon" class="option-icon">
										<i :class="option.icon"></i>
									</div>
									<div class="option-text">
										<div class="option-label-row">
											<span class="option-label">
												{{ __(option.label || option.value) }}
											</span>
											<span
												v-if="option.raw?.fieldtype || option.raw?.type"
												class="option-badge"
												:class="
													'type-' +
													String(
														option.raw?.fieldtype ||
															option.raw?.type ||
															''
													)
														.toLowerCase()
														.replace(' ', '-')
												"
											>
												{{ option.raw?.fieldtype || option.raw?.type }}
											</span>
										</div>
										<div
											v-if="option.description"
											class="option-description text-muted"
										>
											{{ __(option.description) }}
										</div>
									</div>
									<div
										v-if="isOptionSelected(option.value)"
										class="selected-check"
									>
										<i class="fa fa-check"></i>
									</div>
									<button
										v-if="
											navigable && (option.navigable || option.raw?.navigable)
										"
										type="button"
										class="option-nav-btn"
										:title="
											__('Navigate into {0}', [
												__(option.label || option.value),
											])
										"
										@click.stop.prevent="onNavigate(option)"
									>
										<i class="fa fa-chevron-right"></i>
									</button>
								</div>
							</div>

							<!-- Custom Slot for Footer (like 'Add New') -->
							<slot name="footer"></slot>
						</div>
					</transition>
				</Teleport>
			</div>
		</div>

		<div v-if="df?.description && !hideDescription" class="fxr-description">
			{{ __(df.description) }}
		</div>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} is required").replace("{0}", df?.label || __("Field")) }}
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, onBeforeUnmount } from "vue";
import { useMetaStore } from "../stores/useMetaStore";
import { useFloatingDropdown } from "../composables/useFloatingDropdown";
import { useAsyncOptionsSource } from "../composables/useAsyncOptionsSource";

const props = defineProps({
	modelValue: [String, Number, Object],
	df: Object,
	fieldname: String,
	options: { type: Array, default: () => [] },
	get_query: Function,
	doctype: String,
	filters: Object,
	read_only: Boolean,
	hideLabel: Boolean,
	hideDescription: Boolean,
	showValidation: { type: Boolean, default: false },
	placeholder: String,
	trigger: { type: String, default: "input" },
	allowCustomValue: Boolean,
	autocompleteMode: { type: String, default: null }, // "strict" | "creatable" | "prefix"
	hideSearch: Boolean,
	sortBy: [String, Function],
	dropdownMinWidth: { type: Number, default: 220 },
	dropdownMaxWidth: { type: Number, default: 680 },
	map: {
		type: Object,
		default: () => ({
			value: "value",
			label: "label",
			description: "description",
			icon: "icon",
		}),
	},
	context: Object,
	rule: Object,
	navigable: { type: Boolean, default: false },
	navStack: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "change", "navigate", "back"]);
const metaStore = useMetaStore();

const query = ref("");
const mainInputRef = ref(null);
const popoverSearchInput = ref(null);
const activeIndex = ref(-1);
const typeaheadBuffer = ref("");
let typeaheadTimeout = null;

const {
	triggerRef: wrapperRef,
	dropdownRef: optionsRef,
	isOpen: isDropdownOpen,
	dropdownStyle,
	openDropdown: openFloatingDropdown,
	closeDropdown: closeFloatingDropdown,
	toggleDropdown: toggleFloatingDropdown,
	updatePosition: updateDropdownPosition,
	cleanup: cleanupFloatingDropdown,
} = useFloatingDropdown({
	minWidth: props.dropdownMinWidth,
	maxWidth: props.dropdownMaxWidth,
	maxHeight: 360,
	matchTriggerWidth: true,
});

const effectiveDoctype = computed(() => {
	if (
		props.df?.fieldtype === "DocField" ||
		props.df?.fieldtype === "FieldPicker" ||
		props.df?.options === "DocField"
	) {
		return props.doctype || null;
	}

	// For Link/Dynamic Link fields, if no explicit doctype is provided, we should only fall back
	// if the field actually behaves like a standard Link to the parent document type.
	if (props.df?.fieldtype === "Link" || props.df?.fieldtype === "Dynamic Link") {
		return props.doctype || null;
	}

	return props.doctype || props.rule?.document_type || props.context?.document_type;
});

const isRemote = computed(() => Boolean(props.get_query || effectiveDoctype.value));

const canAcceptCustom = computed(() => {
	if (props.autocompleteMode === "strict") {
		return false;
	}
	if (props.autocompleteMode === "creatable" || props.autocompleteMode === "prefix") {
		return true;
	}
	return props.allowCustomValue;
});

const {
	options: fetchedOptions,
	loading,
	run: runOptionFetch,
	reset: resetOptionSource,
} = useAsyncOptionsSource(async ({ query: search, start, pageSize }) => {
	if (props.get_query) {
		const rows = await props.get_query(search, props.filters || {});
		if (rows !== null) {
			return metaStore.uniqueOptions(metaStore.normalizeLinkRows(rows || []));
		}
	}
	if (effectiveDoctype.value) {
		return await metaStore.search_link_options({
			doctype: effectiveDoctype.value,
			txt: search || "",
			filters: props.filters || {},
			start,
			page_length: pageSize,
		});
	}
	return [];
});

const normalizedOptions = computed(() => {
	let source = props.options;
	if (typeof source === "string") {
		source = source
			.split("\n")
			.filter(Boolean)
			.map((opt) => opt.trim());
	}
	if (!source || (Array.isArray(source) && source.length === 0)) {
		source = fetchedOptions.value || [];
	}
	if (!Array.isArray(source)) return [];

	return source.map((opt, idx) => {
		if (typeof opt === "string") return { value: opt, label: opt, raw: opt };
		if (Array.isArray(opt)) {
			return {
				value: opt[0],
				label: opt[1] || opt[0],
				description: opt[2] || null,
				raw: opt,
			};
		}
		if (typeof opt === "object" && opt !== null) {
			const value = String(
				opt[props.map.value] ??
					opt.value ??
					opt.fieldname ??
					opt.name ??
					opt.id ??
					`opt_${idx}`
			);
			const label = String(opt[props.map.label] ?? opt.label ?? value);

			return {
				value,
				label,
				description: String((opt[props.map.description] ?? opt.description) || ""),
				icon: opt[props.map.icon] ?? opt.icon,
				raw: opt,
			};
		}
		return opt;
	});
});

const sortedOptions = computed(() => {
	const options = [...normalizedOptions.value];
	if (!props.sortBy) return options;
	if (typeof props.sortBy === "function") {
		options.sort(props.sortBy);
		return options;
	}
	const key = props.sortBy;
	options.sort((a, b) => {
		const valA = (a[key] || "").toString().toLowerCase();
		const valB = (b[key] || "").toString().toLowerCase();
		return valA.localeCompare(valB);
	});
	return options;
});

const filteredOptions = computed(() => {
	const options = sortedOptions.value || [];
	if (!query.value || typeof query.value !== "string") return options;
	const q = query.value.toLowerCase();
	return options.filter((option) =>
		String(`${option.label} ${option.description || ""} ${option.value}`)
			.toLowerCase()
			.includes(q)
	);
});

const exactMatch = computed(() => {
	const options = normalizedOptions.value || [];
	const q = String(query.value || "").toLowerCase();
	if (!q) return false;
	return options.some((opt) => String(opt.label || "").toLowerCase() === q);
});

function isOptionSelected(optValue) {
	if (props.modelValue === undefined || props.modelValue === null || props.modelValue === "") {
		return false;
	}
	const currentVal = String(props.modelValue);
	const targetVal = String(optValue);
	if (currentVal === targetVal) return true;
	if (currentVal.startsWith(targetVal + ".")) return true;
	return false;
}

const selectedOption = computed(
	() => normalizedOptions.value.find((opt) => isOptionSelected(opt.value)) || null
);

const displayValue = computed(() => {
	if (selectedOption.value) return __(selectedOption.value.label);
	if (props.modelValue === 0 || props.modelValue === "0") return "0";
	if (props.modelValue) return __(String(props.modelValue));
	return "";
});

function openLink() {
	if (!effectiveDoctype.value || !props.modelValue) return;
	const url = `/app/${frappe.router.slug(effectiveDoctype.value)}/${encodeURIComponent(
		props.modelValue
	)}`;
	window.open(url, "_blank");
}

const debouncedRemoteSearch = flexirule.utils.debounce(async (value) => {
	if (!isRemote.value) return;
	await runOptionFetch(value || "");
	nextTick(() => updateDropdownPosition());
}, 220);

function toggleDropdown() {
	if (props.read_only) return;
	if (isDropdownOpen.value) {
		closeDropdown();
	} else {
		openDropdown();
	}
}

function openDropdown(initialQuery = null) {
	if (props.read_only) return;

	// Use provided query, or current display value (for input mode), or empty
	if (initialQuery !== null) {
		query.value = initialQuery;
	} else {
		query.value = props.trigger === "input" ? displayValue.value : "";
	}

	const targetIdx = filteredOptions.value.findIndex((opt) => isOptionSelected(opt.value));
	if (targetIdx >= 0) {
		activeIndex.value = targetIdx;
	} else {
		activeIndex.value = filteredOptions.value.length > 0 ? 0 : -1;
	}

	openFloatingDropdown();

	nextTick(() => {
		updateDropdownPosition();
		scrollToActive();
		if (props.trigger === "button") {
			if (popoverSearchInput.value) {
				popoverSearchInput.value.focus();
			} else if (optionsRef.value) {
				optionsRef.value.focus();
			}
		} else if (mainInputRef.value) {
			mainInputRef.value.focus();
			if (initialQuery === null) {
				mainInputRef.value.select();
			}
		}
	});

	if (isRemote.value) runOptionFetch(query.value || "");
}

function closeDropdown(restoreFocus = false) {
	const active = document.activeElement;
	const wasInsideDropdown = optionsRef.value && optionsRef.value.contains(active);
	closeFloatingDropdown();

	if (restoreFocus || wasInsideDropdown) {
		nextTick(() => {
			if (props.trigger === "button" && wrapperRef.value) {
				const btn = wrapperRef.value.querySelector(".combobox-button-trigger");
				if (btn) btn.focus();
			} else if (mainInputRef.value) {
				// Don't forcefully steal focus if they are already focused on the input
				if (document.activeElement !== mainInputRef.value) {
					mainInputRef.value.focus();
				}
			}
		});
	}
}

function onFocus() {
	if (props.read_only) return;
	if (!isDropdownOpen.value) openDropdown();
}

function onInput(e) {
	const val = e.target.value;
	if (!isDropdownOpen.value) {
		openDropdown(val);
	} else {
		query.value = val;
		if (isRemote.value) debouncedRemoteSearch(val);
	}
}

function onFocusOut(e) {
	if (!isDropdownOpen.value) return;
	const related = e.relatedTarget;
	if (wrapperRef.value && wrapperRef.value.contains(related)) return;
	if (optionsRef.value && optionsRef.value.contains(related)) return;

	if (props.trigger === "input" && query.value === "") {
		onSelect("");
	} else if (props.trigger === "input" && query.value !== "") {
		if (exactMatch.value) {
			const match = normalizedOptions.value.find(
				(opt) => String(opt.label || "").toLowerCase() === String(query.value).toLowerCase()
			);
			if (match) {
				onSelect(match.value);
			} else {
				closeDropdown();
			}
		} else if (
			canAcceptCustom.value ||
			(props.autocompleteMode !== "strict" &&
				(query.value.startsWith("@") ||
					query.value.startsWith("doc.") ||
					query.value.startsWith("vars.")))
		) {
			onSelect(query.value);
		} else {
			closeDropdown();
		}
	} else {
		closeDropdown();
	}
}

function onSelect(val) {
	emit("update:modelValue", val);
	const option = normalizedOptions.value.find((o) => String(o.value) === String(val));
	emit("change", option?.raw || val);
	query.value = "";
	closeDropdown(true);
}

function onNavigate(option) {
	emit("navigate", option.raw || option);
}

function onBack(idx) {
	emit("back", idx);
}

function scrollToActive() {
	nextTick(() => {
		const activeItem = optionsRef.value?.querySelector(".active");
		if (activeItem) activeItem.scrollIntoView({ block: "nearest" });
	});
}

function runTypeahead(key) {
	typeaheadBuffer.value += String(key || "").toLowerCase();
	if (typeaheadTimeout) clearTimeout(typeaheadTimeout);
	typeaheadTimeout = setTimeout(() => {
		typeaheadBuffer.value = "";
	}, 450);
	const idx = filteredOptions.value.findIndex((opt) =>
		String(opt.label || "")
			.toLowerCase()
			.startsWith(typeaheadBuffer.value)
	);
	if (idx > -1) {
		activeIndex.value = idx;
		scrollToActive();
	}
}

function onKeydown(e) {
	if (!isDropdownOpen.value) {
		if (e.key === "ArrowDown" || e.key === "Enter") {
			openDropdown();
			e.preventDefault();
		}
		return;
	}

	if (e.key === "ArrowRight") {
		if (activeIndex.value >= 0 && activeIndex.value < filteredOptions.value.length) {
			const activeOpt = filteredOptions.value[activeIndex.value];
			if (props.navigable && (activeOpt.navigable || activeOpt.raw?.navigable)) {
				e.preventDefault();
				onNavigate(activeOpt);
				return;
			}
		}
	}

	if (e.key === "ArrowLeft" || (e.key === "Backspace" && query.value === "")) {
		if (props.navStack && props.navStack.length > 1) {
			e.preventDefault();
			onBack(props.navStack.length - 2);
			return;
		}
	}

	if (e.key === "ArrowDown") {
		e.preventDefault();
		if (activeIndex.value < filteredOptions.value.length - 1) {
			activeIndex.value++;
			scrollToActive();
		}
		return;
	}

	if (e.key === "ArrowUp") {
		e.preventDefault();
		if (activeIndex.value > 0) {
			activeIndex.value--;
			scrollToActive();
		} else if (
			props.allowCustomValue &&
			query.value !== "" &&
			!exactMatch.value &&
			activeIndex.value !== -2
		) {
			activeIndex.value = -2;
			scrollToActive();
		}
		return;
	}

	if (e.key === "Enter") {
		e.preventDefault();
		if (activeIndex.value === -2 && canAcceptCustom.value) {
			onSelect(query.value);
		} else if (activeIndex.value >= 0 && activeIndex.value < filteredOptions.value.length) {
			onSelect(filteredOptions.value[activeIndex.value].value);
		} else if (filteredOptions.value.length === 1) {
			onSelect(filteredOptions.value[0].value);
		} else if (
			query.value !== "" &&
			!exactMatch.value &&
			(canAcceptCustom.value ||
				(props.autocompleteMode !== "strict" &&
					(query.value.startsWith("@") ||
						query.value.startsWith("doc.") ||
						query.value.startsWith("vars."))))
		) {
			onSelect(query.value);
		}
		return;
	}

	if (e.key === "Escape") {
		e.preventDefault();
		e.stopPropagation();
		e.stopImmediatePropagation();
		closeDropdown(true);
		return;
	}

	if (e.key === "Tab" && isDropdownOpen.value) {
		// If we are at -2 (Create New) or have a selection, commit it
		if (activeIndex.value === -2 && canAcceptCustom.value) {
			onSelect(query.value);
		} else if (activeIndex.value >= 0 && activeIndex.value < filteredOptions.value.length) {
			onSelect(filteredOptions.value[activeIndex.value].value);
		} else {
			closeDropdown();
		}
		// Allow default Tab behavior to move focus to next element
		return;
	}

	if (/^[\w\s-]$/.test(e.key) && (props.trigger === "button" || props.hideSearch)) {
		runTypeahead(e.key);
	}
}

function handleClickOutside(e) {
	if (!isDropdownOpen.value || !wrapperRef.value) return;
	if (wrapperRef.value.contains(e.target)) return;
	if (optionsRef.value && optionsRef.value.contains(e.target)) return;

	if (props.trigger === "input" && query.value === "") {
		onSelect("");
	} else if (props.trigger === "input" && query.value !== "") {
		if (exactMatch.value) {
			const match = normalizedOptions.value.find(
				(opt) => String(opt.label || "").toLowerCase() === String(query.value).toLowerCase()
			);
			if (match) {
				onSelect(match.value);
				return;
			}
		} else if (
			canAcceptCustom.value ||
			(props.autocompleteMode !== "strict" &&
				(query.value.startsWith("@") ||
					query.value.startsWith("doc.") ||
					query.value.startsWith("vars.")))
		) {
			onSelect(query.value);
			return;
		}
	}
	closeDropdown();
}

watch(query, () => {
	activeIndex.value = -1;
});

watch(
	() => props.df?.fieldtype,
	(newVal, oldVal) => {
		if (newVal !== oldVal && ["Link", "Dynamic Link", "Autocomplete"].includes(newVal)) {
			resetOptionSource();
		}
	}
);

watch(
	() => effectiveDoctype.value,
	() => {
		resetOptionSource();
		if (isDropdownOpen.value && isRemote.value) {
			runOptionFetch(query.value || "");
		}
	}
);

watch(
	() => props.filters,
	() => {
		resetOptionSource();
		if (isDropdownOpen.value && isRemote.value) {
			runOptionFetch(query.value || "");
		}
	},
	{ deep: true }
);

const isValid = computed(() => {
	if (!props.df?.reqd) return true;
	return props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "";
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("{0} is required").replace("{0}", props.df?.label || __("Field")));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({
	focus: () => {
		if (props.trigger === "button" && wrapperRef.value) {
			const btn = wrapperRef.value.querySelector(".combobox-button-trigger");
			if (btn) btn.focus();
		} else if (mainInputRef.value) {
			mainInputRef.value.focus();
		}
	},
	validate,
});

onMounted(() => {
	document.addEventListener("mousedown", handleClickOutside);
	if (props.modelValue && isRemote.value) {
		runOptionFetch(query.value || "");
	}
});

onBeforeUnmount(() => {
	document.removeEventListener("mousedown", handleClickOutside);
	cleanupFloatingDropdown();
	if (typeaheadTimeout) clearTimeout(typeaheadTimeout);
});
</script>

<style scoped>
.combobox-container {
	position: relative;
	width: 100%;
}

.combobox-wrapper {
	position: relative;
	width: 100%;
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	background: var(--fxr-bg-input);
	transition: all var(--fxr-transition-normal);
	box-shadow: var(--fxr-shadow-sm);
}

.combobox-wrapper.is-focused {
	border-color: var(--fxr-accent);
	box-shadow: 0 0 0 3px var(--fxr-accent-light);
}

.fxr-control.no-label .combobox-wrapper {
	border-color: var(--fxr-border);
	background-color: var(--fxr-bg-input);
	box-shadow: none;
}

.fxr-control.no-label .combobox-wrapper:hover {
	border-color: var(--fxr-border-strong);
}

.fxr-control.no-label .combobox-wrapper.is-focused {
	border-color: var(--fxr-accent);
	background-color: var(--fxr-bg-input);
	box-shadow: var(--fxr-shadow-focus);
}

.combobox-input-group {
	display: flex;
	align-items: center;
	padding: 0 var(--fxr-input-padding-x);
	height: var(--fxr-input-height);
	width: 100%;
	min-width: 0;
}

.selection-icon {
	flex-shrink: 0;
	margin-right: 8px;
	display: flex;
	align-items: center;
	color: var(--fxr-accent-icon, var(--fxr-accent));
}

.combobox-button-trigger {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: space-between;
	height: 100%;
	width: 100%;
	text-align: left;
	font-size: var(--fxr-input-font-size);
	font-weight: var(--fxr-weight-medium);
	color: var(--fxr-text);
	cursor: pointer;
	padding: 0;
	border: none;
	background: transparent;
	min-width: 0;
}

.selected-label {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	flex: 1;
	min-width: 0;
}

.combobox-input {
	flex: 1;
	border: none;
	background: transparent;
	padding: 0;
	height: 100%;
	font-size: var(--fxr-input-font-size);
	color: var(--fxr-text);
	outline: none;
	width: 100%;
	min-width: 0;
}

.combobox-trigger {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 20px;
	height: 20px;
	color: var(--fxr-text-muted);
	cursor: pointer;
	background: transparent;
	border: none;
	padding: 0;
	margin-left: 4px;
	border-radius: var(--fxr-radius-sm);
	transition: all 0.2s;
	flex-shrink: 0;
}

.combobox-trigger:hover:not(:disabled) {
	color: var(--fxr-accent);
	background: var(--fxr-accent-light);
}

/* Open-link is purely decorative — smaller, more muted */
.combobox-trigger.open-link-btn {
	width: 16px;
	height: 16px;
	font-size: 9px;
	opacity: 0.45;
	margin-left: 2px;
}
.combobox-trigger.open-link-btn:hover {
	opacity: 1;
	color: var(--fxr-accent);
	background: var(--fxr-accent-light);
}

/* Clear button same footprint as chevron but slightly warmer */
.combobox-trigger.clear-btn {
	font-size: 9px;
	opacity: 0.55;
}
.combobox-trigger.clear-btn:hover {
	opacity: 1;
	color: var(--fxr-text-danger);
	background-color: var(--fxr-danger-soft);
}

.option-content {
	display: flex;
	align-items: flex-start;
	gap: var(--fxr-space-3);
	width: 100%;
}

.option-icon {
	flex-shrink: 0;
	margin-top: 2px;
	width: 16px;
	height: 16px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--fxr-accent-icon, var(--fxr-accent));
	font-size: 12px;
}

.option-text {
	flex: 1;
	min-width: 0;
}

.option-label-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fxr-space-3);
}

.option-label {
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-semibold);
	color: var(--fxr-text);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.option-badge {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	padding: 1px 6px;
	border-radius: 4px;
	letter-spacing: 0.05em;
	background: var(--fxr-bg-muted);
	color: var(--fxr-text-muted);
	flex-shrink: 0;
}

.option-description {
	font-size: 10px;
	line-height: 1.4;
	margin-top: 2px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.selected-check {
	flex-shrink: 0;
	color: var(--fxr-accent);
	font-size: 10px;
	margin-top: 4px;
}

/* Dropdown Animation */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
	transition:
		opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1),
		transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
	opacity: 0;
	transform: translateY(-8px) scale(0.98);
}

.transition-transform {
	transition: transform 0.2s ease;
}

/* ─── Popover Search (Button Mode) ─── */
.popover-search {
	display: flex;
	align-items: center;
	padding: 10px 14px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-surface-2);
	backdrop-filter: blur(4px);
}

.popover-search-icon {
	color: var(--fxr-text-muted);
	margin-right: 8px;
	display: flex;
	align-items: center;
}

.popover-search-input {
	flex: 1;
	border: none !important;
	background: transparent !important;
	font-size: 13px;
	outline: none !important;
	box-shadow: none !important;
	color: var(--fxr-text);
	width: 100%;
	padding: 0;
}

.popover-search-input::placeholder {
	color: var(--fxr-text-muted);
	opacity: 0.7;
}

.fxr-dropdown {
	background-color: var(--fxr-surface-elevated);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
	box-shadow: var(--fxr-shadow-lg);
	overflow: auto;
	box-sizing: border-box;
}

.fxr-dropdown-item {
	padding: 8px 12px;
	cursor: pointer;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background-color: transparent;
	transition: background-color 0.12s ease;
}

.fxr-dropdown-item:last-child {
	border-bottom: none;
}

.fxr-dropdown-item:hover,
.fxr-dropdown-item.active {
	background-color: var(--fxr-bg-hover);
}

.fxr-dropdown-item.selected {
	background-color: var(--fxr-accent-soft);
}
</style>

<style>
/* Global styles for teleported ComboBox dropdown content */
.fxr-dropdown .option-content {
	display: flex;
	align-items: flex-start;
	gap: var(--fxr-space-3, 12px);
	width: 100%;
}

.fxr-dropdown .option-icon {
	flex-shrink: 0;
	margin-top: 2px;
	width: 16px;
	height: 16px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--fxr-accent-icon, var(--fxr-accent, #2563eb)) !important;
	font-size: 14px;
}

.fxr-dropdown .option-text {
	flex: 1;
	min-width: 0;
}

.fxr-dropdown .option-label-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fxr-space-3, 12px);
}

.fxr-dropdown .option-label {
	font-size: 13px;
	font-weight: 600;
	color: var(--fxr-text-strong);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.fxr-dropdown .option-badge {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	padding: 1px 6px;
	border-radius: 4px;
	letter-spacing: 0.05em;
	background-color: var(--fxr-bg-muted);
	color: var(--fxr-text-soft);
	flex-shrink: 0;
}

.fxr-dropdown .option-description {
	font-size: 10px;
	line-height: 1.4;
	margin-top: 2px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	color: var(--fxr-text-soft);
}

.fxr-dropdown .selected-check {
	flex-shrink: 0;
	color: var(--fxr-accent);
	font-size: 10px;
	margin-top: 4px;
}

/* Nav Bar & Breadcrumbs Styles */
.fxr-dropdown .nav-breadcrumbs-bar {
	display: flex;
	align-items: center;
	padding: 6px 10px;
	background-color: var(--fxr-bg-muted, #f1f5f9);
	border-bottom: 1px solid var(--fxr-border-subtle, #e2e8f0);
	font-size: 11px;
	gap: 6px;
}

.fxr-dropdown .nav-back-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 22px;
	height: 22px;
	border: 1px solid var(--fxr-border-subtle, #cbd5e1);
	border-radius: 4px;
	background: #ffffff;
	color: var(--fxr-text-strong, #1e293b);
	cursor: pointer;
	padding: 0;
	flex-shrink: 0;
	transition: all 0.15s ease;
}

.fxr-dropdown .nav-back-btn:hover {
	background-color: var(--fxr-accent-soft, #eff6ff);
	color: var(--fxr-accent, #2563eb);
	border-color: var(--fxr-accent, #2563eb);
}

.fxr-dropdown .breadcrumbs-list {
	display: flex;
	align-items: center;
	gap: 4px;
	flex: 1;
	min-width: 0;
	overflow: hidden;
}

.fxr-dropdown .breadcrumb-separator {
	color: var(--fxr-text-muted, #94a3b8);
	font-size: 10px;
}

.fxr-dropdown .breadcrumb-link {
	border: none;
	background: none;
	padding: 0;
	color: var(--fxr-accent, #2563eb);
	cursor: pointer;
	font-weight: 500;
	text-decoration: none;
}

.fxr-dropdown .breadcrumb-link:hover {
	text-decoration: underline;
}

.fxr-dropdown .breadcrumb-current {
	color: var(--fxr-text-strong, #1e293b);
	font-weight: 600;
}

.fxr-dropdown .option-nav-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 22px;
	height: 22px;
	border: 1px solid var(--fxr-border-subtle, #e2e8f0);
	border-radius: 4px;
	background: transparent;
	color: var(--fxr-text-muted, #64748b);
	cursor: pointer;
	padding: 0;
	margin-left: auto;
	flex-shrink: 0;
	transition: all 0.15s ease;
}

.fxr-dropdown .option-nav-btn:hover {
	background-color: var(--fxr-accent, #2563eb);
	color: #ffffff;
	border-color: var(--fxr-accent, #2563eb);
}

/* RTL Language Support for Nav Icons */
[dir="rtl"] .fxr-dropdown .option-nav-btn,
html[dir="rtl"] .fxr-dropdown .option-nav-btn,
body.rtl .fxr-dropdown .option-nav-btn {
	margin-left: 0 !important;
	margin-right: auto !important;
}

[dir="rtl"] .fxr-dropdown .option-nav-btn i,
html[dir="rtl"] .fxr-dropdown .option-nav-btn i,
body.rtl .fxr-dropdown .option-nav-btn i {
	transform: scaleX(-1);
}

[dir="rtl"] .fxr-dropdown .nav-back-btn i,
html[dir="rtl"] .fxr-dropdown .nav-back-btn i,
body.rtl .fxr-dropdown .nav-back-btn i {
	transform: scaleX(-1);
}
</style>
