<script setup>
/**
 * MultiCheckControl - Pure Vue implementation for multiple selection.
 * Replaces legacy Frappe MultiCheck to ensure stability and avoid flickering.
 */
import { ref, computed, watch } from "vue";

const props = defineProps({
	df: Object,
	modelValue: [Array, String],
	read_only: Boolean,
	hideLabel: Boolean,
});

const emit = defineEmits(["update:modelValue"]);

const show_popover = ref(false);

// Internal state for selected values
const selectedValues = computed(() => {
	const val = props.modelValue;
	if (Array.isArray(val)) return val.map((v) => String(v));
	if (val === undefined || val === null || val === "") return [];
	if (typeof val === "string") {
		return val
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
	}
	return [String(val)];
});

const selectedCount = computed(() => selectedValues.value.length);

const summaryLabel = computed(() => {
	const count = selectedCount.value;
	if (count === 0) return __("Select options...");
	if (count === 1) return __("1 Selected");
	return __("{0} Selected", [count]);
});

// Normalize options into {label, value} objects
const normalizedOptions = computed(() => {
	let options = props.df.options || [];
	if (typeof options === "string") {
		return options
			.split("\n")
			.map((o) => o.trim())
			.filter(Boolean)
			.map((o) => ({ label: __(o), value: o }));
	}
	if (Array.isArray(options)) {
		return options.map((o) => {
			const val = typeof o === "object" ? o.value : o;
			const label = typeof o === "object" ? o.label : o;
			return { label: __(label), value: String(val) };
		});
	}
	return [];
});

function togglePopover() {
	if (props.read_only) return;
	show_popover.value = !show_popover.value;
	if (show_popover.value) {
		setTimeout(() => {
			const handleOutsideClick = (e) => {
				if (
					!e.target.closest(".multi-check-popover") &&
					!e.target.closest(".dropdown-trigger")
				) {
					show_popover.value = false;
					document.removeEventListener("click", handleOutsideClick);
				}
			};
			document.addEventListener("click", handleOutsideClick);
		}, 0);
	}
}

function toggleOption(value) {
	if (props.read_only) return;
	const current = [...selectedValues.value];
	const index = current.indexOf(String(value));

	if (index > -1) {
		current.splice(index, 1);
	} else {
		current.push(String(value));
	}

	emit("update:modelValue", current);
}

function checkAll() {
	if (props.read_only) return;
	const all = normalizedOptions.value.map((o) => o.value);
	emit("update:modelValue", all);
}

function uncheckAll() {
	if (props.read_only) return;
	emit("update:modelValue", []);
}
</script>

<template>
	<div class="control frappe-control multi-check-control" :class="{ 'in-grid': hideLabel }">
		<div v-if="df.label && !hideLabel" class="control-label label" :class="{ reqd: df.reqd }">
			{{ __(df.label) }}
		</div>

		<!-- Dropdown Mode -->
		<template v-if="hideLabel">
			<div
				class="dropdown-trigger form-control input-xs"
				:class="{ 'has-value': selectedCount > 0, disabled: read_only }"
				@click.stop="togglePopover"
			>
				<span class="text-truncate">{{ summaryLabel }}</span>
				<i class="fa fa-chevron-down ml-2 text-muted" style="font-size: 10px"></i>
			</div>

			<div v-show="show_popover" class="multi-check-popover">
				<div
					class="popover-actions border-bottom p-2 d-flex align-items-center justify-content-start"
				>
					<button class="btn btn-xs btn-link p-0 mr-3" @click.stop="checkAll">
						<i class="fa fa-check-square-o mr-1"></i> {{ __("Check All") }}
					</button>
					<button class="btn btn-xs btn-link p-0 text-muted" @click.stop="uncheckAll">
						<i class="fa fa-square-o mr-1"></i> {{ __("Uncheck All") }}
					</button>
				</div>
				<div class="popover-inner">
					<div
						v-for="opt in normalizedOptions"
						:key="opt.value"
						class="checkbox-item"
						@click.stop="toggleOption(opt.value)"
					>
						<input
							type="checkbox"
							:checked="selectedValues.includes(opt.value)"
							:disabled="read_only"
							@click.stop="toggleOption(opt.value)"
						/>
						<span class="option-label">{{ opt.label }}</span>
					</div>
				</div>
			</div>
		</template>

		<!-- Normal Mode (Inline) -->
		<template v-else>
			<div class="control-wrapper inline-wrapper">
				<div class="inline-actions mb-2 d-flex gap-2" v-if="!read_only">
					<button class="btn btn-xs btn-link p-0" @click.stop="checkAll">
						{{ __("All") }}
					</button>
					<button class="btn btn-xs btn-link p-0 text-muted" @click.stop="uncheckAll">
						{{ __("None") }}
					</button>
				</div>
				<div class="options-grid">
					<div
						v-for="opt in normalizedOptions"
						:key="opt.value"
						class="checkbox-item"
						@click.stop="toggleOption(opt.value)"
					>
						<input
							type="checkbox"
							:checked="selectedValues.includes(opt.value)"
							:disabled="read_only"
							@click.stop="toggleOption(opt.value)"
						/>
						<span class="option-label">{{ opt.label }}</span>
					</div>
				</div>
			</div>
		</template>

		<div v-if="df.description && !hideLabel" class="description text-muted mt-1">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style scoped>
.multi-check-control {
	margin-bottom: 0;
	position: relative;
}

.dropdown-trigger {
	display: flex;
	align-items: center;
	justify-content: space-between;
	cursor: pointer;
	user-select: none;
	background-color: var(--control-bg, #f1f5f9);
	border: 1px solid transparent;
	transition: border-color 0.2s;
	height: 28px;
	padding: 4px 8px;
	border-radius: 6px;
}

.dropdown-trigger.has-value {
	border-color: var(--primary);
	color: var(--primary);
	font-weight: 600;
	background-color: #fff;
}

.multi-check-popover {
	position: absolute;
	top: 100%;
	left: 0;
	z-index: 2000;
	background: #ffffff !important;
	border: 1px solid #d1d8dd;
	border-radius: 8px;
	box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
	min-width: 220px;
	max-height: 350px;
	overflow: hidden;
	display: flex;
	flex-direction: column;
	margin-top: 4px;
}

.popover-inner {
	padding: 8px;
	overflow-y: auto;
}

.control-wrapper.inline-wrapper {
	padding: 12px;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
}

.options-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
	gap: 8px;
}

.checkbox-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 8px;
	border-radius: 4px;
	cursor: pointer;
	transition: background 0.15s;
	user-select: none;
}

.checkbox-item:hover {
	background: #f1f5f9;
}

.checkbox-item input {
	cursor: pointer;
	margin: 0;
}

.option-label {
	font-size: 12px;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-truncate: ellipsis;
}

.popover-actions .btn-link {
	font-size: 11px;
	text-decoration: none;
}
</style>
