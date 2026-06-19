<template>
	<div class="switch-node-config">
		<div class="form-group">
			<ControlFactory
				:ref="setControlRef"
				:df="{
					fieldname: 'expression',
					fieldtype: 'Small Text',
					label: __('Switch Expression (Python)'),
					placeholder: 'doc.category',
					reqd: 1,
				}"
				:modelValue="getJsonConfig('expression')"
				:showValidation="showValidation"
				@update:modelValue="$emit('update-json-config', 'expression', $event)"
			/>
		</div>

		<div
			class="form-group"
			:class="{ 'has-error': showValidation && Object.keys(cases).length === 0 }"
			data-fxr-fieldname="config.cases"
		>
			<label class="fxr-label reqd">{{ __("Cases") }}</label>
			<div
				v-if="showValidation && Object.keys(cases).length === 0"
				class="fxr-error-msg mb-2"
			>
				{{ __("At least one case is required") }}
			</div>
			<div class="case-list">
				<div
					v-for="(nodeId, val) in cases"
					:key="val"
					class="case-item mb-2 p-2 border rounded bg-light"
				>
					<div class="d-flex justify-content-between align-items-center mb-1">
						<strong class="text-primary">{{ val }}</strong>
						<button class="btn btn-xs btn-danger" @click="removeSwitchCase(val)">
							<i class="fa fa-times"></i>
						</button>
					</div>
					<div class="text-muted small">
						<i class="fa fa-arrow-right"></i> {{ getNodeLabel(nodeId) }}
					</div>
				</div>
			</div>

			<div class="add-case mt-2 p-2 border rounded">
				<DataControl
					class="mb-2"
					:df="{ label: '', placeholder: __('Value (e.g. \'Active\')') }"
					v-model="newCaseValue"
					:hideLabel="true"
				/>
				<SelectControl
					class="mb-2"
					:df="{ label: '', options: availableNodeOptions }"
					v-model="newCaseTarget"
					:hideLabel="true"
				/>
				<button
					class="btn btn-xs btn-default w-100"
					@click="addSwitchCase"
					:disabled="!newCaseValue || !newCaseTarget"
				>
					<i class="fa fa-plus"></i> {{ __("Add Case") }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, onBeforeUpdate } from "vue";
import ControlFactory from "../../controls/ControlFactory.vue";
import DataControl from "../../controls/DataControl.vue";
import SelectControl from "../../controls/SelectControl.vue";
const props = defineProps({
	nodeData: Object,
	availableNodes: { type: Array, default: () => [] },
	getNodeLabel: { type: Function, default: () => "" },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update-json-config"]);

const newCaseValue = ref("");
const newCaseTarget = ref("");
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

const cases = computed(() => {
	return getJsonConfig("cases", {});
});

const availableNodeOptions = computed(() => {
	return [
		{ label: __("Select Target Node"), value: "" },
		...props.availableNodes.map((n) => ({ label: n.label, value: n.id })),
	];
});

function getJsonConfig(key, defaultVal = "") {
	const configStr = props.nodeData?.config;
	const config = flexirule.utils.safe_json_parse(configStr, {});
	return config[key] !== undefined ? config[key] : defaultVal;
}

function addSwitchCase() {
	const currentCases = getJsonConfig("cases", {});
	currentCases[newCaseValue.value] = newCaseTarget.value;
	emit("update-json-config", "cases", currentCases);
	newCaseValue.value = "";
	newCaseTarget.value = "";
}

function removeSwitchCase(val) {
	const currentCases = getJsonConfig("cases", {});
	delete currentCases[val];
	emit("update-json-config", "cases", currentCases);
}

async function validate() {
	const errors = [];

	// 1. Core Control Validation (Aggregated)
	const results = await Promise.all(
		(controlRefs.value || []).map((ctrl) => {
			if (ctrl && typeof ctrl.validate === "function") {
				return ctrl.validate();
			}
			return { valid: true };
		})
	);
	results.forEach((res) => {
		if (!res.valid && res.errors) errors.push(...res.errors);
	});

	// 2. Logic-based Validation
	const currentCases = getJsonConfig("cases", {});
	if (Object.keys(currentCases).length === 0) {
		errors.push(__("At least one case is required for Switch"));
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
