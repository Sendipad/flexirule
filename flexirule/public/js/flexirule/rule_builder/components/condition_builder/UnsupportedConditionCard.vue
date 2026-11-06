<template>
	<div class="unsupported-condition-card alert alert-warning p-3 mb-2">
		<div class="d-flex align-items-start justify-content-between gap-3">
			<div class="d-flex align-items-start gap-2">
				<i class="fa fa-exclamation-triangle text-warning mt-1" style="font-size: 16px"></i>
				<div>
					<div class="font-weight-bold text-dark mb-1">
						{{ __("Preserved Unsupported Condition") }}
					</div>
					<div class="text-muted small mb-2">
						{{
							node.unsupported_reason ||
							__(
								"This legacy or external condition pattern cannot be safely edited without risking data loss. It is preserved unchanged until you deliberately replace or remove it."
							)
						}}
					</div>

					<!-- Collapsible Advanced / Raw Diagnostics -->
					<div class="raw-diagnostics-toggle mb-2">
						<button
							type="button"
							class="btn btn-link btn-xs p-0 text-muted"
							@click="showDiagnostics = !showDiagnostics"
						>
							<i
								:class="showDiagnostics ? 'fa fa-caret-down' : 'fa fa-caret-right'"
								class="mr-1"
							></i>
							{{
								showDiagnostics
									? __("Hide raw payload")
									: __("Show raw payload (advanced)")
							}}
						</button>
						<div
							v-if="showDiagnostics"
							class="raw-payload-box p-2 mt-1 bg-light border rounded small font-monospace text-break"
						>
							{{ payloadJson }}
						</div>
					</div>
				</div>
			</div>
		</div>

		<div
			v-if="!readOnly"
			class="actions-row d-flex align-items-center gap-2 mt-2 pt-2 border-top"
		>
			<button type="button" class="btn btn-xs btn-outline-primary" @click="confirmReplace">
				<i class="fa fa-refresh mr-1"></i>
				{{ __("Replace with a new condition") }}
			</button>

			<button
				v-if="allowRemoval"
				type="button"
				class="btn btn-xs btn-outline-danger"
				@click="confirmRemove"
			>
				<i class="fa fa-trash mr-1"></i>
				{{ __("Remove") }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
	node: { type: Object, required: true },
	readOnly: { type: Boolean, default: false },
	isSoleCondition: { type: Boolean, default: false },
	isEntryNode: { type: Boolean, default: false },
});

const emit = defineEmits(["replace", "remove"]);

const showDiagnostics = ref(false);

const allowRemoval = computed(() => {
	// If it is the sole condition of an Entry Action, removal would broaden rule execution to all documents
	return true;
});

const payloadJson = computed(() => {
	const payload = props.node.original_payload;
	if (typeof payload === "string") return payload;
	try {
		return JSON.stringify(payload, null, 2);
	} catch {
		return String(payload);
	}
});

function confirmReplace() {
	const msg = __(
		"Are you sure you want to replace this preserved condition? Any unmigrated custom expressions in the original condition will be discarded."
	);
	if (typeof frappe !== "undefined" && frappe.confirm) {
		frappe.confirm(msg, () => emit("replace", props.node.id));
	} else {
		if (window.confirm(msg)) {
			emit("replace", props.node.id);
		}
	}
}

function confirmRemove() {
	let msg = __(
		"Are you sure you want to remove this preserved condition? This will delete the condition."
	);
	if (props.isSoleCondition && props.isEntryNode) {
		msg = __(
			"WARNING: Removing the only Entry Condition will remove all trigger filtering, causing the rule to run unconditionally for all documents! Are you sure you want to delete it?"
		);
	}

	if (typeof frappe !== "undefined" && frappe.confirm) {
		frappe.confirm(msg, () => emit("remove", props.node.id));
	} else {
		if (window.confirm(msg)) {
			emit("remove", props.node.id);
		}
	}
}
</script>

<style scoped>
.unsupported-condition-card {
	background-color: var(--fxr-surface-2, #fffbeb);
	border: 1px solid var(--fxr-warning, #f59e0b);
	border-radius: var(--fxr-radius-md, 6px);
}
.raw-payload-box {
	max-height: 140px;
	overflow-y: auto;
	background: rgba(0, 0, 0, 0.04);
}
</style>
