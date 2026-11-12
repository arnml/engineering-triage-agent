"""Fictional source text for read-only investigation; not a running service."""


def checkout_connection_options():
    # Demonstration bug: milliseconds are passed to a seconds-based option.
    database_timeout_ms = 3000
    return {"connect_timeout_seconds": database_timeout_ms}

