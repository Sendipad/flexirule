<template>
	<div
		ref="controlRef"
		class="fsvc-wrap"
		:class="{ 'is-compact': compact, 'is-disabled': disabled || controlReadOnly }"
	>
		<!-- ── Component Body (Single Line Height 32px–38px) ── -->
		<div
			class="fsvc-main-field"
			:class="{
				'is-dynamic': isDynamicMode || !isStaticSupported,
				'is-static-select':
					!isDynamicMode && (fieldType === 'Select' || fieldType === 'Check'),
			}"
			@click="onWrapClick"
		>
			<!-- Static View using ControlFactory -->
			<div
				v-if="!isDynamicMode && isStaticSupported"
				class="fsvc-static-container flex-1"
				@keydown.capture="onStaticKeydown"
			>
				<!-- Dynamic Link Lookup -->
				<template v-if="fieldType === 'Dynamic Link'">
					<div class="d-flex fxr-gap-1 flex-1 align-items-center w-100">
						<!-- Target Doctype Selector -->
						<select
							class="fxr-select select-sm flex-0"
							style="width: 130px"
							v-model="staticDynamicLinkDoctype"
							:disabled="disabled || controlReadOnly"
						>
							<option value="">{{ __("Doctype...") }}</option>
							<option
								v-for="opt in parsedDoctypeOptions"
								:key="opt.value || opt"
								:value="opt.value || opt"
							>
								{{ opt.label || opt }}
							</option>
						</select>

						<!-- Record Lookup based on selected Doctype -->
						<ControlFactory
							v-if="staticDynamicLinkDoctype"
							:df="{
								fieldtype: 'Link',
								options: staticDynamicLinkDoctype,
								read_only: disabled || controlReadOnly,
							}"
							:modelValue="staticValue"
							:doc="doc"
							:engine="engine"
							:hideLabel="true"
							class="flex-1 min-w-0"
							@update:modelValue="updateStaticValue"
						/>
						<span v-else class="text-muted fxr-text-xs ms-2 flex-1">{{
							__("Select DocType first")
						}}</span>
					</div>
				</template>

				<!-- All other standard types -->
				<template v-else>
					<div
						v-if="fieldType === 'Check'"
						class="d-flex align-items-center flex-1 px-2"
						style="height: 100%"
					>
						<div class="tg-switch">
							<input
								type="checkbox"
								id="static-bool-toggle"
								:checked="!!staticValue"
								:disabled="disabled || controlReadOnly"
								@change="updateStaticValue($event.target.checked ? 1 : 0)"
							/>
							<label class="tg-slider" for="static-bool-toggle"></label>
						</div>
						<label
							for="static-bool-toggle"
							class="tg-switch-label mb-0 ms-2 cursor-pointer"
						>
							{{ !!staticValue ? __("Yes") : __("No") }}
						</label>
					</div>
					<ControlFactory
						v-else
						:df="staticDf"
						:modelValue="staticValue"
						:doc="doc"
						:engine="engine"
						:options="parsedSelectOptions"
						:hideLabel="true"
						class="flex-1 min-w-0 w-100"
						@update:modelValue="updateStaticValue"
					/>
				</template>
			</div>

			<!-- Dynamic Visual Tiptap Editor (Text fields or when dynamic is enabled) -->
			<div v-show="isDynamicMode || !isStaticSupported" class="fsvc-editor-container flex-1">
				<div class="fsvc-editor-wrapper">
					<editor-content :editor="editor" class="fsvc-tiptap-editor" />

					<!-- Inline Actions (JSON Preview) -->
					<div class="fsvc-inline-actions" v-if="!controlReadOnly && !isEditorEmpty">
						<button
							class="fsvc-action-btn"
							:title="__('JSON Preview')"
							@click="openTokenEditor(null, null, 'json')"
						>
							<i class="fa fa-code"></i>
						</button>
					</div>

					<!-- Contextual placeholder shown only when editor is empty and not focused -->
					<div
						v-if="!controlReadOnly && isEditorEmpty && !isEditorFocused"
						class="fsvc-empty-hint"
					>
						<span class="hint-part">|</span> {{ __("static") }}
						<span class="hint-sep">·</span>
						<span class="hint-at">@</span>{{ __("variable") }}
						<span class="hint-sep">·</span>
						<span class="hint-slash">/</span>{{ __("command") }}
					</div>
					<!-- While focused, show a subtle cursor caret hint -->
					<div
						v-else-if="!controlReadOnly && isEditorEmpty && isEditorFocused"
						class="fsvc-focus-hint"
					>
						{{ placeholder || __("Type value, @variable or /command...") }}
					</div>
				</div>
			</div>
		</div>

		<!-- ── Teleported Custom Token Popover (ValueResolverControl Style) ── -->
		<Teleport to="body">
			<div v-if="activeTokenType" class="fxr-popover" :style="popoverStyle">
				<div class="fxr-popover__header">
					<span class="fxr-label-sm mb-0">
						<i
							:class="activeTokenPresentation.icon"
							class="me-2 text-primary fw-medium"
						></i>
						<strong>{{ activeTokenPresentation.title }}</strong>
					</span>
					<button class="fxr-btn fxr-btn--icon fxr-btn--sm" @click="closeTokenEditor">
						<i class="fa fa-times"></i>
					</button>
				</div>
				<div class="fxr-popover__body">
					<!-- 🧮 Formula Modal UI -->
					<template v-if="activeTokenType === 'formula'">
						<div class="d-flex flex-column fxr-gap-2">
							<label class="fxr-label-sm">{{
								__("Formula Expression (Python/Jinja)")
							}}</label>
							<textarea
								ref="formulaTextareaRef"
								class="fxr-textarea formula-textarea"
								v-model="tokenDraftAttrs.expression"
								placeholder="e.g. subtotal * tax"
							></textarea>

							<div class="variables-selector-pane mt-3">
								<label class="fxr-label-sm">{{ __("Insert Variable") }}</label>
								<div class="variables-pill-grid v2-scrollbar">
									<button
										v-for="v in variableOptions"
										:key="v.value || v"
										class="var-pill-btn"
										@click="insertVarInFormula(v)"
									>
										👤 {{ v.label || v.value || v }}
									</button>
								</div>
							</div>
						</div>
					</template>

					<!-- ⚡ Resolver Modal UI -->
					<template v-if="activeTokenType === 'resolver'">
						<div class="d-flex flex-column fxr-gap-3">
							<div class="d-flex flex-column fxr-gap-1">
								<label class="fxr-label-sm">{{ __("Value Resolver Type") }}</label>
								<select class="fxr-select" v-model="tokenDraftAttrs.resolver">
									<option value="">{{ __("Select resolver...") }}</option>
									<option value="query_record">{{ __("Query Record") }}</option>
									<option value="resolve_user">
										{{ __("Resolve Current User") }}
									</option>
									<option value="fetch_global_setting">
										{{ __("Fetch Global Setting") }}
									</option>
									<option value="custom">{{ __("Custom API/Method") }}</option>
								</select>
							</div>

							<div class="d-flex flex-column fxr-gap-1 mt-2">
								<label class="fxr-label-sm d-flex justify-content-between">
									<span>{{ __("Parameters Config") }}</span>
									<button
										class="fxr-btn fxr-btn--sm fxr-btn--secondary py-0"
										@click="addConfigParam"
									>
										<i class="fa fa-plus me-1"></i> {{ __("Add Param") }}
									</button>
								</label>

								<div class="params-editor-list">
									<div
										v-for="(v, k) in tokenDraftAttrs.config"
										:key="k"
										class="param-row d-flex fxr-gap-2 align-items-center mb-2"
									>
										<input
											class="fxr-input flex-1"
											:value="k"
											@change="renameConfigKey(k, $event.target.value)"
											placeholder="Key"
										/>
										<input
											class="fxr-input flex-2"
											v-model="tokenDraftAttrs.config[k]"
											placeholder="Value"
										/>
										<button
											class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost text-danger px-0"
											@click="removeConfigKey(k)"
										>
											<i class="fa fa-trash"></i>
										</button>
									</div>
									<div
										v-if="
											Object.keys(tokenDraftAttrs.config || {}).length === 0
										"
										class="text-muted fxr-text-xs py-2 text-center"
									>
										{{ __("No parameters configured.") }}
									</div>
								</div>
							</div>
						</div>
					</template>

					<!-- 🎨 Formatter Modal UI -->
					<template v-if="activeTokenType === 'formatter'">
						<div class="d-flex flex-column fxr-gap-3">
							<div class="d-flex flex-column fxr-gap-1">
								<label class="fxr-label-sm">{{ __("Formatter Type") }}</label>
								<select class="fxr-select" v-model="tokenDraftAttrs.formatter">
									<option value="currency">{{ __("Currency Format") }}</option>
									<option value="date">{{ __("Date Format") }}</option>
									<option value="percent">{{ __("Percentage") }}</option>
									<option value="number">{{ __("Numeric Precision") }}</option>
									<option value="uppercase">{{ __("Uppercase") }}</option>
									<option value="lowercase">{{ __("Lowercase") }}</option>
								</select>
							</div>

							<div class="d-flex flex-column fxr-gap-1 mt-2">
								<label class="fxr-label-sm">{{ __("Formatter Options") }}</label>
								<div class="formatter-options-block p-3 border rounded">
									<template v-if="tokenDraftAttrs.formatter === 'currency'">
										<div class="mb-2">
											<label class="fxr-label-xs">{{
												__("Currency Symbol / Field")
											}}</label>
											<input
												class="fxr-input input-sm"
												v-model="tokenDraftAttrs.options.currency"
												placeholder="e.g. USD, EUR, doc.currency"
											/>
										</div>
										<div>
											<label class="fxr-label-xs">{{ __("Decimals") }}</label>
											<input
												type="number"
												class="fxr-input input-sm"
												v-model.number="tokenDraftAttrs.options.decimals"
											/>
										</div>
									</template>
									<template v-else-if="tokenDraftAttrs.formatter === 'date'">
										<div>
											<label class="fxr-label-xs">{{
												__("Format Pattern")
											}}</label>
											<input
												class="fxr-input input-sm"
												v-model="tokenDraftAttrs.options.format"
												placeholder="e.g. YYYY-MM-DD, DD/MM/YYYY"
											/>
										</div>
									</template>
									<template v-else-if="tokenDraftAttrs.formatter === 'number'">
										<div>
											<label class="fxr-label-xs">{{ __("Decimals") }}</label>
											<input
												type="number"
												class="fxr-input input-sm"
												v-model.number="tokenDraftAttrs.options.precision"
											/>
										</div>
									</template>
									<template v-else>
										<span class="text-muted fxr-text-xs">{{
											__("No additional settings required.")
										}}</span>
									</template>
								</div>
							</div>
						</div>
					</template>

					<!-- 🔄 Normalize Modal UI -->
					<template v-if="activeTokenType === 'normalize'">
						<div class="d-flex flex-column fxr-gap-2">
							<label class="fxr-label-sm d-flex justify-content-between">
								<span>{{ __("Normalization Pipeline Steps") }}</span>
								<button
									class="fxr-btn fxr-btn--sm fxr-btn--secondary py-0"
									@click="tokenDraftAttrs.steps.push({ type: 'trim' })"
								>
									<i class="fa fa-plus me-1"></i> {{ __("Add Step") }}
								</button>
							</label>

							<div
								class="pipeline-editor-list v2-scrollbar"
								style="max-height: 250px"
							>
								<div
									v-for="(step, idx) in tokenDraftAttrs.steps"
									:key="idx"
									class="pipeline-step-card p-3 border rounded mb-2"
								>
									<div
										class="d-flex justify-content-between align-items-center mb-2"
									>
										<span class="badge bg-info text-white"
											>{{ __("Step") }} {{ idx + 1 }}</span
										>
										<button
											class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost text-danger px-0"
											@click="tokenDraftAttrs.steps.splice(idx, 1)"
										>
											<i class="fa fa-trash"></i>
										</button>
									</div>

									<div class="row">
										<div class="col-sm-6 mb-2">
											<label class="fxr-label-xs">{{
												__("Transformation")
											}}</label>
											<select
												class="fxr-select select-sm"
												v-model="tokenDraftAttrs.steps[idx].type"
											>
												<option value="trim">
													{{ __("Trim Whitespace") }}
												</option>
												<option value="lowercase">
													{{ __("To Lowercase") }}
												</option>
												<option value="uppercase">
													{{ __("To Uppercase") }}
												</option>
												<option value="strip_html">
													{{ __("Strip HTML") }}
												</option>
												<option value="replace">
													{{ __("Find & Replace") }}
												</option>
											</select>
										</div>
										<template
											v-if="tokenDraftAttrs.steps[idx].type === 'replace'"
										>
											<div class="col-sm-3 mb-2">
												<label class="fxr-label-xs">{{ __("Find") }}</label>
												<input
													class="fxr-input input-sm"
													v-model="tokenDraftAttrs.steps[idx].find"
													placeholder="e.g. -"
												/>
											</div>
											<div class="col-sm-3 mb-2">
												<label class="fxr-label-xs">{{
													__("Replace With")
												}}</label>
												<input
													class="fxr-input input-sm"
													v-model="tokenDraftAttrs.steps[idx].replace"
													placeholder="e.g. _"
												/>
											</div>
										</template>
									</div>
								</div>
								<div
									v-if="
										!tokenDraftAttrs.steps || tokenDraftAttrs.steps.length === 0
									"
									class="text-muted fxr-text-xs py-4 text-center"
								>
									{{
										__(
											"No steps added. Value will pass through without alterations."
										)
									}}
								</div>
							</div>
						</div>
					</template>

					<!-- 🔀 Condition Modal UI -->
					<template v-if="activeTokenType === 'condition'">
						<div class="d-flex flex-column fxr-gap-2">
							<label class="fxr-label-sm">{{ __("Condition Rule Builder") }}</label>
							<div class="condition-builder-dialog-wrap border p-3 rounded">
								<ConditionBuilder
									:modelValue="tokenDraftAttrs.condition"
									:docFields="parsedDocFieldOptions"
									:variableOptions="variableOptions"
									:readOnly="false"
									@update:modelValue="tokenDraftAttrs.condition = $event"
								/>
							</div>
						</div>
					</template>

					<!-- 🌐 Translation Modal UI -->
					<template v-if="activeTokenType === 'localization'">
						<div class="d-flex flex-column fxr-gap-2">
							<label class="fxr-label-sm">{{
								__("Localized String Value / Key")
							}}</label>
							<input
								class="fxr-input"
								v-model="tokenDraftAttrs.value"
								placeholder="e.g. subtotal_amount"
							/>
							<small class="text-muted">{{
								__(
									"This wraps the value in dynamic localization filters _() at runtime."
								)
							}}</small>
						</div>
					</template>

					<!-- 🔗 Link Picker Modal UI -->
					<template v-if="activeTokenType === 'link'">
						<div class="d-flex flex-column fxr-gap-3">
							<div class="d-flex flex-column fxr-gap-1">
								<label class="fxr-label-sm">{{ __("Doctype") }}</label>
								<select class="fxr-select" v-model="tokenDraftAttrs.doctype">
									<option value="">{{ __("Select Doctype...") }}</option>
									<option
										v-for="opt in parsedDoctypeOptions"
										:key="opt.value || opt"
										:value="opt.value || opt"
									>
										{{ opt.label || opt }}
									</option>
								</select>
							</div>

							<div
								v-if="tokenDraftAttrs.doctype"
								class="d-flex flex-column fxr-gap-1 mt-2"
							>
								<label class="fxr-label-sm">{{ __("Search Linked Record") }}</label>
								<ComboBoxControl
									:df="{ fieldtype: 'Link', options: tokenDraftAttrs.doctype }"
									v-model="tokenDraftAttrs.value"
									:hideLabel="true"
								/>
							</div>
						</div>
					</template>

					<!-- ⌄ Select Modal UI -->
					<template v-if="activeTokenType === 'select'">
						<div class="d-flex flex-column fxr-gap-3">
							<label class="fxr-label-sm">{{ __("Select Option") }}</label>
							<select class="fxr-select" v-model="tokenDraftAttrs.value">
								<option value="">{{ __("Select option...") }}</option>
								<option
									v-for="opt in parsedSelectOptions"
									:key="opt.value || opt"
									:value="opt.value || opt"
								>
									{{ opt.label || opt }}
								</option>
							</select>
						</div>
					</template>

					<!-- 🔘 Boolean Modal UI -->
					<template v-if="activeTokenType === 'boolean'">
						<div class="d-flex align-items-center fxr-gap-3 p-2">
							<div class="tg-switch">
								<input
									type="checkbox"
									id="token-bool-toggle"
									v-model="tokenDraftAttrs.value"
								/>
								<label class="tg-slider" for="token-bool-toggle"></label>
							</div>
							<label for="token-bool-toggle" class="tg-switch-label mb-0">{{
								tokenDraftAttrs.value ? __("Enabled (Yes)") : __("Disabled (No)")
							}}</label>
						</div>
					</template>

					<!-- 📑 MultiSelect Modal UI -->
					<template v-if="activeTokenType === 'multiselect'">
						<div class="d-flex flex-column fxr-gap-3">
							<label class="fxr-label-sm">{{ __("Select Multiple Options") }}</label>
							<MultiSelectList
								:df="{ fieldtype: 'MultiSelect', options: options }"
								:modelValue="tokenDraftAttrs.values"
								@update:modelValue="tokenDraftAttrs.values = $event"
							/>
						</div>
					</template>

					<!-- 📦 JSON Modal UI -->
					<template v-if="activeTokenType === 'json'">
						<div class="d-flex flex-column fxr-gap-3">
							<label class="fxr-label-sm">{{ __("JSON Data Editor") }}</label>
							<textarea
								class="fxr-textarea json-textarea"
								v-model="tokenDraftAttrs.value"
								placeholder='{ "key": "value" }'
							></textarea>
							<div v-if="jsonParseError" class="text-danger fxr-text-xs">
								{{ jsonParseError }}
							</div>
						</div>
					</template>

					<!-- 🔑 Add Key/Value Modal UI -->
					<template v-if="activeTokenType === 'add-key'">
						<div class="d-flex flex-column fxr-gap-2">
							<label class="fxr-label-sm">{{ __("Structured Key/Value") }}</label>
							<div class="d-flex fxr-gap-2">
								<input
									class="fxr-input flex-1"
									v-model="tokenDraftAttrs.key"
									placeholder="Key"
								/>
								<input
									class="fxr-input flex-2"
									v-model="tokenDraftAttrs.value"
									placeholder="Value"
								/>
							</div>
						</div>
					</template>

					<!-- 🧩 Dynamic Link Modal UI -->
					<template v-if="activeTokenType === 'dynamicLink'">
						<div class="d-flex flex-column fxr-gap-3">
							<!-- Dynamic Doctype Mode Selector -->
							<div class="d-flex flex-column fxr-gap-1">
								<label class="fxr-label-sm">{{
									__("Doctype Configuration Mode")
								}}</label>
								<select class="fxr-select" v-model="dynamicLinkMode">
									<option value="static">
										{{ __("Static Override Doctype") }}
									</option>
									<option value="reference">
										{{ __("Reference Field Doctype") }}
									</option>
									<option value="variable">
										{{ __("Variable-based Doctype") }}
									</option>
								</select>
							</div>

							<!-- Depending on selected mode -->
							<div class="d-flex flex-column fxr-gap-1 mt-2">
								<!-- Static Mode Selector -->
								<template v-if="dynamicLinkMode === 'static'">
									<label class="fxr-label-sm">{{
										__("Select Doctype Override")
									}}</label>
									<select class="fxr-select" v-model="tokenDraftAttrs.doctype">
										<option value="">{{ __("Select Doctype...") }}</option>
										<option
											v-for="opt in parsedDoctypeOptions"
											:key="opt.value || opt"
											:value="opt.value || opt"
										>
											{{ opt.label || opt }}
										</option>
									</select>
								</template>

								<!-- Reference Field Selector -->
								<template v-else-if="dynamicLinkMode === 'reference'">
									<label class="fxr-label-sm">{{
										__("Reference Field Name")
									}}</label>
									<select
										class="fxr-select"
										v-model="tokenDraftAttrs.reference_field"
									>
										<option value="">{{ __("Select field...") }}</option>
										<option
											v-for="opt in parsedDocFieldOptions"
											:key="opt.value"
											:value="opt.value"
										>
											{{ opt.label }}
										</option>
									</select>
								</template>

								<!-- Variable-based Selector -->
								<template v-else-if="dynamicLinkMode === 'variable'">
									<label class="fxr-label-sm">{{
										__("Doctype Variable Path")
									}}</label>
									<select
										class="fxr-select"
										v-model="tokenDraftAttrs.doctype_variable"
									>
										<option value="">{{ __("Select variable...") }}</option>
										<option
											v-for="opt in variableOptions"
											:key="opt.value || opt"
											:value="opt.value || opt"
										>
											{{ opt.label || opt }}
										</option>
									</select>
								</template>
							</div>

							<!-- Resolved Preview & Record Picker -->
							<div class="dynamic-resolved-preview-block p-3 border rounded mt-2">
								<div class="mb-2 fxr-text-sm">
									<strong>{{ __("Resolved Doctype:") }}</strong>
									<span class="badge bg-success ms-2">{{
										resolvedDynamicDoctype || __("None")
									}}</span>
								</div>

								<div
									v-if="resolvedDynamicDoctype"
									class="d-flex flex-column fxr-gap-1"
								>
									<label class="fxr-label-sm">{{
										__("Search Linked Record")
									}}</label>
									<ComboBoxControl
										:df="{ fieldtype: 'Link', options: resolvedDynamicDoctype }"
										v-model="tokenDraftAttrs.value"
										:hideLabel="true"
									/>
								</div>
							</div>
						</div>
					</template>
				</div>

				<footer class="fxr-popover__footer d-flex justify-content-end fxr-gap-1 p-3">
					<button
						class="fxr-btn fxr-btn--sm fxr-btn--secondary"
						@click="closeTokenEditor"
					>
						{{ __("Cancel") }}
					</button>
					<button class="fxr-btn fxr-btn--sm fxr-btn--primary" @click="saveTokenEditor">
						{{ __("Save") }}
					</button>
				</footer>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import {
	computed,
	ref,
	watch,
	onBeforeUnmount,
	nextTick,
	shallowRef,
	onMounted,
	defineAsyncComponent,
} from "vue";
import { Editor, EditorContent, VueRenderer } from "@tiptap/vue-3";
import { StarterKit } from "@tiptap/starter-kit";
import { Node, mergeAttributes } from "@tiptap/core";
import Mention from "@tiptap/extension-mention";
import { PluginKey } from "@tiptap/pm/state";
import tippy from "tippy.js";

// Aggressively Reuse MentionList, ComboBoxControl, and ControlFactory
import MentionList from "./MentionList.vue";
import ComboBoxControl from "./ComboBoxControl.vue";
import MultiSelectList from "./MultiSelectList.vue";
import ConditionBuilder from "../components/condition_builder/ConditionBuilder.vue";

const ControlFactory = defineAsyncComponent(() => import("./ControlFactory.vue"));

// ─── Commands registry — one source of truth ─────────────────────────────────
const ALL_SLASH_COMMANDS = [
	{ id: "formula", label: __("Formula"), type: "logic", icon: "🧮", groups: ["*"] },
	{ id: "resolver", label: __("Resolver"), type: "logic", icon: "⚡", groups: ["*"] },
	{
		id: "formatter",
		label: __("Formatter"),
		type: "logic",
		icon: "🎨",
		groups: ["text", "numeric"],
	},
	{ id: "normalize", label: __("Normalize"), type: "logic", icon: "🔄", groups: ["text"] },
	{ id: "localization", label: __("Translation"), type: "logic", icon: "🌐", groups: ["text"] },
	{ id: "condition", label: __("Condition"), type: "logic", icon: "🔀", groups: ["*"] },
	{ id: "link", label: __("Link Picker"), type: "logic", icon: "🔗", groups: ["link"] },
	{ id: "dynamic-link", label: __("Dynamic Link"), type: "logic", icon: "🧩", groups: ["link"] },
	{ id: "json", label: __("JSON Editor"), type: "logic", icon: "📦", groups: ["*"] },
	{ id: "add-key", label: __("Add Key/Value"), type: "logic", icon: "🔑", groups: ["*"] },
	{ id: "clear", label: __("Clear Editor"), type: "logic", icon: "🗑️", groups: ["*"] },
	{ id: "select", label: __("Select Option"), type: "logic", icon: "⌄", groups: ["select"] },
	{ id: "boolean", label: __("Toggle"), type: "logic", icon: "🔘", groups: ["boolean"] },
	{
		id: "multiselect",
		label: __("Multi Select"),
		type: "logic",
		icon: "📑",
		groups: ["multiselect"],
	},
];

// Fieldtype → command group classification
const NUMERIC_FIELDTYPES = new Set(["Int", "Float", "Currency", "Percent", "Duration"]);
const DATE_FIELDTYPES_ALL = new Set(["Date", "Datetime", "Time"]);
const BOOLEAN_FIELDTYPES = new Set(["Check"]);
const LINK_FIELDTYPES = new Set(["Link", "Dynamic Link"]);

function getCommandGroupForFieldtype(ft) {
	if (NUMERIC_FIELDTYPES.has(ft)) return "numeric";
	if (DATE_FIELDTYPES_ALL.has(ft)) return "date";
	if (BOOLEAN_FIELDTYPES.has(ft)) return "boolean";
	if (ft === "Link") return "link";
	if (ft === "Dynamic Link") return "link";
	if (ft === "Select") return "select";
	if (ft === "MultiSelect") return "multiselect";
	return "text";
}

const props = defineProps({
	modelValue: { type: [Object, String], default: null },
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
	placeholder: { type: String, default: "" },
	/** Explicit allowlist of command ids to show (empty = all context-allowed commands shown). */
	allowedModes: { type: Array, default: () => [] },
	/** Explicit denylist of command ids — takes highest priority over fieldtype/allowedModes. */
	disabledCommands: { type: Array, default: () => [] },
	fieldType: { type: String, default: "Data" },
	compact: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
	options: { type: [Array, String], default: () => [] }, // for Select / Autocomplete static rendering
	referenceDoctype: { type: String, default: "" }, // for Link record selection
	referenceField: { type: String, default: "" }, // for Dynamic Link source
	doctypeOptions: { type: Array, default: () => [] }, // list of doctypes
	linkOptions: { type: Object, default: () => ({}) },
	meta: { type: Object, default: () => ({}) },
	engine: { type: Object, default: null },
	doc: { type: Object, default: null },
	operator: { type: String, default: "" },
});

const emit = defineEmits(["update", "update:modelValue"]);

const controlReadOnly = computed(
	() => !!props.readOnly || !!props.read_only || !!props.meta?.read_only
);

// Dynamic toggle indicator
const isDynamicMode = ref(false);
const isSuggestionOpen = ref(false);

// Teleported Modal/Dialog Controllers
const activeTokenType = ref(null); // 'formula', 'resolver', 'formatter', 'normalize', 'condition', 'localization', 'link', 'dynamicLink'
const activeTokenNode = ref(null);
const activeTokenPos = ref(null);
const tokenDraftAttrs = ref({});
const jsonParseError = ref("");
const formulaTextareaRef = ref(null);
const controlRef = ref(null);
const popoverStyle = ref({});

// Dynamic Link Sub-Modes
const dynamicLinkMode = ref("static"); // 'static', 'reference', 'variable'

// Static Local Storage State
const staticValue = ref("");
const staticDynamicLinkDoctype = ref("");

// Generic static input supporting types
// Text-based fields go straight to Tiptap (no static toggle).
// Autocomplete gets a ComboBox in static mode, so it IS static-supported.
const PURE_TEXT_FIELDTYPES = new Set([
	"Data",
	"Small Text",
	"Text",
	"Long Text",
	"Code",
	"Text Editor",
]);
const isStaticSupported = computed(() => {
	return !PURE_TEXT_FIELDTYPES.has(props.fieldType);
});

const staticDf = computed(() => {
	let ft = props.fieldType;
	let options = ft === "Link" ? props.referenceDoctype : props.options || [];

	if (ft === "Select") {
		ft = "Autocomplete";
		options = parsedSelectOptions.value;
	}

	// For Link types, we keep them as Link to use ComboBoxControl via ControlFactory
	// and ensure they trigger dynamic mode on @ or /

	return {
		fieldtype: ft,
		label: "",
		options: options,
		read_only: props.disabled || controlReadOnly.value,
		placeholder: props.placeholder,
		description: "",
	};
});

// ─── Tiptap Custom Token Nodes (Compact Inline Atom Chips) ───

const VariableToken = Node.create({
	name: "variableToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			path: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-path") || "",
				renderHTML: (attrs) => ({ "data-path": attrs.path }),
			},
			label: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-label") || "",
				renderHTML: (attrs) => ({ "data-label": attrs.label }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="variable"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.label || node.attrs.path;
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "variable",
				class: "token-chip token-variable",
			}),
			`👤 ${label}`,
		];
	},
});

const SelectToken = Node.create({
	name: "selectToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			value: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-value") || "",
				renderHTML: (attrs) => ({ "data-value": attrs.value }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="select"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "select",
				class: "token-chip token-select",
			}),
			`⌄ ${node.attrs.value || "Select..."}`,
		];
	},
});

const BooleanToken = Node.create({
	name: "booleanToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			value: {
				default: false,
				parseHTML: (el) => el.getAttribute("data-value") === "true",
				renderHTML: (attrs) => ({ "data-value": attrs.value }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="boolean"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.value ? __("Yes") : __("No");
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "boolean",
				class: `token-chip token-boolean ${node.attrs.value ? "is-true" : "is-false"}`,
			}),
			`🔘 ${label}`,
		];
	},
});

const MultiSelectToken = Node.create({
	name: "multiSelectToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			values: {
				default: () => [],
				parseHTML: (el) => safeJsonDecode(el.getAttribute("data-values")) || [],
				renderHTML: (attrs) => ({ "data-values": safeJsonEncode(attrs.values) }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="multiselect"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const count = node.attrs.values?.length || 0;
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "multiselect",
				class: "token-chip token-multiselect",
			}),
			`📑 ${count} items`,
		];
	},
});

const FormulaToken = Node.create({
	name: "formulaToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			expression: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-expression") || "",
				renderHTML: (attrs) => ({ "data-expression": attrs.expression }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="formula"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.expression ? ` (${node.attrs.expression})` : "";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "formula",
				class: "token-chip token-formula",
			}),
			`🧮 Formula${label}`,
		];
	},
});

const ResolverToken = Node.create({
	name: "resolverToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			resolver: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-resolver") || "",
				renderHTML: (attrs) => ({ "data-resolver": attrs.resolver }),
			},
			config: {
				default: () => ({}),
				parseHTML: (el) => safeJsonDecode(el.getAttribute("data-config")) || {},
				renderHTML: (attrs) => ({ "data-config": safeJsonEncode(attrs.config) }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="resolver"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.resolver ? ` (${node.attrs.resolver})` : "";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "resolver",
				class: "token-chip token-resolver",
			}),
			`⚡ Resolve${label}`,
		];
	},
});

const FormatterToken = Node.create({
	name: "formatterToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			formatter: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-formatter") || "",
				renderHTML: (attrs) => ({ "data-formatter": attrs.formatter }),
			},
			options: {
				default: () => ({}),
				parseHTML: (el) => safeJsonDecode(el.getAttribute("data-options")) || {},
				renderHTML: (attrs) => ({ "data-options": safeJsonEncode(attrs.options) }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="formatter"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.formatter ? ` (${node.attrs.formatter})` : "";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "formatter",
				class: "token-chip token-formatter",
			}),
			`🎨 Format${label}`,
		];
	},
});

const NormalizeToken = Node.create({
	name: "normalizeToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			steps: {
				default: () => [],
				parseHTML: (el) => safeJsonDecode(el.getAttribute("data-steps")) || [],
				renderHTML: (attrs) => ({ "data-steps": safeJsonEncode(attrs.steps) }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="normalize"]' }];
	},
	renderHTML({ HTMLAttributes }) {
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "normalize",
				class: "token-chip token-normalize",
			}),
			`🔄 Normalize`,
		];
	},
});

const ConditionToken = Node.create({
	name: "conditionToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			condition: {
				default: () => ({}),
				parseHTML: (el) => safeJsonDecode(el.getAttribute("data-condition")) || {},
				renderHTML: (attrs) => ({ "data-condition": safeJsonEncode(attrs.condition) }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="condition"]' }];
	},
	renderHTML({ HTMLAttributes }) {
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "condition",
				class: "token-chip token-condition",
			}),
			`🔀 Condition`,
		];
	},
});

const LocalizationToken = Node.create({
	name: "localizationToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			value: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-value") || "",
				renderHTML: (attrs) => ({ "data-value": attrs.value }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="localization"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.value ? ` (${node.attrs.value})` : "";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "localization",
				class: "token-chip token-localization",
			}),
			`🌐 Translation${label}`,
		];
	},
});

const LinkToken = Node.create({
	name: "linkToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			doctype: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-doctype") || "",
				renderHTML: (attrs) => ({ "data-doctype": attrs.doctype }),
			},
			value: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-value") || "",
				renderHTML: (attrs) => ({ "data-value": attrs.value }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="link"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.value ? `: ${node.attrs.value}` : "";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "link",
				class: "token-chip token-link",
			}),
			`🔗 ${node.attrs.doctype || "Link"}${label}`,
		];
	},
});

const DynamicLinkToken = Node.create({
	name: "dynamicLinkToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			reference_field: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-reference-field") || "",
				renderHTML: (attrs) => ({ "data-reference-field": attrs.reference_field }),
			},
			doctype: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-doctype") || "",
				renderHTML: (attrs) => ({ "data-doctype": attrs.doctype }),
			},
			doctype_variable: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-doctype-variable") || "",
				renderHTML: (attrs) => ({ "data-doctype-variable": attrs.doctype_variable }),
			},
			value: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-value") || "",
				renderHTML: (attrs) => ({ "data-value": attrs.value }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="dynamic_link"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.value ? `: ${node.attrs.value}` : "";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "dynamic_link",
				class: "token-chip token-dynamic-link",
			}),
			`🧩 Dynamic Link${label}`,
		];
	},
});

// Helper functions for URI Encoding of Complex Token Data Objects
function safeJsonEncode(obj) {
	try {
		return encodeURIComponent(JSON.stringify(obj || {}));
	} catch (e) {
		return "";
	}
}

function safeJsonDecode(str) {
	try {
		return str ? JSON.parse(decodeURIComponent(str)) : null;
	} catch (e) {
		return null;
	}
}

// ─── Tiptap Mention Extends (Auto suggestions / Command palette) ───

const VariableTrigger = Mention.extend({
	name: "variableTrigger",
});

const CommandTrigger = Mention.extend({
	name: "commandTrigger",
});

// ─── Vue-based Suggestion Renderers & Tippy Popup ───

function createSuggestionRenderer() {
	let component;
	let popup;
	return {
		onStart: (props) => {
			isSuggestionOpen.value = true;
			component = new VueRenderer(MentionList, { props, editor: props.editor });
			if (!props.clientRect) return;
			popup = tippy("body", {
				getReferenceClientRect: props.clientRect,
				appendTo: () => document.body,
				content: component.element,
				showOnCreate: true,
				interactive: true,
				trigger: "manual",
				placement: "bottom-start",
			});
		},
		onUpdate(props) {
			component?.updateProps(props);
			popup?.[0]?.setProps({ getReferenceClientRect: props.clientRect });
		},
		onKeyDown(props) {
			if (props.event.key === "Escape") {
				popup?.[0]?.hide();
				return true;
			}
			return component?.ref?.onKeyDown(props);
		},
		onExit() {
			isSuggestionOpen.value = false;
			popup?.[0]?.destroy();
			component?.destroy();
		},
	};
}

// ─── Tiptap Editor Core Hook Setup ───

let emitting = false;

const editor = new Editor({
	extensions: [
		StarterKit.configure({
			heading: false,
			codeBlock: false,
			blockquote: false,
			bulletList: false,
			orderedList: false,
			listItem: false,
			horizontalRule: false,
		}),
		VariableToken,
		FormulaToken,
		ResolverToken,
		FormatterToken,
		NormalizeToken,
		ConditionToken,
		LocalizationToken,
		LinkToken,
		DynamicLinkToken,
		SelectToken,
		BooleanToken,
		MultiSelectToken,
		VariableTrigger.configure({
			suggestion: {
				char: "@",
				pluginKey: new PluginKey("variableTrigger"),
				command: ({ editor, range, props }) => {
					editor
						.chain()
						.focus()
						.insertContentAt(range, [
							{
								type: "variableToken",
								attrs: { path: props.id, label: props.label },
							},
						])
						.run();
				},
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					const q = query.toLowerCase();
					const systemMentions = [
						{
							id: "doc",
							label: "doc",
							type: "variable",
							icon: "📄",
							description: __("Current Document"),
						},
						{
							id: "user",
							label: "user",
							type: "variable",
							icon: "👤",
							description: __("Current User"),
						},
						{
							id: "now",
							label: "now",
							type: "variable",
							icon: "🕒",
							description: __("Current Time"),
						},
						{
							id: "today",
							label: "today",
							type: "variable",
							icon: "📅",
							description: __("Current Date"),
						},
						{
							id: "param",
							label: "param",
							type: "variable",
							icon: "📥",
							description: __("Action Parameters"),
						},
					];
					const options = [
						...systemMentions,
						...(props.variableOptions || []).map((v) => ({
							id: v.value || v,
							label: v.label || v,
							type: "variable",
							icon: v.is_variable ? "fa fa-code" : "fa fa-cube",
						})),
					];
					return options
						.filter(
							(v) =>
								v.id.toLowerCase().includes(q) || v.label.toLowerCase().includes(q)
						)
						.slice(0, 50);
				},
			},
		}),
		CommandTrigger.configure({
			suggestion: {
				char: "/",
				pluginKey: new PluginKey("commandTrigger"),
				command: ({ editor, range, props }) => {
					if (props.id === "clear") {
						editor.chain().focus().setContent("").run();
						return;
					}

					const tokenMap = {
						formula: "formulaToken",
						resolver: "resolverToken",
						formatter: "formatterToken",
						normalize: "normalizeToken",
						localization: "localizationToken",
						condition: "conditionToken",
						link: "linkToken",
						"dynamic-link": "dynamicLinkToken",
						json: "resolverToken", // For now map JSON to resolver or a generic handler
						"add-key": "resolverToken",
						select: "selectToken",
						boolean: "booleanToken",
						multiselect: "multiSelectToken",
					};
					const tokenName = tokenMap[props.id];
					if (tokenName) {
						editor
							.chain()
							.focus()
							.insertContentAt(range, [{ type: tokenName, attrs: {} }])
							.run();

						// Focus after content insertion and fire dialog configuration for custom token
						nextTick(() => {
							if (props.id === "json" || props.id === "add-key") {
								openTokenEditor(null, null, props.id);
							} else {
								const { selection } = editor.state;
								const pos = selection.$from.pos - 1;
								const node = editor.state.doc.nodeAt(pos);

								if (node && node.type.name === tokenName) {
									openTokenEditor(node, pos);
								} else {
									// fallback to scanning if cursor position logic fails
									editor.state.doc.descendants((node, pos) => {
										if (node.type.name === tokenName) {
											openTokenEditor(node, pos);
											return false;
										}
									});
								}
							}
						});
					}
				},
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					const q = query.toLowerCase();
					const fType = props.fieldType;
					const group = getCommandGroupForFieldtype(fType);

					// ── 1. Start with all commands ───────────────────────────────
					let filtered = [...ALL_SLASH_COMMANDS];

					// ── 2. Fieldtype-based group filter ──────────────────────────
					// Each command declares which groups it belongs to.
					// "*" means it appears for every fieldtype.
					filtered = filtered.filter((c) => {
						if (c.groups.includes("*")) return true;
						if (c.groups.includes(group)) return true;
						return false;
					});

					// ── 3. Additional per-fieldtype exclusions ───────────────────
					// Boolean fields: formula/resolver/condition/boolean make sense
					if (BOOLEAN_FIELDTYPES.has(fType)) {
						filtered = filtered.filter((c) =>
							["formula", "resolver", "condition", "boolean"].includes(c.id)
						);
					}
					// Date fields: normalize/localization/link/dynamic-link don't apply
					if (DATE_FIELDTYPES_ALL.has(fType)) {
						filtered = filtered.filter(
							(c) =>
								!["localization", "normalize", "link", "dynamic-link"].includes(
									c.id
								)
						);
					}
					// Numeric fields: formula/resolver/formatter/condition make sense
					if (NUMERIC_FIELDTYPES.has(fType)) {
						filtered = filtered.filter((c) =>
							["formula", "resolver", "formatter", "condition"].includes(c.id)
						);
					}

					// ── 4. Operator-based filtering ──────────────────────────────
					if (props.operator === "toggle") {
						// Toggle doesn't need a value usually, but if they enter one...
						filtered = filtered.filter((c) => ["formula", "resolver"].includes(c.id));
					} else if (props.operator === "increment" || props.operator === "decrement") {
						// Only formula/resolver make sense for numeric adjustments
						filtered = filtered.filter((c) => ["formula", "resolver"].includes(c.id));
					} else if (props.operator === "append") {
						// For list append, only formula/resolver make sense
						filtered = filtered.filter((c) => ["formula", "resolver"].includes(c.id));
					} else if (props.operator === "merge") {
						// For object merge, formula/resolver/json make sense
						filtered = filtered.filter((c) =>
							["formula", "resolver", "json"].includes(c.id)
						);
					}

					// ── 4. Props allowedModes override (explicit allowlist) ──────
					if (props.allowedModes && props.allowedModes.length > 0) {
						filtered = filtered.filter(
							(c) =>
								props.allowedModes.includes(c.id) ||
								(c.id === "dynamic-link" &&
									props.allowedModes.includes("dynamic_link"))
						);
					}

					// ── 5. Caller-level denylist (highest priority) ──────────────
					if (props.disabledCommands && props.disabledCommands.length > 0) {
						filtered = filtered.filter((c) => !props.disabledCommands.includes(c.id));
					}

					// ── 6. Query text filter ────────────────────────────────────
					return filtered.filter((c) => c.label.toLowerCase().includes(q));
				},
			},
		}),
	],
	editable: !controlReadOnly.value,
	editorProps: {
		handleKeyDown(view, event) {
			// Compact single line editor, block Enter key from creating newlines
			if (event.key === "Enter") {
				if (isSuggestionOpen.value) return false;
				event.preventDefault();
				emit("submit");
				return true;
			}
			return false;
		},
		transformPastedText(text) {
			// Strip all newlines on paste to guarantee a single-line constraint
			return text.replace(/[\r\n]+/g, " ");
		},
		handleClick(view, pos, event) {
			// Intercept node clicks on custom tokens to configure them in dialog
			const { state } = view;
			let node = state.doc.nodeAt(pos);
			let resolvedPos = pos;
			if (!node) {
				node = state.doc.nodeAt(pos - 1);
				if (node) resolvedPos = pos - 1;
			}

			if (
				node &&
				[
					"variableToken",
					"formulaToken",
					"resolverToken",
					"formatterToken",
					"normalizeToken",
					"conditionToken",
					"localizationToken",
					"linkToken",
					"dynamicLinkToken",
					"selectToken",
					"booleanToken",
					"multiSelectToken",
				].includes(node.type.name)
			) {
				openTokenEditor(node, resolvedPos);
				return true;
			}
			return false;
		},
	},
	onUpdate: () => {
		if (emitting) return;
		emitChanges();
	},
	onFocus: () => {
		isEditorFocused.value = true;
	},
	onBlur: () => {
		isEditorFocused.value = false;
	},
});

const isEditorEmpty = computed(() => editor.isEmpty);
const isEditorFocused = ref(false);

// ─── Input Adapters and Parsing Helper Functions ───

const parsedSelectOptions = computed(() => {
	if (props.fieldType === "Link" || props.fieldType === "Dynamic Link") return [];
	if (typeof props.options === "string") {
		return props.options.split("\n").map((o) => ({ label: o, value: o }));
	}
	if (Array.isArray(props.options)) {
		return props.options.map((o) => {
			if (typeof o === "string") return { label: o, value: o };
			return { label: o.label || o.value, value: o.value };
		});
	}
	return [];
});

const parsedDoctypeOptions = computed(() => {
	if (props.doctypeOptions && props.doctypeOptions.length > 0) return props.doctypeOptions;
	// standard fallback list
	return ["Customer", "Supplier", "Item", "Sales Invoice", "Purchase Invoice", "User"];
});

const parsedDocFieldOptions = computed(() => {
	if (props.meta?.fields) {
		return props.meta.fields.map((f) => ({
			label: f.label || f.fieldname,
			value: f.fieldname,
		}));
	}
	return [
		{ label: "Posting Date (posting_date)", value: "posting_date" },
		{ label: "Customer Name (customer_name)", value: "customer_name" },
		{ label: "Subtotal (subtotal)", value: "subtotal" },
		{ label: "Grand Total (grand_total)", value: "grand_total" },
		{ label: "Reference Doctype (reference_doctype)", value: "reference_doctype" },
	];
});

// ─── Serialization & Deserialization Engine (AST-First Architecture) ───

function serializeToStructuredValue() {
	if (!editor) return { mode: "static", value: "" };

	// Find the first token node in the document to decide the structured mode
	let tokenNode = null;
	editor.state.doc.descendants((node) => {
		if (
			[
				"variableToken",
				"formulaToken",
				"resolverToken",
				"formatterToken",
				"normalizeToken",
				"conditionToken",
				"localizationToken",
				"linkToken",
				"dynamicLinkToken",
			].includes(node.type.name)
		) {
			tokenNode = node;
			return false;
		}
	});

	if (tokenNode) {
		const name = tokenNode.type.name;
		const attrs = tokenNode.attrs;

		if (name === "variableToken") {
			return { mode: "variable", path: attrs.path, label: attrs.label };
		}
		if (name === "formulaToken") {
			return { mode: "formula", expression: attrs.expression };
		}
		if (name === "resolverToken") {
			return { mode: "resolver", resolver: attrs.resolver, config: attrs.config };
		}
		if (name === "formatterToken") {
			return { mode: "formatter", formatter: attrs.formatter, options: attrs.options };
		}
		if (name === "normalizeToken") {
			return { mode: "normalize", steps: attrs.steps };
		}
		if (name === "conditionToken") {
			return { mode: "condition", condition: attrs.condition };
		}
		if (name === "localizationToken") {
			return { mode: "localization", value: attrs.value };
		}
		if (name === "linkToken") {
			return { mode: "link", doctype: attrs.doctype, value: attrs.value };
		}
		if (name === "dynamicLinkToken") {
			return {
				mode: "dynamic_link",
				reference_field: attrs.reference_field,
				doctype: attrs.doctype,
				doctype_variable: attrs.doctype_variable,
				value: attrs.value,
			};
		}
		if (name === "selectToken") {
			return { mode: "static", value: attrs.value };
		}
		if (name === "booleanToken") {
			return { mode: "static", value: attrs.value ? 1 : 0 };
		}
		if (name === "multiSelectToken") {
			return { mode: "static", value: attrs.values };
		}
	}

	return { mode: "static", value: editor.getText().trim() };
}

function deserializeStructuredValue(val) {
	if (!val) return "";

	if (val.mode === "static" || typeof val === "string") {
		return typeof val === "string" ? val : val.value || "";
	}

	if (val.mode === "variable") {
		return `<span data-token-type="variable" data-path="${val.path || ""}" data-label="${
			val.label || ""
		}"></span>`;
	}

	if (val.mode === "formula") {
		return `<span data-token-type="formula" data-expression="${val.expression || ""}"></span>`;
	}

	if (val.mode === "resolver") {
		const configStr = safeJsonEncode(val.config || {});
		return `<span data-token-type="resolver" data-resolver="${
			val.resolver || ""
		}" data-config="${configStr}"></span>`;
	}

	if (val.mode === "formatter") {
		const optionsStr = safeJsonEncode(val.options || {});
		return `<span data-token-type="formatter" data-formatter="${
			val.formatter || ""
		}" data-options="${optionsStr}"></span>`;
	}

	if (val.mode === "normalize") {
		const stepsStr = safeJsonEncode(val.steps || []);
		return `<span data-token-type="normalize" data-steps="${stepsStr}"></span>`;
	}

	if (val.mode === "condition") {
		const conditionStr = safeJsonEncode(val.condition || {});
		return `<span data-token-type="condition" data-condition="${conditionStr}"></span>`;
	}

	if (val.mode === "localization") {
		return `<span data-token-type="localization" data-value="${val.value || ""}"></span>`;
	}

	if (val.mode === "link") {
		return `<span data-token-type="link" data-doctype="${val.doctype || ""}" data-value="${
			val.value || ""
		}"></span>`;
	}

	if (val.mode === "dynamic_link") {
		return `<span data-token-type="dynamic_link" data-reference-field="${
			val.reference_field || ""
		}" data-doctype="${val.doctype || ""}" data-doctype-variable="${
			val.doctype_variable || ""
		}" data-value="${val.value || ""}"></span>`;
	}

	return "";
}

// ─── Component Dynamic Mode Switching and Syncing ───

function onWrapClick(e) {
	if (isDynamicMode.value || !isStaticSupported.value) {
		editor.commands.focus();
	}
}

function toggleDynamicMode() {
	if (controlReadOnly.value || props.disabled) return;
	isDynamicMode.value = !isDynamicMode.value;

	if (isDynamicMode.value) {
		// Convert current static value into raw Tiptap content
		emitting = true;
		editor.commands.setContent(String(staticValue.value || ""));
		emitting = false;
		nextTick(() => editor.commands.focus());
	} else {
		// Clearing dynamic value and switching back to static representation
		staticValue.value = "";
		updateStaticValue("");
	}
}

function onStaticKeydown(e) {
	if (controlReadOnly.value || props.disabled) return;

	// In Select mode, capture alphanumeric keys to trigger dynamic editor?
	// Or only @ and /
	if (e.key === "@" || e.key === "/") {
		e.preventDefault();
		e.stopPropagation();

		isDynamicMode.value = true;

		emitting = true;
		editor.commands.setContent(String(staticValue.value || ""));
		emitting = false;

		nextTick(() => {
			if (editor) {
				editor.commands.focus();
				editor.commands.insertContent(e.key);
			}
		});
	}
}

function updateStaticValue(val) {
	staticValue.value = val;
	emitChanges();
}

function emitChanges() {
	emitting = true;
	let output;
	if (!isDynamicMode.value && isStaticSupported.value) {
		if (props.fieldType === "Dynamic Link") {
			output = {
				mode: "dynamic_link",
				reference_field: props.referenceField || "",
				doctype: staticDynamicLinkDoctype.value || "",
				value: staticValue.value || "",
			};
		} else if (props.fieldType === "Link") {
			output = {
				mode: "link",
				doctype: props.referenceDoctype || "",
				value: staticValue.value || "",
			};
		} else {
			output = { mode: "static", value: staticValue.value };
		}
	} else {
		output = serializeToStructuredValue();
	}
	emit("update:modelValue", output);
	emit("update", output);
	nextTick(() => {
		emitting = false;
	});
}

// Watch modelValue changes to keep editor and local static state synchronized
watch(
	() => props.modelValue,
	(val) => {
		if (emitting) return;
		if (val && typeof val === "object") {
			const isStaticallyHandledLink =
				isStaticSupported.value &&
				((props.fieldType === "Link" && val.mode === "link") ||
					(props.fieldType === "Dynamic Link" && val.mode === "dynamic_link"));

			if (val.mode && val.mode !== "static" && !isStaticallyHandledLink) {
				isDynamicMode.value = true;
				emitting = true;
				editor.commands.setContent(deserializeStructuredValue(val));
				emitting = false;
			} else {
				isDynamicMode.value = false;
				staticValue.value = val.value ?? "";
				if (props.fieldType === "Dynamic Link") {
					staticDynamicLinkDoctype.value = val.doctype || "";
				}
			}
		} else {
			isDynamicMode.value = false;
			staticValue.value = val || "";
		}
	},
	{ immediate: true, deep: true }
);

// ─── Built-in Token Popover Editors (Configuration Panels) ───

const activeTokenPresentation = computed(() => {
	const map = {
		formula: { title: __("Configure Formula"), icon: "fa fa-calculator" },
		resolver: { title: __("Configure Resolver"), icon: "fa fa-bolt" },
		formatter: { title: __("Configure Formatter"), icon: "fa fa-paint-brush" },
		normalize: { title: __("Configure Normalization"), icon: "fa fa-refresh" },
		condition: { title: __("Configure Condition"), icon: "fa fa-code-fork" },
		localization: { title: __("Configure Localized String"), icon: "fa fa-globe" },
		link: { title: __("Configure Link Picker"), icon: "fa fa-link" },
		dynamicLink: { title: __("Configure Dynamic Link"), icon: "fa fa-cubes" },
		select: { title: __("Select Option"), icon: "fa fa-list" },
		boolean: { title: __("Toggle Value"), icon: "fa fa-toggle-on" },
		multiselect: { title: __("Select Multiple"), icon: "fa fa-check-square-o" },
		json: { title: __("JSON Editor"), icon: "fa fa-archive" },
		"add-key": { title: __("Key/Value Pair"), icon: "fa fa-key" },
	};
	return map[activeTokenType.value] || { title: __("Token Configuration"), icon: "fa fa-cog" };
});

function updatePopoverPosition() {
	if (!controlRef.value) return;
	const rect = controlRef.value.getBoundingClientRect();
	const spaceBelow = window.innerHeight - rect.bottom;
	const popoverHeight = 360; // Estimated height for token popovers

	if (spaceBelow < popoverHeight && rect.top > popoverHeight) {
		// Position above the control
		popoverStyle.value = {
			position: "fixed",
			bottom: `${window.innerHeight - rect.top + 4}px`,
			left: `${rect.left}px`,
			width: `${Math.max(rect.width, 360)}px`,
			"z-index": 12000,
		};
	} else {
		// Position below the control
		popoverStyle.value = {
			position: "fixed",
			top: `${rect.bottom + 4}px`,
			left: `${rect.left}px`,
			width: `${Math.max(rect.width, 360)}px`,
			"z-index": 12000,
		};
	}
}

function openTokenEditor(node, pos, typeOverride = null) {
	if (controlReadOnly.value || props.disabled) return;
	activeTokenNode.value = node;
	activeTokenPos.value = pos;

	if (typeOverride) {
		activeTokenType.value = typeOverride;
		if (typeOverride === "json") {
			tokenDraftAttrs.value = { value: editor.getText() || "" };
		} else if (typeOverride === "add-key") {
			tokenDraftAttrs.value = { key: "", value: "" };
		}
		jsonParseError.value = "";
		nextTick(() => {
			updatePopoverPosition();
		});
		return;
	}

	// Populate Token Edit Values based on token node attributes
	const name = node.type.name;
	const attrs = node.attrs ? JSON.parse(JSON.stringify(node.attrs)) : {}; // clone attributes

	if (name === "variableToken") {
		activeTokenType.value = null; // Variable node requires no dialog
		return;
	}

	if (name === "formulaToken") {
		activeTokenType.value = "formula";
		tokenDraftAttrs.value = { expression: attrs.expression || "" };
	} else if (name === "resolverToken") {
		activeTokenType.value = "resolver";
		tokenDraftAttrs.value = {
			resolver: attrs.resolver || "",
			config: attrs.config || {},
		};
	} else if (name === "formatterToken") {
		activeTokenType.value = "formatter";
		tokenDraftAttrs.value = {
			formatter: attrs.formatter || "currency",
			options: attrs.options || {},
		};
	} else if (name === "normalizeToken") {
		activeTokenType.value = "normalize";
		tokenDraftAttrs.value = { steps: attrs.steps || [] };
	} else if (name === "conditionToken") {
		activeTokenType.value = "condition";
		tokenDraftAttrs.value = { condition: attrs.condition || {} };
	} else if (name === "localizationToken") {
		activeTokenType.value = "localization";
		tokenDraftAttrs.value = { value: attrs.value || "" };
	} else if (name === "linkToken") {
		activeTokenType.value = "link";
		tokenDraftAttrs.value = {
			doctype: attrs.doctype || props.referenceDoctype || "",
			value: attrs.value || "",
		};
	} else if (name === "dynamicLinkToken") {
		activeTokenType.value = "dynamicLink";
		tokenDraftAttrs.value = {
			reference_field: attrs.reference_field || "",
			doctype: attrs.doctype || "",
			doctype_variable: attrs.doctype_variable || "",
			value: attrs.value || "",
		};

		if (attrs.reference_field) {
			dynamicLinkMode.value = "reference";
		} else if (attrs.doctype_variable) {
			dynamicLinkMode.value = "variable";
		} else {
			dynamicLinkMode.value = "static";
		}
	} else if (name === "selectToken") {
		activeTokenType.value = "select";
		tokenDraftAttrs.value = { value: attrs.value || "" };
	} else if (name === "booleanToken") {
		activeTokenType.value = "boolean";
		tokenDraftAttrs.value = { value: !!attrs.value };
	} else if (name === "multiSelectToken") {
		activeTokenType.value = "multiselect";
		tokenDraftAttrs.value = { values: attrs.values || [] };
	}

	nextTick(() => {
		updatePopoverPosition();
		window.addEventListener("scroll", updatePopoverPosition, true);
		window.addEventListener("resize", updatePopoverPosition);
	});
}

function closeTokenEditor() {
	activeTokenType.value = null;
	activeTokenNode.value = null;
	activeTokenPos.value = null;
	tokenDraftAttrs.value = {};
	window.removeEventListener("scroll", updatePopoverPosition, true);
	window.removeEventListener("resize", updatePopoverPosition);
}

function saveTokenEditor() {
	if (!editor || activeTokenPos.value === null) return;

	let attrs = {};
	const name = activeTokenNode.value.type.name;

	if (name === "formulaToken") {
		attrs = { expression: tokenDraftAttrs.value.expression };
	} else if (name === "resolverToken") {
		attrs = {
			resolver: tokenDraftAttrs.value.resolver,
			config: tokenDraftAttrs.value.config,
		};
	} else if (name === "formatterToken") {
		attrs = {
			formatter: tokenDraftAttrs.value.formatter,
			options: tokenDraftAttrs.value.options,
		};
	} else if (name === "normalizeToken") {
		attrs = { steps: tokenDraftAttrs.value.steps };
	} else if (name === "conditionToken") {
		attrs = { condition: tokenDraftAttrs.value.condition };
	} else if (name === "localizationToken") {
		attrs = { value: tokenDraftAttrs.value.value };
	} else if (name === "linkToken") {
		attrs = {
			doctype: tokenDraftAttrs.value.doctype,
			value: tokenDraftAttrs.value.value,
		};
	} else if (name === "dynamicLinkToken") {
		attrs = {
			reference_field:
				dynamicLinkMode.value === "reference" ? tokenDraftAttrs.value.reference_field : "",
			doctype: dynamicLinkMode.value === "static" ? tokenDraftAttrs.value.doctype : "",
			doctype_variable:
				dynamicLinkMode.value === "variable" ? tokenDraftAttrs.value.doctype_variable : "",
			value: tokenDraftAttrs.value.value,
		};
	} else if (name === "selectToken") {
		attrs = { value: tokenDraftAttrs.value.value };
	} else if (name === "booleanToken") {
		attrs = { value: tokenDraftAttrs.value.value };
	} else if (name === "multiSelectToken") {
		attrs = { values: tokenDraftAttrs.value.values };
	}

	if (activeTokenType.value === "json") {
		try {
			const json = JSON.parse(tokenDraftAttrs.value.value);
			emitting = true;
			editor.commands.setContent(JSON.stringify(json, null, 2));
			emitting = false;
			emitChanges();
			closeTokenEditor();
			return;
		} catch (e) {
			jsonParseError.value = __("Invalid JSON format");
			return;
		}
	}

	if (activeTokenType.value === "add-key") {
		const key = tokenDraftAttrs.value.key;
		const val = tokenDraftAttrs.value.value;
		if (key) {
			const content = editor.getText();
			let obj = {};
			try {
				obj = JSON.parse(content);
			} catch (e) {}
			obj[key] = val;
			emitting = true;
			editor.commands.setContent(JSON.stringify(obj, null, 2));
			emitting = false;
			emitChanges();
		}
		closeTokenEditor();
		return;
	}

	// Update node attributes in Tiptap
	emitting = true;
	editor
		.chain()
		.focus()
		.setNodeSelection(activeTokenPos.value)
		.updateAttributes(name, attrs)
		.run();
	emitting = false;

	emitChanges();
	closeTokenEditor();
}

// ─── Resolver Parameter Editor Helpers ───

function addConfigParam() {
	if (!tokenDraftAttrs.value.config) tokenDraftAttrs.value.config = {};
	const key = `param_${Object.keys(tokenDraftAttrs.value.config).length + 1}`;
	tokenDraftAttrs.value.config[key] = "";
}

function removeConfigKey(key) {
	if (tokenDraftAttrs.value.config) {
		delete tokenDraftAttrs.value.config[key];
	}
}

function renameConfigKey(oldKey, newKey) {
	if (!newKey || oldKey === newKey) return;
	if (tokenDraftAttrs.value.config) {
		const val = tokenDraftAttrs.value.config[oldKey];
		delete tokenDraftAttrs.value.config[oldKey];
		tokenDraftAttrs.value.config[newKey] = val;
	}
}

// Formula Var Selection Injection Helper
function insertVarInFormula(v) {
	const textarea = formulaTextareaRef.value;
	if (!textarea) return;
	const start = textarea.selectionStart;
	const end = textarea.selectionEnd;
	const text = textarea.value;
	const insert = v.value || v;
	tokenDraftAttrs.value.expression = text.slice(0, start) + insert + text.slice(end);
	nextTick(() => {
		textarea.focus();
		textarea.setSelectionRange(start + insert.length, start + insert.length);
	});
}

// ─── Expanded Mode Preview Helper (removed — expand button no longer shown) ───

// Dynamic link target doctype resolution
const resolvedDynamicDoctype = computed(() => {
	if (activeTokenType.value === "dynamicLink") {
		if (dynamicLinkMode.value === "static") {
			return tokenDraftAttrs.value.doctype;
		}
		if (dynamicLinkMode.value === "reference") {
			// Lookup fieldtype metadata inside fields
			const fld = tokenDraftAttrs.value.reference_field;
			// Simple dynamic link lookup fallback
			if (fld === "customer_name" || fld === "customer") return "Customer";
			if (fld === "supplier") return "Supplier";
			if (fld === "item") return "Item";
			return "Customer"; // fallback
		}
		if (dynamicLinkMode.value === "variable") {
			const v = tokenDraftAttrs.value.doctype_variable;
			if (v && v.includes("customer")) return "Customer";
			if (v && v.includes("supplier")) return "Supplier";
			return "Customer";
		}
	}
	return "";
});

const handleClickOutside = (e) => {
	if (!activeTokenType.value) return;

	// If click is inside the root control, do not close
	if (controlRef.value && controlRef.value.contains(e.target)) return;

	// If target is inside any .fxr-popover, do not close
	if (e.target.closest(".fxr-popover")) return;

	// Ignore clicks on teleported dropdowns and overlays
	if (
		e.target.closest(".fxr-dropdown") ||
		e.target.closest(".mention-list") ||
		e.target.closest(".tippy-box") ||
		e.target.closest(".flatpickr-calendar") ||
		e.target.closest(".awesomplete") ||
		e.target.closest(".ts-dropdown")
	) {
		return;
	}

	closeTokenEditor();
};

onMounted(() => {
	document.addEventListener("click", handleClickOutside);
});

onBeforeUnmount(() => {
	if (editor) {
		editor.destroy();
	}
	document.removeEventListener("click", handleClickOutside);
	window.removeEventListener("scroll", updatePopoverPosition, true);
	window.removeEventListener("resize", updatePopoverPosition);
});
</script>

<style scoped>
/* ── Parent Container Styles ── */
.fsvc-wrap {
	display: flex;
	flex-direction: column;
	width: 100%;
}

.fsvc-wrap.is-disabled {
	opacity: 0.7;
	pointer-events: none;
}

/* ── Flex Utilities ── */
.flex-1 {
	flex: 1 1 0%;
	min-width: 0;
}
.flex-0 {
	flex: 0 0 auto;
}

/* ── Main Input Field Layout (Height 32px–38px) ── */
.fsvc-main-field {
	display: flex;
	align-items: center;
	width: 100%;
	min-height: 32px;
	border: 1px solid var(--fxr-border, #e2e8f0);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-bg-input, #fff);
	transition: all var(--fxr-transition-fast, 0.2s);
}

.fsvc-main-field:focus-within {
	border-color: var(--fxr-accent, #2490ef);
	box-shadow: var(--fxr-shadow-focus);
}

.fsvc-static-container {
	display: flex;
	align-items: center;
	flex: 1;
	min-width: 0;
	height: 100%;
}

/* Support full width for select controls in static mode */
.fsvc-main-field.is-static-select .fsvc-static-container {
	padding: 0;
}

/* Deep override to remove internal borders from nested controls when wrapped by fsvc-main-field */
.fsvc-static-container :deep(.combobox-wrapper),
.fsvc-static-container :deep(.form-control),
.fsvc-static-container :deep(.fxr-input),
.fsvc-static-container :deep(.combobox-container .combobox-wrapper),
.fsvc-static-container :deep(.fxr-input-group),
.fsvc-static-container :deep(.fxr-select) {
	border: none !important;
	box-shadow: none !important;
	background: transparent !important;
	height: var(--fxr-input-height, 28px) !important;
	margin-bottom: 0 !important;
	padding-bottom: 0 !important;
}

.fsvc-static-container :deep(.fxr-input-group.has-floating-label) {
	padding-top: 0 !important;
}

/* Ensure dropdown buttons and clear triggers are properly aligned and visible */
.fsvc-static-container :deep(.combobox-trigger) {
	height: 24px !important;
	width: 24px !important;
	margin-top: 0 !important;
	opacity: 1 !important;
	display: flex !important;
	align-items: center !important;
	justify-content: center !important;
}

.fsvc-static-container :deep(.combobox-button-trigger) {
	padding-left: 8px !important;
}

.fsvc-static-container :deep(.combobox-input-group) {
	padding-right: 4px !important;
}

.fsvc-editor-container {
	display: flex;
	align-items: center;
	flex: 1;
	height: 100%;
	min-height: 30px;
	position: relative;
	overflow: hidden;
	padding: 2px 8px;
}

.fsvc-editor-wrapper {
	width: 100%;
	position: relative;
}

/* ── Tiptap Visual Styles ── */
.fsvc-tiptap-editor :deep(.ProseMirror) {
	outline: none;
	line-height: 1.4;
	font-size: 13px;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	display: block;
	min-height: 22px;
	unicode-bidi: plaintext;
	text-align: start;
}

.fsvc-empty-hint {
	position: absolute;
	top: 3px;
	left: 0;
	display: flex;
	align-items: center;
	gap: 3px;
	color: #94a3b8;
	font-size: 11px;
	font-family: var(--font-stack-mono, monospace);
	pointer-events: none;
	user-select: none;
	white-space: nowrap;
}
.fsvc-empty-hint .hint-part {
	color: #64748b;
	font-weight: 700;
	letter-spacing: -0.5px;
}
.fsvc-empty-hint .hint-sep {
	color: #cbd5e1;
	margin: 0 2px;
}
.fsvc-empty-hint .hint-at {
	color: #059669;
	font-weight: 700;
}
.fsvc-empty-hint .hint-slash {
	color: #7c3aed;
	font-weight: 700;
}
.fsvc-focus-hint {
	position: absolute;
	top: 3px;
	left: 0;
	color: #cbd5e1;
	font-size: 12px;
	font-style: italic;
	pointer-events: none;
	user-select: none;
}

.fsvc-inline-actions {
	position: absolute;
	right: 0;
	top: 50%;
	transform: translateY(-50%);
	display: flex;
	gap: 4px;
	padding-right: 4px;
	background: linear-gradient(to left, var(--fxr-bg-input, #fff) 80%, transparent);
}

.fsvc-action-btn {
	background: transparent;
	border: none;
	color: var(--fxr-text-muted, #94a3b8);
	cursor: pointer;
	padding: 2px 4px;
	border-radius: 4px;
	font-size: 12px;
	transition: all 0.2s;
}

.fsvc-action-btn:hover {
	color: var(--fxr-accent, #2490ef);
	background: var(--fxr-bg-hover, #f1f5f9);
}

/* ── Token Chips Styles (Aggressive curated HSL colors) ── */
:deep(.token-chip) {
	display: inline-flex;
	align-items: center;
	padding: 1px 6px;
	border-radius: 4px;
	font-size: 11px;
	font-weight: 600;
	margin: 0px 2px;
	cursor: pointer;
	border: 1px solid transparent;
	transition: all 0.2s ease;
	white-space: nowrap;
	vertical-align: middle;
	user-select: none;
}

:deep(.token-chip:hover) {
	filter: brightness(0.95);
	transform: scale(1.02);
}

:deep(.token-variable) {
	background: #ecfdf5;
	color: #059669;
	border-color: #10b98133;
}

:deep(.token-formula) {
	background: #f5f3ff;
	color: #7c3aed;
	border-color: #8b5cf633;
}

:deep(.token-resolver) {
	background: #fffbeb;
	color: #d97706;
	border-color: #f59e0b33;
}

:deep(.token-formatter) {
	background: #fdf2f8;
	color: #db2777;
	border-color: #f472b633;
}

:deep(.token-normalize) {
	background: #eff6ff;
	color: #2563eb;
	border-color: #3b82f633;
}

:deep(.token-condition) {
	background: #fae8ff;
	color: #c084fc;
	border-color: #d946ef33;
}

:deep(.token-localization) {
	background: #e0f2fe;
	color: #0284c7;
	border-color: #0ea5e933;
}

:deep(.token-link) {
	background: #f1f5f9;
	color: #475569;
	border-color: #64748b33;
}

:deep(.token-dynamic-link) {
	background: #f0fdfa;
	color: #0d9488;
	border-color: #14b8a633;
}

:deep(.token-select) {
	background: #fff1f2;
	color: #e11d48;
	border-color: #fb718533;
}

:deep(.token-boolean) {
	background: #f8fafc;
	color: #64748b;
	border-color: #cbd5e1;
}

:deep(.token-boolean.is-true) {
	background: #ecfdf5;
	color: #059669;
	border-color: #10b98133;
}

:deep(.token-multiselect) {
	background: #f0f9ff;
	color: #0284c7;
	border-color: #0ea5e933;
}

/* ── Boolean Toggle Switch Layout ── */
.tg-switch {
	position: relative;
	display: inline-block;
	width: 32px;
	height: 18px;
}

.tg-switch input {
	opacity: 0;
	width: 0;
	height: 0;
}

.tg-slider {
	position: absolute;
	cursor: pointer;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: #cbd5e1;
	transition: 0.4s;
	border-radius: 18px;
}

.tg-slider:before {
	position: absolute;
	content: "";
	height: 12px;
	width: 12px;
	left: 3px;
	bottom: 3px;
	background-color: white;
	transition: 0.4s;
	border-radius: 50%;
}

input:checked + .tg-slider {
	background-color: #10b981;
}

input:checked + .tg-slider:before {
	transform: translateX(14px);
}

.tg-switch-label {
	font-size: 12px;
	font-weight: 600;
	color: #64748b;
}

.cursor-pointer {
	cursor: pointer;
}

/* ── Teleported Popover Modals ── */
.fxr-token-modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background: rgba(15, 23, 42, 0.4);
	backdrop-filter: blur(8px);
	z-index: 11000;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 16px;
}

.fxr-token-modal-container {
	background: #ffffff;
	width: 100%;
	max-width: 580px;
	border-radius: 12px;
	box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
	display: flex;
	flex-direction: column;
	max-height: 90vh;
	overflow: hidden;
	border: 1px solid #e2e8f0;
	animation: slide-up 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.fxr-token-modal-container.full-expanded {
	max-width: 800px;
}

.fxr-token-modal-header {
	height: 52px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 16px;
	border-bottom: 1px solid #e2e8f0;
}

.header-title {
	font-weight: 700;
	font-size: 14px;
	color: #1e293b;
	display: flex;
	align-items: center;
}

.btn-close {
	background: transparent;
	border: none;
	color: #94a3b8;
	cursor: pointer;
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
	transition: all 0.2s ease;
}

.btn-close:hover {
	background: #f1f5f9;
	color: #1e293b;
}

.fxr-token-modal-body {
	padding: 16px;
	overflow-y: auto;
	flex: 1;
}

.fxr-token-modal-footer {
	height: 56px;
	border-top: 1px solid #e2e8f0;
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 8px;
	padding: 0 16px;
	background: #f8fafc;
}

/* ── Dialog Panels Layouts ── */
.formula-textarea {
	font-family: monospace;
	min-height: 120px;
	font-size: 13px;
	line-height: 1.5;
	resize: vertical;
}

.variables-pill-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	max-height: 140px;
	overflow-y: auto;
	padding: 4px;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	background: #f8fafc;
}

.var-pill-btn {
	background: #ffffff;
	border: 1px solid #cbd5e1;
	border-radius: 4px;
	font-size: 11px;
	font-weight: 600;
	color: #334155;
	padding: 3px 8px;
	cursor: pointer;
	transition: all 0.2s ease;
}

.var-pill-btn:hover {
	background: #f1f5f9;
	border-color: #94a3b8;
	color: #0f172a;
}

.pipeline-step-card {
	background: #f8fafc;
	transition: all 0.2s ease;
}

.pipeline-step-card:hover {
	border-color: #cbd5e1;
}

.json-textarea {
	font-family: var(--fxr-font-mono, monospace);
	min-height: 200px;
	font-size: 12px;
}

/* ── HSL Layout helpers ── */
.fxr-gap-1 {
	gap: 4px;
}
.fxr-gap-2 {
	gap: 8px;
}
.fxr-gap-3 {
	gap: 12px;
}
.fxr-text-xs {
	font-size: 11px;
}
.fxr-text-sm {
	font-size: 13px;
}

.select-sm,
.input-sm {
	padding: 4px 8px;
	font-size: 12px;
	height: 28px;
}

/* ── Animation transitions ── */
.fxr-modal-fade-enter-active,
.fxr-modal-fade-leave-active {
	transition: opacity 0.25s ease;
}

.fxr-modal-fade-enter-from,
.fxr-modal-fade-leave-to {
	opacity: 0;
}

@keyframes slide-up {
	from {
		transform: translateY(16px);
		opacity: 0;
	}
	to {
		transform: translateY(0);
		opacity: 1;
	}
}
</style>
