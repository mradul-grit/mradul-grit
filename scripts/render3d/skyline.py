"""Render the hero's 3D contribution skyline with Blender (bpy).

    python scripts/render3d/skyline.py --data data.json --out skyline.webp [--samples 48]

Each column is one day of the last 26 weeks of the real contribution calendar
(data.json comes from `build --dump-data`). Height grows with the day's count
on a square-root scale so one huge day doesn't flatten the rest. Empty days are
flat dark tiles. The render has a transparent background so the hero SVG can
place it over its own backdrop.

Needs the `bpy` package (Blender as a Python module). Cycles on the CPU, so it
runs on a GitHub-hosted runner without a GPU.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date, timedelta

import bpy

CYAN = (0.133, 0.827, 0.933)
VIOLET = (0.655, 0.545, 0.980)
TILE = (0.055, 0.075, 0.115)
WEEKS = 26  # keep in sync with SKYLINE_WEEKS in scripts/profile_cards/build.py (a test checks)
STEP = 1.0  # grid pitch
SIZE = 0.82  # column footprint
MAX_H = 6.0  # height of the busiest day


def load_grid(path: str, weeks: int = WEEKS) -> list[tuple[int, int, int]]:
    """(week, weekday, count) for the last `weeks` weeks, Sunday-first like GitHub."""
    with open(path, encoding="utf-8") as fh:
        days = {d["date"]: d["count"] for d in json.load(fh)["calendar"]}
    end = date.fromisoformat(max(days)) if days else date.today()
    start = end - timedelta(days=(end.weekday() + 1) % 7 + weeks * 7)
    out, d, col = [], start, 0
    while d <= end:
        row = (d.weekday() + 1) % 7
        if row == 0 and d != start:
            col += 1
        out.append((col, row, days.get(d.isoformat(), 0)))
        d += timedelta(days=1)
    return out


def material(name: str, color, strength: float, rough: float = 0.35):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def build_scene(grid: list[tuple[int, int, int]]) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    peak = max([c for _, _, c in grid] or [1]) or 1
    cols = max(w for w, _, _ in grid) + 1

    tile_mat = material("tile", TILE, 0.0, 0.6)
    # A small ramp of emissive materials: low days cyan, the busiest days violet.
    ramp = []
    for i in range(6):
        t = i / 5
        color = tuple(CYAN[k] * (1 - t) + VIOLET[k] * t for k in range(3))
        ramp.append(material(f"col{i}", color, 0.12 + 0.55 * t))

    for week, weekday, count in grid:
        x = (week - cols / 2) * STEP
        y = (weekday - 3) * STEP
        if count == 0:
            h, mat = 0.08, tile_mat
        else:
            f = math.sqrt(count / peak)
            h = 0.25 + MAX_H * f
            mat = ramp[min(5, int(f * 6))]
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2))
        ob = bpy.context.active_object
        ob.scale = (SIZE, SIZE, h)
        ob.data.materials.append(mat)
        bev = ob.modifiers.new("bevel", "BEVEL")
        bev.width, bev.segments = 0.04, 2

    # Base plate catches the glow.
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    plate = bpy.context.active_object
    plate.scale = (cols * STEP + 2, 7 * STEP + 2, 1)
    plate.data.materials.append(material("plate", (0.03, 0.04, 0.07), 0.0, 0.25))

    # Camera: orthographic, so all 53 weeks stay the same size and the whole
    # year fits the frame. Viewed from the front-right, oldest weeks at the left.
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = cols * 1.0
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (22.0, -34.0, 20.0)
    target = bpy.data.objects.new("target", None)
    target.location = (0.0, 0.0, 2.6)
    scene.collection.objects.link(target)
    track = cam.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    scene.camera = cam

    # Cool key light and a faint violet rim; the emissive columns do the rest.
    for name, loc, energy, color in [("key", (12, -20, 30), 900, (0.75, 0.9, 1.0)),
                                     ("rim", (-30, 14, 12), 700, VIOLET)]:
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.color, light.size = energy, color, 12
        ob = bpy.data.objects.new(name, light)
        ob.location = loc
        scene.collection.objects.link(ob)
        c = ob.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"

    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.01, 0.012, 0.02, 1)
    scene.world = world


def render(out: str, samples: int, width: int, height: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.view_settings.view_transform = "Standard"  # AgX washes saturated emission out to white
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.quality = 82
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--samples", type=int, default=48)
    p.add_argument("--width", type=int, default=1400)
    p.add_argument("--height", type=int, default=640)
    a = p.parse_args()
    build_scene(load_grid(a.data))
    render(a.out, a.samples, a.width, a.height)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
