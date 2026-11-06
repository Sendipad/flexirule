<template>
	<div
		ref="controlRef"
		class="fvc-wrap"
		:class="{
			'is-compact': compact,
			'is-disabled': disabled || isReadOnly,
			'has-error': invalid || (showValidation && !isValid),
		}"
		v-fxr-fieldname="context?.df?.fieldname || fieldname || null"
	>
		<!-- ── Main Control Area ── -->
		<div
			class="fvc-main-field"
			:class="{
				'is-dynamic': currentMode !== 'static',
				'is-multi-select': isMultiSelect,
			}"
		>
			<!-- 1. Source/Mode Pill Button: indicates current mode & opens embedded dropdown -->
			<div class="fvc-source-badge-wrap">
				<button
					type="button"
					class="fvc-source-pill"
					:class="sourcePillClass"
					:disabled="isReadOnly || disabled"
					:title="__('Select source or calculation')"
					@click.stop="toggleDropdown"
				>
					<i :class="sourcePillIcon"></i>
					<span class="fvc-source-pill-text">{{ sourcePillLabel }}</span>
					<i v-if="!isReadOnly && !disabled" class="fa fa-caret-down ml-1"></i>
				</button>
			</div>

			<!-- 2. Value Input Area depending on currentMode -->
			<!-- A. Static Mode -->
			<div v-if="currentMode === 'static'" class="fvc-editor-container flex-1">
				<MultiSelectList
					v-if="isMultiSelectInline"
					:df="staticDf"
					:modelValue="staticValue"
					:documentType="isLinkType ? referenceDoctype : undefined"
					:options="isLinkType ? undefined : fieldOptions"
					:filters="context?.filters || {}"
					:get_data="context?.df?.get_data || undefined"
					displayMode="badges"
					:badgeCollapseAfter="2"
					:allowWrap="false"
					:hideLabel="true"
					class="flex-1 min-w-0 w-100"
					@update:modelValue="updateStaticValue"
				/>
				<ControlFactory
					v-else
					:df="staticDf"
					:modelValue="staticValue"
					:doc="doc"
					:engine="engine"
					:context="context"
					:options="isLinkType ? undefined : fieldOptions"
					:hideLabel="true"
					class="flex-1 min-w-0 w-100 static-control-factory"
					@update:modelValue="updateStaticValue"
				/>
			</div>

			<!-- B. Variable Mode (displays selected variable path, click opens source dropdown) -->
			<div
				v-else-if="currentMode === 'variable'"
				class="fvc-editor-container flex-1 fvc-variable-display"
				@click="!isReadOnly && !disabled && openDropdown()"
			>
				<span class="token-chip token-variable text-truncate">
					<i class="fa fa-cube mr-1"></i>
					{{ currentVariableLabel }}
				</span>
				<button
					v-if="!isReadOnly && !disabled"
					type="button"
					class="fvc-clear-source-btn"
					:title="__('Clear source / Switch to fixed value')"
					@click.stop="switchToStatic"
				>
					<i class="fa fa-times"></i>
				</button>
			</div>

			<!-- C. Resolver Mode (guided resolver configuration) -->
			<div
				v-else-if="currentMode === 'resolver'"
				class="fvc-editor-container flex-1 fvc-resolver-display"
				@click="!isReadOnly && !disabled && openResolverEditor()"
			>
				<span class="token-chip token-resolver text-truncate">
					<i class="fa fa-bolt mr-1"></i>
					{{ currentResolverLabel }}
				</span>
				<div class="d-flex align-items-center fxr-gap-1" v-if="!isReadOnly && !disabled">
					<button
						type="button"
						class="fvc-action-btn"
						:title="__('Configure resolver')"
						@click.stop="openResolverEditor"
					>
						<i class="fa fa-pencil"></i>
					</button>
					<button
						type="button"
						class="fvc-clear-source-btn"
						:title="__('Clear resolver / Switch to fixed value')"
						@click.stop="switchToStatic"
					>
						<i class="fa fa-times"></i>
					</button>
				</div>
			</div>

			<!-- D. Template Mode (fallback structured template display) -->
			<div
				v-else-if="currentMode === 'template'"
				class="fvc-editor-container flex-1 fvc-template-display"
			>
				<span class="fvc-template-preview text-truncate">
					{{ currentTemplatePreview }}
				</span>
				<button
					v-if="!isReadOnly && !disabled"
					type="button"
					class="fvc-clear-source-btn"
					:title="__('Clear template / Switch to fixed value')"
					@click.stop="switchToStatic"
				>
					<i class="fa fa-times"></i>
				</button>
			</div>
		</div>

		<!-- ── Embedded Searchable Source Dropdown (Compact, attached directly to control) ── -->
		<div v-if="isDropdownOpen" class="fvc-embedded-dropdown" ref="dropdownRef">
			<div class="fvc-dropdown-search">
				<i class="fa fa-search text-muted mr-1"></i>
				<input
					ref="searchInputRef"
					type="text"
					v-model="searchQuery"
					class="fvc-search-input"
					:placeholder="__('Search fields, variables, resolvers...')"
					@keydown.esc.stop="closeDropdown"
				/>
				<button
					v-if="searchQuery"
					type="button"
					class="fvc-icon-btn"
					@click="searchQuery = ''"
				>
					<i class="fa fa-times"></i>
				</button>
			</div>

			<div class="fvc-dropdown-body">
				<!-- Switch to Fixed Value option if not static -->
				<div
					v-if="currentMode !== 'static'"
					class="fvc-dropdown-item fvc-item-fixed"
					@click="switchToStatic"
				>
					<i class="fa fa-font mr-2 text-muted"></i>
					<span class="flex-1 font-weight-bold">{{ __("Enter Fixed / Static Value") }}</span>
				</div>

				<!-- Categories & Items -->
				<div v-if="filteredGroups.length === 0" class="fvc-empty-msg">
					{{ __("No matching sources found") }}
				</div>

				<div v-for="group in filteredGroups" :key="group.name" class="fvc-group">
					<div class="fvc-group-header">
						<i :class="group.icon" class="mr-1"></i>
						{{ group.label }}
					</div>
					<div
						v-for="item in group.items"
						:key="item.value"
						class="fvc-dropdown-item"
						:class="{ 'is-selected': isItemSelected(item) }"
						@click="selectItem(item)"
					>
						<div class="d-flex align-items-center text-truncate flex-1">
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

				<!-- Approved Resolvers Group (if allowed) -->
				<div v-if="approvedResolverOptions.length" class="fvc-group">
					<div class="fvc-group-header">
						<i class="fa fa-bolt mr-1"></i>
						{{ __("Calculations & Resolvers") }}
					</div>
					<div
						v-for="res in approvedResolverOptions"
						:key="res.key"
						class="fvc-dropdown-item"
						@click="selectResolver(res)"
					>
						<div class="d-flex align-items-center text-truncate flex-1">
							<i :class="res.icon || 'fa fa-calculator'" class="mr-2 text-primary"></i>
							<span class="item-label font-weight-medium text-truncate mr-2">
								{{ res.label }}
							</span>
						</div>
						<span class="item-path text-muted font-monospace small">
							{{ res.family }}.{{ res.operation }}
						</span>
					</div>
				</div>
			</div>
		</div>

		<!-- ── Guided Resolver Config Modal (Teleported) ── -->
		<Teleport to="body">
			<div
				v-if="isResolverModalOpen"
				class="fxr-resolver-modal-overlay"
				@click.self="isResolverModalOpen = false"
			>
				<div class="fxr-resolver-modal-card">
					<div class="fxr-resolver-modal-header">
						<div class="d-flex align-items-center fxr-gap-2">
							<i class="fa fa-bolt text-primary"></i>
							<h6 class="mb-0 font-weight-bold">{{ resolverModalTitle }}</h6>
						</div>
						<button
							type="button"
							class="fvc-action-btn"
							@click="isResolverModalOpen = false"
						>
							<i class="fa fa-times"></i>
						</button>
					</div>
					<div class="fxr-resolver-modal-body">
						<ValueResolverControl
							viewMode="inline"
							:modelValue="resolverDraftConfig"
							:doctype="triggerDoctype"
							:context="resolverContext"
							:variableOptions="availableVariableOptions"
							:allowedKinds="allowedBuilderKinds"
							@update:modelValue="onResolverBuilderUpdate"
						/>
					</div>
					<div class="fxr-resolver-modal-footer">
						<button
							type="button"
							class="fxr-btn fxr-btn--secondary"
							@click="isResolverModalOpen = false"
						>
							{{ __("Cancel") }}
						</button>
						<button
							type="button"
							class="fxr-btn fxr-btn--primary"
							@click="saveResolverConfig"
						>
							{{ __("Done") }}
						</button>
					</div>
				</div>
			</div>
		</Teleport>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} is required").replace("{0}", context?.df?.label || __("Field")) }}
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import ControlFactory from "./ControlFactory.vue";
import MultiSelectList from "./MultiSelectList.vue";
import ValueResolverControl from "./ValueResolverControl.vue";
import { getAllowedBuilderKinds } from "../../core/formula_registry";

const props = defineProps({
	modelValue: { type: [Object, String, Number, Boolean], default: null },
	fieldname: String,
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
	placeholder: { type: String, default: "" },
	compact: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
	engine: { type: Object, default: null },
	doc: { type: Object, default: null },
	showValidation: { type: Boolean, default: false },
	invalid: { type: Boolean, default: false },
	context: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["update:modelValue", "update", "change"]);

const isReadOnly = computed(() => !!props.readOnly || !!props.read_only);

// ── Dropdown / Search State ──
const controlRef = ref(null);
const dropdownRef = ref(null);
const searchInputRef = ref(null);
const isDropdownOpen = ref(false);
const searchQuery = ref("");

// ── Resolver Modal State ──
const isResolverModalOpen = ref(false);
const resolverDraftConfig = ref({});
const resolverDraftFamily = ref("math");
const resolverDraftOperation = ref("formula");

// ── Mode & Value State ──
// Canonical modes: 'static' | 'variable' | 'resolver' | 'template'
const currentMode = ref("static");
const staticValue = ref("");
const variablePath = ref({ scope: "doc", segments: [] });
const variableLabel = ref("");
const resolverPayload = ref(null);
const templateSegments = ref([]);

let lastEmittedJSON = "";

// ── Type metadata helpers ──
const fieldType = computed(() => props.context?.df?.fieldtype || "Data");
const fieldOptions = computed(() => props.context?.df?.options || []);
const referenceDoctype = computed(() => {
	if (fieldType.value === "Link" && fieldOptions.value) {
		return fieldOptions.value;
	}
	const opts = fieldOptions.value;
	if (opts && typeof opts === "string" && props.context?.filters) {
		const filterVal = props.context.filters[opts];
		if (filterVal !== undefined && filterVal !== null) {
			if (typeof filterVal === "object" && filterVal.mode === "static") {
				return String(filterVal.value || "");
			}
			if (typeof filterVal === "string") {
				return filterVal;
			}
		}
	}
	return props.context?.referenceDoctype || opts || "";
});

const triggerDoctype = computed(() => {
	return props.doctype || props.engine?.rule_doc?.document_type || "";
});

const resolverContext = computed(() => {
	const df = props.context?.df || {};
	const fieldname = props.context?.fieldname || df.fieldname || df.value || "";
	return {
		...props.context,
		df,
		fieldname,
		target: props.context?.target || fieldname,
		referenceDoctype: referenceDoctype.value,
		triggerDoctype: triggerDoctype.value,
	};
});

const isLinkType = computed(() => {
	const ft = fieldType.value;
	return (
		ft === "Link" || ft === "Dynamic Link" || ft === "MultiSelectList" || ft === "MultiSelect"
	);
});

const TEXT_FIELDTYPES = new Set([
	"Data",
	"Small Text",
	"Text",
	"Long Text",
	"Code",
	"Text Editor",
	"JSON",
]);

const isMultiSelect = computed(() => {
	const ft = fieldType.value;
	if (["MultiSelect", "MultiSelectList", "Table MultiSelect", "MultiCheck"].includes(ft)) {
		return true;
	}
	const op = props.context?.operator;
	const isListOp = ["in", "not in", "not_in", "in list", "not in list"].includes(
		String(op || "").toLowerCase()
	);
	if (!isListOp) return false;
	return ft === "Select" || TEXT_FIELDTYPES.has(ft) || ft === "Link" || ft === "Dynamic Link";
});

const isMultiSelectInline = computed(() => {
	const op = props.context?.operator;
	const isListOp = ["in", "not in", "not_in", "in list", "not in list"].includes(
		String(op || "").toLowerCase()
	);
	if (!isListOp) return false;
	const ft = fieldType.value;
	return ft === "Select" || TEXT_FIELDTYPES.has(ft) || ft === "Link" || ft === "Dynamic Link";
});

const staticDf = computed(() => {
	let ft = fieldType.value;
	let opts = fieldOptions.value;
	if (ft === "Link") {
		opts = referenceDoctype.value;
	}
	return {
		...props.context?.df,
		fieldtype: ft,
		label: "",
		options: opts,
		read_only: props.disabled || isReadOnly.value,
		placeholder: props.placeholder,
	};
});

// ── Available variable options ──
const availableVariableOptions = computed(() => {
	let options = Array.isArray(props.variableOptions) ? [...props.variableOptions] : [];
	if (typeof props.context?.getVariableOptions === "function") {
		options = props.context.getVariableOptions(options, {
			fieldType: fieldType.value,
			context: props.context,
		});
	}
	if (typeof props.context?.filterVariableOptions === "function") {
		options = options.filter((item) =>
			props.context.filterVariableOptions(item, {
				fieldType: fieldType.value,
				context: props.context,
			})
		);
	}
	return Array.isArray(options) ? options : [];
});

const allowedBuilderKinds = computed(() => {
	let kinds =
		Array.isArray(props.context?.allowedKinds) && props.context.allowedKinds.length
			? [...props.context.allowedKinds]
			: getAllowedBuilderKinds(fieldType.value);
	if (typeof props.context?.getAllowedKinds === "function") {
		kinds = props.context.getAllowedKinds(kinds, {
			fieldType: fieldType.value,
			context: props.context,
		});
	}
	return Array.isArray(kinds) && kinds.length ? kinds : null;
});

// Approved Resolvers mapped to options
const approvedResolverOptions = computed(() => {
	if (props.context?.allowResolvers === false) return [];
	const kinds = allowedBuilderKinds.value || ["math_formula", "text", "date_time", "lookup"];
	const options = [];
	if (kinds.includes("math_formula")) {
		options.push({
			key: "math_formula",
			family: "math",
			operation: "formula",
			label: __("Math Formula"),
			icon: "fa fa-calculator",
		});
	}
	if (kinds.includes("text")) {
		options.push({
			key: "text_combine",
			family: "text",
			operation: "combine",
			label: __("Text Combine"),
			icon: "fa fa-font",
		});
	}
	if (kinds.includes("date_time")) {
		options.push({
			key: "date_time_calculate",
			family: "date_time",
			operation: "calculate",
			label: __("Date/Time Calculation"),
			icon: "fa fa-calendar",
		});
	}
	if (kinds.includes("lookup")) {
		options.push({
			key: "lookup_fetch",
			family: "lookup",
			operation: "fetch",
			label: __("Record Lookup"),
			icon: "fa fa-search",
		});
	}
	return options;
});

// Grouped variable sources for compact embedded dropdown
const categorizedGroups = computed(() => {
	const raw = availableVariableOptions.value;
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
			label: __("Document Fields"),
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
			label: __("Step Outputs & Variables"),
			icon: "fa fa-cubes",
			items: stepItems,
		});
	}
	if (contextItems.length) {
		groups.push({
			name: "context",
			label: __("Rule & System Context"),
			icon: "fa fa-info-circle",
			items: contextItems,
		});
	}
	if (otherItems.length) {
		groups.push({
			name: "other",
			label: __("Other Sources"),
			icon: "fa fa-sliders",
			items: otherItems,
		});
	}
	return groups;
});

function cleanFriendlyLabel(label, value) {
	if (!label) return value;
	const parenMatch = label.match(/\(([^)]+)\)/);
	if (parenMatch && parenMatch[1]) {
		return parenMatch[1].trim();
	}
	return label.replace(/^(doc|old_doc|vars|caller|rule)\./, "");
}

const filteredGroups = computed(() => {
	const q = searchQuery.value.toLowerCase().trim();
	if (!q) return categorizedGroups.value;

	const result = [];
	for (const group of categorizedGroups.value) {
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

// ── Source Pill Display Helpers ──
const sourcePillClass = computed(() => {
	if (currentMode.value === "variable") return "is-var";
	if (currentMode.value === "resolver") return "is-resolver";
	if (currentMode.value === "template") return "is-template";
	return "is-static";
});

const sourcePillIcon = computed(() => {
	if (currentMode.value === "variable") return "fa fa-cube";
	if (currentMode.value === "resolver") return "fa fa-bolt";
	if (currentMode.value === "template") return "fa fa-code";
	return "fa fa-font";
});

const sourcePillLabel = computed(() => {
	if (currentMode.value === "variable") return __("Field/Var");
	if (currentMode.value === "resolver") return __("Calculation");
	if (currentMode.value === "template") return __("Template");
	return __("Fixed");
});

const currentVariableLabel = computed(() => {
	if (variableLabel.value) return variableLabel.value;
	const p = variablePath.value;
	const segs = p?.segments || [];
	return segs.length ? `${p.scope || "doc"}.${segs.join(".")}` : p?.scope || "";
});

const currentResolverLabel = computed(() => {
	if (!resolverPayload.value) return __("Calculation");
	const fam = resolverPayload.value.family || "";
	const op = resolverPayload.value.operation || "";
	return `${fam}.${op}`;
});

const currentTemplatePreview = computed(() => {
	if (!templateSegments.value?.length) return "";
	return templateSegments.value
		.map((s) => (s.type === "text" ? s.value : "[Dynamic]"))
		.join("");
});

const resolverModalTitle = computed(() => {
	return __("Configure {0}.{1}").replace("{0}", resolverDraftFamily.value).replace("{1}", resolverDraftOperation.value);
});

// ── Dropdown & Selection Handlers ──
function toggleDropdown() {
	if (isReadOnly.value || props.disabled) return;
	if (isDropdownOpen.value) {
		closeDropdown();
	} else {
		openDropdown();
	}
}

function openDropdown() {
	if (isReadOnly.value || props.disabled) return;
	isDropdownOpen.value = true;
	searchQuery.value = "";
	nextTick(() => {
		searchInputRef.value?.focus();
	});
}

function closeDropdown() {
	isDropdownOpen.value = false;
	searchQuery.value = "";
}

function isItemSelected(item) {
	if (currentMode.value !== "variable") return false;
	const path = variablePath.value;
	const pathStr = path.segments?.length ? `${path.scope}.${path.segments.join(".")}` : path.scope;
	return item.value === pathStr || item.value === path.segments?.join(".");
}

function selectItem(item) {
	const val = item.value || item;
	const pathStr = String(val).startsWith("@") ? String(val).substring(1) : String(val);
	const parts = pathStr.split(".");
	const knownScopes = new Set(["doc", "old_doc", "vars", "caller", "rule", "doctype"]);
	const scope = knownScopes.has(parts[0]) ? parts[0] : parts.length > 1 ? parts[0] : "doc";
	const segments = knownScopes.has(parts[0]) || parts.length > 1 ? parts.slice(1) : parts;

	currentMode.value = "variable";
	variablePath.value = { scope, segments };
	variableLabel.value = item.friendlyLabel || item.label || pathStr;
	closeDropdown();
	emitChanges();
}

function selectResolver(res) {
	closeDropdown();
	resolverDraftFamily.value = res.family;
	resolverDraftOperation.value = res.operation;
	resolverDraftConfig.value = { kind: res.key };
	isResolverModalOpen.value = true;
}

function openResolverEditor() {
	if (isReadOnly.value || props.disabled) return;
	if (resolverPayload.value) {
		resolverDraftFamily.value = resolverPayload.value.family || "math";
		resolverDraftOperation.value = resolverPayload.value.operation || "formula";
		resolverDraftConfig.value = resolverPayload.value.config || {};
	}
	isResolverModalOpen.value = true;
}

function onResolverBuilderUpdate(config) {
	resolverDraftConfig.value = config;
}

function saveResolverConfig() {
	currentMode.value = "resolver";
	resolverPayload.value = {
		mode: "resolver",
		family: resolverDraftFamily.value,
		operation: resolverDraftOperation.value,
		value_type: fieldType.value || "Data",
		config: resolverDraftConfig.value,
	};
	isResolverModalOpen.value = false;
	emitChanges();
}

function switchToStatic() {
	currentMode.value = "static";
	if (isMultiSelect.value) {
		if (!Array.isArray(staticValue.value)) staticValue.value = [];
	} else if (typeof staticValue.value !== "string" && typeof staticValue.value !== "number") {
		staticValue.value = "";
	}
	closeDropdown();
	emitChanges();
}

function updateStaticValue(val) {
	staticValue.value = val;
	emitChanges();
}

// ── Serialization & Deserialization ──
function serialize() {
	const currentFieldType = fieldType.value || "Data";

	if (currentMode.value === "variable") {
		const scope = variablePath.value?.scope || "doc";
		const segments = Array.isArray(variablePath.value?.segments)
			? [...variablePath.value.segments]
			: [];
		return {
			mode: "variable",
			path: { scope, segments },
		};
	}

	if (currentMode.value === "resolver") {
		return {
			mode: "resolver",
			family: resolverPayload.value?.family || "text",
			operation: resolverPayload.value?.operation || "combine",
			value_type: resolverPayload.value?.value_type || currentFieldType,
			config: resolverPayload.value?.config || {},
		};
	}

	if (currentMode.value === "template") {
		return {
			mode: "template",
			segments: Array.isArray(templateSegments.value) ? templateSegments.value : [],
		};
	}

	return {
		mode: "static",
		value_type: currentFieldType,
		value: staticValue.value,
	};
}

function coerceStructuredValue(val) {
	const currentFieldType = fieldType.value || "Data";

	if (val && typeof val === "object" && val.mode) {
		if (["formula", "format", "normalize", "normalization"].includes(val.mode)) {
			const config = { ...(val.config || {}) };
			let fam = val.family || config.family;
			let op = val.operation || config.operation;

			if (!fam || !op) {
				if (val.mode === "formula") {
					if (config.kind === "date_time" || config.base_type || config.offset_unit) {
						fam = "date_time";
						op = "calculate";
					} else if (config.str_op || config.kind === "text") {
						fam = "text";
						op = "combine";
					} else {
						fam = "math";
						op = "formula";
					}
				} else if (["normalize", "normalization"].includes(val.mode)) {
					fam = "text";
					op = "normalize";
				} else if (val.mode === "format") {
					if (config.fmt_op === "format_date" || config.kind === "date_time") {
						fam = "date_time";
						op = "format";
					} else {
						fam = "text";
						op = "format";
					}
				}
			}

			return {
				mode: "resolver",
				family: fam || "text",
				operation: op || "combine",
				value_type: val.value_type || currentFieldType,
				config: config.config && typeof config.config === "object" ? config.config : config,
			};
		}
		if (val.mode === "variable") {
			if (val.path && typeof val.path === "object") {
				const scope = val.path.scope || "doc";
				const segments = Array.isArray(val.path.segments) ? [...val.path.segments] : [];
				return {
					mode: "variable",
					path: { scope, segments },
				};
			}
			const pathStr = String(val.path || val.value || "");
			const parts = pathStr.split(".");
			const scope = parts[0] || "doc";
			const segments = parts.slice(1);
			return {
				mode: "variable",
				path: { scope, segments },
			};
		}
		if (val.mode === "resolver") {
			const rawConfig = val.config || {};
			let family = val.family || rawConfig.family;
			let operation = val.operation || rawConfig.operation;
			let config = rawConfig;

			if (!family) {
				if (rawConfig.kind === "math_formula") {
					family = "math";
					operation = operation || "formula";
				} else if (
					rawConfig.kind === "collection" ||
					rawConfig.kind === "child_aggregation"
				) {
					family = "collection";
					operation = operation || rawConfig.operation || rawConfig.agg_op || "any";
				} else if (rawConfig.kind === "lookup" || rawConfig.kind === "fetch") {
					family = "lookup";
					operation = operation || "fetch";
				} else if (rawConfig.kind === "system_context") {
					family = "system_context";
					operation = operation || "get";
				} else if (rawConfig.kind) {
					family = rawConfig.kind;
				}
			}

			if (config.config && typeof config.config === "object") {
				config = config.config;
			}

			return {
				mode: "resolver",
				family: family || "text",
				operation: operation || "combine",
				value_type: val.value_type || currentFieldType,
				config,
			};
		}
		if (val.mode === "template") {
			return { mode: "template", segments: Array.isArray(val.segments) ? val.segments : [] };
		}
		return {
			mode: "static",
			value_type: val.value_type || currentFieldType,
			value: val.value,
		};
	}

	if (val === null || val === undefined) {
		return { mode: "static", value_type: currentFieldType, value: "" };
	}
	return { mode: "static", value_type: currentFieldType, value: val };
}

function emitChanges() {
	const output = serialize();
	const json = JSON.stringify(output);
	if (json === lastEmittedJSON) return;
	lastEmittedJSON = json;
	emit("update:modelValue", output);
	emit("update", output);
	emit("change", output);
	try {
		if (typeof props.context?.onUpdate === "function") {
			props.context.onUpdate(output);
		}
		if (typeof props.context?.onChange === "function") {
			props.context.onChange(output);
		}
	} catch (error) {
		console.warn("FlexValueControl context callback failed:", error);
	}
}

// ── Validation ──
const isValid = computed(() => {
	if (!props.context?.df?.reqd) return true;
	const struct = serialize();
	if (struct.mode === "static") {
		if (Array.isArray(struct.value)) {
			return (
				struct.value.length > 0 &&
				struct.value.every(
					(v) => v !== undefined && v !== null && !(typeof v === "string" && v.trim() === "")
				)
			);
		}
		if (typeof struct.value === "string") return struct.value.trim() !== "";
		return struct.value !== undefined && struct.value !== null && struct.value !== "";
	}
	if (struct.mode === "variable") {
		return !!(struct.path?.scope && struct.path?.segments?.length);
	}
	if (struct.mode === "resolver") {
		return !!(struct.family && struct.operation);
	}
	if (struct.mode === "template") {
		return Array.isArray(struct.segments) && struct.segments.length > 0;
	}
	return true;
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("{0} is required").replace("{0}", props.context?.df?.label || __("Field")));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

// ── Watch modelValue changes ──
watch(
	() => props.modelValue,
	(val) => {
		const normalized = coerceStructuredValue(val);
		const json = JSON.stringify(normalized);
		if (json === lastEmittedJSON) return;
		lastEmittedJSON = json;

		if (normalized.mode === "variable") {
			currentMode.value = "variable";
			variablePath.value = normalized.path || { scope: "doc", segments: [] };
			const pathStr = variablePath.value.segments?.length
				? `${variablePath.value.scope}.${variablePath.value.segments.join(".")}`
				: variablePath.value.scope;
			const match = availableVariableOptions.value.find((o) => (o.value || o) === pathStr);
			variableLabel.value = match?.friendlyLabel || match?.label || pathStr;
		} else if (normalized.mode === "resolver") {
			currentMode.value = "resolver";
			resolverPayload.value = normalized;
		} else if (normalized.mode === "template") {
			currentMode.value = "template";
			templateSegments.value = normalized.segments || [];
		} else {
			currentMode.value = "static";
			staticValue.value = normalized.value ?? "";
		}
	},
	{ immediate: true }
);

function handleClickOutside(e) {
	if (!isDropdownOpen.value) return;
	if (controlRef.value?.contains(e.target)) return;
	if (dropdownRef.value?.contains(e.target)) return;
	closeDropdown();
}

onMounted(() => {
	document.addEventListener("click", handleClickOutside);
});

onBeforeUnmount(() => {
	document.removeEventListener("click", handleClickOutside);
});
</script>

<style scoped>
.fvc-wrap {
	display: flex;
	flex-direction: column;
	width: 100%;
	position: relative;
}

.fvc-main-field {
	display: flex;
	align-items: center;
	width: 100%;
	height: var(--fxr-input-height, 32px);
	min-height: var(--fxr-input-height, 32px);
	border: 1px solid var(--fxr-border, #d1d5db);
	border-radius: var(--fxr-radius-sm, 4px);
	background-color: var(--fxr-bg-input, #ffffff);
	transition: all 0.15s ease;
}

.fvc-main-field.is-multi-select {
	height: auto !important;
	min-height: var(--fxr-input-height, 32px) !important;
}

.fvc-main-field:focus-within {
	border-color: var(--fxr-accent, #2490ef);
	box-shadow: 0 0 0 2px color-mix(in srgb, var(--fxr-accent, #2490ef) 20%, transparent);
}

.fvc-source-badge-wrap {
	padding: 2px 4px 2px 6px;
	display: flex;
	align-items: center;
	flex-shrink: 0;
	border-right: 1px solid var(--fxr-border-subtle, #f3f4f6);
}

.fvc-source-pill {
	display: inline-flex;
	align-items: center;
	padding: 2px 6px;
	border-radius: 4px;
	font-size: 11px;
	font-weight: 600;
	cursor: pointer;
	border: 1px solid transparent;
	background: transparent;
	color: var(--fxr-text-muted, #64748b);
	transition: all 0.15s ease;
	line-height: 1.2;
}

.fvc-source-pill:hover:not(:disabled) {
	background-color: var(--fxr-bg-hover, #f1f5f9);
	color: var(--fxr-text-strong, #0f172a);
}

.fvc-source-pill.is-var {
	background-color: var(--fxr-badge-bool, #dcfce7);
	color: var(--fxr-badge-bool-text, #166534);
	border-color: rgba(16, 185, 129, 0.2);
}

.fvc-source-pill.is-resolver {
	background-color: var(--fxr-badge-resolver, #fef3c7);
	color: var(--fxr-badge-resolver-text, #92400e);
	border-color: rgba(217, 119, 6, 0.2);
}

.fvc-source-pill.is-template {
	background-color: var(--fxr-badge-formatter, #fce7f3);
	color: var(--fxr-badge-formatter-text, #9d174d);
	border-color: rgba(219, 39, 119, 0.2);
}

.fvc-source-pill-text {
	margin: 0 4px;
}

.fvc-editor-container {
	padding: 2px 6px;
	flex: 1;
	display: flex;
	align-items: center;
	min-width: 0;
	overflow: hidden;
}

.fvc-variable-display,
.fvc-resolver-display,
.fvc-template-display {
	display: flex;
	align-items: center;
	justify-content: space-between;
	cursor: pointer;
	padding-right: 6px;
}

.fvc-clear-source-btn {
	background: transparent;
	border: none;
	color: var(--fxr-text-muted, #94a3b8);
	cursor: pointer;
	font-size: 12px;
	padding: 2px 4px;
	border-radius: 4px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.fvc-clear-source-btn:hover {
	color: var(--fxr-text-danger, #ef4444);
	background-color: var(--fxr-danger-soft, #fee2e2);
}

.fvc-action-btn {
	background: transparent;
	border: none;
	color: var(--fxr-text-muted, #94a3b8);
	cursor: pointer;
	font-size: 12px;
	padding: 2px 4px;
	border-radius: 4px;
}

.fvc-action-btn:hover {
	color: var(--fxr-accent, #2490ef);
	background-color: var(--fxr-bg-hover, #f1f5f9);
}

/* Static controls interior adjustments */
.fvc-editor-container :deep(.combobox-wrapper),
.fvc-editor-container :deep(.form-control),
.fvc-editor-container :deep(.fxr-input),
.fvc-editor-container :deep(.fxr-input-group),
.fvc-editor-container :deep(.fxr-select),
.fvc-editor-container :deep(.multi-select-trigger) {
	border: none !important;
	box-shadow: none !important;
	background: transparent !important;
	height: var(--fxr-input-height, 30px) !important;
	margin-bottom: 0 !important;
	padding-bottom: 0 !important;
	border-radius: inherit !important;
}

.fvc-editor-container :deep(.fxr-control),
.fvc-editor-container :deep(.fxr-input-group),
.fvc-editor-container :deep(.combobox-container) {
	width: 100% !important;
	flex: 1 !important;
	min-width: 0 !important;
}

.fvc-editor-container :deep(.fxr-input),
.fvc-editor-container :deep(.fxr-select),
.fvc-editor-container :deep(.combobox-input),
.fvc-editor-container :deep(.awesomplete input) {
	padding: 0 6px !important;
	font-weight: var(--fxr-weight-bold, 600) !important;
	color: var(--fxr-text-strong, #1f2937) !important;
	height: var(--fxr-input-height, 30px) !important;
}

/* ── Embedded Dropdown (compact, clean, attached to control) ── */
.fvc-embedded-dropdown {
	position: absolute;
	top: 100%;
	left: 0;
	width: 100%;
	min-width: 280px;
	max-width: 440px;
	max-height: 280px;
	background: var(--fxr-bg-surface, #ffffff);
	border: 1px solid var(--fxr-border, #cbd5e1);
	border-radius: 6px;
	margin-top: 2px;
	z-index: 15000;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.fvc-dropdown-search {
	display: flex;
	align-items: center;
	padding: 6px 8px;
	border-bottom: 1px solid var(--fxr-border-subtle, #f1f5f9);
	background: var(--fxr-surface-2, #f8fafc);
}

.fvc-search-input {
	flex: 1;
	border: none;
	background: transparent;
	font-size: 12px;
	outline: none;
	color: var(--fxr-text, #1e293b);
}

.fvc-icon-btn {
	background: transparent;
	border: none;
	color: var(--fxr-text-muted, #94a3b8);
	cursor: pointer;
	padding: 2px;
}

.fvc-dropdown-body {
	flex: 1;
	overflow-y: auto;
	padding: 4px;
}

.fvc-item-fixed {
	background-color: var(--fxr-surface-2, #f8fafc);
	border-bottom: 1px solid var(--fxr-border-subtle, #e2e8f0);
	margin-bottom: 4px;
}

.fvc-dropdown-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 5px 8px;
	border-radius: 4px;
	font-size: 12px;
	cursor: pointer;
	transition: background-color 0.15s ease;
}

.fvc-dropdown-item:hover {
	background-color: var(--fxr-bg-hover, #f1f5f9);
}

.fvc-dropdown-item.is-selected {
	background-color: var(--fxr-accent-soft, #eff6ff);
	color: var(--fxr-accent, #2563eb);
}

.fvc-group-header {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: var(--fxr-text-secondary, #64748b);
	padding: 4px 8px 2px 8px;
}

.fvc-empty-msg {
	padding: 12px;
	font-size: 12px;
	color: var(--fxr-text-muted, #94a3b8);
	text-align: center;
}

:deep(.token-chip) {
	padding: 1px 6px;
	border-radius: 4px;
	font-size: 11px;
	font-weight: 600;
	margin: 0 2px;
	display: inline-flex;
	align-items: center;
}

:deep(.token-variable) {
	background-color: var(--fxr-badge-bool, #dcfce7);
	color: var(--fxr-badge-bool-text, #166534);
	border: 1px solid rgba(16, 185, 129, 0.2);
}

:deep(.token-resolver) {
	background-color: var(--fxr-badge-resolver, #fef3c7);
	color: var(--fxr-badge-resolver-text, #92400e);
	border: 1px solid rgba(217, 119, 6, 0.2);
}

.fxr-resolver-modal-overlay {
	position: fixed;
	inset: 0;
	background-color: rgba(0, 0, 0, 0.4);
	z-index: 20000;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 16px;
}

.fxr-resolver-modal-card {
	background-color: var(--fxr-surface-elevated, #ffffff);
	border-radius: 10px;
	width: 100%;
	max-width: 520px;
	overflow: hidden;
	box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
	border: 1px solid var(--fxr-border-subtle, #e2e8f0);
}

.fxr-resolver-modal-header {
	height: 48px;
	padding: 0 16px;
	border-bottom: 1px solid var(--fxr-border-subtle, #e2e8f0);
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.fxr-resolver-modal-body {
	padding: 16px;
	max-height: 65vh;
	overflow-y: auto;
}

.fxr-resolver-modal-footer {
	height: 52px;
	padding: 0 16px;
	border-top: 1px solid var(--fxr-border-subtle, #e2e8f0);
	display: flex;
	justify-content: flex-end;
	gap: 8px;
	background-color: var(--fxr-surface-2, #f8fafc);
	align-items: center;
}

.fvc-wrap.has-error .fvc-main-field {
	border-color: var(--fxr-border-danger, var(--fxr-text-danger, #ef4444)) !important;
	box-shadow: 0 0 0 1px var(--fxr-border-danger, var(--fxr-text-danger, #ef4444)) !important;
}
</style>
