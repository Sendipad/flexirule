<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Target Field") }}</label>
		<select class="fxr-select" v-model="modelValue.norm_field" :disabled="readOnly">
			<option value="">{{ __("Select field...") }}</option>
			<option v-for="opt in stringFieldOptions" :key="opt.value" :value="opt.value">
				{{ opt.label }}
			</option>
		</select>
	</div>

	<div class="d-flex flex-column fxr-gap-1 mt-3">
		<label class="fxr-label-sm">{{ __("Normalization Profile") }}</label>
		<select class="fxr-select" v-model="modelValue.norm_profile" :disabled="readOnly">
			<option value="Custom">{{ __("Custom Pipeline") }}</option>
			<option v-for="profile in availableProfiles" :key="profile" :value="profile">
				{{ profile }}
			</option>
		</select>
	</div>

	<div class="d-flex flex-column fxr-gap-1 mt-3">
		<div class="d-flex align-items-center justify-content-between">
			<label class="fxr-label-sm mb-0">{{ __("Pipeline Operations") }}</label>
			<span v-if="!isCustomProfile" class="fxr-text-xs text-muted">
				{{ __("Read-only for selected profile") }}
			</span>
		</div>
		<MultiSelectList
			v-model="modelValue.norm_pipeline"
			:options="operationOptions"
			:read_only="readOnly || !isCustomProfile"
			displayMode="badges"
			:placeholder="__('Select operations...')"
		/>
	</div>

	<!-- Live Demo Section -->
	<div class="fxr-demo-section mt-4 pt-3 border-top">
		<div
			class="d-flex align-items-center justify-content-between cursor-pointer"
			@click="showDemo = !showDemo"
		>
			<span class="fxr-text-sm font-weight-bold">
				<i class="fa fa-flask mr-1 text-primary"></i>
				{{ __("Live Demo / Preview") }}
			</span>
			<i class="fa" :class="showDemo ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
		</div>

		<div v-if="showDemo" class="mt-2">
			<div class="d-flex flex-column fxr-gap-1">
				<label class="fxr-label-xs text-muted">{{ __("Example Text") }}</label>
				<input
					type="text"
					v-model="demoInput"
					class="fxr-input fxr-input--sm"
					:placeholder="__('Type something to test...')"
				/>
			</div>

			<div v-if="demoLoading" class="mt-3 text-center py-2">
				<i class="fa fa-spinner fa-spin text-muted"></i>
			</div>

			<div v-else-if="demoResult" class="mt-3">
				<div class="fxr-demo-result p-2 rounded bg-light border">
					<div class="fxr-text-xs text-muted mb-1">{{ __("Result:") }}</div>
					<div class="fxr-text-base font-weight-bold text-primary break-word">
						{{ demoResult.normalized_value || '""' }}
					</div>
				</div>

				<div v-if="demoResult.breakdown?.length > 1" class="mt-2">
					<div class="fxr-text-xs text-muted mb-1">{{ __("Pipeline Breakdown:") }}</div>
					<div class="fxr-breakdown-list">
						<div
							v-for="(step, idx) in demoResult.breakdown"
							:key="idx"
							class="fxr-breakdown-item d-flex align-items-start fxr-gap-1"
						>
							<div class="fxr-step-idx">{{ idx }}</div>
							<div class="flex-1 min-width-0">
								<div class="fxr-text-xs font-weight-bold">
									{{ step.operation }}
								</div>
								<div class="fxr-text-xs text-muted truncate">
									{{ step.value }}
								</div>
							</div>
							<i
								v-if="idx < demoResult.breakdown.length - 1"
								class="fa fa-arrow-down fxr-step-arrow"
							></i>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "../../../stores";
import { __ } from "../utils";
import MultiSelectList from "../../MultiSelectList.vue";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();
const showDemo = ref(true);
const demoInput = ref("FlexiRule Normalization Test 123!");
const demoResult = ref(null);
const demoLoading = ref(false);
const availableOperations = ref([]);
const availableProfiles = ref([]);

const isCustomProfile = computed(() => props.modelValue.norm_profile === "Custom");

const operationOptions = computed(() => {
	return availableOperations.value.map((op) => ({
		value: op,
		label: op.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
	}));
});

const stringFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Data", "Text", "Small Text", "Select"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});

const fetchMetadata = async () => {
	try {
		const res = await frappe.call("flexirule.ruleflow.api.normalize_test_value", {
			input_value: "",
		});
		if (res.message) {
			availableOperations.value = res.message.available_operations || [];
			availableProfiles.value = res.message.available_profiles || [];
		}
	} catch (e) {
		console.error("Failed to fetch normalization metadata", e);
	}
};

const runDemo = async () => {
	if (!demoInput.value && demoInput.value !== "") return;

	demoLoading.value = true;
	try {
		const res = await frappe.call("flexirule.ruleflow.api.normalize_test_value", {
			input_value: demoInput.value,
			profile:
				props.modelValue.norm_profile === "Custom" ? "" : props.modelValue.norm_profile,
			pipeline:
				props.modelValue.norm_profile === "Custom" ? props.modelValue.norm_pipeline : [],
		});
		demoResult.value = res.message;

		// If profile was changed, update the read-only pipeline view
		if (!isCustomProfile.value && res.message.breakdown) {
			props.modelValue.norm_pipeline = res.message.breakdown
				.filter((b) => b.operation !== "Initial")
				.map((b) => b.operation);
		}
	} catch (e) {
		console.error("Normalization demo failed", e);
	} finally {
		demoLoading.value = false;
	}
};

const debouncedRunDemo = flexirule.utils.debounce(runDemo, 500);

watch(
	() => [
		demoInput.value,
		props.modelValue.norm_profile,
		JSON.stringify(props.modelValue.norm_pipeline),
	],
	() => {
		if (showDemo.value) debouncedRunDemo();
	}
);

watch(
	() => props.modelValue.norm_profile,
	(newProfile) => {
		if (newProfile !== "Custom") {
			runDemo(); // Immediate run to update pipeline view
		}
	}
);

onMounted(() => {
	fetchMetadata();
	runDemo();
});
</script>

<style scoped>
.fxr-demo-section {
	border-top: 1px solid var(--fxr-border-subtle);
}

.fxr-demo-result {
	background-color: var(--fxr-bg-muted);
}

.break-word {
	word-break: break-all;
}

.fxr-breakdown-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.fxr-breakdown-item {
	position: relative;
	padding-bottom: 4px;
}

.fxr-step-idx {
	width: 18px;
	height: 18px;
	background: var(--fxr-accent-soft);
	color: var(--fxr-accent);
	border-radius: 4px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
	font-weight: 700;
	flex-shrink: 0;
	margin-top: 2px;
}

.fxr-step-arrow {
	position: absolute;
	left: 5px;
	bottom: -8px;
	font-size: 8px;
	color: var(--fxr-text-muted);
	opacity: 0.5;
}

.truncate {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
</style>
