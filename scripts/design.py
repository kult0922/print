"""Read the CAD source parameters shared by rendering and mesh inspection."""
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def assembly_parameters():
    source = (ROOT / "models" / "nikko_trophy.scad").read_text()
    values = {}
    for name in (
        "card_w", "card_h", "card_r", "lean_side", "lean_back",
        "base_h", "insertion", "card_y",
    ):
        match = re.search(rf"^{name}\s*=\s*([\d.]+)\s*;", source, re.MULTILINE)
        if match is None:
            raise ValueError(f"Missing numeric CAD parameter: {name}")
        values[name] = float(match.group(1))
    side, back = map(math.radians, (values["lean_side"], values["lean_back"]))
    low = -(values["card_w"] / 2 * math.sin(side) + values["card_h"] / 2 * math.cos(side))
    low += values["card_r"] * (math.sin(side) + math.cos(side) - 1)
    values.update(
        side=side, back=back,
        lift=values["base_h"] - values["insertion"] - math.cos(back) * low,
    )
    return values
