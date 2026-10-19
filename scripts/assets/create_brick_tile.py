"""Resource dioramas, using the approved forest hex and review studio.

Blender --background --python this_file -- --asset-type desert --review-dir /tmp/...
After Computer Use review repeat with --export. --check-glb reimports the GLB.
Only blend/GLB are delivered; all checks and renders require a temporary folder.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import closest_point_on_tri

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, help='Optional temporary draft .blend; defaults to canonical source')
parser.add_argument('--asset-type', choices=['brick', 'stone', 'wheat', 'sheep', 'desert'], default='brick')
parser.add_argument('--review-dir', required=True)
parser.add_argument('--export', action='store_true')
parser.add_argument('--check-glb', action='store_true')
parser.add_argument('--composition', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
ASSET_ID = args.asset_type + '-tile'
COLLECTION = 'ASSET_' + args.asset_type + '_tile'
FLOOR_NAME = 'terrain.clay-floor' if args.asset_type == 'brick' else 'terrain.' + args.asset_type + '-floor'
SOURCE = (args.source or ROOT / 'assets' / ASSET_ID / 'model.blend').resolve()
MODEL = ROOT / 'assets' / ASSET_ID / 'model.glb'
REVIEW = Path(args.review_dir).resolve()
if not str(REVIEW).startswith(('/private/tmp/', '/tmp/')):
    raise ValueError('Review output must be temporary, outside the project')
REVIEW.mkdir(parents=True, exist_ok=True)


def mat(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = 0.91
    bsdf.inputs['Specular IOR Level'].default_value = 0.16
    return m


def link(obj):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    ASSET.objects.link(obj)
    obj.parent = ROOT_OBJ
    return obj


def mesh(name, vertices, faces, materials, indices=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    for material in materials:
        data.materials.append(material)
    for p, index in zip(data.polygons, indices or [0] * len(faces)):
        p.material_index = index
    obj = bpy.data.objects.new(name, data)
    ASSET.objects.link(obj)
    obj.parent = ROOT_OBJ
    return obj


def box(name, pos, size, material, bevel=0.014, angle=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = link(bpy.context.object)
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        mod = obj.modifiers.new('soft-handmade-edges', 'BEVEL')
        mod.width, mod.segments = bevel, 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.rotation_euler.z = angle
    return obj


def build():
    global ASSET, ROOT_OBJ
    if SOURCE.exists():
        raise FileExistsError(f'Refusing to overwrite {SOURCE}')
    template = ROOT/'assets/forest-tile/model.blend'
    bpy.ops.wm.open_mainfile(filepath=str(template))
    ASSET = bpy.data.collections['ASSET_forest_tile']
    ASSET.name = COLLECTION
    ROOT_OBJ = bpy.data.objects['forest_tile']
    ROOT_OBJ.name = args.asset_type + '_tile'
    for obj in list(ASSET.objects):
        if obj.type == 'MESH' and not obj.name.startswith('terrain.'):
            bpy.data.objects.remove(obj, do_unlink=True)
    floor = bpy.data.objects['terrain.forest-floor']
    floor.name = FLOOR_NAME
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    if args.asset_type == 'desert':
        from desert_dune_geometry import build_quarry, ground_color
    elif args.asset_type == 'sheep':
        from sheep_pasture_geometry import build_quarry, ground_color
    elif args.asset_type == 'wheat':
        from wheat_field_geometry import build_quarry, ground_color
    elif args.asset_type == 'stone':
        from stone_quarry_geometry import build_quarry, ground_color
    else:
        from brick_quarry_geometry import build_quarry, ground_color
    bm=bmesh.new()
    bm.from_mesh(floor.data)
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True)
    bm.to_mesh(floor.data)
    bm.free()
    # Keep mounting circles flat and boundary exact; inherited topology is reused.
    for v in floor.data.vertices:
        v.co.z = 0
    colors = floor.data.color_attributes['COLOR_0']
    for p in floor.data.polygons:
        for idx in p.loop_indices:
            x,y,_ = floor.data.vertices[floor.data.loops[idx].vertex_index].co
            colors.data[idx].color = (*ground_color(x,y),1)
    # Each resource owns its silhouette; only contract and studio are shared.
    build_quarry(ASSET, ROOT_OBJ, mat, box, mesh, link)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.scene.camera = bpy.data.objects['review.board']
    bpy.context.scene.cycles.samples = 32
    SOURCE.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))


def check(assets, label):
    points, count, errors = [],0,[]
    for obj in assets:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        world = [obj.matrix_world @ v.co for v in obj.data.vertices]
        points.extend(world)
        count += len(obj.data.loop_triangles)
        is_floor=obj.name==FLOOR_NAME
        if obj.name.startswith('terrain.') and not is_floor:
            continue
        edge_points=[p for p in world if not is_floor or p.z>1e-6]
        if any(any(p.x*math.cos(math.pi/6+n*math.pi/3)+p.y*math.sin(math.pi/6+n*math.pi/3)>3*math.sqrt(3)/2-.28+1e-5 for n in range(6)) for p in edge_points):
            errors.append(obj.name+': reserved edge strip')
        for name,r,h in [('anchor_number',.50,.40),('anchor_robber',.34,1.15)]:
            anchor = bpy.data.objects[name].matrix_world.translation
            test = Vector((anchor.x,anchor.y,0))
            for tri in obj.data.loop_triangles:
                xyz = [world[v] for v in tri.vertices]
                if max(p.z for p in xyz)<=anchor.z+1e-6 or min(p.z for p in xyz)>anchor.z+h:
                    continue
                xy = [Vector((p.x,p.y,0)) for p in xyz]
                if (closest_point_on_tri(test,*xy)-test).length < r-1e-5:
                    errors.append(obj.name+': '+name)
                    break
    bounds = [[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
    anchors = {n:list(bpy.data.objects[n].matrix_world.translation) for n in ['anchor_number','anchor_robber']}
    assert all(abs(anchors[n][i]-target[i])<1e-5 for n,target in [('anchor_number',(-.55,-.72,0)),('anchor_robber',(.70,-.83,0))] for i in range(3))
    assert not [o for o in assets if o.type in {'CAMERA','LIGHT'}]
    report = dict(stage=label,errors=errors,bounds_blender=bounds,triangles=count,
                  mesh_objects=sum(o.type=='MESH' for o in assets),
                  unique_meshes=len({o.data.name for o in assets if o.type=='MESH'}),
                  materials=len({m.name for o in assets if o.type=='MESH' for m in o.data.materials}),anchors=anchors)
    (REVIEW/(label+'-check.json')).write_text(json.dumps(report,indent=2))
    print(args.asset_type.upper()+'_CHECK',json.dumps(report))
    if errors:
        raise RuntimeError(errors)


def render(name, camera='board'):
    scene = bpy.context.scene
    scene.camera = bpy.data.objects['review.'+camera]
    scene.render.filepath = str(REVIEW/(name+'.png'))
    bpy.ops.render.render(write_still=True)


def composition():
    # Temporary test attachments, never saved into the source or exported.
    ivory = mat('TEST.ivory',(.69,.57,.36))
    charcoal = mat('TEST.charcoal',(.048,.058,.065))
    number = bpy.data.objects['anchor_number'].matrix_world.translation
    robber = bpy.data.objects['anchor_robber'].matrix_world.translation
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.46,depth=.075,
                                      location=(number.x,number.y,.0375))
    bpy.context.object.data.materials.append(ivory)
    bpy.ops.object.text_add(location=(number.x,number.y,.079))
    text = bpy.context.object
    text.data.body = '8'
    text.data.align_x = text.data.align_y = 'CENTER'
    text.data.size, text.data.extrude = .5,.001
    text.data.materials.append(charcoal)
    bpy.ops.mesh.primitive_cone_add(vertices=48,radius1=.23,radius2=.11,depth=.58,
                                   location=(robber.x,robber.y,.29))
    bpy.context.object.data.materials.append(charcoal)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.16,
                                        location=(robber.x,robber.y,.71))
    bpy.context.object.data.materials.append(charcoal)
    render('composition')
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/forest-tile/model.glb'))
    for obj in bpy.context.selected_objects:
        if obj.parent is None:
            obj.location += Vector((4.5,3*math.sqrt(3)/2,0))
    camera = bpy.data.objects['review.board']
    camera.location += Vector((1.7,.9,0))
    camera.data.ortho_scale = 12.5
    render('forest-neighbor')
    if args.asset_type in {'stone', 'wheat', 'sheep', 'desert'}:
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/brick-tile/model.glb'))
        for obj in bpy.context.selected_objects:
            if obj.parent is None:
                obj.location += Vector((-4.5,3*math.sqrt(3)/2,0))
        camera.location -= Vector((1.7,0,0))
        camera.data.ortho_scale = 18
        render('resource-family')
    if args.asset_type in {'wheat', 'sheep', 'desert'}:
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/stone-tile/model.glb'))
        for obj in bpy.context.selected_objects:
            if obj.parent is None:
                obj.location += Vector((0,6*math.sqrt(3)/2,0))
        camera.location += Vector((0,1,0))
        camera.data.ortho_scale = 19
        render('four-resource-family')
    if args.asset_type in {'sheep', 'desert'}:
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/wheat-tile/model.glb'))
        for obj in bpy.context.selected_objects:
            if obj.parent is None:
                obj.location += Vector((-4.5,-3*math.sqrt(3)/2,0))
        camera.data.ortho_scale = 23
        render('five-resource-family')
    if args.asset_type == 'desert':
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/sheep-tile/model.glb'))
        for obj in bpy.context.selected_objects:
            if obj.parent is None:
                obj.location += Vector((4.5,-3*math.sqrt(3)/2,0))
        render('six-resource-family')


if args.export or args.check_glb or args.composition:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
else:
    build()
ASSET = bpy.data.collections[COLLECTION]
bpy.context.view_layer.update()
if args.export:
    check(list(ASSET.objects),'source')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in ASSET.objects:
        obj.select_set(True)
    MODEL.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(MODEL),export_format='GLB',use_selection=True,
                             export_yup=True,export_extras=True,export_cameras=False,export_lights=False)
elif args.check_glb:
    for obj in list(ASSET.objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(MODEL))
    assets = list(bpy.context.selected_objects)
    bpy.context.view_layer.update()
    check(assets,'glb')
    bpy.ops.wm.save_as_mainfile(filepath=str(REVIEW/'glb-review.blend'))
    render('glb-board')
elif args.composition:
    composition()
else:
    check(list(ASSET.objects),'source')
    for name in ['board','close','side']:
        render(name,name)
