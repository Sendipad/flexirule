/**
 * Normalize permission override fields for Rule Action persistence.
 *
 * The graph model accepts the legacy skip_permissions name for compatibility,
 * but the Rule Action DocType stores the canonical ignore_permissions field.
 */
export function serializeActionPermissionFields(actionData = {}) {
	return {
		ignore_permissions: actionData.ignore_permissions ?? actionData.skip_permissions ?? 0,
		permission_audit_reason: actionData.permission_audit_reason ?? "",
	};
}
