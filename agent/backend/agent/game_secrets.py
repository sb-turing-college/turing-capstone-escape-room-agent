"""Known solution fragments for The Haunted Manor's fixed puzzle set.

Centralized here so the value isn't duplicated (and can't drift) across the
places that need to know it: the tool description shown to the explorer LLM
and the moderation allowlist that prevents the safe code from being
misclassified as PII.
"""

from __future__ import annotations

SAFE_CODE = "617482"
SAFE_CODE_REVERSED = "482617"
SAFE_CODE_PARTS = ("482", "617")

SAFE_CODE_ALLOWLIST = frozenset({SAFE_CODE, SAFE_CODE_REVERSED, *SAFE_CODE_PARTS})
