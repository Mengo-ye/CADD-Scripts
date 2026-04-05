from .config import XDockConfig

# Each mode overrides specific flags on the config.
# Keys match the flag names in XDockConfig.
MODES = {
    "SITEMAP": {
        "by_center": False, "by_complex": False, "by_sitemap": True,
        "xglide": True, "docking": "true", "induce_fit": False, "grid_in": False,
    },
    "AllSite": {
        "by_center": False, "by_complex": True, "by_sitemap": True,
        "xglide": True, "docking": "true", "induce_fit": False, "grid_in": False,
    },
    "Native": {
        "by_center": False, "by_complex": False, "by_sitemap": False,
        "xglide": False, "docking": "false", "induce_fit": False, "grid_in": False,
    },
    "COMPD": {
        "by_center": False, "by_complex": True, "by_sitemap": False,
        "xglide": True, "docking": "true", "induce_fit": False, "grid_in": False,
    },
    "COMPI": {
        "by_center": False, "by_complex": True, "by_sitemap": False,
        "xglide": False, "docking": "false", "induce_fit": True, "grid_in": False,
    },
    "GCD": {
        "by_center": True, "by_complex": False, "by_sitemap": False,
        "xglide": True, "docking": "true", "induce_fit": False, "grid_in": False,
    },
    "GCI": {
        "by_center": True, "by_complex": False, "by_sitemap": False,
        "xglide": False, "docking": "false", "induce_fit": True, "grid_in": False,
    },
    "SiteMapGrid": {
        "by_center": False, "by_complex": False, "by_sitemap": True,
        "xglide": True, "docking": "false", "induce_fit": False, "grid_in": False,
    },
    "ComplexGrid": {
        "by_center": False, "by_complex": True, "by_sitemap": False,
        "xglide": True, "docking": "false", "induce_fit": False, "grid_in": False,
    },
    "CenterGrid": {
        "by_center": True, "by_complex": False, "by_sitemap": False,
        "xglide": True, "docking": "false", "induce_fit": False, "grid_in": False,
    },
    "Dock": {
        "by_center": False, "by_complex": False, "by_sitemap": False,
        "xglide": True, "docking": "true", "induce_fit": False, "grid_in": True,
    },
}

VALID_MODES = list(MODES.keys())


def resolve_mode(config: XDockConfig) -> None:
    """Apply mode-specific flag overrides to the config."""
    if config.mode not in MODES:
        valid = ", ".join(VALID_MODES)
        raise ValueError(f"Unknown mode '{config.mode}'. Valid modes: {valid}")

    overrides = MODES[config.mode]
    for key, value in overrides.items():
        setattr(config, key, value)

    # AllSite mode forces ligand_asl to "ligand" (Bash line 318)
    if config.mode == "AllSite":
        config.ligand_asl = "ligand"
