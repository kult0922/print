"""Render the exported, printable meshes with Blender (no speculative geometry)."""
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from design import assembly_parameters
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, rgb, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = 0.35
    return mat


gold = material("Gold filament (single color)", (0.46, 0.25, 0.065), 0.45)
ivory = material("Ivory filament (single color)", (0.85, 0.81, 0.68))
floor = material("Backdrop", (0.055, 0.07, 0.09))


def load(part, mat):
    bpy.ops.wm.stl_import(filepath=str(ROOT / "output" / (part + ".stl")))
    obj = bpy.context.object
    obj.data.materials.append(mat)
    return obj


base = load("base", gold)
card = load("card", ivory)
design = assembly_parameters()
side, back, lift = design["side"], design["back"], design["lift"]
card.matrix_world = (
    Matrix.Translation((0, design["card_y"], lift))
    @ Matrix.Rotation(-back, 4, "X")
    @ Matrix.Rotation(-side, 4, "Y")
    @ Matrix.Rotation(math.pi / 2, 4, "X")
)

bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, -0.1))
bpy.context.object.data.materials.append(floor)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = False
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.world.color = (0.22, 0.22, 0.22)


def area(name, location, energy, size, target=(0, 0, 45)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.shape, data.size = energy, "DISK", size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


area("Key", (-100, -100, 210), 450000, 100)
area("Fill", (130, -40, 110), 180000, 90)
area("Rim", (10, 130, 180), 400000, 80)
camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
scene.collection.objects.link(camera)
height = max((obj.matrix_world @ Vector(v)).z for obj in (card, base) for v in obj.bound_box)
camera.location = (125, -235, height + 33)
target = Vector((0, 0, height / 2))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = max(159, height * 1.42)
scene.camera = camera
scene.view_settings.view_transform = "AgX"
scene.render.filepath = str(ROOT / "output" / "assembled.png")
bpy.ops.render.render(write_still=True)

# Show actual bed orientation: the card's back and the base's bottom are flat.
card.matrix_world = Matrix.Translation((0, 48, 0))
base.location = (0, -43, 0)
coupon = load("fit_test", gold)
coupon.location = (88, 10, 0)
camera.location = (155, -205, 260)
target = Vector((12, 5, 4))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.ortho_scale = 245
scene.render.filepath = str(ROOT / "output" / "parts.png")
bpy.ops.render.render(write_still=True)
