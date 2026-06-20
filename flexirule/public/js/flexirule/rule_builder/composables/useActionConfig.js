import { reactive, ref, computed, watch, onMounted, provide } from "vue";
import { useStore } from "../stores";
import { fromCodeString } from "../utils/serialization";

export function useActionConfig(props, options = {}) {
	const store = useStore();
	const config = reactive({});
	const docMeta = ref(null);
	const doctype_fields = ref([]);
	const variable_options = ref([]);
	const loading = ref(false);

	// Fetch metadata if needed
	const loadDocMeta = async (dt) => {
		if (!dt) {
			docMeta.value = null;
			return;
		}
		loading.value = true;
		try {
			await frappe.model.with_doctype(dt);
			docMeta.value = frappe.get_meta(dt);
		} finally {
			loading.value = false;
		}
	};

	const mode = computed(() => props.node?.data?.operation || "");
	const reference_doctype = computed(() => {
		const explicit = props.node?.data?.reference_doctype || props.node?.data?.doctype || "";
		if (explicit) return explicit;

		// Only fall back to rule's document_type for types that operate on the trigger doc.
		// Document Action / Query Records target a separate doctype and must set it explicitly.
		const actionType = props.node?.data?.action_type;
		const op = props.node?.data?.operation;

		// Default mappings for common Document Action operations
		if (actionType === "Document Action") {
			if (op === "Create ToDo") return "ToDo";
			if (op === "Add Comment") return "Comment";
		}
		if (actionType === "Query Records") {
			if (op === "Query Report") return "Report";
			return store.rule_doc?.document_type || "";
		}

		const TRIGGER_DOC_TYPES = ["Assignment", "Entry Action", "Notify", "Document Action"];
		if (!actionType || TRIGGER_DOC_TYPES.includes(actionType)) {
			return store.rule_doc?.document_type || "";
		}
		return "";
	});
	const reference_docname = computed(
		() => props.node?.data?.reference_docname || props.node?.data?.docname || ""
	);

	function with_read_only(field) {
		return { ...field, read_only: props.readOnly };
	}

	async function load_doctype_fields(doctype) {
		if (!doctype) {
			doctype_fields.value = [];
			return;
		}
		try {
			loading.value = true;
			const metaStore = store;
			await metaStore.fetch_metadata(doctype);

			// Merge defaults with caller-provided options
			const fieldOptions = {
				alias: options.fieldAlias || "doc",
				valueMode: options.fieldValueMode || "expression",
			};

			doctype_fields.value = metaStore.get_fields_for_doctype(doctype, fieldOptions);
		} catch (e) {
			console.error("FlexiRule: Failed to load doctype fields", e);
			doctype_fields.value = [];
		} finally {
			loading.value = false;
		}
	}

	async function refresh_variables() {
		if (!props.node?.id) {
			variable_options.value = [];
			return;
		}
		try {
			variable_options.value = await store.getAvailableVariables(props.node.id);
		} catch (e) {
			variable_options.value = [];
		}
	}

	function parse_value_type(val, variable_set) {
		if (typeof val === "number") return "Number";
		if (typeof val === "boolean") return "Boolean";
		if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
			const inner = val.slice(1, -1);
			if (variable_set && variable_set.has(inner)) return "Variable";
			return "Expression";
		}
		return "Value";
	}

	function strip_expression(val) {
		if (typeof val === "string" && val.startsWith("{") && val.endsWith("}")) {
			return val.slice(1, -1);
		}
		return val;
	}

	function encode_value(row) {
		let val = row.value;
		if (row.value_type === "Number") {
			const num = Number(val);
			if (!Number.isNaN(num)) return num;
			return val;
		}
		if (row.value_type === "Boolean") {
			if (val === true || val === "true" || val === 1 || val === "1") return true;
			if (val === false || val === "false" || val === 0 || val === "0") return false;
			return Boolean(val);
		}
		if (row.value_type === "Expression" || row.value_type === "Variable") {
			return `{${val}}`;
		}
		return val;
	}

	/**
	 * Sync local config object back to the node state.
	 * Internal state (node.data.config) MUST always be a plain Object.
	 */
	function sync_config(new_config) {
		if (!props.node?.data) return;

		// Ensure we are working with an object internally
		const current =
			typeof props.node.data.config === "string"
				? fromCodeString(props.node.data.config)
				: props.node.data.config || {};

		const current_str = JSON.stringify(current || {});
		const next_str = JSON.stringify(new_config || {});

		if (current_str !== next_str) {
			// Explicitly store as Object
			props.node.data.config =
				typeof new_config === "string" ? fromCodeString(new_config) : new_config;
			store.mark_dirty();
		}
	}

	function update_action_field(fieldname, value) {
		if (!props.node?.data) return;
		if (props.node.data[fieldname] === value) return;

		props.node.data[fieldname] = value;

		// Avoid marking dirty if we are modifying a draft node (inside a modal)
		// or if we are currently in a read-only state.
		// Note: draftNode is created by useRuleConfig and is not present in store.nodes.
		const isDraft = !store.nodes.some((n) => n === props.node);
		if (!props.readOnly && !isDraft) {
			store.mark_dirty();
		}
	}

	watch(
		() => reference_doctype.value,
		(val) => load_doctype_fields(val),
		{ immediate: true }
	);

	watch(
		() => props.node?.id,
		() => refresh_variables(),
		{ immediate: true }
	);

	// Also refresh when nodes in the store change (e.g. alias rename, new upstream node)
	watch(
		() => store.nodes,
		() => refresh_variables(),
		{ deep: true }
	);

	provide(
		"variableOptions",
		computed(() => variable_options.value)
	);
	provide(
		"docFields",
		computed(() => doctype_fields.value)
	);

	function is_field_valid(fieldname, dt_fields) {
		if (!dt_fields || !dt_fields.length) return true;
		if (!fieldname) return true;
		// Allow expressions, variables, and direct var paths
		if (
			typeof fieldname === "string" &&
			(fieldname.startsWith("{") || fieldname.startsWith("vars."))
		)
			return true;

		return dt_fields.some((f) => f.value === fieldname);
	}

	return {
		store,
		config,
		doctype_fields,
		variable_options,
		loading,
		docMeta,
		mode,
		reference_doctype,
		with_read_only,
		loadDocMeta,
		load_doctype_fields,
		refresh_variables,
		parse_value_type,
		strip_expression,
		encode_value,
		sync_config,
		update_action_field,
		is_field_valid,
	};
}
