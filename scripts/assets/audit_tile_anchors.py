"""Read-only audit of every delivered tile source and GLB (Blender background).

Prints JSON to stdout; writes no models, renders or project logs.
Checks actual evaluated geometry, not just anchor node names.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import closest_point_on_tri

ROOT = Path(__file__).resolve().parents[2]
TILES = ('forest', 'brick', 'stone', 'wheat', 'sheep', 'desert')
ANCHORS = {
    'anchor_number': ((-.55, -.72, 0), .50, .40),
    'anchor_robber': ((.70, -.83, 0), .34, 1.15),
}


def clip_height(polygon, height, above):
    """Clip to one horizontal half-space before testing the cylinder radius."""
    result = []
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        a_in = a.z >= height if above else a.z <= height
        b_in = b.z >= height if above else b.z <= height
        if a_in:
            result.append(a)
        if a_in != b_in:
            result.append(a.lerp(b, (height-a.z)/(b.z-a.z)))
    return result


def inspect(objects):
    errors, positions, triangles = [], {}, []
    names = {o.name: o for o in objects}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if obj.type != 'MESH':
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        world = [obj.matrix_world @ v.co for v in mesh.vertices]
        triangles.extend((obj.name, [world[i] for i in t.vertices]) for t in mesh.loop_triangles)
        evaluated.to_mesh_clear()
    for name, (target, radius, height) in ANCHORS.items():
        anchor = names.get(name)
        if anchor is None:
            errors.append(name + ': missing')
            continue
        pos = anchor.matrix_world.translation
        positions[name] = list(pos)
        if (pos - Vector(target)).length > 1e-5:
            errors.append(name + ': wrong position')
        if abs(anchor.get('clearance_radius', -1)-radius) > 1e-5 or abs(anchor.get('clearance_height', -1)-height) > 1e-5:
            errors.append(name + ': wrong clearance metadata')
        test = Vector((pos.x, pos.y, 0))
        collisions = set()
        support = False
        for obj_name, xyz in triangles:
            xy = [Vector((p.x, p.y, 0)) for p in xyz]
            distance = (closest_point_on_tri(test, *xy)-test).length
            if distance < 1e-5 and all(abs(p.z-pos.z) < 1e-5 for p in xyz):
                support = True
            if max(p.z for p in xyz) > pos.z+1e-5 and min(p.z for p in xyz) < pos.z+height and distance < radius-1e-5:
                clipped = clip_height(clip_height(xyz, pos.z+1e-5, True), pos.z+height, False)
                flat = [Vector((p.x, p.y, 0)) for p in clipped]
                if any((closest_point_on_tri(test, flat[0], flat[i], flat[i+1])-test).length < radius-1e-5 for i in range(1, len(flat)-1)):
                    collisions.add(obj_name)
        errors.extend(name + ': obstruction ' + n for n in sorted(collisions))
        if not support:
            errors.append(name + ': no flat ground at anchor')
    for name, xyz in triangles:
        if any(p.z > 1e-5 and max(p.x*math.cos(math.pi/6+i*math.pi/3)+p.y*math.sin(math.pi/6+i*math.pi/3) for i in range(6)) > 3*math.sqrt(3)/2-.28+1e-5 for p in xyz):
            errors.append(name + ': reserved edge strip')
            break
    return dict(anchors=positions, errors=errors, triangles=len(triangles))


def main():
    reports = []
    for tile in TILES:
        for kind in ('source', 'glb'):
            if kind == 'source':
                path = ROOT / 'assets' / (tile+'-tile') / 'model.blend'
                bpy.ops.wm.open_mainfile(filepath=str(path))
                objects = list(bpy.data.collections['ASSET_'+tile+'_tile'].all_objects)
            else:
                path = ROOT / 'assets' / (tile+'-tile') / 'model.glb'
                bpy.ops.wm.read_factory_settings(use_empty=True)
                bpy.ops.import_scene.gltf(filepath=str(path))
                objects = list(bpy.context.scene.objects)
            bpy.context.view_layer.update()
            report = dict(tile=tile, kind=kind, path=str(path.relative_to(ROOT)), **inspect(objects))
            reports.append(report)
            print('TILE_AUDIT', json.dumps(report), flush=True)
    if any(r['errors'] for r in reports):
        raise RuntimeError('Tile contract audit failed; see TILE_AUDIT output')
    print('TILE_AUDIT_PASS', len(reports), flush=True)


if __name__ == '__main__':
    main()
