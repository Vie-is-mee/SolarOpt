from __future__ import annotations

DEPENDENCIES = {
    "panel_model": ["candidates", "layout", "electrical", "energy", "cost", "roi", "bom", "report"],
    "panel_size": ["candidates", "layout", "shadow", "energy", "electrical", "cost", "roi", "bom", "report"],
    "panel_price": ["cost", "roi", "bom", "report"],
    "obstacle_height": ["shadow", "layout", "energy", "roi", "report"],
    "roof_geometry": ["candidates", "layout", "shadow", "energy", "electrical", "cost", "roi", "bom", "report"],
}

ORDER = ["candidates", "shadow", "layout", "energy", "electrical", "cost", "roi", "bom", "report"]


def affected_nodes(change_type: str):
    nodes = DEPENDENCIES.get(change_type, [])
    return [n for n in ORDER if n in nodes]


def status_map(change_type: str):
    affected = set(affected_nodes(change_type))
    return {node: ("DIRTY" if node in affected else "CLEAN") for node in ORDER}
