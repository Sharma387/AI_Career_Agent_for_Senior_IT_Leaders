"""Role presets configuration for scheduled Seek scraping.

Defines default search presets for senior IT leadership roles and provides
runtime-configurable filtering based on the SEEK_ROLE_PRESETS setting.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings
from app.ingestion.seek_models import RolePreset

logger = logging.getLogger(__name__)

# Default role presets for senior IT leadership positions in New Zealand
DEFAULT_PRESETS: list[RolePreset] = [
    RolePreset(
        id="project-manager",
        label="Project Manager",
        keywords="project manager",
        location="New Zealand",
        enabled=True,
    ),
    RolePreset(
        id="sr-project-manager",
        label="Senior Project Manager",
        keywords="senior project manager",
        location="New Zealand",
        enabled=True,
    ),
    RolePreset(
        id="it-manager",
        label="IT Manager",
        keywords="IT manager",
        location="New Zealand",
        enabled=True,
    ),
    RolePreset(
        id="engineering-manager",
        label="Engineering Manager",
        keywords="engineering manager",
        location="New Zealand",
        enabled=True,
    ),
    RolePreset(
        id="it-director",
        label="IT Director",
        keywords="IT director",
        location="New Zealand",
        enabled=True,
    ),
    RolePreset(
        id="Program_manager",
        label="Program Manager",
        keywords="Program Manager",
        location="New Zealand",
        enabled=True,
    ),
]


def get_active_presets() -> list[RolePreset]:
    """Return only role presets that are enabled via settings.

    Reads settings.SEEK_ROLE_PRESETS on each call to support runtime
    changes without application restart. The setting is a comma-separated
    string of preset IDs that should be active.

    Returns:
        List of RolePreset instances where the preset ID is included
        in the SEEK_ROLE_PRESETS setting string.
    """
    # Re-read settings on each call to support runtime changes
    enabled_ids_raw = settings.SEEK_ROLE_PRESETS
    if not enabled_ids_raw or not enabled_ids_raw.strip():
        logger.debug("No role presets configured in SEEK_ROLE_PRESETS")
        return []

    enabled_ids = {
        preset_id.strip()
        for preset_id in enabled_ids_raw.split(",")
        if preset_id.strip()
    }

    active_presets = [
        preset for preset in DEFAULT_PRESETS if preset.id in enabled_ids
    ]

    logger.debug(
        f"Active role presets: {[p.id for p in active_presets]} "
        f"(from configured: {enabled_ids})"
    )

    return active_presets
