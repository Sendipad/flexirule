import assert from "node:assert/strict";
import { serializeActionPermissionFields } from "./action_permissions.mjs";

const canonical = serializeActionPermissionFields({
	ignore_permissions: 1,
	skip_permissions: 0,
	permission_audit_reason: "Fetch Records service integration",
});
assert.deepEqual(canonical, {
	ignore_permissions: 1,
	permission_audit_reason: "Fetch Records service integration",
});
assert.equal("skip_permissions" in canonical, false);

const legacyPayload = serializeActionPermissionFields({
	skip_permissions: 1,
	permission_audit_reason: "Legacy graph payload",
});
assert.deepEqual(legacyPayload, {
	ignore_permissions: 1,
	permission_audit_reason: "Legacy graph payload",
});

const explicitFalse = serializeActionPermissionFields({
	ignore_permissions: 0,
	skip_permissions: 1,
	permission_audit_reason: "Explicit opt-out wins",
});
assert.deepEqual(explicitFalse, {
	ignore_permissions: 0,
	permission_audit_reason: "Explicit opt-out wins",
});

assert.deepEqual(serializeActionPermissionFields({}), {
	ignore_permissions: 0,
	permission_audit_reason: "",
});
console.log("action permission serializer tests passed");
