<template>
	<div class="switch-node-config">
		<div
			class="form-group"
			:class="{ 'has-error': showValidation && !getJsonConfig('expression') }"
			v-field-reveal="'config.expression'"
		>
			<label>{{ __("Switch Expression (Python)") }}</label>
			<textarea
				class="form-control"
				rows="2"
				:value="getJsonConfig('expression')"
				@input="$emit('update-json-config', 'expression', $event.target.value)"
				placeholder="doc.category"
			></textarea>
			<div v-if="showValidation && !getJsonConfig('expression')" class="fxr-error-msg">
				{{ __("Switch Expression is required") }}
			</div>
		</div>

		<div
			class="form-group"
			:class="{ 'has-error': showValidation && Object.keys(cases).length === 0 }"
			v-field-reveal="'config.cases'"
		>
			<label>{{ __("Cases") }}</label>
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
				<input
					type="text"
					class="form-control input-sm mb-1"
					v-model="newCaseValue"
					:placeholder="__('Value (e.g. \'Active\')')"
				/>
				<select class="form-control input-sm mb-1" v-model="newCaseTarget">
					<option value="" disabled>{{ __("Select Target Node") }}</option>
					<option v-for="node in availableNodes" :key="node.id" :value="node.id">
						{{ node.label }}
					</option>
				</select>
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
import { computed, ref } from "vue";
const props = defineProps({
	nodeData: Object,
	availableNodes: { type: Array, default: () => [] },
	getNodeLabel: { type: Function, default: () => "" },
	showValidation: { type: Boolean, default: false },
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
	const errors = [];
	const expression = getJsonConfig("expression");
	const currentCases = getJsonConfig("cases", {});

	if (!expression) {
		errors.push(__("Switch Expression is required"));
	}

	if (Object.keys(currentCases).length === 0) {
		errors.push(__("At least one case is required for Switch"));
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
