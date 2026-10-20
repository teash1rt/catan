"""制作、视觉评审、导出并组合可换色的中世纪道路。

Blender --background --python-exit-code 1 --python scripts/assets/create_road.py
    -- --work-dir /private/tmp/... --mode build|export|composition
草稿和评审证据保留在临时目录，通过 Computer Use 视觉评审后再归档。
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--mode', choices=['build', 'export', 'composition'], default='build')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
WORK = args.work_dir.resolve()
if not str(WORK).startswith(('/private/tmp/', '/tmp/')):
    raise ValueError('Use a project-external temporary directory')
WORK.mkdir(parents=True, exist_ok=True)
COLORS = {'blue': (.024,.085,.22), 'red': (.43,.055,.033),
          'ivory': (.74,.63,.40), 'orange': (.72,.235,.032)}


def tint(mat, color):
    mat.diffuse_color = (*color,1)
    next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(*color,1)


def material(name, color, rough=.84):
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    tint(mat,color)
    node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    node.inputs['Roughness'].default_value=rough
    node.inputs['Specular IOR Level'].default_value=.23
    return mat


def collection(name):
    col=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col)
    return col


def move(obj,col):
    for old in list(obj.users_collection): old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def box(name, center, size, mat, col, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj=move(bpy.context.object,col); obj.name=name; obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod=obj.modifiers.new('subtle worn arris','BEVEL'); mod.width=bevel; mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def studio():
    col=collection('REVIEW_ONLY')
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.001))
    obj=move(bpy.context.object,col); obj.name='review.ground'
    obj.data.materials.append(material('review.neutral',(.24,.27,.28)))
    for name,pos,energy,size in [('key',(-3,-4,6),450,4),('fill',(4,-1,3),210,3),('rim',(1,3,5),350,3)]:
        data=bpy.data.lights.new('review.'+name,'AREA'); data.energy=energy; data.size=size
        obj=bpy.data.objects.new(data.name,data); col.objects.link(obj); obj.location=pos; aim(obj,(0,0,0))
    for name,pos,scale in [('close',(2,-3,3),2.85),('side',(.8,-4,.8),2.85),('top',(0,0,4),2.85),('board',(1,-3,4),3.65)]:
        data=bpy.data.cameras.new('review.'+name); data.type='ORTHO'; data.ortho_scale=scale
        obj=bpy.data.objects.new(data.name,data); col.objects.link(obj); obj.location=pos; aim(obj,(0,0,.035))
    scene=bpy.context.scene; scene.camera=bpy.data.objects['review.close']
    scene.world=bpy.data.worlds.new('review.world'); scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.55,.6,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.38
    scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.use_denoising=True
    scene.render.resolution_x=1400; scene.render.resolution_y=800; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'


def render(name,camera='close'):
    scene=bpy.context.scene; scene.camera=bpy.data.objects['review.'+camera]
    scene.render.filepath=str(WORK/(name+'.png')); bpy.ops.render.render(write_still=True)


def check(objects,label):
    points=[]; tris=0; mats=set()
    for obj in objects:
        assert obj.type not in {'CAMERA','LIGHT','FONT'}
        assert not obj.name.startswith('review.')
        if obj.type!='MESH': continue
        data=obj.data; data.calc_loop_triangles(); tris+=len(data.loop_triangles)
        points.extend(obj.matrix_world@v.co for v in data.vertices)
        mats.update(m.name for m in data.materials if m)
        assert all(math.isfinite(c) for v in data.vertices for c in v.co)
        assert all(math.isfinite(c) for v in data.vertices for c in v.normal)
    low=[min(p[i] for p in points) for i in range(3)]
    high=[max(p[i] for p in points) for i in range(3)]
    assert low[0]>=-1.20001 and high[0]<=1.20001
    assert low[1]>=-.18001 and high[1]<=.18001
    assert abs(low[2])<1e-6 and high[2]<=.09
    # 使用保守的端面边界，确保整个三角面都避开端点建筑的圆形净空区。
    assert 1.5-max(abs(low[0]),abs(high[0]))>=.28
    assert 'player_color' in mats
    anchors={o.name:list(o.matrix_world.translation) for o in objects if o.name.startswith('anchor_')}
    for name,expected in [('anchor_edge_a',(-1.5,0,0)),('anchor_edge_b',(1.5,0,0))]:
        assert (Vector(anchors[name])-Vector(expected)).length<1e-6
    result=dict(bounds=[low,high],triangles=tris,materials=sorted(mats),anchors=anchors,
                nominal_edge_length=3,end_clearance=.30,half_width=.18)
    (WORK/(label+'-check.json')).write_text(json.dumps(result,indent=2)); print('ROAD_CHECK',label,json.dumps(result))


def build():
    source=WORK/'model.blend'
    if source.exists(): raise FileExistsError('Use a new temporary directory for revisions')
    bpy.ops.wm.read_factory_settings(use_empty=True); col=collection('ASSET_road')
    player=material('player_color',COLORS['blue']); player['role']='player_color'
    stone=material('road.warm-limestone',(.46,.42,.33))
    pale=material('road.light-limestone',(.54,.49,.38))
    shade=material('road.ochre-stone',(.39,.345,.265))
    mortar=material('road.earth-mortar',(.21,.17,.115))
    wood=material('road.dark-oak',(.14,.064,.024))
    # 薄接触底座配合修整侧边与略微拱起的卵石路面。
    box('road.mortar-bed',(0,0,.018),(2.40,.36,.036),mortar,col,.008)
    for s in [-1,1]:
        box('road.oak-bound-edge',(0,s*.166,.029),(2.385,.023,.033),wood,col,.004)
    rng=random.Random(73)
    for row in range(3):
        y=(row-1)*.077
        boundaries=[-1.187]
        step=.174
        x=-1.187+step*(.50 if row==1 else 1)
        while x<1.15:
            boundaries.append(x); x+=step
        boundaries.append(1.187)
        for i,(a,b) in enumerate(zip(boundaries,boundaries[1:])):
            top=.054+(1-abs(row-1))*.005+rng.uniform(-.002,.002)
            mat=rng.choices([stone,pale,shade],[6,3,1])[0]
            obj=box('road.sett.%d.%d'%(row,i),((a+b)/2,y,(top+.025)/2),(b-a-.008,.073,top-.025),mat,col,.005)
            obj.rotation_euler.z=rng.uniform(-.016,.016)
    for side in [-1,1]:
        for i in range(14):
            x=-1.20+(i+.5)*2.4/14
            box('road.player-dressed-curb',(x,side*.141,.052),(2.4/14-.006,.053,.044),player,col,.004)
    root=bpy.data.objects.new('road',None); col.objects.link(root)
    root['asset_id']='road'; root['contract']='edge-road-v1'; root['nominal_edge_length']=3.0
    root['length']=2.4; root['width']=.36; root['end_clearance']=.30
    root['player_color_material']='player_color'; root['length_axis']='+X'
    for obj in col.objects:
        if obj!=root:
            obj.parent=root
            bpy.context.view_layer.objects.active=obj
            bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
            bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    for name,x in [('anchor_edge_a',-1.5),('anchor_edge_b',1.5)]:
        obj=bpy.data.objects.new(name,None); col.objects.link(obj); obj.parent=root; obj.location=(x,0,0)
        obj['role']='logical_vertex_not_mesh_end'
    bpy.context.view_layer.update(); check(list(col.objects),'source')
    studio(); bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    for camera in ['close','side','top','board']: render('road-'+camera,camera)


def import_asset(path):
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(path))
    objects=set(bpy.data.objects)-before
    roots=[o for o in objects if o.parent not in objects]; assert len(roots)==1
    return roots[0],objects


def export():
    bpy.ops.wm.open_mainfile(filepath=str(WORK/'model.blend'))
    col=bpy.data.collections['ASSET_road']
    for colored in [False,True]:
        items=[o for o in col.objects if o.type=='MESH' and any(m.name=='player_color' for m in o.data.materials)==colored]
        bpy.ops.object.select_all(action='DESELECT')
        for obj in items: obj.select_set(True)
        bpy.context.view_layer.objects.active=items[0]; bpy.ops.object.join()
        obj=bpy.context.object; obj.name='road.player' if colored else 'road.body'
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col.objects: obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(WORK/'road.glb'),export_format='GLB',use_selection=True,
                             export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    for obj in list(col.objects): bpy.data.objects.remove(obj,do_unlink=True)
    for data in list(bpy.data.meshes):
        if data.users==0: bpy.data.meshes.remove(data)
    for mat in list(bpy.data.materials):
        if mat.users==0: bpy.data.materials.remove(mat)
    root,objects=import_asset(WORK/'road.glb'); check(objects,'glb'); render('road-glb')
    base_mat=next(m for m in bpy.data.materials if m.name=='player_color')
    original=tuple(base_mat.diffuse_color); root.location.y=-.81
    for index,color in enumerate(['red','ivory','orange'],start=1):
        copies={old:old.copy() for old in objects}
        for old,new in copies.items():
            bpy.context.scene.collection.objects.link(new)
            new.parent=copies.get(old.parent)
            if old==root: new.location.y=-.81+index*.54
            if new.type=='MESH':
                for slot in new.material_slots:
                    if slot.material==base_mat:
                        slot.link='OBJECT'; slot.material=base_mat.copy(); tint(slot.material,COLORS[color])
    assert tuple(base_mat.diffuse_color)==original
    cam=bpy.data.objects['review.close']; cam.location=(2,-3,5); aim(cam,(0,0,.03)); cam.data.ortho_scale=3.8
    bpy.context.scene.render.resolution_y=1100
    render('road-colors')
    (WORK/'color-check.json').write_text(json.dumps({'colors':list(COLORS),'original_unchanged':True,'geometry_shared':True},indent=2))


def composition():
    bpy.ops.wm.read_factory_settings(use_empty=True); studio()
    model_dir=ROOT/'assets'
    centers=[(-3,0),(1.5,3*math.sqrt(3)/2),(1.5,-3*math.sqrt(3)/2)]
    for kind,xy in zip(['forest','wheat','sheep'],centers):
        root,_=import_asset(model_dir/(kind+'-tile')/'model.glb'); root.location=(*xy,0)
    bpy.data.objects['review.ground'].location.z=-.302
    report=[]
    for deg in [0,120,240]:
        angle=math.radians(deg); direction=Vector((math.cos(angle),math.sin(angle),0))
        root,objects=import_asset(WORK/'road.glb'); root.location=direction*1.5
        root.rotation_mode='XYZ'; root.rotation_euler.z=angle
        bpy.context.view_layer.update()
        anchors=[o for o in objects if o.name.startswith('anchor_edge_')]
        assert any(o.matrix_world.translation.length<1e-5 for o in anchors)
        assert any((o.matrix_world.translation-direction*3).length<1e-5 for o in anchors)
        # 每条逻辑边仅使用一个根变换，避免相邻地块各生成一条重复道路。
        report.append({'angle':deg,'center':list(root.location),'scale':list(root.scale),'endpoint_alignment':True})
    building,_=import_asset(model_dir/'settlement'/'model.glb'); building.location=(3,0,0)
    cam=bpy.data.objects['review.close']; cam.location=(2,-6,9); aim(cam,(.15,0,.06)); cam.data.ortho_scale=7.2
    scene=bpy.context.scene; scene.render.resolution_x=1500; scene.render.resolution_y=1250
    render('junction-empty')
    for kind in ['settlement','city']:
        root,objects=import_asset(model_dir/kind/'model.glb')
        assert root.location.length<1e-6 and tuple(root.scale)==(1,1,1)
        render('junction-'+kind)
        if kind=='city':
            cam.location=(3,-5,4); aim(cam,(.13,0,.13)); cam.data.ortho_scale=2.0
            render('junction-city-close')
        for obj in objects: bpy.data.objects.remove(obj,do_unlink=True)
    (WORK/'composition-check.json').write_text(json.dumps({'edges':report,'vertex_exclusion_radius':.28,
        'road_end_distance':.30,'building_upgrade_same_transform':True,
        'bare_vertex_gap_intentional':True,'runtime_tested':False},indent=2))


{'build':build,'export':export,'composition':composition}[args.mode]()
