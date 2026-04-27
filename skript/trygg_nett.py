"""
SSL-kontekst for urllib som brukar certifi når tilgjengeleg
(særleg nyttig på macOS sitt innebygde Python).
"""
from __future__ import annotations

import ssl


def ssl_kontekst() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore[import-untyped]
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())
