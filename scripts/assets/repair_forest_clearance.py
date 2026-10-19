"""Repair only the forest floor; keep drafts, recovery and renders temporary.

Blender --background --python this_file -- --work-dir /private/tmp/... [--export]
Prepare -> Computer Use review -> export -> review -> promote verified pair.
"""
import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_tile_anchors import inspect

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--export', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
work = args.work_dir.resolve()
if not str(work).startswith(('/private/tmp/', '/tmp/')):
    raise ValueError('Use a temporary work directory')
work.mkdir(parents=True, exist_ok=True)
source = ROOT/'assets/forest-tile/model.blend'
runtime = ROOT/'assets/forest-tile/model.glb'
draft = work/'model.blend'


def render(name, camera='board'):
    scene = bpy.context.scene
    scene.camera = bpy.data.objects['review.'+camera]
    scene.render.filepath = str(work/(name+'.png'))
    bpy.ops.render.render(write_still=True)


if not args.export:
    if draft.exists():
        raise FileExistsError('Choose a new temporary work directory')
    shutil.copy2(source, work/'before.blend')
    shutil.copy2(runtime, work/'before.glb')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    assets = list(bpy.data.collections['ASSET_forest_tile'].all_objects)
    before = inspect(assets)
    render('before-board')
    floor = bpy.data.objects['terrain.forest-floor']
    floor.data.calc_loop_triangles()
    # Extra support radius covers a complete triangle, not only its vertices.
    edge = max((floor.data.vertices[t.vertices[i]].co.xy-floor.data.vertices[t.vertices[(i+1)%3]].co.xy).length
               for t in floor.data.loop_triangles for i in range(3))
    changed, max_change = 0, 0
    for vertex in floor.data.vertices:
        x, y, z = vertex.co
        factor = 1
        for name in ('anchor_number', 'anchor_robber'):
            anchor = bpy.data.objects[name]
            radius = anchor['clearance_radius']
            t = max(0, min(1, (math.hypot(x-anchor.location.x, y-anchor.location.y)-radius-edge-.002)/.12))
            factor = min(factor, t*t*(3-2*t))
        vertex.co.z = z*factor
        if abs(vertex.co.z-z) > 1e-8:
            changed += 1
            max_change = max(max_change, abs(vertex.co.z-z))
    floor.data.update()
    bpy.context.view_layer.update()
    after = inspect(assets)
    report = dict(before=before, after=after, max_triangle_edge=edge,
                  changed_floor_vertices=changed, max_height_change=max_change)
    print('FOREST_REPAIR', json.dumps(report), flush=True)
    (work/'repair-check.json').write_text(json.dumps(report, indent=2))
    if after['errors']:
        raise RuntimeError(after['errors'])
    bpy.ops.wm.save_as_mainfile(filepath=str(draft))
    for camera in ('board', 'close', 'side'):
        render('after-'+camera, camera)
else:
    bpy.ops.wm.open_mainfile(filepath=str(draft))
    assets = list(bpy.data.collections['ASSET_forest_tile'].all_objects)
    report = inspect(assets)
    if report['errors']:
        raise RuntimeError(report['errors'])
    bpy.ops.object.select_all(action='DESELECT')
    for obj in assets:
        obj.select_set(True)
    model = work/'forest-tile.glb'
    bpy.ops.export_scene.gltf(filepath=str(model), export_format='GLB', use_selection=True,
                             export_yup=True, export_extras=True, export_cameras=False, export_lights=False)
    for obj in assets:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(model))
    bpy.context.view_layer.update()
    report = inspect(list(bpy.context.selected_objects))
    print('FOREST_REIMPORT', json.dumps(report), flush=True)
    if report['errors']:
        raise RuntimeError(report['errors'])
    bpy.ops.wm.save_as_mainfile(filepath=str(work/'glb-review.blend'))
    render('glb-board')
