"""
Compatibility stub.

`token_budget.py` (owned by C4-3) imports `estimate_tokens` from here.
Language rules / skeleton extraction were replaced by `tags.py`.
"""

from .code_graph import estimate_tokens

__all__ = ["estimate_tokens"]
