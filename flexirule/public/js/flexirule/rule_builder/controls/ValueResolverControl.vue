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
			:class="{ 'is-active': showPopover, 'is-invalid': !validationResult.valid }"
			tabindex="0"
			@click="togglePopover"
			@keydown="handleParentKeydown"
			:title="validationResult.message"
		>
			<div class="fxr-token__content">
				<i :class="categoryIcon" class="text-muted mr-1"></i>
				<span class="fxr-token__text">{{ previewText }}</span>
			</div>
			<i v-if="!validationResult.valid" class="fa fa-exclamation-triangle text-danger mr-1" style="font-size: 10px"></i>
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
							v-model="localState.kind"
							:disabled="readOnly"
							data-fxr-fieldname="value_resolver.kind"
						>
							<option
								v-for="cat in availableCategories"
								:key="cat.value"
								:value="cat.value"
							>
								{{ cat.label }}
							</option>
						</select>
					</div>

					<hr class="my-2 border-top" />

					<!-- ═══════════ Date Formula ═══════════ -->
					<template v-if="localState.kind === 'date_formula'">
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("Base Date") }}</label>
							<div class="d-flex fxr-gap-2">
								<select
									class="fxr-select flex-1"
									v-model="localState.base_type"
									:disabled="readOnly"
								>
									<option value="today">{{ __("Today") }}</option>
									<option value="doc_field">{{ __("Document Field") }}</option>
								</select>
								<select
									v-if="localState.base_type === 'doc_field'"
									class="fxr-select flex-1"
									v-model="localState.base_field"
									:disabled="readOnly"
								>
									<option
										v-for="opt in dateFieldOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
							</div>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("Offset") }}</label>
							<div class="d-flex align-items-center fxr-gap-2">
								<select
									class="fxr-select"
									v-model="localState.offset_sign"
									style="width: 70px"
									:disabled="readOnly"
								>
									<option value="+">+</option>
									<option value="-">-</option>
								</select>
								<input
									type="number"
									class="fxr-input"
									style="width: 80px"
									v-model.number="localState.offset_value"
									min="0"
									:disabled="readOnly"
								/>
								<select
									class="fxr-select flex-1"
									v-model="localState.offset_unit"
									:disabled="readOnly"
								>
									<option value="days">{{ __("Days") }}</option>
									<option value="weeks">{{ __("Weeks") }}</option>
									<option value="months">{{ __("Months") }}</option>
									<option value="years">{{ __("Years") }}</option>
									<option value="hours">{{ __("Hours") }}</option>
								</select>
							</div>
						</div>
					</template>

					<!-- ═══════════ Math Formula ═══════════ -->
					<template v-else-if="localState.kind === 'math_formula'">
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("Field A") }}</label>
							<select
								class="fxr-select"
								v-model="localState.field_a"
								:disabled="readOnly"
							>
								<option value="">{{ __("Select field...") }}</option>
								<option
									v-for="opt in numericFieldOptions"
									:key="opt.value"
									:value="opt.value"
								>
									{{ opt.label }}
								</option>
							</select>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("Operator") }}</label>
							<select
								class="fxr-select"
								v-model="localState.math_op"
								:disabled="readOnly"
							>
								<option value="+">{{ __("Add (+)") }}</option>
								<option value="-">{{ __("Subtract (-)") }}</option>
								<option value="*">{{ __("Multiply (×)") }}</option>
								<option value="/">{{ __("Divide (÷)") }}</option>
							</select>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("Field B / Value") }}</label>
							<div class="d-flex fxr-gap-2">
								<select
									class="fxr-select flex-1"
									v-model="localState.field_b_type"
									:disabled="readOnly"
								>
									<option value="field">{{ __("Document Field") }}</option>
									<option value="constant">{{ __("Fixed Value") }}</option>
								</select>
								<select
									v-if="localState.field_b_type === 'field'"
									class="fxr-select flex-1"
									v-model="localState.field_b"
									:disabled="readOnly"
								>
									<option value="">{{ __("Select field...") }}</option>
									<option
										v-for="opt in numericFieldOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
								<input
									v-else
									type="number"
									step="any"
									class="fxr-input flex-1"
									v-model.number="localState.constant_b"
									:disabled="readOnly"
									:placeholder="__('Enter value')"
								/>
							</div>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("Round To") }}</label>
							<div class="d-flex align-items-center fxr-gap-2">
								<input
									type="number"
									class="fxr-input"
									style="width: 80px"
									v-model.number="localState.precision"
									min="0"
									max="9"
									:disabled="readOnly"
								/>
								<span class="text-muted fxr-text-xs">{{
									__("decimal places")
								}}</span>
							</div>
						</div>
					</template>

					<!-- ═══════════ Date Difference ═══════════ -->
					<template v-else-if="localState.kind === 'date_diff'">
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("Start Date") }}</label>
							<div class="d-flex fxr-gap-2">
								<select
									class="fxr-select flex-1"
									v-model="localState.diff_start_type"
									:disabled="readOnly"
								>
									<option value="today">{{ __("Today") }}</option>
									<option value="doc_field">{{ __("Document Field") }}</option>
								</select>
								<select
									v-if="localState.diff_start_type === 'doc_field'"
									class="fxr-select flex-1"
									v-model="localState.diff_start_field"
									:disabled="readOnly"
								>
									<option
										v-for="opt in dateFieldOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
							</div>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("End Date") }}</label>
							<div class="d-flex fxr-gap-2">
								<select
									class="fxr-select flex-1"
									v-model="localState.diff_end_type"
									:disabled="readOnly"
								>
									<option value="today">{{ __("Today") }}</option>
									<option value="doc_field">{{ __("Document Field") }}</option>
								</select>
								<select
									v-if="localState.diff_end_type === 'doc_field'"
									class="fxr-select flex-1"
									v-model="localState.diff_end_field"
									:disabled="readOnly"
								>
									<option
										v-for="opt in dateFieldOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
							</div>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("Result Unit") }}</label>
							<select
								class="fxr-select"
								v-model="localState.diff_unit"
								:disabled="readOnly"
							>
								<option value="days">{{ __("Days") }}</option>
								<option value="months">{{ __("Months") }}</option>
								<option value="years">{{ __("Years") }}</option>
							</select>
						</div>
					</template>

					<!-- ═══════════ Aggregation Formula ═══════════ -->
					<template v-else-if="localState.kind === 'child_aggregation'">
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("Child Table") }}</label>
							<select
								class="fxr-select"
								v-model="localState.agg_table"
								:disabled="readOnly"
							>
								<option value="">{{ __("Select child table...") }}</option>
								<option
									v-for="opt in tableFieldOptions"
									:key="opt.value"
									:value="opt.value"
								>
									{{ opt.label }}
								</option>
							</select>
						</div>
						<div
							class="d-flex flex-column fxr-gap-1 mt-2"
							v-if="localState.agg_op !== 'count'"
						>
							<label class="fxr-label-sm">{{ __("Numeric Field") }}</label>
							<select
								class="fxr-select"
								v-model="localState.agg_field"
								:disabled="readOnly"
							>
								<option value="">{{ __("Select field...") }}</option>
								<option
									v-for="opt in aggFieldOptions"
									:key="opt.value"
									:value="opt.value"
								>
									{{ opt.label }}
								</option>
							</select>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("Operation") }}</label>
							<select
								class="fxr-select"
								v-model="localState.agg_op"
								:disabled="readOnly"
							>
								<option value="sum">{{ __("Sum") }}</option>
								<option value="avg">{{ __("Average") }}</option>
								<option value="count">{{ __("Count Rows") }}</option>
							</select>
						</div>
					</template>

					<!-- ═══════════ String Formula ═══════════ -->
					<template v-else-if="localState.kind === 'string_formula'">
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("Operation") }}</label>
							<select
								class="fxr-select"
								v-model="localState.str_op"
								:disabled="readOnly"
							>
								<option value="concat">{{ __("Concatenate") }}</option>
								<option value="fmt_money">{{ __("Format Currency") }}</option>
								<option value="uppercase">{{ __("Uppercase") }}</option>
								<option value="lowercase">{{ __("Lowercase") }}</option>
							</select>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{
								localState.str_op === "fmt_money"
									? __("Numeric Field")
									: __("Value A")
							}}</label>
							<div class="d-flex gap-2">
								<select
									class="fxr-select flex-1"
									v-model="localState.str_a_type"
									:disabled="readOnly"
								>
									<option value="field">{{ __("Document Field") }}</option>
									<option value="constant">{{ __("Fixed Text") }}</option>
								</select>
								<select
									v-if="localState.str_a_type === 'field'"
									class="fxr-select flex-1"
									v-model="localState.str_a"
									:disabled="readOnly"
								>
									<option value="">{{ __("Select field...") }}</option>
									<option
										v-for="opt in localState.str_op === 'fmt_money'
											? numericFieldOptions
											: stringFieldOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
								<input
									v-else
									type="text"
									class="fxr-input flex-1"
									v-model="localState.str_a"
									:disabled="readOnly"
									:placeholder="__('Enter text')"
								/>
							</div>
						</div>
						<div
							class="d-flex flex-column fxr-gap-1 mt-2"
							v-if="['concat', 'fmt_money'].includes(localState.str_op)"
						>
							<label class="fxr-label-sm">{{
								localState.str_op === "fmt_money" ? __("Currency") : __("Value B")
							}}</label>
							<div class="d-flex gap-2">
								<select
									class="fxr-select flex-1"
									v-model="localState.str_b_type"
									:disabled="readOnly"
								>
									<option value="field">{{ __("Document Field") }}</option>
									<option value="constant">
										{{
											localState.str_op === "fmt_money"
												? __("Fixed Currency")
												: __("Fixed Text")
										}}
									</option>
								</select>
								<select
									v-if="localState.str_b_type === 'field'"
									class="fxr-select flex-1"
									v-model="localState.str_b"
									:disabled="readOnly"
								>
									<option value="">{{ __("Select field...") }}</option>
									<option
										v-for="opt in stringFieldOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
								<input
									v-else
									type="text"
									class="fxr-input flex-1"
									v-model="localState.str_b"
									:disabled="readOnly"
									:placeholder="
										localState.str_op === 'fmt_money'
											? __('e.g. USD')
											: __('Enter text')
									"
								/>
							</div>
						</div>
					</template>

					<!-- ═══════════ Normalization ═══════════ -->
					<template v-else-if="localState.kind === 'normalization'">
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("Operation") }}</label>
							<select
								class="fxr-select"
								v-model="localState.norm_op"
								:disabled="readOnly"
							>
								<option value="trim">{{ __("Trim Whitespace") }}</option>
								<option value="slug">{{ __("Slugify") }}</option>
								<option value="title">{{ __("Title Case") }}</option>
								<option value="upper">{{ __("Uppercase") }}</option>
								<option value="lower">{{ __("Lowercase") }}</option>
								<option value="snake">{{ __("Snake Case") }}</option>
							</select>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("Field") }}</label>
							<select
								class="fxr-select"
								v-model="localState.norm_field"
								:disabled="readOnly"
							>
								<option value="">{{ __("Select field...") }}</option>
								<option
									v-for="opt in stringFieldOptions"
									:key="opt.value"
									:value="opt.value"
								>
									{{ opt.label }}
								</option>
							</select>
						</div>
					</template>

					<!-- ═══════════ Format ═══════════ -->
					<template v-else-if="localState.kind === 'format'">
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("Format Type") }}</label>
							<select
								class="fxr-select"
								v-model="localState.fmt_op"
								:disabled="readOnly"
							>
								<option value="format_date">{{ __("Date/Time Format") }}</option>
								<option value="fmt_money">{{ __("Currency Format") }}</option>
								<option value="format">{{ __("String Template") }}</option>
							</select>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("Field") }}</label>
							<select
								class="fxr-select"
								v-model="localState.fmt_field"
								:disabled="readOnly"
							>
								<option value="">{{ __("Select field...") }}</option>
								<option
									v-for="opt in localState.fmt_op === 'fmt_money'
										? numericFieldOptions
										: localState.fmt_op === 'format_date'
										? dateFieldOptions
										: stringFieldOptions"
									:key="opt.value"
									:value="opt.value"
								>
									{{ opt.label }}
								</option>
							</select>
						</div>
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{
								localState.fmt_op === "fmt_money"
									? __("Currency (Field or Code)")
									: localState.fmt_op === "format_date"
									? __("Date Format (e.g. YYYY-MM-DD)")
									: __("Template")
							}}</label>
							<input
								type="text"
								class="fxr-input"
								v-model="localState.fmt_config"
								:disabled="readOnly"
								:placeholder="
									localState.fmt_op === 'format_date' ? 'YYYY-MM-DD' : ''
								"
							/>
						</div>
					</template>

					<!-- ═══════════ Fetch Resolver ═══════════ -->
					<template v-else-if="localState.kind === 'fetch'">
						<!-- Step 1: Source DocType -->
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("1. Source DocType") }}</label>
							<ComboBoxControl
								v-model="localState.linked_doctype"
								doctype="DocType"
								:read_only="readOnly"
								:placeholder="__('Select Source DocType...')"
								hide-label
								allow-custom-value
							/>
						</div>

						<!-- Step 2: Source Document -->
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("2. Source Document") }}</label>
							<div class="d-flex fxr-gap-2">
								<select
									class="fxr-select"
									style="width: 100px"
									v-model="localState.link_source_type"
									:disabled="readOnly"
									@change="localState.link_field = ''"
								>
									<option value="doc_field">{{ __("Field") }}</option>
									<option value="variable">{{ __("Var") }}</option>
									<option value="expression">{{ __("Expr") }}</option>
								</select>
								<ComboBoxControl
									v-if="localState.link_source_type !== 'expression'"
									class="flex-1 min-w-0"
									v-model="localState.link_field"
									:options="sourceLinkOptions"
									:read_only="readOnly"
									:placeholder="
										localState.link_source_type === 'variable'
											? __('Search variable...')
											: __('Select field...')
									"
									:allow-custom-value="localState.link_source_type === 'variable'"
									hide-label
								/>
								<input
									v-else
									type="text"
									class="fxr-input flex-1"
									v-model="localState.link_field"
									:disabled="readOnly"
									:placeholder="__('e.g. doc.party')"
								/>
							</div>
						</div>

						<!-- Step 3: Fetch Field -->
						<div class="d-flex flex-column fxr-gap-1 mt-2">
							<label class="fxr-label-sm">{{ __("3. Fetch Field") }}</label>
							<ComboBoxControl
								v-model="localState.fetch_field"
								:options="fetchFieldOptions"
								:read_only="readOnly || !localState.linked_doctype"
								:loading="fetchMetaLoading"
								:placeholder="
									fetchMetaLoading
										? __('Loading...')
										: __('Select field to fetch...')
								"
								:allow-custom-value="true"
								hide-label
							/>
						</div>
					</template>

					<!-- ═══════════ System Context ═══════════ -->
					<template v-else-if="localState.kind === 'system_context'">
						<div class="d-flex flex-column fxr-gap-1">
							<label class="fxr-label-sm">{{ __("System Token") }}</label>
							<select
								class="fxr-select"
								v-model="localState.sys_token"
								:disabled="readOnly"
							>
								<option value="user">{{ __("Current User") }}</option>
								<option value="role_check">{{ __("Has Role?") }}</option>
							</select>
						</div>
						<div
							class="d-flex flex-column fxr-gap-1 mt-2"
							v-if="localState.sys_token === 'role_check'"
						>
							<label class="fxr-label-sm">{{ __("Role Name") }}</label>
							<input
								type="text"
								class="fxr-input"
								v-model="localState.sys_role"
								:disabled="readOnly"
								:placeholder="__('e.g. System Manager')"
							/>
						</div>
					</template>
				</div>
				<div :class="viewMode === 'inline' ? 'fxr-inline-footer' : 'fxr-popover__footer'">
					<div class="fxr-preview-snippet">
						<code>{{ expressionSnippet }}</code>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useStore } from "../stores";
import ComboBoxControl from "./ComboBoxControl.vue";
import { useFloatingDropdown } from "../composables/useFloatingDropdown";
import { useKeyboardRegistry } from "../composables/useKeyboardRegistry";
import { useValueResolver, RESOLVER_STRATEGIES } from "../composables/useValueResolver";

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
		default: null, // null = all categories
	},
	/** 'popover' (default) or 'inline' */
	viewMode: {
		type: String,
		default: "popover",
	},
});

const emit = defineEmits(["update:modelValue"]);
const store = useStore();
const tokenRef = ref(null);
const kindSelectRef = ref(null);
const { registerShortcut } = useKeyboardRegistry();
const unregisterEsc = ref(null);

const {
	localState,
	validationResult,
	availableCategories,
	categoryIcon,
	popoverTitle,
	previewText,
	expressionSnippet,
} = useValueResolver(props, emit);

// ─── Legacy Category Icons (used by template kind selection) ───
const ALL_CATEGORIES = Object.entries(RESOLVER_STRATEGIES).map(([value, config]) => ({
	value,
	label: __(config.label),
	icon: config.icon,
}));

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
	// Strip both doc. and vars. prefixes
	return String(fieldname)
		.replace(/^doc\./, "")
		.replace(/^vars\./, "");
});

// ─── Field Options ───
const dateFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Date", "Datetime"].includes(f.fieldtype))
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

const numericFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

const stringFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Data", "Text", "Small Text", "Select"].includes(f.fieldtype))
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

const tableFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => f.fieldtype === "Table")
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.fieldname,
				options: f.options,
			};
		});
});

const aggFieldOptions = computed(() => {
	const tableField = localState.value.agg_table;
	if (!tableField) return [];
	const tableMeta = tableFieldOptions.value.find((f) => f.value === tableField);
	if (!tableMeta || !tableMeta.options) return [];
	const childFields = store.doc_meta[tableMeta.options];
	if (!childFields || !Array.isArray(childFields)) return [];
	return childFields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});

const sourceLinkOptions = computed(() => {
	if (localState.value.link_source_type === "variable") {
		const vars = props.variableOptions || [];
		return vars.map((v) => ({
			label: `${v.label || v.value} (vars.${v.value})`,
			value: `vars.${v.value}`,
			options: v.options,
			fieldtype: v.fieldtype,
		}));
	}
	return prioritizedFieldOptions.value;
});

const prioritizedFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];

	const prioritizedTypes = ["Link", "Dynamic Link", "Data", "Select"];

	return [...fields]
		.sort((a, b) => {
			const aPrio = prioritizedTypes.indexOf(a.fieldtype);
			const bPrio = prioritizedTypes.indexOf(b.fieldtype);

			if (aPrio !== -1 && bPrio !== -1) return aPrio - bPrio;
			if (aPrio !== -1) return -1;
			if (bPrio !== -1) return 1;
			return 0;
		})
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
			options: f.options,
			fieldtype: f.fieldtype,
			icon: ["Link", "Dynamic Link"].includes(f.fieldtype) ? "fa fa-link" : "fa fa-columns",
		}));
});

const fetchFieldOptions = computed(() => {
	const linkedDt = localState.value.linked_doctype;
	if (!linkedDt) return [];
	return store.get_fields_for_doctype(linkedDt, { valueMode: "fieldname" });
});

const fetchMetaLoading = ref(false);

watch(
	() => localState.value.link_field,
	async (newVal, oldVal) => {
		if (!newVal) return;

		const opt = sourceLinkOptions.value.find((o) => o.value === newVal);
		if (opt && (opt.options || opt.fieldtype === "Dynamic Link")) {
			let linkedDt = opt.options;
			if (opt.fieldtype === "Dynamic Link") {
				linkedDt = `doc.${opt.options}`;
			}

			// Auto-populate Source DocType if it's empty
			if (linkedDt && !localState.value.linked_doctype) {
				localState.value.linked_doctype = linkedDt;
			}
		}
	}
);

watch(
	() => localState.value.linked_doctype,
	async (newVal, oldVal) => {
		if (!newVal) {
			localState.value.fetch_field = "";
			return;
		}

		if (newVal !== oldVal) {
			// Auto-default fetch field to target field name if it's empty
			if (!localState.value.fetch_field && resolverFieldname.value) {
				localState.value.fetch_field = resolverFieldname.value;
			}
		}

		if (newVal && !newVal.startsWith("doc.") && !newVal.startsWith("vars.")) {
			fetchMetaLoading.value = true;
			try {
				await store.fetch_metadata(newVal);

				// Re-verify auto-defaulted field exists in metadata
				if (
					localState.value.fetch_field === resolverFieldname.value &&
					fetchFieldOptions.value.length > 0
				) {
					const match = fetchFieldOptions.value.find(
						(f) => f.value === resolverFieldname.value
					);
					if (!match) {
						// Don't clear if it was manually typed, but here it's likely our auto-default
						// We'll keep it for now as per user request "default fieldname could hold the same fieldname in target"
					}
				}
			} finally {
				fetchMetaLoading.value = false;
			}
		}
	}
);

watch(
	() => localState.value,
	() => {
		if (showPopover.value) {
			nextTick(() => updatePosition());
		}
	},
	{ deep: true }
);

onMounted(() => {
	document.addEventListener("mousedown", handleClickOutside);
});

onBeforeUnmount(() => {
	document.removeEventListener("mousedown", handleClickOutside);
	if (unregisterEsc.value) unregisterEsc.value();
	cleanupFloatingDropdown();
});

const handleClickOutside = (e) => {
	if (!showPopover.value) return;

	// Ignore clicks inside the control or the popover itself
	if (controlRef.value?.contains(e.target)) return;
	if (popoverRef.value?.contains(e.target)) return;

	// CRITICAL: Ignore clicks on teleported overlays (like ComboBox dropdowns)
	// These are usually children of <body> and outside the popover DOM tree.
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

const handleGlobalKeydown = (e) => {
	if (!showPopover.value) return;

	if (e.key === "Tab") {
		const popover = popoverRef.value;
		if (!popover) return;

		const focusableElements = popover.querySelectorAll(
			'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
		);
		const first = focusableElements[0];
		const last = focusableElements[focusableElements.length - 1];

		if (e.shiftKey) {
			if (document.activeElement === first) {
				last.focus();
				e.preventDefault();
			}
		} else {
			if (document.activeElement === last) {
				first.focus();
				e.preventDefault();
			}
		}
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

	// Return focus to trigger
	nextTick(() => {
		tokenRef.value?.focus();
	});
};

defineExpose({
	open,
	close: closePopover,
	focus: () => tokenRef.value?.focus(),
});
</script>

<style scoped>
.fxr-preview-snippet {
	font-family: var(--fxr-font-mono);
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
	text-align: center;
	word-break: break-all;
}

.preview-snippet code {
	background: transparent;
	color: var(--fxr-accent);
}

.config-row {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-1);
}

.fxr-gap-2 {
	gap: var(--fxr-space-2);
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
