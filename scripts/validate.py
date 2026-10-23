"""Check printable STL topology and record dimensions. Requires numpy, trimesh."""
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix, translation_matrix
from design import assembly_parameters

ROOT = Path(__file__).resolve().parents[1]
report = {"units": "mm", "build_volume_mm": [180, 180, 180], "parts": {}}
meshes = {}
for name in ("base", "card", "fit_test", "text_test"):
    mesh = trimesh.load_mesh(ROOT / "output" / f"{name}.stl")
    assert mesh.is_watertight and mesh.is_winding_consistent, name
    assert len(mesh.split()) == 1 and mesh.volume > 0, name
    assert np.all(mesh.extents < 180) and abs(mesh.bounds[0, 2]) < 0.001, name
    meshes[name] = mesh
    report["parts"][name] = {
        "size_mm": mesh.extents.round(3).tolist(),
        "watertight": True,
        "connected_solids": 1,
        "consistent_winding": True,
        "volume_mm3": round(mesh.volume, 2),
    }

design = assembly_parameters()
side, back = design["side"], design["back"]
matrix = (
    translation_matrix([0, design["card_y"], design["lift"]])
    @ rotation_matrix(-back, [1, 0, 0])
    @ rotation_matrix(-side, [0, 1, 0])
    @ rotation_matrix(math.pi / 2, [1, 0, 0])
)
card = meshes["card"].copy()
card.apply_transform(matrix)
base = meshes["base"]
report["assembled_size_mm"] = (
    np.maximum(card.bounds[1], base.bounds[1]) - np.minimum(card.bounds[0], base.bounds[0])
).round(3).tolist()
source = (ROOT / "models" / "nikko_trophy.scad").read_text()
with tempfile.TemporaryDirectory(prefix="nikko-fit-") as temporary:
    check = Path(temporary) / "intersection.scad"
    check.write_text(
        source[:source.index('if (part == "card")')]
        + "intersection() { base(); mounted_card() card(); }\n"
    )
    result = subprocess.run(
        ["openscad", "-o", str(Path(temporary) / "intersection.stl"), str(check)],
        text=True, capture_output=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=120,
    )
    # OpenSCAD reports an intentionally empty STL with exit 1.
    assert result.returncode == 1 and "Current top level object is empty." in result.stderr, result.stderr
    assert "ERROR:" not in result.stderr, result.stderr
    report["assembly_solid_intersection"] = "empty (OpenSCAD intersection check)"
report["sliced_in_bambu_studio"] = False
report["physically_printed"] = False
out = ROOT / "output" / "validation.json"
out.write_text(json.dumps(report, indent=2) + "\n")
print(out.read_text())
