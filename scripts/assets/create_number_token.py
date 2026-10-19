"""Build a reusable blank token; numerals/pips exist only in temporary reviews.

Blender --background --python-exit-code 1 --python scripts/assets/create_number_token.py
    -- --work-dir /private/tmp/... --mode build|export|composition
Canonical delivery is manual after Computer Use review. No game code is changed.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--mode', choices=['build', 'export', 'composition'], default='build')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
WORK = args.work_dir.resolve()
if not str(WORK).startswith(('/private/tmp/', '/tmp/')):
    raise ValueError('Use a project-external temporary directory')
WORK.mkdir(parents=True, exist_ok=True)
SOURCE = WORK / 'model.blend'


def material(name, rgb, rough=.78, metal=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Specular IOR Level'].default_value = .25
    return mat


def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def move(obj, col):
    for prior in list(obj.users_collection):
        prior.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def lathe(name, profile, mat, col):
    n = 96
    verts = [(r * math.cos(i * math.tau / n), r * math.sin(i * math.tau / n), z)
             for r, z in profile for i in range(n)]
    faces = [(j*n+i, j*n+(i+1)%n, (j+1)*n+(i+1)%n, (j+1)*n+i)
             for j in range(len(profile)-1) for i in range(n)]
    faces.extend([tuple(reversed(range(n))), tuple((len(profile)-1)*n+i for i in range(n))])
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    data.materials.append(mat)
    for poly in data.polygons:
        # Flat annuli retain a clean face; the rounded edge is smoothly shaded.
        poly.use_smooth = abs(poly.normal.z) < .999
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    col = collection('REVIEW_ONLY')
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.006))
    ground = move(bpy.context.object, col)
    ground.name = 'review.ground'
    ground.data.materials.append(material('review.grey', (.28,.30,.29)))
    for name, pos, energy, size in [('key',(-3,-4,6),450,4),('fill',(4,-1,3),220,3),('rim',(1,3,5),400,3)]:
        data = bpy.data.lights.new('review.'+name, 'AREA')
        data.energy, data.size = energy, size
        obj = bpy.data.objects.new(data.name, data)
        col.objects.link(obj)
        obj.location = pos
        aim(obj, (0,0,0))
    for name, pos, zoom in [('close',(0,-2,3),1.28),('board',(0,-3,3),1.55),('side',(0,-3,.8),1.35),('top',(0,0,4),1.25)]:
        data = bpy.data.cameras.new('review.'+name)
        data.type, data.ortho_scale = 'ORTHO', zoom
        obj = bpy.data.objects.new(data.name, data)
        col.objects.link(obj)
        obj.location = pos
        aim(obj, (0,0,.045))
    scene = bpy.context.scene
    scene.camera = bpy.data.objects['review.close']
    scene.world = bpy.data.worlds.new('review.neutral')
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (.5,.55,.60,1)
    bg.inputs[1].default_value = .35
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'


def render(camera, filename):
    scene = bpy.context.scene
    scene.camera = bpy.data.objects['review.'+camera]
    scene.render.filepath = str(WORK / (filename+'.png'))
    bpy.ops.render.render(write_still=True)


def check(objects, stage):
    points, triangles, mats = [], 0, set()
    for obj in objects:
        if obj.type != 'MESH':
            continue
        points.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
        mats.update(m.name for m in obj.data.materials if m)
        assert all(math.isfinite(c) for v in obj.data.vertices for c in v.normal)
    radius = max(math.hypot(p.x,p.y) for p in points)
    low, high = min(p.z for p in points), max(p.z for p in points)
    assert radius <= .5 and abs(low) < 1e-5 and high <= .4
    assert not any(o.type in {'CAMERA','LIGHT','FONT'} for o in objects)
    assert not any('TEST_ONLY' in o.name or 'review.' in o.name for o in objects)
    anchors = {o.name: list(o.matrix_world.translation) for o in objects if o.name.startswith('anchor_')}
    assert set(anchors) == {'anchor_content','anchor_probability'}
    assert (Vector(anchors['anchor_content'])-Vector((0,.055,.1015))).length < 1e-5
    assert (Vector(anchors['anchor_probability'])-Vector((0,-.245,.1015))).length < 1e-5
    report = dict(radius=radius,z_min=low,z_max=high,triangles=triangles,materials=len(mats),anchors=anchors)
    (WORK / (stage+'-check.json')).write_text(json.dumps(report,indent=2))
    print('TOKEN_CHECK', stage, json.dumps(report))


def build():
    if SOURCE.exists():
        raise FileExistsError('Use a fresh temporary directory for another revision')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    col = collection('ASSET_number-token')
    walnut = material('token.walnut', (.135,.071,.033))
    trim = material('token.muted-brass', (.40,.235,.085), .65, .25)
    ivory = material('token.warm-ivory', (.79,.70,.49), .88)
    lathe('token.turned-walnut',[(.452,0),(.466,.006),(.477,.019),(.478,.035),(.472,.052),(.457,.071),(.446,.081),(.425,.083)],walnut,col)
    lathe('token.fine-brass-rim',[(.413,.078),(.434,.078),(.438,.086),(.434,.096),(.427,.101),(.416,.101),(.411,.096),(.413,.078)],trim,col)
    lathe('token.ivory-inlay',[(.409,.071),(.413,.080),(.412,.093),(.406,.100)],ivory,col)
    # One reusable mesh, separate material slots; no numeral geometry in this asset.
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = col.objects[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = 'number-token.body'
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    root = bpy.data.objects.new('number-token', None)
    col.objects.link(root)
    root['asset_id'], root['contract'] = 'number-token','number-token-v1'
    root['clearance_radius'], root['clearance_height'] = .5,.4
    body.parent = root
    for name, pos, width, height in [('anchor_content',(0,.055,.1015),.60,.42),('anchor_probability',(0,-.245,.1015),.34,.045)]:
        anchor = bpy.data.objects.new(name,None)
        col.objects.link(anchor)
        anchor.parent, anchor.location = root,pos
        anchor['max_width'],anchor['max_height'] = width,height
        anchor['normal_blender'],anchor['up_blender'] = '+Z','+Y'
    bpy.context.view_layer.update()
    studio()
    check(list(col.objects),'source')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    render('close','blank-close')
    render('side','blank-side')
    review_labels()


def label(value, offset=(0,0,0)):
    """Temporary readable content; never exported or saved in canonical source."""
    before = set(bpy.data.objects)
    ink = material('TEST_ONLY.red' if value in (6,8) else 'TEST_ONLY.ink', (.40,.030,.017) if value in (6,8) else (.036,.026,.017))
    bpy.ops.object.text_add()
    text = bpy.context.object
    text.name = 'TEST_ONLY.number'
    text.data.body = str(value)
    font = Path('/System/Library/Fonts/Supplemental/Georgia Bold.ttf')
    if font.exists():
        text.data.font = bpy.data.fonts.load(str(font), check_existing=True)
    text.data.extrude = .0007
    text.data.resolution_u = 10
    text.data.materials.append(ink)
    bpy.context.view_layer.update()
    coords = [Vector(v) for v in text.bound_box]
    lo = Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    scale = min(.60/(hi.x-lo.x), .42/(hi.y-lo.y))
    text.scale = (scale,scale,1)
    text.location = Vector(offset)+Vector((-(lo.x+hi.x)*scale/2,.055-(lo.y+hi.y)*scale/2,.1015))
    # Standard two-dice likelihood marks; 1/7 are custom previews without pips.
    pips = {2:1,3:2,4:3,5:4,6:5,8:5,9:4,10:3,11:2,12:1}.get(value,0)
    for i in range(pips):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.020,depth=.0015,location=Vector(offset)+Vector(((i-(pips-1)/2)*.066,-.245,.1015)))
        obj = bpy.context.object
        obj.name = 'TEST_ONLY.probability'
        obj.data.materials.append(ink)
    return list(set(bpy.data.objects)-before)


def remove(objects):
    for obj in objects:
        bpy.data.objects.remove(obj,do_unlink=True)


def review_labels():
    labels = label(8)
    render('close','label-close')
    render('board','label-board')
    render('side','label-side')
    remove(labels)
    body = bpy.data.objects['number-token.body']
    body.hide_render = True
    for number in range(1,13):
        offset = ((number-1)%4*1.12-1.68, 1.15-(number-1)//4*1.15, 0)
        obj = bpy.data.objects.new('TEST_ONLY.base',body.data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = offset
        label(number,offset)
    cam = bpy.data.objects['review.top']
    cam.data.ortho_scale = 4.65
    bpy.context.scene.render.resolution_x = 1400
    bpy.context.scene.render.resolution_y = 1100
    render('top','numbers-1-12')


def export():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    objects = list(bpy.data.collections['ASSET_number-token'].objects)
    check(objects,'pre-export')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(WORK/'number-token.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    remove(objects)
    bpy.ops.import_scene.gltf(filepath=str(WORK/'number-token.glb'))
    bpy.context.view_layer.update()
    check(list(bpy.context.selected_objects),'glb')
    render('close','glb-blank-close')
    label(8)
    render('close','glb-label-close')


def composition():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    remove(list(bpy.data.collections['ASSET_number-token'].objects))
    bpy.ops.import_scene.gltf(filepath=str(WORK/'number-token.glb'))
    token = next(o for o in bpy.context.selected_objects if o.parent is None)
    token.location = (-.55,-.72,0)
    labels = label(8,token.location)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/robber/model.glb'))
    robber = next(o for o in bpy.context.selected_objects if o.parent is None)
    robber.location = (.70,-.83,0)
    bpy.data.objects['review.ground'].location.z = -.307
    cam = bpy.data.objects['review.board']
    cam.location = (2,-10,12)
    aim(cam,(0,0,.35))
    cam.data.ortho_scale = 7.4
    for obj in bpy.data.collections['REVIEW_ONLY'].objects:
        if obj.type == 'LIGHT':
            obj.location *= 3
            obj.data.energy *= 9
            obj.data.size *= 3
    report = []
    for tile in ['forest','brick','stone','wheat','sheep','desert']:
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets'/f'{tile}-tile'/'model.glb'))
        objects = list(bpy.context.selected_objects)
        bpy.context.view_layer.update()
        for name, root in [('anchor_number',token),('anchor_robber',robber)]:
            anchor = next(o for o in objects if o.name == name)
            assert (anchor.matrix_world.translation-root.location).length < 1e-5
        render('board','mount-'+tile)
        if tile == 'forest':
            remove(labels)
            render('board','forest-without-number')
            labels = label(12,token.location)
            render('board','forest-number-12')
            remove(labels)
            labels = label(8,token.location)
        report.append(dict(tile=tile,same_anchor_transform=True))
        remove(objects)
    (WORK/'mount-check.json').write_text(json.dumps(report,indent=2))


if args.mode == 'build':
    build()
elif args.mode == 'export':
    export()
else:
    composition()
