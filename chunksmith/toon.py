from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional


def encode(value: Any, options: Optional[Dict[str, Any]] = None) -> str:
    """
    Converts Python objects to TOON format.
    Handles tabular arrays (uniform objects) and mixed/bulleted arrays.
    """
    indent_size = (options or {}).get("indent", 2)
    delimiter = (options or {}).get("delimiter", ",")
    return _encode_recursive(value, 0, indent_size, delimiter)


def _encode_recursive(value: Any, indent_level: int, indent_size: int, delimiter: str) -> str:
    indent = " " * (indent_level * indent_size)

    if value is None:
        return f"{indent}null"
    
    if isinstance(value, bool):
        return f"{indent}{str(value).lower()}"

    if isinstance(value, (int, float)):
        return f"{indent}{value}"

    if isinstance(value, str):
        # Quote if it contains structural characters or the delimiter
        if any(c in value for c in [":", "-", "[", "]", "{", "}", delimiter, "\n"]):
            # Simple quoting (double quotes)
            escaped = value.replace('"', '\\"')
            return f'{indent}"{escaped}"'
        return f"{indent}{value}"

    if isinstance(value, (datetime.datetime, datetime.date)):
        return f"{indent}{value.isoformat()}"

    if isinstance(value, dict):
        if not value:
            return f"{indent}{{}}"
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{indent}{k}:")
                lines.append(_encode_recursive(v, indent_level + 1, indent_size, delimiter))
            else:
                # For dict values that are primitives, we don't indent the value line
                # But we do need to handle the key
                val_str = _encode_recursive(v, 0, indent_size, delimiter)
                lines.append(f"{indent}{k}: {val_str}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return f"{indent}[]"

        # Check if it's a tabular array (list of dicts with same keys)
        is_tabular = False
        if all(isinstance(x, dict) for x in value) and len(value) > 0:
            keys = list(value[0].keys())
            # All must have exactly the same keys for tabular format
            if all(isinstance(x, dict) and list(x.keys()) == keys for x in value):
                # Check if values are primitives (TOON tables are for flat data)
                if all(all(not isinstance(v, (dict, list)) for v in x.values()) for x in value):
                    is_tabular = True

        if is_tabular:
            keys = list(value[0].keys())
            header = f"{indent}[{len(value)},]{{{delimiter.join(keys)}}}:"
            lines = [header]
            for item in value:
                # Properly quote values in the row if they contain the delimiter
                row_vals = []
                for k in keys:
                    v = item[k]
                    v_str = str(v) if v is not None else "null"
                    if delimiter in v_str or '"' in v_str or "\n" in v_str:
                        v_str = f'"{v_str.replace("\"", "\\\"")}"'
                    row_vals.append(v_str)
                lines.append(f"{indent}{' ' * indent_size}{delimiter.join(row_vals)}")
            return "\n".join(lines)

        # Standard array (bulleted)
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{indent}-")
                lines.append(_encode_recursive(item, indent_level + 1, indent_size, delimiter))
            else:
                val_str = _encode_recursive(item, 0, indent_size, delimiter)
                lines.append(f"{indent}- {val_str}")
        return "\n".join(lines)

    return f"{indent}{str(value)}"
