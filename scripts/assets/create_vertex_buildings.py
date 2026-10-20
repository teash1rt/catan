"""在临时目录中创建模块化中世纪建筑，再进行评审与导出。

Blender --background --python-exit-code 1 --python scripts/assets/create_vertex_buildings.py
    -- --work-dir /private/tmp/... --mode build|export|composition
仅手动归档通过评审的源文件与 GLB，不在此处覆盖正式资产。
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
    raise ValueError('Review files must remain outside the repository')
WORK.mkdir(parents=True, exist_ok=True)
COLORS = {'red': (.43,.055,.033), 'blue': (.024,.085,.22),
          'ivory': (.74,.63,.40), 'orange': (.72,.235,.032)}


def material(name, rgb, rough=.82, metal=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tint(mat, rgb)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Specular IOR Level'].default_value = .23
    return mat


def tint(mat, rgb):
    mat.diffuse_color = (*rgb, 1)
    next(node for node in mat.node_tree.nodes if node.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (*rgb, 1)


def move(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def mesh(name, vertices, faces, mat, bevel=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    ASSET.objects.link(obj)
    data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('small softened edges', 'BEVEL')
        mod.width, mod.segments = bevel, 2
    return obj


def box(name, pos, dims, mat, bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = move(bpy.context.object, ASSET)
    obj.name, obj.scale = name, dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('small softened edges', 'BEVEL')
        mod.width, mod.segments = bevel, 2
    return obj


def beam(name, a, b, width, mat, depth=None):
    a, b = Vector(a), Vector(b)
    obj = box(name, (a+b)/2, (width, depth or width, (b-a).length), mat, width*.13)
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return obj


def gable(name, x, y, width, depth, eave, peak, mat):
    vertices = [(x-width/2,y-depth/2,eave),(x+width/2,y-depth/2,eave),(x,y-depth/2,peak),
                (x-width/2,y+depth/2,eave),(x+width/2,y+depth/2,eave),(x,y+depth/2,peak)]
    return mesh(name,vertices,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],mat,.02)


def roof(x, y, width, depth, eave, peak, rows=6):
    """厚瓦错缝铺设，共用一种可换色材质，避免棋盘格配色。"""
    for sign in [-1,1]:
        for row in range(rows):
            t0 = max(0, row/rows-.016)
            t1 = (row+1)/rows
            n = 7
            for j in range(n):
                ya = y-depth/2 + depth*max(0,(j-(row%2)*.5)/n)
                yb = y-depth/2 + depth*min(1,(j+1-(row%2)*.5)/n)
                if j == n-1:
                    yb = y+depth/2
                xa, xb = x+sign*width*.5*t0, x+sign*width*.5*t1
                za, zb = peak+(eave-peak)*t0+.035, peak+(eave-peak)*t1+.055
                verts = [(xa,ya,za),(xb,ya,zb),(xb,yb-.012,zb),(xa,yb-.012,za)]
                verts += [(a,b,c-.075) for a,b,c in verts]
                mesh('roof.course', verts, [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)], M['player'],.018)
    beam('ridge.bound-cap',(x,y-depth/2-.015,peak+.06),(x,y+depth/2+.015,peak+.06),.13,M['player'])
    for yy in [y-depth/2-.012,y+depth/2+.012]:
        for sign in [-1,1]:
            beam('gable.fascia',(x,yy,peak),(x+sign*width/2,yy,eave),.105,M['wood'])


def arch_face(name, x, y, bottom, width, height, mat):
    r = width/2
    spring = bottom+height-r
    points = [(x-r,y,bottom),(x+r,y,bottom),(x+r,y,spring)]
    points += [(x+r*math.cos(i*math.pi/12),y,spring+r*math.sin(i*math.pi/12)) for i in range(1,13)]
    return mesh(name, points, [tuple(range(len(points)))],mat)


def arch_frame(x,y,bottom,width,height,mat,thickness=.085):
    r = width/2
    spring = bottom+height-r
    for sign in [-1,1]:
        beam('arch.jamb',(x+sign*r,y,bottom),(x+sign*r,y,spring),thickness,mat)
    for i in range(12):
        a,b = i*math.pi/12,(i+1)*math.pi/12
        beam('arch.voussoir',(x+r*math.cos(a),y,spring+r*math.sin(a)),
             (x+r*math.cos(b),y,spring+r*math.sin(b)),thickness,mat)


def window(x,y,z,width=.56,height=.83):
    outward = -1 if y < 0 else 1
    arch_face('window.dark-recess',x,y,z,width,height,M['shadow'])
    arch_frame(x,y+outward*.012,z,width,height,M['wood'],.065)
    beam('window.mullion',(x,y+outward*.025,z+.04),(x,y+outward*.025,z+height-.09),.038,M['honey'])
    beam('window.transom',(x-width*.41,y+outward*.025,z+height*.46),(x+width*.41,y+outward*.025,z+height*.46),.036,M['honey'])
    box('window.deep-sill',(x,y+outward*.04,z-.035),(width+.16,.18,.09),M['stone_light'])


def door(x,y,z,width=.75,height=1.38,stone=False):
    arch_face('door.recess',x,y,z,width+.09,height+.04,M['shadow'])
    arch_face('door.oak',x,y-.014,z,width,height,M['oak'])
    arch_frame(x,y-.035,z,width+.06,height+.04,M['stone_light'] if stone else M['wood'],.12)
    for i in range(1,5):
        xx=x-width/2+width*i/5
        beam('door.plank-joint',(xx,y-.027,z+.06),(xx,y-.027,z+height-width*.5),.015,M['wood'])
    for zz in [.28,.72]:
        box('door.iron-strap',(x,y-.040,z+zz),(width*.8,.023,.047),M['iron'],.006)
    box('door.latch',(x+width*.24,y-.065,z+.55),(.07,.035,.09),M['iron'],.01)


def foundation(width,depth):
    box('foundation.slate-foot',(0,0,.105),(width,depth,.21),M['stone'],.07)
    box('foundation.chamfered-top',(0,0,.205),(width-.05,depth-.05,.10),M['stone_light'],.03)


def settlement():
    foundation(3.55,3.35)
    box('house.warm-plaster',(0,.10,1.72),(2.80,2.55,2.97),M['plaster'],.05)
    gable('house.gable',0,.10,2.8,2.55,3.2,4.78,M['plaster'])
    # 底层使用石质台基，上层采用外挑结构。
    box('house.stone-plinth',(0,.10,.43),(2.93,2.66,.38),M['stone'])
    for z in [.63,1.70,3.17]:
        box('house.front-rail',(0,-1.207,z),(2.96,.13,.13),M['wood'])
        box('house.back-rail',(0,1.407,z),(2.96,.13,.13),M['wood'])
        for x in [-1.43,1.43]:
            box('house.side-rail',(x,.1,z),(.13,2.65,.13),M['wood'])
    for x in [-1.37,0,1.37]:
        for y in [-1.23,1.43]:
            beam('house.timber-post',(x,y,.57),(x,y,3.24),.125,M['wood'])
    for x in [-1.43,1.43]:
        for y in [-.55,.72]:
            beam('house.side-post',(x,y,.58),(x,y,3.18),.12,M['wood'])
        for a,b in [(-1.15,-.57),(.73,1.35)]:
            beam('house.side-brace',(x,a,1.81),(x,b,2.37),.10,M['wood'])
        # 两侧墙面均设置浅窗洞，并保留清晰窗框。
        for y in [-.56,.71]:
            box('side-window.recess',(x*1.014,y,2.52),(.04,.42,.63),M['shadow'])
            for dy in [-.245,0,.245]:
                box('side-window.mullion',(x*1.04,y+dy,2.52),(.05,.04,.69),M['wood'])
            box('side-window.sill',(x*1.04,y,2.17),(.14,.59,.08),M['stone_light'])
    for x in [-.67,.67]:
        window(x,-1.267,2.0,.62,.87)
        window(x,1.472,2.0,.62,.87)
    door(-.47,-1.28,.26,.75,1.32)
    window(.80,-1.272,.88,.50,.59)
    # 山墙木构强化中世纪建筑轮廓，控制无关装饰。
    for y in [-1.23,1.43]:
        beam('gable.king-post',(0,y,3.2),(0,y,4.76),.13,M['wood'])
        for s in [-1,1]:
            beam('gable.brace',(s*1.27,y,3.23),(0,y,4.68),.11,M['wood'])
            beam('gable.short-post',(s*.51,y,3.24),(s*.51,y,4.13),.075,M['wood'])
    roof(0,.10,3.37,3.08,3.19,4.91,7)
    box('chimney.shaft',(.87,.79,4.61),(.42,.48,1.25),M['stone'],.035)
    for z in [4.35,4.65,4.95]:
        box('chimney.course',(.87,.79,z),(.445,.50,.075),M['stone_light'],.012)
    box('chimney.cap',(.87,.79,5.26),(.53,.57,.16),M['stone_light'])
    box('chimney.dark-flue',(.87,.79,5.345),(.30,.33,.01),M['shadow'],.006)
    box('threshold.step',(-.47,-1.46,.275),(.99,.33,.16),M['stone_light'])


def city():
    foundation(3.86,3.35)
    # 城市由不对称公共建筑和防御门塔组成，形成区别于村庄的轮廓。
    tx,ty=-.78,-.24
    box('tower.limestone-body',(tx,ty,2.04),(1.70,2.22,3.57),M['stone'],.055)
    for z in [.51,1.05,1.64,2.23,2.82,3.42]:
        box('tower.masonry-band',(tx,ty,z),(1.77,2.29,.075),M['stone_light'],.015)
    for x in [tx-.79,tx+.79]:
        for y in [ty-1.075,ty+1.075]:
            for i in range(7):
                box('tower.corner-quoin',(x,y,.68+i*.52),(.27,.29,.31),M['stone_light'],.025)
    door(tx,ty-1.15,.27,1.03,1.78,stone=True)
    window(tx,ty-1.155,2.63,.51,.86)
    # 外挑廊道搭配成对尖拱窗和厚实托梁。
    box('tower.gallery-overhang',(tx,ty,3.83),(1.94,2.45,.24),M['stone_light'])
    box('tower.upper-plaster',(tx,ty,4.48),(1.86,2.35,1.19),M['plaster'])
    for x in [tx-.80,tx,tx+.80]:
        box('tower.gallery-front-post',(x,ty-1.20,4.47),(.10,.10,1.25),M['wood'])
    for x in [tx-.65,tx+.65]:
        beam('tower.front-corbel',(x,ty-1.07,3.37),(x,ty-1.30,3.82),.14,M['stone_light'])
    for x in [tx-.43,tx+.43]:
        window(x,ty-1.215,4.06,.48,.74)
        window(x,ty+1.215,4.06,.48,.74)
    for x in [tx-.80,tx,tx+.80]:
        box('tower.gallery-back-post',(x,ty+1.20,4.47),(.10,.10,1.25),M['wood'])
    window(tx,ty+1.16,2.54,.47,.89)
    for x in [tx-.96,tx+.96]:
        for y in [ty-.62,ty+.54]:
            box('tower.side-lancet',(x,y,4.46),(.028,.39,.61),M['shadow'])
            for dy in [-.215,0,.215]:
                box('tower.side-mullion',(x,y+dy,4.46),(.055,.038,.70),M['honey'] if dy==0 else M['wood'])
            box('tower.side-sill',(x,y,4.10),(.14,.56,.09),M['stone_light'])
    box('tower.upper-beam',(tx,ty,5.095),(1.96,2.46,.14),M['wood'])
    # 四面陡坡屋顶采用重叠瓦层，形成独立的城市轮廓。
    for row in range(8):
        t0=max(0,row/8-.014); t1=(row+1)/8
        r0=1.20*(1-t0)+.075; r1=1.20*(1-t1)+.045
        z0=5.09+1.57*t0; z1=5.09+1.57*t1
        corners=[(-1,-1),(1,-1),(1,1),(-1,1)]
        count=max(1,6-row//2)
        for side in range(4):
            a,b=Vector(corners[side]),Vector(corners[(side+1)%4])
            for j in range(count):
                u=a.lerp(b,j/count+.004); v=a.lerp(b,(j+1)/count-.004)
                verts=[(tx+p.x*r,ty+p.y*r*.98,z) for p,r,z in [(u,r0,z0),(v,r0,z0),(v,r1,z1),(u,r1,z1)]]
                verts += [(x,y,z-.045) for x,y,z in verts]
                mesh('tower.hipped-tile',verts,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],M['player'],.012)
    beam('tower.finial',(tx,ty,6.59),(tx,ty,7.24),.055,M['iron'])
    # 紧凑的布旗保持在约定的圆形占地内。
    mesh('tower.player-pennant',[(tx,ty,7.19),(tx+.62,ty+.025,7.12),(tx+.46,ty+.01,6.91),(tx,ty,6.94)],[(0,1,2,3)],M['player'])
    # 较低的木构大厅直接连接门塔。
    hx,hy=.92,.22
    box('hall.plaster',(hx,hy,1.79),(1.38,2.55,3.09),M['plaster'],.045)
    gable('hall.gable',hx,hy,1.38,2.55,3.30,4.42,M['plaster'])
    for z in [.55,1.78,3.30]:
        box('hall.front-rail',(hx,hy-1.31,z),(1.54,.12,.12),M['wood'])
        box('hall.back-rail',(hx,hy+1.31,z),(1.54,.12,.12),M['wood'])
        box('hall.side-rail',(hx+.725,hy,z),(.12,2.65,.12),M['wood'])
    for x in [hx-.64,hx+.64]:
        box('hall.front-post',(x,hy-1.32,1.99),(.12,.12,2.83),M['wood'])
        box('hall.back-post',(x,hy+1.32,1.99),(.12,.12,2.83),M['wood'])
    window(hx,hy-1.365,2.04,.65,.94)
    window(hx,hy+1.365,2.04,.65,.94)
    window(hx,hy+1.365,.79,.47,.66)
    door(hx,hy-1.355,.28,.57,1.31)
    for yy in [hy-.66,hy+.62]:
        box('hall.side-window',(hx+.715,yy,2.49),(.025,.55,.82),M['shadow'])
        for dy in [-.30,0,.30]:
            box('hall.side-window-frame',(hx+.75,yy+dy,2.49),(.07,.05,.91),M['wood'])
        box('hall.side-window-sill',(hx+.75,yy,2.00),(.16,.74,.10),M['stone_light'])
        beam('hall.side-brace',(hx+.76,yy-.26,.60),(hx+.76,yy+.26,1.73),.11,M['wood'])
    beam('hall.gable-post',(hx,hy-1.32,3.31),(hx,hy-1.32,4.43),.10,M['wood'])
    beam('hall.gable-back-post',(hx,hy+1.32,3.31),(hx,hy+1.32,4.43),.10,M['wood'])
    roof(hx,hy,1.82,2.96,3.29,4.55,6)
    box('city.front-step',(tx,ty-1.36,.275),(1.33,.36,.15),M['stone_light'])


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def studio():
    col=bpy.data.collections.new('REVIEW_ONLY'); bpy.context.scene.collection.children.link(col)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002))
    ground=move(bpy.context.object,col); ground.name='review.ground'
    ground.data.materials.append(material('review.neutral',(.24,.27,.28)))
    for name,pos,energy,size in [('key',(-3,-4,6),450,4),('fill',(4,-1,3),210,3),('rim',(1,3,5),350,3)]:
        data=bpy.data.lights.new('review.'+name,'AREA'); data.energy=energy; data.size=size
        obj=bpy.data.objects.new(data.name,data); col.objects.link(obj); obj.location=pos; aim(obj,(0,0,.3))
    for name,pos,scale in [('close',(1.4,-2.2,1.7),1.08),('side',(2,-1,.72),1.02),('back',(-1.7,2,1.5),1.08),('board',(1.4,-2.2,3.4),1.7)]:
        data=bpy.data.cameras.new('review.'+name); data.type='ORTHO'; data.ortho_scale=scale
        obj=bpy.data.objects.new(data.name,data); col.objects.link(obj); obj.location=pos; aim(obj,(0,0,.31))
    scene=bpy.context.scene; scene.camera=bpy.data.objects['review.close']
    scene.world=bpy.data.worlds.new('review.world'); scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.55,.6,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.38
    scene.render.engine='CYCLES'; scene.cycles.samples=24; scene.cycles.use_denoising=True
    scene.render.resolution_x=1000; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'


def render(name, camera='close'):
    scene=bpy.context.scene; scene.camera=bpy.data.objects['review.'+camera]
    scene.render.filepath=str(WORK/(name+'.png')); bpy.ops.render.render(write_still=True)


def check(objects, label):
    points=[]; tris=0; mats=set()
    for obj in objects:
        assert obj.type not in {'LIGHT','CAMERA','FONT'}
        if obj.type!='MESH': continue
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); data=evaluated.to_mesh()
        points.extend(obj.matrix_world@v.co for v in data.vertices)
        data.calc_loop_triangles(); tris+=len(data.loop_triangles)
        mats.update(m.name for m in data.materials if m)
        assert all(math.isfinite(c) for v in data.vertices for c in v.co)
        evaluated.to_mesh_clear()
    radius=max(math.hypot(p.x,p.y) for p in points); low=min(p.z for p in points); high=max(p.z for p in points)
    assert radius<=.28, radius
    assert abs(low)<1e-5 and high<=.8, (low,high)
    assert 'player_color' in mats
    result=dict(radius=radius,z_min=low,z_max=high,triangles=tris,materials=sorted(mats))
    (WORK/(label+'-check.json')).write_text(json.dumps(result,indent=2))
    print('BUILDING_CHECK',label,json.dumps(result))


def build(kind):
    global ASSET,M
    source=WORK/(kind+'.blend')
    if source.exists(): raise FileExistsError(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ASSET=bpy.data.collections.new('ASSET_'+kind); bpy.context.scene.collection.children.link(ASSET)
    M={key:material(name,rgb) for key,name,rgb in [
        ('player','player_color',COLORS['blue']),('plaster','building.warm-limewash',(.70,.55,.33)),
        ('wood','building.dark-oak',(.14,.064,.024)),('oak','building.door-oak',(.34,.18,.060)),
        ('honey','building.warm-mullions',(.42,.26,.10)),('stone','building.limestone',(.38,.36,.29)),
        ('stone_light','building.cut-stone',(.54,.49,.38)),('shadow','building.recess',(.046,.065,.067)),
        ('iron','building.blackened-iron',(.055,.065,.070))]}
    M['player']['role']='player_color'; M['player']['input']='linear RGB baseColorFactor'
    (settlement if kind=='settlement' else city)()
    # 单位转换前先烘焙倒角，源文件保留具名且可编辑的组件。
    for obj in list(ASSET.objects):
        bpy.context.view_layer.objects.active=obj
        for mod in list(obj.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.location*=.1; obj.scale*=.1
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    root=bpy.data.objects.new(kind,None); ASSET.objects.link(root)
    root['asset_id']=kind; root['contract']='vertex-building-v1'
    root['clearance_radius']=.28; root['clearance_height']=.8
    root['player_color_material']='player_color'; root['front_blender']='-Y'
    for obj in ASSET.objects:
        if obj!=root: obj.parent=root
    bpy.context.view_layer.update(); check(list(ASSET.objects),kind+'-source')
    studio(); bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    for camera in ['close','side','back','board']: render(kind+'-'+camera,camera)


def export(kind):
    bpy.ops.wm.open_mainfile(filepath=str(WORK/(kind+'.blend')))
    col=bpy.data.collections['ASSET_'+kind]
    root=bpy.data.objects[kind]
    # 拆分为可复用的中性主体和可独立换色的屋顶、旗帜网格。
    for colored in [False,True]:
        items=[o for o in col.objects if o.type=='MESH' and any(m.name=='player_color' for m in o.data.materials)==colored]
        bpy.ops.object.select_all(action='DESELECT')
        for obj in items: obj.select_set(True)
        bpy.context.view_layer.objects.active=items[0]; bpy.ops.object.join()
        obj=bpy.context.object; obj.name=kind+('.player' if colored else '.body')
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col.objects: obj.select_set(True)
    target=WORK/(kind+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    for obj in list(col.objects): bpy.data.objects.remove(obj,do_unlink=True)
    # 清理无引用的源材质，确保导入后的材质名称符合契约。
    for data in list(bpy.data.meshes):
        if data.users==0: bpy.data.meshes.remove(data)
    for mat in list(bpy.data.materials):
        if mat.users==0: bpy.data.materials.remove(mat)
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(target))
    imported=set(bpy.data.objects)-before
    check(imported,kind+'-glb')
    render(kind+'-glb')
    # 实例之间隔离玩家材质：仅复制玩家材质，不修改共享原材质。
    roots=[o for o in imported if o.parent not in imported]
    assert len(roots)==1
    original=roots[0]; original.location.x=-.96
    source_meshes=[o for o in imported if o.type=='MESH']
    source_mat=bpy.data.materials['player_color']; before_color=tuple(source_mat.diffuse_color)
    for index,color in enumerate(['red','ivory','orange'],start=1):
        copyroot=original.copy(); bpy.context.scene.collection.objects.link(copyroot); copyroot.location.x=-.96+index*.64
        for obj in source_meshes:
            clone=obj.copy(); clone.data=obj.data; bpy.context.scene.collection.objects.link(clone); clone.parent=copyroot
            for slot in clone.material_slots:
                if slot.material==source_mat:
                    slot.link='OBJECT'; slot.material=source_mat.copy(); tint(slot.material,COLORS[color])
    assert tuple(source_mat.diffuse_color)==before_color
    scene=bpy.context.scene; scene.render.resolution_x=1600; scene.render.resolution_y=700
    cam=bpy.data.objects['review.close']; cam.location=(.8,-4,2.7); aim(cam,(0,0,.32)); cam.data.ortho_scale=2.8
    render(kind+'-colors')


def composition():
    bpy.ops.wm.read_factory_settings(use_empty=True); studio()
    # 三个相邻的平顶六边形共用一个顶点，该位置仅放置一栋建筑。
    centers=[(-3,0),(1.5,3*math.sqrt(3)/2),(1.5,-3*math.sqrt(3)/2)]
    for kind,xy in zip(['forest','wheat','sheep'],centers):
        before=set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets'/(kind+'-tile')/'model.glb'))
        imported=set(bpy.data.objects)-before
        for obj in imported:
            if obj.parent not in imported: obj.location+=Vector((*xy,0))
    ground=bpy.data.objects['review.ground']; ground.location.z=-.302
    scene=bpy.context.scene; scene.render.resolution_x=1300; scene.render.resolution_y=1100
    cam=bpy.data.objects['review.close']; cam.location=(2,-7,8); aim(cam,(0,0,.05)); cam.data.ortho_scale=5
    for kind in ['settlement','city']:
        before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(WORK/(kind+'.glb')))
        imported=set(bpy.data.objects)-before
        render(kind+'-vertex')
        for obj in imported: bpy.data.objects.remove(obj,do_unlink=True)
    (WORK/'composition-check.json').write_text(json.dumps({'shared_vertex':[0,0,0],'tile_centers':centers,'building_offset':[0,0,0],'building_scale':1,'upgrade_same_transform':True},indent=2))


if args.mode=='composition': composition()
else:
    for asset in ['settlement','city']:
        (build if args.mode=='build' else export)(asset)
