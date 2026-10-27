"""
Canonical FlexValue Backend Contract and Validation

Implements strict validation and evaluation boundaries for FlexValues according to the
frozen canonical condition evaluation specification.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

# Central resource limits
MAX_CONDITION_DEPTH = 32
MAX_CONDITION_NODES = 1000
MAX_RESOLVER_NESTING = 16
MAX_PATH_SEGMENTS = 32
MAX_TEMPLATE_SEGMENTS = 1000
MAX_COLLECTION_ROWS = 10000

VALID_MODES = {"static", "variable", "resolver", "template"}
VALID_VALUE_TYPES = {
	"string",
	"integer",
	"decimal",
	"boolean",
	"date",
	"datetime",
	"time",
	"null",
	"list",
	"object",
}
VALID_SCOPES = {"doc", "vars", "system", "env"}


class FlexValueValidationError(ValueError):
	"""Raised when a FlexValue payload fails strict contract validation."""

	def __init__(self, message: str, path: str = "$"):
		super().__init__(f"{path}: {message}" if path else message)
		self.message = message
		self.path = path


class FlexValueResolverRegistry:
	"""Registry managing allowed/disallowed resolver operations as condition operands."""

	_capabilities: ClassVar[dict[tuple[str, str], dict[str, Any]]] = {}

	@classmethod
	def register_operation(
		cls,
		family: str,
		operation: str,
		output_type: str,
		condition_operand_allowed: bool = False,
		required_capability: str | None = None,
	):
		cls._capabilities[(family, operation)] = {
			"family": family,
			"operation": operation,
			"output_type": output_type,
			"condition_operand_allowed": condition_operand_allowed,
			"required_capability": required_capability,
		}

	@classmethod
	def get_operation_capability(cls, family: str, operation: str) -> dict[str, Any] | None:
		return cls._capabilities.get((family, operation))

	@classmethod
	def is_allowed_as_condition_operand(cls, family: str, operation: str) -> bool:
		cap = cls.get_operation_capability(family, operation)
		if not cap:
			return False
		return bool(cap.get("condition_operand_allowed", False))


def validate_flex_value(
	flex_value: Any,
	path: str = "$",
	allowed_scopes: set | None = None,
	resolver_nesting_depth: int = 0,
) -> None:
	"""
	Strictly validates a FlexValue payload against canonical contract rules.
	Does NOT mutate flex_value.
	"""
	if not isinstance(flex_value, dict):
		raise FlexValueValidationError("FlexValue must be a JSON object", path)

	if resolver_nesting_depth > MAX_RESOLVER_NESTING:
		raise FlexValueValidationError(
			f"Exceeded maximum resolver nesting depth of {MAX_RESOLVER_NESTING}", path
		)

	keys = set(flex_value.keys())
	if "mode" not in keys:
		raise FlexValueValidationError("Missing required key 'mode'", path)

	mode = flex_value["mode"]
	if mode not in VALID_MODES:
		raise FlexValueValidationError(f"Invalid mode '{mode}'", path)

	effective_scopes = allowed_scopes if allowed_scopes is not None else VALID_SCOPES

	if mode == "static":
		_validate_static_flex_value(flex_value, keys, path)

	elif mode == "variable":
		_validate_variable_flex_value(flex_value, keys, path, effective_scopes)

	elif mode == "resolver":
		_validate_resolver_flex_value(flex_value, keys, path, effective_scopes, resolver_nesting_depth)

	elif mode == "template":
		_validate_template_flex_value(flex_value, keys, path, effective_scopes, resolver_nesting_depth)


def _validate_static_flex_value(flex_value: dict, keys: set, path: str) -> None:
	allowed_keys = {"mode", "value_type", "value"}
	unknown_keys = keys - allowed_keys
	if unknown_keys:
		raise FlexValueValidationError(
			f"Unknown key(s) in static FlexValue: {sorted(list(unknown_keys))}", path
		)

	if "value_type" not in keys:
		raise FlexValueValidationError("Static FlexValue requires 'value_type'", path)
	if "value" not in keys:
		raise FlexValueValidationError("Static FlexValue requires 'value'", path)

	val_type = flex_value["value_type"]
	val = flex_value["value"]

	if val_type not in VALID_VALUE_TYPES:
		raise FlexValueValidationError(f"Invalid static value_type '{val_type}'", path)

	if val_type == "null":
		if val is not None:
			raise FlexValueValidationError("Static value_type 'null' requires value to be None/null", path)
	elif val_type == "string":
		if not isinstance(val, str):
			raise FlexValueValidationError("Static value_type 'string' requires string value", path)
	elif val_type == "boolean":
		if not isinstance(val, bool):
			raise FlexValueValidationError("Static value_type 'boolean' requires boolean value", path)
	elif val_type == "integer":
		if isinstance(val, bool) or not isinstance(val, int):
			raise FlexValueValidationError("Static value_type 'integer' requires integer value", path)
	elif val_type == "decimal":
		if not isinstance(val, (str, int, float, Decimal)):
			raise FlexValueValidationError(
				"Static value_type 'decimal' must be string, number or Decimal", path
			)
		try:
			Decimal(str(val))
		except InvalidOperation:
			raise FlexValueValidationError(f"Invalid decimal string format '{val}'", path)
	elif val_type in ("date", "datetime", "time"):
		if not isinstance(val, str):
			raise FlexValueValidationError(
				f"Static value_type '{val_type}' requires string formatted value", path
			)
	elif val_type == "list":
		if not isinstance(val, list):
			raise FlexValueValidationError("Static value_type 'list' requires list value", path)
	elif val_type == "object":
		if not isinstance(val, dict):
			raise FlexValueValidationError("Static value_type 'object' requires dict value", path)


def _validate_variable_flex_value(flex_value: dict, keys: set, path: str, allowed_scopes: set) -> None:
	allowed_keys = {"mode", "path"}
	unknown_keys = keys - allowed_keys
	if unknown_keys:
		raise FlexValueValidationError(
			f"Unknown key(s) in variable FlexValue: {sorted(list(unknown_keys))}", path
		)

	if "path" not in keys:
		raise FlexValueValidationError("Variable FlexValue requires 'path'", path)

	path_obj = flex_value["path"]
	if not isinstance(path_obj, dict):
		raise FlexValueValidationError("Variable FlexValue 'path' must be an object", path)

	p_keys = set(path_obj.keys())
	allowed_p_keys = {"scope", "segments"}
	p_unknown = p_keys - allowed_p_keys
	if p_unknown:
		raise FlexValueValidationError(
			f"Unknown key(s) in variable path: {sorted(list(p_unknown))}", f"{path}.path"
		)

	if "scope" not in p_keys or "segments" not in p_keys:
		raise FlexValueValidationError("Variable path requires 'scope' and 'segments'", f"{path}.path")

	scope = path_obj["scope"]
	if scope not in allowed_scopes:
		raise FlexValueValidationError(f"Invalid or disallowed path scope '{scope}'", f"{path}.path")

	segments = path_obj["segments"]
	if not isinstance(segments, list):
		raise FlexValueValidationError("Variable path 'segments' must be a list", f"{path}.path")
	if not segments:
		raise FlexValueValidationError("Variable path 'segments' cannot be empty", f"{path}.path")
	if len(segments) > MAX_PATH_SEGMENTS:
		raise FlexValueValidationError(
			f"Path segments exceed max limit of {MAX_PATH_SEGMENTS}", f"{path}.path"
		)

	for idx, seg in enumerate(segments):
		if not isinstance(seg, str) or not seg:
			raise FlexValueValidationError(
				f"Segment at index {idx} must be a non-empty string", f"{path}.path.segments[{idx}]"
			)
		if seg.startswith("__") or seg.endswith("__"):
			raise FlexValueValidationError(
				f"Segment at index {idx} cannot be a dunder attribute", f"{path}.path.segments[{idx}]"
			)


def _validate_resolver_flex_value(
	flex_value: dict,
	keys: set,
	path: str,
	allowed_scopes: set,
	resolver_nesting_depth: int,
) -> None:
	allowed_keys = {"mode", "family", "operation", "config", "output_type"}
	unknown_keys = keys - allowed_keys
	if unknown_keys:
		raise FlexValueValidationError(
			f"Unknown key(s) in resolver FlexValue: {sorted(list(unknown_keys))}", path
		)

	for req_key in ("family", "operation", "config"):
		if req_key not in keys:
			raise FlexValueValidationError(f"Resolver FlexValue requires '{req_key}'", path)

	family = flex_value["family"]
	operation = flex_value["operation"]
	config = flex_value["config"]

	if not isinstance(family, str) or not family:
		raise FlexValueValidationError("Resolver family must be a non-empty string", path)
	if not isinstance(operation, str) or not operation:
		raise FlexValueValidationError("Resolver operation must be a non-empty string", path)
	if not isinstance(config, dict):
		raise FlexValueValidationError("Resolver config must be an object", path)

	# Validate recursive FlexValues in config if any
	_validate_nested_config_flex_values(config, f"{path}.config", allowed_scopes, resolver_nesting_depth + 1)


def _validate_nested_config_flex_values(
	config_obj: Any, path: str, allowed_scopes: set, resolver_nesting_depth: int
) -> None:
	if isinstance(config_obj, dict):
		if "mode" in config_obj and config_obj["mode"] in VALID_MODES:
			validate_flex_value(config_obj, path, allowed_scopes, resolver_nesting_depth)
		else:
			for k, v in config_obj.items():
				_validate_nested_config_flex_values(v, f"{path}.{k}", allowed_scopes, resolver_nesting_depth)
	elif isinstance(config_obj, list):
		for idx, item in enumerate(config_obj):
			_validate_nested_config_flex_values(
				item, f"{path}[{idx}]", allowed_scopes, resolver_nesting_depth
			)


def _validate_template_flex_value(
	flex_value: dict,
	keys: set,
	path: str,
	allowed_scopes: set,
	resolver_nesting_depth: int,
) -> None:
	allowed_keys = {"mode", "segments"}
	unknown_keys = keys - allowed_keys
	if unknown_keys:
		raise FlexValueValidationError(
			f"Unknown key(s) in template FlexValue: {sorted(list(unknown_keys))}", path
		)

	if "segments" not in keys:
		raise FlexValueValidationError("Template FlexValue requires 'segments'", path)

	segments = flex_value["segments"]
	if not isinstance(segments, list):
		raise FlexValueValidationError("Template 'segments' must be a list", path)
	if len(segments) > MAX_TEMPLATE_SEGMENTS:
		raise FlexValueValidationError(f"Template segments exceed max limit of {MAX_TEMPLATE_SEGMENTS}", path)

	for idx, seg in enumerate(segments):
		seg_path = f"{path}.segments[{idx}]"
		if isinstance(seg, str):
			continue
		elif isinstance(seg, dict):
			validate_flex_value(seg, seg_path, allowed_scopes, resolver_nesting_depth)
		else:
			raise FlexValueValidationError(
				f"Template segment at index {idx} must be a string or FlexValue object", seg_path
			)
