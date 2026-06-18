<template>
	<div class="switch-node-config">
		<div class="form-group">
			<TextControl
				:df="{
					label: __('Switch Expression (Python)'),
					fieldtype: 'Small Text',
					reqd: 1,
					placeholder: 'doc.category',
				}"
				:modelValue="getJsonConfig('expression')"
				@update:modelValue="$emit('update-json-config', 'expression', $event)"
			/>
		</div>

		<div class="form-group">
			<label>{{ __("Cases") }}</label>
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

			<div class="add-case mt-2 p-3 border rounded bg-light">
				<div class="fxr-label-sm mb-2">{{ __("Add New Case") }}</div>
				<DataControl
					v-model="newCaseValue"
					:df="{
						label: __('Value'),
						fieldtype: 'Data',
						placeholder: __('e.g. \'Active\''),
					}"
					class="mb-2"
				/>
				<SelectControl
					v-model="newCaseTarget"
					:df="{
						label: __('Target Node'),
						fieldtype: 'Select',
						options: availableNodes,
					}"
					class="mb-3"
				/>
				<button
					class="fxr-btn fxr-btn--primary w-100 justify-content-center"
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
import { computed, ref } from "vue";
import DataControl from "../../controls/DataControl.vue";
import SelectControl from "../../controls/SelectControl.vue";
import TextControl from "../../controls/TextControl.vue";

const props = defineProps({
	nodeData: Object,
	availableNodes: { type: Array, default: () => [] },
	getNodeLabel: { type: Function, default: () => "" },
});

const emit = defineEmits(["update-json-config"]);

const newCaseValue = ref("");
const newCaseTarget = ref("");

const cases = computed(() => {
	return getJsonConfig("cases", {});
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

function validate() {
	const expression = getJsonConfig("expression");
	if (!expression) {
		return { valid: false, message: __("Switch Expression is required") };
	}
	return { valid: true };
}

defineExpose({ validate });
</script>
