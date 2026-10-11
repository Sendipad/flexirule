<template>
	<div class="fetch-records-functions">
		<div class="functions-header">
			<div>
				<h6 class="mb-0">{{ __("SQL Functions & Aggregations") }}</h6>
				<p class="section-description">
					{{ __("Configure verified SQL functions and assign output aliases.") }}
				</p>
			</div>
			<button
				v-if="!readOnly"
				type="button"
				class="btn btn-xs btn-outline-primary"
				@click="addFunction"
			>
				<i class="fa fa-plus mr-1"></i>{{ __("Add Function") }}
			</button>
		</div>

		<div v-if="localFunctions.length === 0" class="empty-state text-muted py-2 text-center">
			<small>{{ __("No SQL functions configured.") }}</small>
		</div>

		<div v-else class="function-rows">
			<div v-for="(fnRow, index) in localFunctions" :key="fnRow.id" class="function-row-card">
				<div class="function-row-header">
					<div class="func-type-select">
						<label class="func-label">{{ __("Function") }}</label>
						<select
							v-model="fnRow.function"
							class="form-control form-control-sm"
							:disabled="readOnly"
							@change="onFunctionTypeChange(fnRow)"
						>
							<option v-for="f in FUNCTION_OPTIONS" :key="f.value" :value="f.value">
								{{ f.label }}
							</option>
						</select>
					</div>

					<div class="func-alias-input">
						<label class="func-label"
							>{{ __("Output Alias") }} <span class="text-danger">*</span></label
						>
						<input
							v-model="fnRow.alias"
							type="text"
							class="form-control form-control-sm"
							:placeholder="__('e.g. total_amount')"
							:disabled="readOnly"
							@input="emitUpdate"
						/>
					</div>

					<button
						v-if="!readOnly"
						type="button"
						class="btn btn-xs btn-link text-danger remove-func-btn"
						:title="__('Remove function')"
						@click="removeFunction(index)"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>

				<!-- Dynamic Argument Controls -->
				<div class="function-row-body">
					<!-- COUNT -->
					<div v-if="fnRow.function === 'COUNT'" class="arg-group">
						<label class="arg-label">{{ __("Target Field") }}</label>
						<select
							:value="getArgValue(fnRow, 0)"
							class="form-control form-control-sm"
							:disabled="readOnly"
							@change="setArgValue(fnRow, 0, 'field', $event.target.value)"
						>
							<option value="*">{{ __("* (All Rows)") }}</option>
							<option
								v-for="field in fieldsOptions"
								:key="field.value"
								:value="field.value"
							>
								{{ field.label }}
							</option>
						</select>
					</div>

					<!-- SUM, AVG, MIN, MAX, ABS -->
					<div
						v-else-if="['SUM', 'AVG', 'MIN', 'MAX', 'ABS'].includes(fnRow.function)"
						class="arg-group"
					>
						<label class="arg-label">{{ __("Target Field") }}</label>
						<select
							:value="getArgValue(fnRow, 0)"
							class="form-control form-control-sm"
							:disabled="readOnly"
							@change="setArgValue(fnRow, 0, 'field', $event.target.value)"
						>
							<option value="">{{ __("-- Select Field --") }}</option>
							<option
								v-for="field in fieldsOptions"
								:key="field.value"
								:value="field.value"
							>
								{{ field.label }}
							</option>
						</select>
					</div>

					<!-- IFNULL -->
					<div v-else-if="fnRow.function === 'IFNULL'" class="arg-grid">
						<div class="arg-group">
							<label class="arg-label">{{ __("Field") }}</label>
							<select
								:value="getArgValue(fnRow, 0)"
								class="form-control form-control-sm"
								:disabled="readOnly"
								@change="setArgValue(fnRow, 0, 'field', $event.target.value)"
							>
								<option value="">{{ __("-- Select Field --") }}</option>
								<option
									v-for="field in fieldsOptions"
									:key="field.value"
									:value="field.value"
								>
									{{ field.label }}
								</option>
							</select>
						</div>
						<div class="arg-group">
							<label class="arg-label">{{ __("Fallback Value") }}</label>
							<input
								type="text"
								class="form-control form-control-sm"
								:value="getArgValue(fnRow, 1)"
								:placeholder="__('e.g. N/A or 0')"
								:disabled="readOnly"
								@input="setArgValue(fnRow, 1, 'literal', $event.target.value)"
							/>
						</div>
					</div>

					<!-- CONCAT -->
					<div v-else-if="fnRow.function === 'CONCAT'" class="concat-args">
						<label class="arg-label">{{ __("Concat Arguments") }}</label>
						<div v-for="(arg, aIdx) in fnRow.args" :key="aIdx" class="concat-arg-row">
							<select
								v-model="arg.type"
								class="form-control form-control-sm arg-type-select"
								:disabled="readOnly"
								@change="emitUpdate"
							>
								<option value="field">{{ __("Field") }}</option>
								<option value="literal">{{ __("Literal") }}</option>
							</select>

							<select
								v-if="arg.type === 'field'"
								v-model="arg.value"
								class="form-control form-control-sm flex-1"
								:disabled="readOnly"
								@change="emitUpdate"
							>
								<option value="">{{ __("-- Select Field --") }}</option>
								<option
									v-for="field in fieldsOptions"
									:key="field.value"
									:value="field.value"
								>
									{{ field.label }}
								</option>
							</select>

							<input
								v-else
								v-model="arg.value"
								type="text"
								class="form-control form-control-sm flex-1"
								:placeholder="__('Literal text')"
								:disabled="readOnly"
								@input="emitUpdate"
							/>

							<button
								v-if="!readOnly && fnRow.args.length > 2"
								type="button"
								class="btn btn-xs btn-link text-danger"
								@click="removeConcatArg(fnRow, aIdx)"
							>
								<i class="fa fa-times"></i>
							</button>
						</div>
						<button
							v-if="!readOnly"
							type="button"
							class="btn btn-xs btn-link p-0 text-primary mt-1"
							@click="addConcatArg(fnRow)"
						>
							<i class="fa fa-plus mr-1"></i>{{ __("Add Concat Argument") }}
						</button>
					</div>

					<!-- EXTRACT -->
					<div v-else-if="fnRow.function === 'EXTRACT'" class="arg-grid">
						<div class="arg-group">
							<label class="arg-label">{{ __("Date Unit") }}</label>
							<select
								:value="getArgValue(fnRow, 0) || 'year'"
								class="form-control form-control-sm"
								:disabled="readOnly"
								@change="setArgValue(fnRow, 0, 'literal', $event.target.value)"
							>
								<option value="year">{{ __("YEAR") }}</option>
								<option value="month">{{ __("MONTH") }}</option>
								<option value="day">{{ __("DAY") }}</option>
								<option value="hour">{{ __("HOUR") }}</option>
								<option value="minute">{{ __("MINUTE") }}</option>
								<option value="second">{{ __("SECOND") }}</option>
							</select>
						</div>
						<div class="arg-group">
							<label class="arg-label">{{ __("Date/Time Field") }}</label>
							<select
								:value="getArgValue(fnRow, 1)"
								class="form-control form-control-sm"
								:disabled="readOnly"
								@change="setArgValue(fnRow, 1, 'field', $event.target.value)"
							>
								<option value="">{{ __("-- Select Field --") }}</option>
								<option
									v-for="field in fieldsOptions"
									:key="field.value"
									:value="field.value"
								>
									{{ field.label }}
								</option>
							</select>
						</div>
					</div>

					<!-- NOW -->
					<div v-else-if="fnRow.function === 'NOW'" class="text-muted">
						<small>{{
							__("NOW() takes no parameters and returns current system timestamp.")
						}}</small>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	fieldsOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const FUNCTION_OPTIONS = [
	{ label: "COUNT", value: "COUNT" },
	{ label: "SUM", value: "SUM" },
	{ label: "AVG", value: "AVG" },
	{ label: "MIN", value: "MIN" },
	{ label: "MAX", value: "MAX" },
	{ label: "ABS", value: "ABS" },
	{ label: "IFNULL", value: "IFNULL" },
	{ label: "CONCAT", value: "CONCAT" },
	{ label: "EXTRACT", value: "EXTRACT" },
	{ label: "NOW", value: "NOW" },
];

const localFunctions = ref(normalizeFunctions(props.modelValue));

function normalizeFunctions(list) {
	if (!Array.isArray(list)) return [];
	return list.map((item) => ({
		id: item.id || "fn-" + Math.random().toString(36).substring(2, 8),
		function: item.function || "COUNT",
		args: Array.isArray(item.args)
			? item.args.map(normalizeArg)
			: defaultArgsFor(item.function || "COUNT"),
		alias: item.alias || "",
	}));
}

function normalizeArg(arg) {
	if (typeof arg === "object" && arg !== null) {
		return { type: arg.type || "field", value: arg.value ?? "" };
	}
	return { type: "field", value: String(arg ?? "") };
}

function defaultArgsFor(funcName) {
	if (funcName === "COUNT") return [{ type: "field", value: "*" }];
	if (funcName === "CONCAT")
		return [
			{ type: "field", value: "" },
			{ type: "literal", value: " " },
		];
	if (funcName === "IFNULL")
		return [
			{ type: "field", value: "" },
			{ type: "literal", value: "N/A" },
		];
	if (funcName === "EXTRACT")
		return [
			{ type: "literal", value: "year" },
			{ type: "field", value: "" },
		];
	if (funcName === "NOW") return [];
	return [{ type: "field", value: "" }];
}

function onFunctionTypeChange(fnRow) {
	fnRow.args = defaultArgsFor(fnRow.function);
	if (!fnRow.alias) {
		fnRow.alias = fnRow.function.toLowerCase() + "_val";
	}
	emitUpdate();
}

function getArgValue(fnRow, index) {
	if (!fnRow.args || !fnRow.args[index]) return "";
	return fnRow.args[index].value ?? "";
}

function setArgValue(fnRow, index, type, value) {
	if (!fnRow.args) fnRow.args = [];
	while (fnRow.args.length <= index) {
		fnRow.args.push({ type: "field", value: "" });
	}
	fnRow.args[index] = { type, value };
	emitUpdate();
}

function addConcatArg(fnRow) {
	fnRow.args.push({ type: "literal", value: " " });
	emitUpdate();
}

function removeConcatArg(fnRow, index) {
	fnRow.args.splice(index, 1);
	emitUpdate();
}

function addFunction() {
	if (props.readOnly) return;
	localFunctions.value.push({
		id: "fn-" + Date.now() + "-" + Math.random().toString(36).substring(2, 6),
		function: "COUNT",
		args: defaultArgsFor("COUNT"),
		alias: "count_total",
	});
	emitUpdate();
}

function removeFunction(index) {
	if (props.readOnly) return;
	localFunctions.value.splice(index, 1);
	emitUpdate();
}

function emitUpdate() {
	emit("update:modelValue", localFunctions.value);
}

watch(
	() => props.modelValue,
	(val) => {
		if (JSON.stringify(val) === JSON.stringify(localFunctions.value)) return;
		localFunctions.value = normalizeFunctions(val);
	},
	{ deep: true }
);
</script>

<style scoped>
.fetch-records-functions {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.functions-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: var(--spacing-md);
}

.section-description {
	margin: 2px 0 0;
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
}

.function-rows {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-3);
}

.function-row-card {
	background: var(--fxr-bg-subtle, #f8fafc);
	border: 1px solid var(--fxr-border-color, #e2e8f0);
	border-radius: 6px;
	padding: var(--spacing-sm) var(--spacing-md);
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.function-row-header {
	display: flex;
	align-items: flex-end;
	gap: var(--spacing-md);
	width: 100%;
}

.func-type-select {
	width: 150px;
	flex-shrink: 0;
}

.func-alias-input {
	flex: 1;
	min-width: 0;
}

.func-label,
.arg-label {
	display: block;
	font-size: 11px;
	font-weight: 600;
	color: var(--fxr-text-muted);
	margin-bottom: 2px;
}

.remove-func-btn {
	padding: 0;
	height: 30px;
	line-height: 30px;
	align-self: flex-end;
}

.function-row-body {
	padding-top: var(--spacing-xs);
	border-top: 1px dashed var(--fxr-border-color, #cbd5e1);
}

.arg-grid {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: var(--spacing-md);
}

.concat-args {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.concat-arg-row {
	display: flex;
	align-items: center;
	gap: var(--spacing-xs);
}

.arg-type-select {
	width: 90px !important;
	flex-shrink: 0;
}

.flex-1 {
	flex: 1;
}
</style>
