<template>
	<div class="tgc-wrap" @focusin="onFocusIn">
		<!-- Label -->
		<div v-if="df?.label && !hideLabel" class="control-label label" :class="{ reqd: df?.reqd }">
			{{ __(df.label) }}
		</div>

		<!-- Toolbar: mode toggle + live Jinja preview pill -->
		<div class="tgc-toolbar">
			<div class="tgc-mode-tabs" v-if="!readOnly">
				<button
					class="tgc-mode-tab"
					:class="{ active: mode === 'visual' }"
					@click="switchMode('visual')"
					:title="__('Visual segment builder')"
				>
					<i class="fa fa-th-large"></i> {{ __("Visual") }}
				</button>
				<button
					class="tgc-mode-tab"
					:class="{ active: mode === 'raw' }"
					@click="switchMode('raw')"
					:title="__('Edit raw Jinja template')"
				>
					<i class="fa fa-code"></i> {{ __("Jinja") }}
				</button>
			</div>
			<div v-else class="tgc-mode-ro-label">
				<i class="fa fa-lock text-muted"></i>
				<span class="text-muted small">{{ __("Read-only") }}</span>
			</div>

			<!-- Jinja preview pill — always visible when non-empty, click to copy -->
			<div class="tgc-pill-wrap" v-if="compiledJinja">
				<span
					class="tgc-preview-pill"
					@click="copyJinja"
					:title="__('Click to copy Jinja')"
				>
					<i class="fa fa-code tgc-pill-icon"></i>
					<code class="tgc-pill-code">{{
						compiledJinja.length > 68 ? compiledJinja.slice(0, 65) + "…" : compiledJinja
					}}</code>
					<i class="fa fa-clone tgc-pill-copy"></i>
				</span>
			</div>
		</div>

		<!-- Editor area -->
		<div class="tgc-body">
			<!-- ── Visual Mode ── -->
			<div v-if="mode === 'visual'" class="tgc-canvas">
				<TextSegmentList
					v-model="ui.segments"
					:readOnly="readOnly"
					:variableOptions="variableOptions"
					:docFieldOptions="docFieldOptions"
					:knownVarRoots="knownVarRoots"
				/>
				<div v-if="!readOnly && ui.segments.length === 0" class="tgc-empty-hint">
					<i class="fa fa-magic"></i>
					{{
						__(
							"Add segments below, or switch to Jinja mode to write a template directly."
						)
					}}
					<br />
					<span class="tgc-empty-tip">{{
						__("Click a variable or field in the sidebar to insert it here.")
					}}</span>
				</div>
			</div>

			<!-- ── Raw Jinja Mode ── -->
			<div v-else class="tgc-raw-wrap">
				<textarea
					ref="rawTextareaRef"
					class="tgc-raw-textarea"
					v-model="rawJinja"
					:readonly="readOnly"
					spellcheck="false"
					:placeholder="rawPlaceholder"
					@keydown.tab.prevent="insertTabInRaw"
					@click="onRawClick"
					@keyup="onRawClick"
					@select="onRawClick"
				></textarea>
				<div class="tgc-raw-hint">
					<i class="fa fa-info-circle"></i>
					{{ __("Type") }} <code>{{ jinjaExprExample }}</code
					>, <code>{% if … %}</code>, <code>{% for … in … %}</code>.
					{{ __("Click a variable in the sidebar to insert at cursor.") }}
				</div>
			</div>
		</div>

		<div
			v-if="df?.description && !hideDescription"
			class="description text-muted mt-1"
			style="font-size: 11px"
		>
			{{ __(df.description) }}
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onBeforeUnmount } from "vue";
import TextSegmentList from "./TextSegmentList.vue";
import {
	compileSegmentsToJinja,
	normalizeTemplatePath,
	parseJinjaToSegments,
} from "../utils/text_generator";
import { setActiveTGC, clearActiveTGC } from "../utils/tgc_focus";

const props = defineProps({
	df: { type: Object, default: null },
	modelValue: { type: [Object, String], default: null },
	templateValue: { type: String, default: "" },
	read_only: { type: Boolean, default: false },
	variableOptions: { type: Array, default: () => [] },
	docFieldOptions: { type: Array, default: () => [] },
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const readOnly = computed(() => !!props.read_only || !!props.df?.read_only);

// Literal shown in the hint — defined here to keep it out of template expressions
// where esbuild's Vue parser misreads {{ inside a string as a template token.
const jinjaExprExample = "{{ doc.field }}";

// ─── Placeholder extracted to avoid esbuild escaping issues ───
const rawPlaceholder = computed(() =>
	[
		__("Write Jinja template here…"),
		__("Examples:"),
		"  Hello {{ doc.customer_name }}",
		"  {% if doc.status == 'Open' %}Pending{% endif %}",
		"  {% for item in doc.items %}{{ item.item_code }}{% endfor %}",
	].join("\n")
);

// ─── Mode ───
const mode = ref("visual");
const rawJinja = ref("");
const rawTextareaRef = ref(null);

// ─── Internal UI state ───
const ui = ref({ version: 2, segments: [] });
let emitting = false;

function genKey() {
	return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

// ─── knownVarRoots (for normalising paths) ───
const normalizedVariables = computed(() =>
	(props.variableOptions || []).map((opt) => {
		if (typeof opt === "string") return { label: opt, value: opt };
		return { label: opt?.label || opt?.value || "", value: opt?.value || "" };
	})
);

const knownVarRoots = computed(() => {
	const roots = new Set();
	normalizedVariables.value.forEach((v) => {
		const val = String(v?.value || "").trim();
		const match = val.match(/^vars\.([A-Za-z_][A-Za-z0-9_]*)/);
		if (match?.[1]) roots.add(match[1]);
	});
	return [...roots];
});

// ─── Jinja preview ───
const compiledJinja = computed(() =>
	compileSegmentsToJinja(ui.value.segments, { knownVarRoots: knownVarRoots.value })
);

function copyJinja() {
	navigator.clipboard?.writeText(compiledJinja.value).catch(() => {});
	frappe?.show_alert?.({ message: __("Jinja copied!"), indicator: "blue" }, 1);
}

// ─── Mode switching ───
function switchMode(newMode) {
	if (newMode === mode.value) return;
	if (newMode === "raw") {
		rawJinja.value = compiledJinja.value;
	} else {
		const raw = rawJinja.value.trim();
		if (raw) {
			try {
				const parsed = parseJinjaToSegments(raw);
				ui.value = {
					version: 2,
					segments: parsed.length
						? parsed.map((s) => ({ ...s, _key: s._key || genKey() }))
						: [{ type: "text", content: raw, _key: genKey() }],
				};
			} catch {
				ui.value = {
					version: 2,
					segments: [{ type: "text", content: raw, _key: genKey() }],
				};
			}
		} else {
			ui.value = { version: 2, segments: [] };
		}
	}
	mode.value = newMode;
}

// ─── Focus tracking (registers this TGC as the insert target) ───
function onFocusIn() {
	setActiveTGC(insertExpression);
}

function onRawClick() {
	// Raw textarea clicks also count as focus
	setActiveTGC(insertExpression);
}

onBeforeUnmount(() => {
	clearActiveTGC(insertExpression);
});

// ─── insertExpression — the public API, also exposed via defineExpose ───
function insertExpression(path) {
	if (!path) return;
	if (mode.value === "raw") {
		_insertIntoRaw(`{{ ${path} }}`);
	} else {
		// Visual mode: append a variable segment
		ui.value = {
			...ui.value,
			segments: [...ui.value.segments, { type: "variable", path, _key: genKey() }],
		};
	}
}

function _insertIntoRaw(text) {
	const el = rawTextareaRef.value;
	if (!el) {
		rawJinja.value += text;
		return;
	}
	const start = el.selectionStart ?? rawJinja.value.length;
	const end = el.selectionEnd ?? rawJinja.value.length;
	rawJinja.value = rawJinja.value.slice(0, start) + text + rawJinja.value.slice(end);
	nextTick(() => {
		el.selectionStart = el.selectionEnd = start + text.length;
		el.focus();
	});
}

function insertTabInRaw() {
	_insertIntoRaw("  ");
}

// ─── Raw textarea → ui (live sync for preview pill) ───
watch(rawJinja, (val) => {
	if (mode.value !== "raw") return;
	try {
		const segs = parseJinjaToSegments(val || "");
		emitting = true;
		ui.value = { version: 2, segments: segs.map((s) => ({ ...s, _key: s._key || genKey() })) };
		setTimeout(() => {
			emitting = false;
		}, 0);
	} catch {}
});

// ─── Model normalisation ───
function normalizeModel(val) {
	if (val && typeof val === "object" && val.segments) {
		return {
			version: val.version || 2,
			segments: (val.segments || []).map((s) => ({ ...s, _key: s._key || genKey() })),
		};
	}
	if (typeof val === "string" && val.trim()) {
		try {
			const parsed = JSON.parse(val);
			if (parsed?.segments) return normalizeModel(parsed);
		} catch {}
		try {
			const segs = parseJinjaToSegments(val);
			if (segs.length) {
				return {
					version: 2,
					segments: segs.map((s) => ({ ...s, _key: s._key || genKey() })),
				};
			}
		} catch {}
		return { version: 2, segments: [{ type: "text", content: val, _key: genKey() }] };
	}
	return { version: 2, segments: [] };
}

// Incoming model → ui
watch(
	() => [props.modelValue, props.templateValue],
	([val, tmpl]) => {
		if (emitting) return;
		const normalized = normalizeModel(val || tmpl);
		ui.value = normalized;
		if (mode.value === "raw") {
			rawJinja.value = compileSegmentsToJinja(normalized.segments, {
				knownVarRoots: knownVarRoots.value,
			});
		}
	},
	{ immediate: true, deep: true }
);

// ui → emit
watch(
	ui,
	() => {
		if (emitting) return;
		emitting = true;
		const payload = JSON.parse(JSON.stringify(ui.value));
		const clean = (segs) =>
			(segs || [])
				.map((s) => {
					const c = { ...s };
					delete c._key;
					if (c.type === "variable") {
						c.path = normalizeTemplatePath(c.path || "", knownVarRoots.value);
					}
					if (c.type === "loop") {
						c.iterable = normalizeTemplatePath(c.iterable || "", knownVarRoots.value);
						if (c.segments) c.segments = clean(c.segments);
					}
					if (c.then_segments) c.then_segments = clean(c.then_segments);
					if (c.else_segments) c.else_segments = clean(c.else_segments);
					if (c.elif_branches)
						c.elif_branches = c.elif_branches.map((b) => ({
							...b,
							segments: clean(b.segments || []),
						}));
					return c;
				})
				.filter((c) => !(c.type === "variable" && !(c.path || "").trim()));
		payload.segments = clean(payload.segments);
		emit("update:modelValue", payload);
		setTimeout(() => {
			emitting = false;
		}, 0);
	},
	{ deep: true }
);

// Expose for parent components to call directly (e.g. InputPanel)
defineExpose({ insertExpression });
</script>

<style scoped>
/* ── Wrapper ── */
.tgc-wrap {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

/* ── Toolbar ── */
.tgc-toolbar {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}

.tgc-mode-tabs {
	display: flex;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	overflow: hidden;
	flex-shrink: 0;
}

.tgc-mode-tab {
	background: #f8fafc;
	border: none;
	border-right: 1px solid #e2e8f0;
	color: #64748b;
	font-size: 11px;
	font-weight: 600;
	padding: 4px 10px;
	cursor: pointer;
	display: flex;
	align-items: center;
	gap: 4px;
	transition: background 0.15s, color 0.15s;
}

.tgc-mode-tab:last-child {
	border-right: none;
}

.tgc-mode-tab.active {
	background: #2490ef;
	color: #fff;
}

.tgc-mode-tab:not(.active):hover {
	background: #e8f0fe;
	color: #1d4ed8;
}

.tgc-mode-ro-label {
	display: flex;
	align-items: center;
	gap: 4px;
}

/* ── Preview pill ── */
.tgc-pill-wrap {
	flex: 1;
	min-width: 0;
	overflow: hidden;
}

.tgc-preview-pill {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	background: #f1f5f9;
	border: 1px solid #e2e8f0;
	border-radius: 20px;
	padding: 3px 10px 3px 8px;
	cursor: pointer;
	max-width: 100%;
	transition: background 0.15s, border-color 0.15s;
}

.tgc-preview-pill:hover {
	background: #e0f2fe;
	border-color: #93c5fd;
}

.tgc-pill-icon {
	font-size: 10px;
	color: #64748b;
	flex-shrink: 0;
}

.tgc-pill-code {
	font-size: 11px;
	font-family: monospace;
	color: #1e40af;
	background: transparent;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	flex: 1;
	min-width: 0;
}

.tgc-pill-copy {
	font-size: 10px;
	color: #94a3b8;
	flex-shrink: 0;
	opacity: 0;
	transition: opacity 0.15s;
}

.tgc-preview-pill:hover .tgc-pill-copy {
	opacity: 1;
}

/* ── Editor body ── */
.tgc-body {
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	overflow: hidden;
	background: #fff;
	min-height: 100px;
}

/* ── Visual canvas ── */
.tgc-canvas {
	padding: 10px;
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.tgc-empty-hint {
	padding: 16px 12px;
	color: #94a3b8;
	font-size: 12px;
	text-align: center;
	line-height: 1.7;
	border: 1.5px dashed #e2e8f0;
	border-radius: 6px;
}

.tgc-empty-hint .fa {
	display: block;
	font-size: 18px;
	margin-bottom: 6px;
	color: #cbd5e1;
}

.tgc-empty-tip {
	font-size: 11px;
	color: #b0bec5;
}

/* ── Raw Jinja editor ── */
.tgc-raw-wrap {
	display: flex;
	flex-direction: column;
}

.tgc-raw-textarea {
	width: 100%;
	min-height: 130px;
	resize: vertical;
	border: none;
	outline: none;
	padding: 10px 12px;
	font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
	font-size: 12.5px;
	line-height: 1.65;
	color: #1e293b;
	background: #fafbfe;
	tab-size: 2;
}

.tgc-raw-textarea::placeholder {
	color: #94a3b8;
	font-style: italic;
}

.tgc-raw-textarea:focus {
	background: #fff;
}

.tgc-raw-hint {
	padding: 5px 10px;
	font-size: 10.5px;
	color: #94a3b8;
	border-top: 1px solid #e2e8f0;
	background: #f8fafc;
	line-height: 1.5;
}

.tgc-raw-hint code {
	font-size: 10.5px;
	background: #e2e8f0;
	padding: 0 3px;
	border-radius: 3px;
	color: #1e40af;
}
</style>
