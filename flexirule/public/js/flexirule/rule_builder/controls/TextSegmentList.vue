<template>
	<div class="tg-segments">
		<div
			v-for="(segment, idx) in modelValue"
			:key="`seg-${idx}-${segment._key}`"
			class="tg-segment"
		>
			<!-- ═══ Text Segment ═══ -->
			<div v-if="segment.type === 'text'" class="tg-segment-text">
				<div class="tg-seg-head">
					<span class="tg-seg-badge tg-badge-text">{{ __("Text") }}</span>
					<button v-if="!readOnly" class="tg-seg-remove" @click="removeSegment(idx)">
						<i class="fa fa-times"></i>
					</button>
				</div>
				<div class="tg-editor-mini" @click="focusMiniEditor($refs[`editor_${idx}`])">
					<editor-content
						:ref="`editor_${idx}`"
						:editor="getOrCreateEditor(segment, idx)"
					/>
				</div>
			</div>

			<!-- ═══ Variable Segment ═══ -->
			<div v-else-if="segment.type === 'variable'" class="tg-segment-variable">
				<div class="tg-seg-head">
					<span class="tg-seg-badge tg-badge-var">{{ __("Variable") }}</span>
					<button v-if="!readOnly" class="tg-seg-remove" @click="removeSegment(idx)">
						<i class="fa fa-times"></i>
					</button>
				</div>
				<AutocompleteControl
					:df="{ fieldtype: 'Autocomplete', label: '' }"
					:options="variableOptions"
					:modelValue="segment.path"
					:read_only="readOnly"
					:hideLabel="true"
					@update:modelValue="
						(val) => updateSegment(idx, { path: normalizeTemplatePathLocal(val || '') })
					"
				/>
			</div>

			<!-- ═══ Loop Segment ═══ -->
			<div
				v-else-if="segment.type === 'loop'"
				class="tg-segment-loop compact-block compact-loop"
			>
				<div class="compact-header">
					<div class="compact-header-left" @click="toggleLoopEditor(idx)">
						<span class="compact-badge badge-loop">
							<i class="fa fa-refresh mr-1"></i> {{ __("FOR EACH") }}
						</span>
						<div class="compact-summary">
							<span class="text-primary font-weight-bold mx-1">{{
								segment.iterator || "item"
							}}</span>
							<span class="text-muted mx-1">IN</span>
							<span class="text-primary mx-1">{{ segment.iterable || "..." }}</span>
						</div>
					</div>
					<div v-if="!readOnly" class="compact-actions">
						<button
							class="btn-action"
							@click="toggleLoopEditor(idx)"
							:title="__('Edit')"
						>
							<i class="fa fa-pencil"></i>
						</button>
						<button
							class="btn-action text-danger"
							@click="removeSegment(idx)"
							:title="__('Remove')"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>

				<div v-if="expandedLoopIdx === idx && !readOnly" class="compact-editor">
					<div class="tg-loop-config">
						<div class="tg-loop-iterator">
							<label>{{ __("Iterator") }}</label>
							<input
								class="form-control input-sm"
								:value="segment.iterator"
								:disabled="readOnly"
								@input="updateSegment(idx, { iterator: $event.target.value })"
							/>
						</div>
						<div class="tg-loop-in">{{ __("in") }}</div>
						<div class="tg-loop-iterable">
							<label>{{ __("Collection") }}</label>
							<AutocompleteControl
								:df="{ fieldtype: 'Autocomplete', label: '' }"
								:options="collectionOptions"
								:modelValue="segment.iterable"
								:read_only="readOnly"
								:hideLabel="true"
								@update:modelValue="
									(val) =>
										updateSegment(idx, {
											iterable: normalizeTemplatePathLocal(val || ''),
										})
								"
							/>
						</div>
					</div>
				</div>

				<div class="compact-body">
					<TextSegmentList
						:modelValue="segment.segments || []"
						@update:modelValue="(val) => updateSegment(idx, { segments: val })"
						:readOnly="readOnly"
						:variableOptions="getLoopOptions(variableOptions, segment)"
						:docFieldOptions="getLoopOptions(docFieldOptions, segment)"
						:knownVarRoots="[...knownVarRoots, segment.iterator || 'item']"
					/>
				</div>
			</div>

			<!-- ═══ Conditional Segment ═══ -->
			<div
				v-else-if="segment.type === 'conditional'"
				class="tg-segment-cond compact-block compact-cond"
			>
				<div class="compact-header">
					<div class="compact-header-left" @click="toggleConditionEditor(idx)">
						<span class="compact-badge badge-cond">
							<i class="fa fa-code-fork mr-1"></i> {{ __("IF") }}
						</span>
						<div class="compact-summary px-2">
							<code v-if="conditionSummary(segment.condition)">{{
								conditionSummary(segment.condition)
							}}</code>
							<span v-else class="text-muted small">{{
								__("Click to define condition…")
							}}</span>
						</div>
					</div>
					<div v-if="!readOnly" class="compact-actions">
						<button
							class="btn-action"
							@click="toggleConditionEditor(idx)"
							:title="__('Edit')"
						>
							<i class="fa fa-pencil"></i>
						</button>
						<button
							class="btn-action text-danger"
							@click="removeSegment(idx)"
							:title="__('Remove')"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>

				<!-- Condition Editor (expanded) -->
				<div v-if="expandedCondIdx === idx && !readOnly" class="compact-editor">
					<ConditionBuilder
						:modelValue="segment.condition || { op: 'and', conditions: [] }"
						:docFields="docFieldOptions"
						:readOnly="readOnly"
						@update:modelValue="(val) => updateSegment(idx, { condition: val })"
					/>
				</div>

				<!-- Then Branch -->
				<div class="compact-body">
					<TextSegmentList
						:modelValue="segment.then_segments || []"
						@update:modelValue="(val) => updateSegment(idx, { then_segments: val })"
						:readOnly="readOnly"
						:variableOptions="variableOptions"
						:docFieldOptions="docFieldOptions"
						:knownVarRoots="knownVarRoots"
					/>
				</div>

				<!-- Elif Branches -->
				<template
					v-for="(elif_b, eIdx) in segment.elif_branches || []"
					:key="`elif-${idx}-${eIdx}`"
				>
					<div class="compact-header compact-header-alt">
						<div
							class="compact-header-left"
							@click="toggleConditionEditor(`elif-${idx}-${eIdx}`)"
						>
							<span class="compact-badge badge-cond-alt">
								{{ __("ELSE IF") }}
							</span>
							<div class="compact-summary px-2">
								<code v-if="conditionSummary(elif_b.condition)">{{
									conditionSummary(elif_b.condition)
								}}</code>
								<span v-else class="text-muted small">{{
									__("Click to set condition…")
								}}</span>
							</div>
						</div>
						<div v-if="!readOnly" class="compact-actions">
							<button
								class="btn-action"
								@click="toggleConditionEditor(`elif-${idx}-${eIdx}`)"
								:title="__('Edit')"
							>
								<i class="fa fa-pencil"></i>
							</button>
							<button
								class="btn-action text-danger"
								@click="removeElif(idx, eIdx)"
								:title="__('Remove')"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
					</div>

					<div
						v-if="expandedCondIdx === `elif-${idx}-${eIdx}` && !readOnly"
						class="compact-editor"
					>
						<ConditionBuilder
							:modelValue="elif_b.condition || { op: 'and', conditions: [] }"
							:docFields="docFieldOptions"
							:readOnly="readOnly"
							@update:modelValue="(val) => updateElifCondition(idx, eIdx, val)"
						/>
					</div>

					<div class="compact-body">
						<TextSegmentList
							:modelValue="elif_b.segments || []"
							@update:modelValue="(val) => updateElifSegments(idx, eIdx, val)"
							:readOnly="readOnly"
							:variableOptions="variableOptions"
							:docFieldOptions="docFieldOptions"
							:knownVarRoots="knownVarRoots"
						/>
					</div>
				</template>

				<!-- Else Branch (Always show header if else_segments exist, or button to add it) -->
				<template
					v-if="
						(segment.else_segments && segment.else_segments.length > 0) ||
						showElseInput === idx
					"
				>
					<div class="compact-header compact-header-alt">
						<div class="compact-header-left">
							<span class="compact-badge badge-cond-alt">
								{{ __("ELSE") }}
							</span>
						</div>
						<div v-if="!readOnly" class="compact-actions">
							<button
								class="btn-action text-danger"
								@click="removeElse(idx)"
								:title="__('Remove Else')"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
					</div>
					<div class="compact-body">
						<TextSegmentList
							:modelValue="segment.else_segments || []"
							@update:modelValue="(val) => updateSegment(idx, { else_segments: val })"
							:readOnly="readOnly"
							:variableOptions="variableOptions"
							:docFieldOptions="docFieldOptions"
							:knownVarRoots="knownVarRoots"
						/>
					</div>
				</template>

				<!-- Add Branch Buttons -->
				<div v-if="!readOnly" class="compact-footer">
					<button class="btn-add-branch" @click="addElif(idx)">
						<i class="fa fa-plus"></i> {{ __("Add Else If") }}
					</button>
					<button
						v-if="!segment.else_segments || segment.else_segments.length === 0"
						class="btn-add-branch"
						@click="
							showElseInput = idx;
							updateSegment(idx, {
								else_segments: [{ type: 'text', content: '', _key: genKey() }],
							});
						"
					>
						<i class="fa fa-plus"></i> {{ __("Add Else") }}
					</button>
				</div>
			</div>
		</div>

		<!-- Add Segment Toolbar -->
		<div v-if="!readOnly" class="tg-add-bar">
			<button class="tg-add-btn" @click="addSegment('text')">
				<i class="fa fa-font"></i> {{ __("Text") }}
			</button>
			<button class="tg-add-btn" @click="addSegment('variable')">
				<i class="fa fa-code"></i> {{ __("Variable") }}
			</button>
			<button class="tg-add-btn tg-add-btn-cond" @click="addSegment('conditional')">
				<i class="fa fa-code-fork"></i> {{ __("If / Else") }}
			</button>
			<button class="tg-add-btn tg-add-btn-loop" @click="addSegment('loop')">
				<i class="fa fa-refresh"></i> {{ __("For Loop") }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from "vue";
import { EditorContent, Editor } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import Mention from "@tiptap/extension-mention";
import { VueRenderer } from "@tiptap/vue-3";
import tippy from "tippy.js";

import AutocompleteControl from "./AutocompleteControl.vue";
import MentionList from "./MentionList.vue";
import ConditionBuilder from "../components/condition_builder/ConditionBuilder.vue";
import { compileConditionTree, normalizeTemplatePath } from "../utils/text_generator";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: () => [] },
	docFieldOptions: { type: Array, default: () => [] },
	knownVarRoots: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue"]);

const expandedCondIdx = ref(null);
const expandedLoopIdx = ref(null);
const showElseInput = ref(null);
const editorInstances = new Map();

function genKey() {
	return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

function makeSegment(type) {
	if (type === "text") return { type: "text", content: "", _key: genKey() };
	if (type === "variable") return { type: "variable", path: "", _key: genKey() };
	if (type === "loop")
		return { type: "loop", iterator: "item", iterable: "", segments: [], _key: genKey() };
	if (type === "conditional") {
		return {
			type: "conditional",
			condition: { op: "and", conditions: [] },
			then_segments: [],
			elif_branches: [],
			else_segments: [],
			_key: genKey(),
		};
	}
	return { type: "text", content: "", _key: genKey() };
}

function addSegment(type) {
	const next = [...props.modelValue, makeSegment(type)];
	emit("update:modelValue", next);
}

function removeSegment(idx) {
	const seg = props.modelValue[idx];
	if (seg && seg._key && editorInstances.has(seg._key)) {
		editorInstances.get(seg._key).destroy();
		editorInstances.delete(seg._key);
	}
	const next = [...props.modelValue];
	next.splice(idx, 1);
	emit("update:modelValue", next);
}

function updateSegment(idx, patch) {
	const next = [...props.modelValue];
	next[idx] = { ...next[idx], ...patch };
	emit("update:modelValue", next);
}

function addElif(idx) {
	const seg = props.modelValue[idx];
	const elifs = [...(seg.elif_branches || [])];
	elifs.push({
		condition: { op: "and", conditions: [] },
		segments: [],
	});
	updateSegment(idx, { elif_branches: elifs });
}

function removeElif(idx, eIdx) {
	const seg = props.modelValue[idx];
	if (!seg.elif_branches) return;
	const elifs = [...seg.elif_branches];
	elifs.splice(eIdx, 1);
	updateSegment(idx, { elif_branches: elifs });
}

function updateElifCondition(idx, eIdx, cond) {
	const seg = props.modelValue[idx];
	const elifs = [...(seg.elif_branches || [])];
	elifs[eIdx] = { ...elifs[eIdx], condition: cond };
	updateSegment(idx, { elif_branches: elifs });
}

function updateElifSegments(idx, eIdx, segs) {
	const seg = props.modelValue[idx];
	const elifs = [...(seg.elif_branches || [])];
	elifs[eIdx] = { ...elifs[eIdx], segments: segs };
	updateSegment(idx, { elif_branches: elifs });
}

function removeElse(idx) {
	updateSegment(idx, { else_segments: [] });
	showElseInput.value = null;
}

function toggleConditionEditor(idx) {
	expandedCondIdx.value = expandedCondIdx.value === idx ? null : idx;
}

function toggleLoopEditor(idx) {
	expandedLoopIdx.value = expandedLoopIdx.value === idx ? null : idx;
}

function conditionSummary(condition) {
	if (!condition) return "";
	try {
		const expr = compileConditionTree(condition, props.knownVarRoots);
		if (!expr || expr === "True") return "";
		return expr.length > 80 ? expr.substring(0, 77) + "…" : expr;
	} catch (e) {
		return "";
	}
}

function normalizeTemplatePathLocal(val) {
	return normalizeTemplatePath(val, props.knownVarRoots);
}

function getLoopOptions(baseOptions, segment) {
	if (!baseOptions || !Array.isArray(baseOptions)) return [];
	if (!segment || segment.type !== "loop") return baseOptions;

	let iterable = (segment.iterable || "").trim();
	if (iterable.startsWith("doc.")) iterable = iterable.substring(4);
	if (iterable.startsWith("old_doc.")) iterable = iterable.substring(8);
	if (!iterable) return baseOptions;

	const iterator = (segment.iterator || "").trim() || "item";
	const prefix = `${iterable}.`;
	const newPrefix = `${iterator}.`;

	const mappedOptions = [];
	for (const opt of baseOptions) {
		if (typeof opt === "string") {
			if (opt.startsWith(prefix)) {
				mappedOptions.push(opt.replace(prefix, newPrefix));
			}
		} else if (opt && opt.value && opt.value.startsWith(prefix)) {
			mappedOptions.push({
				...opt,
				value: opt.value.replace(prefix, newPrefix),
				label: opt.label
					? opt.label.replace(prefix, newPrefix)
					: opt.value.replace(prefix, newPrefix),
			});
		}
	}

	// Prepend mapped options so they appear first in autocomplete
	return [...mappedOptions, ...baseOptions];
}

// Filter options for the loop collection field (must be Table or list)
const collectionOptions = computed(() => {
	return props.variableOptions.filter(
		(opt) => opt.fieldtype === "Table" || opt.fieldtype === "Table MultiSelect" || opt.is_list
	);
});

// ─── TipTap Editors ───

const normalizedVariables = computed(() =>
	(props.variableOptions || []).map((opt) => {
		if (typeof opt === "string") return { label: opt, value: opt };
		return { label: opt?.label || opt?.value || "", value: opt?.value || "" };
	})
);

function createMentionSuggestion() {
	return {
		items: ({ query }) => {
			const q = (query || "").toLowerCase();
			return normalizedVariables.value
				.filter(
					(v) =>
						(v.value || "").toLowerCase().includes(q) ||
						(v.label || "").toLowerCase().includes(q)
				)
				.slice(0, 15);
		},
		render: () => {
			let component;
			let popup;
			return {
				onStart: (props) => {
					component = new VueRenderer(MentionList, {
						props,
						editor: props.editor,
					});
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
					if (popup && popup[0]) {
						popup[0].setProps({
							getReferenceClientRect: props.clientRect,
						});
					}
				},
				onKeyDown(props) {
					if (props.event.key === "Escape") {
						popup?.[0]?.hide();
						return true;
					}
					return component?.ref?.onKeyDown(props);
				},
				onExit() {
					popup?.[0]?.destroy();
					component?.destroy();
				},
			};
		},
	};
}

function getOrCreateEditor(segment, idx) {
	const key = segment._key || `seg_${idx}`;
	if (editorInstances.has(key)) return editorInstances.get(key);

	const content = mentionContentToHtml(segment.content || segment.text || "");

	const editor = new Editor({
		extensions: [
			StarterKit.configure({
				heading: false,
				bold: false,
				italic: false,
				strike: false,
				code: false,
				codeBlock: false,
				blockquote: false,
				bulletList: false,
				orderedList: false,
				horizontalRule: false,
			}),
			Mention.configure({
				HTMLAttributes: { class: "mention" },
				renderLabel({ node }) {
					return `@${node.attrs.id || ""}`;
				},
				suggestion: createMentionSuggestion(),
			}),
		],
		content,
		editable: !props.readOnly,
		onUpdate: ({ editor: ed }) => {
			const text = htmlToTextContent(ed.getHTML());
			if (text !== segment.content) {
				updateSegment(idx, { content: text });
			}
		},
	});

	editorInstances.set(key, editor);
	return editor;
}

function mentionContentToHtml(text) {
	if (!text) return "<p></p>";
	let html = String(text).replace(
		/\{\{\s*([^}]+?)\s*\}\}/g,
		(_, v) =>
			`<span data-type="mention" data-id="${v.trim()}" class="mention">@${v.trim()}</span>`
	);
	if (!html.startsWith("<p>")) html = "<p>" + html + "</p>";
	return html;
}

function htmlToTextContent(html) {
	if (!html) return "";
	const div = document.createElement("div");
	div.innerHTML = html;
	function walk(node) {
		if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
		if (node.nodeType === Node.ELEMENT_NODE) {
			if (node.getAttribute("data-type") === "mention") {
				const id = node.getAttribute("data-id") || "";
				return id ? `{{ ${id} }}` : "";
			}
			const tag = node.tagName.toLowerCase();
			let children = "";
			for (const c of node.childNodes) children += walk(c);
			if (tag === "br") return "\n";
			if (tag === "p" && children) return children;
			return children;
		}
		return "";
	}
	let r = "";
	for (const c of div.childNodes) r += walk(c);
	return r;
}

function focusMiniEditor(refEl) {
	const el = Array.isArray(refEl) ? refEl[0] : refEl;
	if (el?.$el) {
		const proseMirror = el.$el.querySelector(".ProseMirror");
		if (proseMirror) proseMirror.focus();
	}
}

onBeforeUnmount(() => {
	for (const ed of editorInstances.values()) {
		ed.destroy();
	}
	editorInstances.clear();
});
</script>

<style scoped>
/* ─── Segments ─── */
.tg-segments {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.tg-segment {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	overflow: hidden;
}

/* ─── Compact Blocks ─── */
.compact-block {
	border-radius: 8px;
	border: 1px solid #e2e8f0;
	background: #fff;
	overflow: hidden;
	display: flex;
	flex-direction: column;
	margin-bottom: 4px;
}

.compact-cond {
	border-left: 3px solid #f97316; /* Orange for IF */
}

.compact-loop {
	border-left: 3px solid #8b5cf6; /* Purple for FOR */
}

.compact-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 12px;
	background: #fff;
	cursor: pointer;
	border-bottom: 1px solid transparent;
	transition: background 0.15s;
}

.compact-header:hover {
	background: #f8fafc;
}

.compact-header-left {
	display: flex;
	align-items: center;
	flex: 1;
	gap: 8px;
}

.compact-badge {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	padding: 2px 6px;
	border-radius: 4px;
}

.badge-cond {
	color: #c2410c;
	background: #ffedd5;
}

.badge-cond-alt {
	color: #ea580c;
	background: transparent;
}

.badge-loop {
	color: #6d28d9;
	background: #ede9fe;
}

.compact-summary {
	font-size: 12px;
	color: #334155;
	font-family: monospace;
	background: #f8fafc;
	padding: 2px 8px;
	border-radius: 12px;
	border: 1px solid #e2e8f0;
}

.compact-actions {
	display: flex;
	gap: 4px;
	opacity: 0;
	transition: opacity 0.2s;
}

.compact-header:hover .compact-actions {
	opacity: 1;
}

.btn-action {
	background: none;
	border: none;
	color: #94a3b8;
	cursor: pointer;
	padding: 4px;
	border-radius: 4px;
}

.btn-action:hover {
	background: #f1f5f9;
	color: #475569;
}

.btn-action.text-danger:hover {
	color: #ef4444;
	background: #fef2f2;
}

.compact-editor {
	padding: 12px;
	background: #f8fafc;
	border-bottom: 1px solid #e2e8f0;
	border-top: 1px solid #e2e8f0;
}

.compact-body {
	padding: 12px 12px 12px 24px;
	background: #fff;
}

.compact-header-alt {
	border-top: 1px dashed #e2e8f0;
}

.compact-footer {
	padding: 8px 12px;
	border-top: 1px dashed #e2e8f0;
	background: #fafaf9;
	display: flex;
	gap: 8px;
}

.btn-add-branch {
	background: none;
	border: none;
	color: #8b5cf6;
	font-size: 11px;
	font-weight: 600;
	cursor: pointer;
	padding: 4px 8px;
	border-radius: 4px;
}

.btn-add-branch:hover {
	background: #ede9fe;
}

.btn-add-branch i {
	margin-right: 4px;
}

/* ─── Variables Pills (TipTap Mention) ─── */
:deep(.mention) {
	background: #e0f2fe;
	color: #0369a1;
	border: 1px solid #bae6fd;
	border-radius: 12px;
	padding: 2px 8px;
	font-size: 12px;
	font-family: monospace;
	font-weight: 500;
	box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.5);
}

/* ─── Old Styles to keep for text segments ─── */
.tg-seg-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 4px 8px;
	background: #f8fafc;
	border-bottom: 1px solid var(--border-color);
}

.tg-seg-badge {
	font-size: 10px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	padding: 1px 6px;
	border-radius: 3px;
}

.tg-badge-text {
	background: #e8f5e9;
	color: #2e7d32;
}

.tg-badge-var {
	background: #e3f2fd;
	color: #1565c0;
}

.tg-badge-cond {
	background: #fff3e0;
	color: #e65100;
	display: inline-flex;
	align-items: center;
	gap: 4px;
}

/* Loop badge styles */
.tg-badge-loop {
	background: #f3e5f5;
	color: #7b1fa2;
	display: inline-flex;
	align-items: center;
	gap: 4px;
}
.tg-loop-config {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 8px 10px;
	background: #fafafa;
	border-bottom: 1px dashed var(--border-color);
}
.tg-loop-iterator,
.tg-loop-iterable {
	display: flex;
	flex-direction: column;
	gap: 4px;
	flex: 1;
}
.tg-loop-iterator label,
.tg-loop-iterable label {
	font-size: 10px;
	font-weight: 600;
	color: var(--text-muted);
	text-transform: uppercase;
}
.tg-loop-in {
	font-size: 12px;
	color: var(--text-muted);
	font-weight: bold;
	margin-top: 14px;
}

.tg-seg-remove {
	background: transparent;
	border: none;
	color: var(--text-muted);
	cursor: pointer;
	padding: 2px 4px;
	font-size: 11px;
	transition: color 0.1s;
}

.tg-seg-remove:hover {
	color: var(--red-500, #e53e3e);
}

/* ─── Text Segment Editor ─── */
.tg-segment-text {
	background: var(--bg-light, #fff);
}

.tg-editor-mini {
	padding: 6px 10px;
	min-height: 36px;
	cursor: text;
}

.tg-editor-mini :deep(.ProseMirror) {
	outline: none;
	min-height: 24px;
	font-size: 13px;
	line-height: 1.6;
}

.tg-editor-mini :deep(.ProseMirror p) {
	margin: 0;
}

.tg-editor-mini :deep(.mention) {
	display: inline-flex;
	align-items: center;
	padding: 0px 6px;
	border-radius: 4px;
	background: linear-gradient(135deg, #e8f0fe, #d4e4fd);
	color: var(--primary, #2490ef);
	font-size: 12px;
	font-weight: 500;
	font-family: var(--font-monospace, monospace);
	white-space: nowrap;
	border: 1px solid rgba(36, 144, 239, 0.2);
}

/* ─── Variable Segment ─── */
.tg-segment-variable {
	background: var(--bg-light, #fff);
	padding-bottom: 6px;
}

.tg-segment-variable .frappe-control {
	padding: 0 8px;
}

/* ─── Conditional Segment ─── */
.tg-segment-cond,
.tg-segment-loop {
	background: var(--bg-light, #fff);
	display: flex;
	flex-direction: column;
	gap: 0;
}

.tg-cond-card {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 6px 10px;
	margin: 6px 8px;
	background: #f8f9fa;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	cursor: pointer;
	transition: all 0.15s;
}

.tg-cond-card:hover {
	border-color: var(--primary, #2490ef);
	background: #f0f7ff;
}

.tg-cond-card-active {
	border-color: var(--primary, #2490ef);
	box-shadow: 0 0 0 2px rgba(36, 144, 239, 0.1);
}

.tg-cond-card-sm {
	margin: 4px 8px;
	padding: 4px 8px;
}

.tg-cond-summary {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 12px;
	overflow: hidden;
}

.tg-cond-summary i {
	color: var(--text-muted);
	flex-shrink: 0;
}

.tg-cond-summary code {
	font-size: 11px;
	color: var(--text-color);
	background: transparent;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.tg-cond-editor {
	padding: 8px;
	border-top: 1px dashed var(--border-color);
}

/* ─── Branches ─── */
.tg-branch {
	border-top: 1px dashed var(--border-color);
	padding: 6px 8px;
}

.tg-branch-label {
	font-size: 10px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	margin-bottom: 4px;
	display: flex;
	align-items: center;
	gap: 6px;
	justify-content: space-between;
	flex-wrap: wrap;
}

.tg-branch-then {
	color: #2e7d32;
}

.tg-branch-elif {
	color: #e65100;
}

.tg-branch-else {
	color: #c62828;
}

.tg-branch-content {
	padding-left: 8px;
	border-left: 2px solid var(--border-color);
}

.tg-add-elif {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 3px 10px;
	margin: 4px 8px;
	font-size: 11px;
	color: #e65100;
	border: 1px dashed #ffcc80;
	border-radius: 4px;
	background: #fff8e1;
	cursor: pointer;
	transition: all 0.15s;
}

.tg-add-elif:hover {
	background: #fff3e0;
	border-color: #e65100;
}

/* ─── Add Bar ─── */
.tg-add-bar {
	display: flex;
	gap: 6px;
	flex-wrap: wrap;
	margin-top: 4px;
}

.tg-add-btn {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 5px 12px;
	font-size: 11px;
	font-weight: 500;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	background: var(--bg-light, #fff);
	color: var(--text-color);
	cursor: pointer;
	transition: all 0.15s;
}

.tg-add-btn:hover {
	background: var(--bg-blue, #e8f0fe);
	border-color: var(--primary, #2490ef);
	color: var(--primary, #2490ef);
}

.tg-add-btn-cond {
	color: #e65100;
}

.tg-add-btn-cond:hover {
	border-color: #e65100;
	background: #fff3e0;
	color: #bf360c;
}

.tg-add-btn-loop {
	color: #7b1fa2;
}

.tg-add-btn-loop:hover {
	border-color: #7b1fa2;
	background: #f3e5f5;
	color: #4a148c;
}

/* ─── Nested Segments (inside branches) ─── */
.tg-nested-segments {
	display: flex;
	flex-direction: column;
	gap: 4px;
}
</style>
