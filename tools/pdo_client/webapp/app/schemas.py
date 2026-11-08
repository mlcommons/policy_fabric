"""JSON Schema helpers for card parameters and credential claims."""

import jsonschema


def errors(value, schema):
    """Every reason ``value`` does not satisfy ``schema``, as readable strings."""
    schema = {k: v for k, v in schema.items() if k != "$id"}
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for error in sorted(validator.iter_errors(value), key=lambda e: list(e.path)):
        where = ".".join(str(p) for p in error.path)
        out.append(f"{where}: {error.message}" if where else error.message)
    return out
