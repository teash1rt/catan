"""Build/review the independent robber miniature in a temporary directory.

Blender --background --python-exit-code 1 --python scripts/assets/create_robber.py
    -- --work-dir /private/tmp/... [--mode build|export|composition] [--source ...]
No canonical files are overwritten. Export only after Computer Use review.
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
PARSER = argparse.ArgumentParser()
PARSER.add_argument('--work-dir', type=Path, required=True)
PARSER.add_argument('--mode', choices=['build', 'export', 'composition'], default='build')
PARSER.add_argument('--source', type=Path)
ARGS = PARSER.parse_args(sys.argv[sys.argv.index('--')+1:])
WORK = ARGS.work_dir.resolve()
if not str(WORK).startswith(('/private/tmp/', '/tmp/')):
    raise ValueError('Drafts and review evidence must stay outside the project')
WORK.mkdir(parents=True, exist_ok=True)
SOURCE = (ARGS.source or WORK / 'model.blend').resolve()
SCALE = .18


def material(name, color, rough=.72, metal=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Specular IOR Level'].default_value = .25
    return m


def move_to(obj, collection):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def mesh(name, vertices, faces, mat, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    ASSET.objects.link(obj)
    data.materials.append(mat)
    for p in data.polygons:
        p.use_smooth = smooth
    return obj


def bevel(obj, width=.025, segments=3):
    mod = obj.modifiers.new('soft handcrafted edges', 'BEVEL')
    mod.width, mod.segments = width, segments
    return obj


def ellipsoid(name, pos, scale, mat, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=pos)
    obj = move_to(bpy.context.object, ASSET)
    obj.name, obj.scale = name, scale
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def loft(name, rings, mat, n=40, folds=0):
    # Rings are (x, y, z, x radius, y radius). Sculpted contours, not stacked balls.
    vertices = []
    for j, (x, y, z, rx, ry) in enumerate(rings):
        for i in range(n):
            a = i*math.tau/n
            wave = 1+folds*math.sin(7*a+j*.36)
            vertices.append((x+rx*math.cos(a)*wave, y+ry*math.sin(a)*wave, z))
    faces = []
    for j in range(len(rings)-1):
        for i in range(n):
            k = (i+1) % n
            faces.append((j*n+i, j*n+k, (j+1)*n+k, (j+1)*n+i))
    faces.extend([tuple(reversed(range(n))), tuple((len(rings)-1)*n+i for i in range(n))])
    return mesh(name, vertices, faces, mat)


def tube(name, points, radii, mat, n=12):
    verts, faces = [], []
    for j, (point, radius) in enumerate(zip(points, radii)):
        direction = Vector(points[min(j+1,len(points)-1)])-Vector(points[max(0,j-1)])
        direction.normalize()
        u = direction.cross(Vector((0,1,0)))
        if u.length < .1:
            u = direction.cross(Vector((1,0,0)))
        u.normalize()
        v = direction.cross(u).normalized()
        verts.extend(Vector(point)+radius*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for i in range(n))
    for j in range(len(points)-1):
        for i in range(n):
            k = (i+1) % n
            faces.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
    faces.extend([tuple(reversed(range(n))),tuple((len(points)-1)*n+i for i in range(n))])
    return mesh(name, verts, faces, mat)


def line(name, points, width, mat):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 10
    curve.bevel_depth, curve.bevel_resolution = width, 3
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for p, co in zip(spline.bezier_points, points):
        p.co = co
        p.handle_left_type = p.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    ASSET.objects.link(obj)
    curve.materials.append(mat)
    return obj


def block(name, pos, scale, mat, width=.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = move_to(bpy.context.object, ASSET)
    obj.name, obj.scale = name, scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return bevel(obj, width)


def build():
    global ASSET
    if SOURCE.exists():
        raise FileExistsError('Use a new temporary --source for each draft')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ASSET = bpy.data.collections.new('ASSET_robber')
    bpy.context.scene.collection.children.link(ASSET)
    teal = material('robber.cloak.charcoal', (.014,.017,.020), .86)
    fold = material('robber.cloak.bound-edge', (.025,.029,.032), .8)
    lining = material('robber.lining.graphite', (.023,.024,.026), .9)
    tunic = material('robber.tunic.black-wool', (.035,.033,.031), .83)
    leather = material('robber.leather.black-brown', (.026,.021,.017), .56)
    edge = material('robber.leather.bound-edge', (.043,.034,.026), .62)
    pants = material('robber.trousers.soot', (.018,.019,.020), .92)
    skin = material('robber.skin.warm', (.61,.335,.18))
    skin_hi = material('robber.skin.light', (.70,.41,.23))
    beard = material('robber.hair.dark-umber', (.055,.036,.024))
    ivory = material('robber.eye.ivory', (.68,.64,.46))
    dark = material('robber.eye.dark', (.012,.018,.018))
    brass = material('robber.hardware.blackened-iron', (.072,.077,.08), .46, .65)
    steel = material('robber.hardware.satin-steel', (.14,.16,.17), .48, .65)
    plinth = material('robber.base.slate', (.065,.07,.07))

    # A low, neutral gaming foot: footprint <= .34 at final scale.
    loft('base.low-slate', [(0,0,.0,1.70,1.70),(0,0,.045,1.74,1.74),(0,0,.115,1.70,1.70)], plinth, n=80)
    # Wide grounded stance; individually contoured boots and trouser legs.
    for s, y in [(-1,-.12),(1,.08)]:
        x = s*.51
        loft('boot.left' if s<0 else 'boot.right', [(x,y-.14,.12,.31,.48),(x,y-.20,.18,.34,.54),(x,y-.18,.34,.32,.50),(x,y,.55,.24,.28),(x,y,.95,.23,.245),(x,y,1.24,.275,.27)], leather)
        loft('boot.cuff',[(x,y,1.17,.28,.28),(x,y,1.30,.285,.285),(x,y,1.36,.255,.25)],edge)
        loft('leg.trouser',[(x,y,1.23,.23,.24),(s*.46,y,1.65,.30,.28),(s*.40,.025,2.18,.34,.32),(s*.35,.04,2.65,.35,.32)],pants,folds=.035)
        line('boot.front-seam',[(x,y-.50,.23),(x,y-.30,.51),(x,y-.251,1.17)],.013,edge)
        block('boot.strap',(x,y-.02,.89),(.49,.53,.065),leather,.018)
        block('boot.small-buckle',(x+s*.245,y-.12,.89),(.035,.14,.115),brass,.016)
    # Broad chest tapered into a belted waist and split skirt.
    loft('tunic.contoured-body',[(0,.03,2.18,.76,.41),(0,.03,2.30,.77,.43),(0,.02,2.75,.59,.37),(0,0,3.05,.57,.35),(0,.035,3.45,.72,.39),(0,.055,3.92,.89,.40),(0,.07,4.17,.86,.38),(0,.06,4.38,.47,.28)],tunic,folds=.018)
    line('tunic.front-opening',[(0,-.40,2.19),(.015,-.40,2.5),(.035,-.354,3.04)],.019,lining)
    line('tunic.hem-left',[(-.74,-.08,2.20),(-.49,-.33,2.19),(0,-.405,2.19)],.025,edge)
    line('tunic.hem-right',[(0,-.405,2.19),(.49,-.33,2.19),(.74,-.08,2.20)],.025,edge)
    loft('belt.leather',[(0,.01,2.96,.606,.384),(0,.01,3.16,.612,.39)],leather)
    block('belt.buckle',(0,-.399,3.065),(.24,.055,.235),brass,.035)
    block('belt.buckle-inset',(0,-.438,3.065),(.145,.022,.135),leather,.015)
    block('belt.buckle-tongue',(0,-.457,3.065),(.025,.018,.15),brass,.008)
    for x in [.20,.32,.44]:
        ellipsoid('belt.rivet',(x,-math.sqrt(max(.02,.38**2*(1-(x/.64)**2)))-.025,3.06),(.025,.017,.025),brass,16,8)
    # A quiet, shaped leather breast panel replaces the bright diagonal baldric.
    # Broad facets and restrained rivets read as medieval brigandine, not sci-fi armor.
    panel=mesh('brigandine.chest-panel',[(-.58,-.295,3.98),(0,-.47,4.04),(.58,-.295,3.98),(-.43,-.325,3.23),(0,-.425,3.24),(.43,-.325,3.23)],[(0,3,4,1),(1,4,5,2)],leather)
    mod=panel.modifiers.new('leather thickness','SOLIDIFY');mod.thickness=.035
    bevel(panel,.022,3)
    # One arm hangs with a closed hand, the other rests on an upright sheathed sword.
    for side, pts in [(-1,[(-.68,.045,4.04),(-1.00,-.03,3.75),(-1.10,-.16,3.40),(-1.04,-.30,3.07)]),(1,[(.68,.04,4.04),(1.00,-.04,3.80),(1.13,-.22,3.48),(1.03,-.53,3.31)])]:
        tube('sleeve.sculpted',pts,[.30,.285,.24,.19],tunic,24)
        wrist=Vector(pts[-1]); elbow=Vector(pts[-2]); d=(wrist-elbow).normalized()
        tube('bracer.leather',[elbow.lerp(wrist,.12),wrist,wrist+d*.035],[.257,.205,.205],leather,24)
        tube('bracer.bound-edge',[wrist-d*.025,wrist+d*.035],[.22,.216],edge,24)
        for f in [.3,.68]:
            c=elbow.lerp(wrist,f)
            ellipsoid('bracer.rivet',(c.x,c.y-.22,c.z),(.03,.025,.03),brass,16,8)
        if side<0:
            palm=(-1.04,-.32,2.91)
            ellipsoid('hand.closed',palm,(.205,.15,.23),leather)
            for i in range(4):
                xx=-1.19+i*.084
                tube('hand.finger',[(xx,-.445,3.00),(xx,-.482,2.86),(xx,-.40,2.77)],[.048,.049,.044],leather,12)
            ellipsoid('hand.thumb',(-.86,-.44,2.94),(.075,.085,.14),leather)
        else:
            ellipsoid('hand.sword-palm',(1.02,-.57,3.21),(.20,.14,.14),leather)
            for i in range(4):
                xx=.88+i*.088
                tube('hand.sword-finger',[(xx,-.59,3.25),(xx,-.728,3.20),(xx,-.73,3.06)],[.047,.047,.043],leather,12)
            ellipsoid('hand.sword-thumb',(.85,-.60,3.13),(.065,.095,.11),leather)
    # Small provision pouch, rather than ornamental clutter.
    loft('belt.pouch', [(-.59,-.26,2.48,.16,.14),(-.59,-.28,2.55,.215,.15),(-.59,-.28,2.84,.20,.15),(-.59,-.26,2.94,.14,.13)],leather,n=24)
    block('pouch.flap',(-.59,-.427,2.80),(.32,.05,.22),edge,.055)
    ellipsoid('pouch.button',(-.59,-.469,2.75),(.032,.018,.032),brass,16,8)
    # Sword is entirely sheathed: a grounded leader pose, not a battle swing.
    tube('sword.scabbard',[(1.00,-.61,.12),(1.01,-.61,.34),(1.025,-.62,2.79)],[.025,.095,.11],leather,16)
    tube('sword.chape',[(1.00,-.61,.12),(1.01,-.61,.42)],[.03,.095],brass,16)
    tube('sword.throat',[(1.025,-.62,2.55),(1.025,-.62,2.80)],[.12,.12],brass,16)
    line('sword.scabbard-seam',[(1.0,-.713,.56),(1.025,-.735,2.43)],.014,edge)
    line('sword.crossguard',[(.67,-.62,2.69),(.78,-.62,2.77),(1.025,-.62,2.78),(1.25,-.62,2.77),(1.36,-.62,2.69)],.048,steel)
    tube('sword.grip',[(1.025,-.62,2.80),(1.025,-.62,3.18)],[.077,.068],leather,20)
    for i in range(6):
        z=2.84+i*.052
        line('sword.grip-wrap',[(1.025+.079*math.cos(a*math.tau/24),-.62+.079*math.sin(a*math.tau/24),z+a*.03/24) for a in range(25)],.009,edge)
    ellipsoid('sword.pommel',(1.025,-.62,3.20),(.106,.104,.116),brass)
    # Open draped cape: its transverse folds are continuous from shoulders to hem.
    cape_rows=[(.24,1.43,.59),(.43,1.47,.67),(1.12,1.42,.67),(1.85,1.32,.65),(2.62,1.22,.61),(3.40,1.18,.53),(3.92,1.13,.40),(4.22,1.00,.31),(4.43,.47,.23)]
    count=65; verts=[]
    for j,(z,rx,ry) in enumerate(cape_rows):
        for i in range(count):
            a=-.12+(math.pi+.24)*i/(count-1)
            wave=1+.045*math.cos(8*a+.10*j)
            x=rx*math.cos(a)*wave
            # Upper front corners sit behind the arms, not through the sleeves.
            # Tuck the upper seam underneath the shoulder mantle; exposed lining
            # on its back would read as a split rather than a sewn connection.
            upper_tuck=min(1,max(0,(4.25-z)/.5))
            y=.12+ry*math.sin(a)*wave+.22*min(1,max(0,(z-2.5)/.65))*upper_tuck*abs(math.cos(a))**8
            zz=z+(1-j/(len(cape_rows)-1))*.08*math.cos(5*a+.5)
            verts.append((x,y,zz))
    faces=[(j*count+i,j*count+i+1,(j+1)*count+i+1,(j+1)*count+i) for j in range(len(cape_rows)-1) for i in range(count-1)]
    cape=mesh('cloak.continuous-drape',verts,faces,teal)
    cape.data.materials.append(lining)
    mod=cape.modifiers.new('lined wool thickness','SOLIDIFY'); mod.thickness=.045; mod.material_offset=1
    bevel(cape,.018,2)
    for i in [0,count-1]:
        line('cloak.bound-front-edge',[verts[j*count+i] for j in range(len(cape_rows))],.041,fold)
    line('cloak.bound-hem',verts[:count],.035,fold)
    # Broad shoulder mantle gives an unmistakable commanding silhouette.
    loft('cloak.shoulder-mantle',[(0,.085,3.88,1.05,.46),(0,.085,4.00,1.16,.48),(0,.065,4.20,1.21,.50),(0,.05,4.39,.92,.42),(0,.04,4.56,.46,.31)],teal,folds=.012)
    loft('hood.draped-cowl',[(0,.04,4.38,.47,.33),(0,.025,4.58,.43,.335),(0,.03,4.77,.37,.32),(0,.045,4.92,.32,.29)],teal,folds=.045)
    line('cowl.soft-fold',[(-.31,-.21,4.66),(-.12,-.317,4.59),(.10,-.32,4.58),(.32,-.20,4.65)],.024,fold)
    line('mantle.lower-piping',[(-.87,-.06,4.025),(-.64,-.25,4.0),(0,-.365,4.02),(.64,-.25,4.0),(.87,-.06,4.025)],.028,fold)
    block('mantle.iron-clasp',(0,-.437,4.22),(.19,.05,.15),brass,.025)
    # Neck and stylized sculpted face, with a firm jaw and small, focused eyes.
    loft('neck',[(0,.015,4.34,.24,.24),(0,.015,4.90,.245,.24)],skin)
    loft('head.sculpted-face',[(0,-.01,4.78,.17,.20),(0,-.045,4.86,.29,.28),(0,-.02,5.05,.36,.335),(0,-.02,5.23,.41,.365),(0,0,5.36,.415,.37),(0,.015,5.52,.39,.345),(0,.035,5.68,.33,.28),(0,.04,5.74,.19,.17)],skin,n=40)
    # Lower-face beard uses one tapered volume, with a few broad carved locks.
    loft('face.short-beard',[(0,-.10,4.76,.13,.20),(0,-.095,4.85,.27,.255),(0,-.085,4.99,.34,.28),(0,-.06,5.09,.35,.292)],beard,n=32)
    for s in [-1,1]:
        ellipsoid('face.eye',(s*.163,-.342,5.43),(.092,.027,.033),ivory,24,12)
        ellipsoid('face.iris',(s*.154,-.368,5.43),(.021,.009,.025),dark,20,12)
        line('face.upper-lid',[(s*.077,-.359,5.440),(s*.16,-.37,5.453),(s*.245,-.311,5.448)],.013,skin)
        line('face.commanding-brow',[(s*.070,-.376,5.482),(s*.165,-.363,5.511),(s*.27,-.295,5.521)],.029,beard)
        line('face.moustache',[(s*.022,-.43,5.143),(s*.12,-.404,5.137),(s*.22,-.36,5.107)],.036,beard)
    nose=mesh('face.nose', [(-.06,-.335,5.50),(.06,-.335,5.50),(-.075,-.48,5.22),(.075,-.48,5.22),(0,-.536,5.255),(0,-.386,5.18)],[(0,2,4),(0,4,1),(1,4,3),(2,5,4),(4,5,3),(0,1,3,5,2)],skin_hi)
    bevel(nose,.02,3)
    line('face.lower-lip',[(-.10,-.399,5.087),(0,-.427,5.078),(.10,-.399,5.087)],.016,skin)
    for x in [-.15,0,.15]:
        line('beard.carved-lock',[(x,-.337,5.025),(x*.83,-.365,4.91),(x*.5,-.301,4.80)],.011,leather)
    # Wrapped charcoal cloth hides the lower face, leaving a narrow human gaze.
    # No helmet, respirator, emissive eyes or technological surface details.
    scarf=loft('face.wrapped-scarf',[(0,-.02,4.77,.25,.32),(0,-.045,4.92,.36,.37),(0,-.065,5.12,.40,.46),(0,-.05,5.27,.375,.55)],lining,folds=.012)
    for vertex in list(scarf.data.vertices)[-40:]:
        front=max(0,(-vertex.co.y-.05)/.55)
        vertex.co.z+=.085*front**3
    line('scarf.diagonal-fold',[(-.32,-.25,5.20),(-.16,-.445,5.15),(.08,-.475,5.07),(.32,-.27,5.03)],.017,fold)
    # An open hood, not a solid cone: front rim and nested rear dome rings.
    hoodverts=[]; hn=64
    for j in range(9):
        t=j/8
        shrink=math.cos(t*math.pi/2)*.98+.02
        for i in range(hn):
            a=i*math.tau/hn
            x=.58*math.sin(a)*shrink
            z=5.30+(.68*math.cos(a)+.15*max(0,math.cos(a))**8)*shrink+.055*t
            y=-.365+.94*math.sin(t*math.pi/2)
            if j==0:
                y-=.22*max(0,math.cos(a))
            hoodverts.append((x,y,z))
    hoodfaces=[(j*hn+i,j*hn+(i+1)%hn,(j+1)*hn+(i+1)%hn,(j+1)*hn+i) for j in range(8) for i in range(hn)]
    hoodfaces.append(tuple(8*hn+i for i in range(hn)))
    hood=mesh('hood.open-sculpted',hoodverts,hoodfaces,teal)
    hood.data.materials.append(lining)
    mod=hood.modifiers.new('hood lined thickness','SOLIDIFY');mod.thickness=.04;mod.material_offset=1
    line('hood.bound-opening',hoodverts[:hn]+[hoodverts[0]],.038,fold)
    # A single offset seam on the dome, not dense decorative noise.
    line('hood.crown-seam',[hoodverts[j*hn+2] for j in range(9)],.015,fold)

    # Bake geometry, scale and normals. One static asset: no armature required.
    for obj in list(ASSET.objects):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True); bpy.context.view_layer.objects.active=obj
        if obj.type=='CURVE':
            bpy.ops.object.convert(target='MESH')
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        for v in obj.data.vertices:
            v.co*=SCALE
        obj.location*=SCALE
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    root=bpy.data.objects.new('robber',None);ASSET.objects.link(root)
    root['asset_id']='robber';root['contract']='robber-v1';root['clearance_radius']=.34;root['clearance_height']=1.15
    for obj in list(ASSET.objects):
        if obj!=root:
            obj.parent=root
    # Consolidate by material into one mesh: compact GLB, editable disconnected parts.
    bpy.ops.object.select_all(action='DESELECT')
    meshes=[o for o in ASSET.objects if o.type=='MESH']
    for obj in meshes:obj.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    bpy.ops.object.join();joined=bpy.context.object;joined.name='robber.character'
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    studio()
    check(list(ASSET.objects),'source')
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    for name in ['board','close','side','rear']:
        render(name,WORK/(name+'.png'))


def aim(obj, point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()


def studio():
    global ASSET
    ASSET=bpy.data.collections.get('ASSET_robber')
    review=bpy.data.collections.new('REVIEW_ONLY');bpy.context.scene.collection.children.link(review)
    ground=material('review.warm-grey',(.26,.275,.26))
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.007))
    o=move_to(bpy.context.object,review);o.name='review.ground';o.data.materials.append(ground)
    for name,pos,energy,size in [('key',(-3,-4,6),450,4),('fill',(4,-1,3),220,3),('rim',(1,3,5),400,3)]:
        data=bpy.data.lights.new('review.'+name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(data.name,data);review.objects.link(obj);obj.location=pos;aim(obj,(0,0,.5))
    for name,pos,target,size in [('board',(1.65,-2.9,2.4),(0,0,.55),1.50),('close',(1.4,-3.4,1.65),(0,-.01,.57),1.40),('side',(-3,-.6,1.7),(0,0,.56),1.42),('rear',(1.7,3,1.9),(0,0,.55),1.45)]:
        data=bpy.data.cameras.new('review.'+name);data.type='ORTHO';data.ortho_scale=size
        obj=bpy.data.objects.new(data.name,data);review.objects.link(obj);obj.location=pos;aim(obj,target)
    scene=bpy.context.scene;scene.camera=bpy.data.objects['review.board']
    scene.world=bpy.data.worlds.new('review.neutral');scene.world.use_nodes=True
    scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.5,.55,.60,1)
    scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.35
    scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.image_settings.file_format='PNG'


def render(camera,path):
    bpy.context.scene.camera=bpy.data.objects['review.'+camera]
    bpy.context.scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)


def check(objects,label):
    verts=[];triangles=0;materials=set();errors=[]
    for obj in objects:
        if obj.type!='MESH':continue
        verts.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
        materials.update(m.name for m in obj.data.materials if m)
        if any(not all(math.isfinite(c) for c in v.normal) for v in obj.data.vertices):errors.append('nonfinite normals')
    radius=max(math.hypot(v.x,v.y) for v in verts)
    bounds=[[min(v[i] for v in verts) for i in range(3)],[max(v[i] for v in verts) for i in range(3)]]
    if radius>.34+1e-5:errors.append('outside radial clearance')
    if bounds[0][2]<-1e-5 or bounds[1][2]>1.15+1e-5:errors.append('outside height clearance')
    if abs(bounds[0][2])>1e-5:errors.append('base not grounded')
    if any(o.type in {'CAMERA','LIGHT'} for o in objects):errors.append('studio exported')
    result=dict(stage=label,radius=radius,bounds=bounds,triangles=triangles,materials=len(materials),errors=errors)
    (WORK/(label+'-check.json')).write_text(json.dumps(result,indent=2))
    print('ROBBER_CHECK',json.dumps(result))
    if errors:raise RuntimeError(errors)


def export():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    objects=list(bpy.data.collections['ASSET_robber'].objects)
    bpy.context.view_layer.update();check(objects,'pre-export')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(WORK/'robber.glb'),export_format='GLB',use_selection=True,export_extras=True,export_cameras=False,export_lights=False,export_yup=True)
    for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(WORK/'robber.glb'))
    bpy.context.view_layer.update();check(list(bpy.context.selected_objects),'glb')
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'glb-review.blend'))
    render('close',WORK/'glb-close.png')


def composition():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    characters=list(bpy.data.collections['ASSET_robber'].objects)
    # Use the independently exported GLB for all mounting views.
    for obj in characters:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(WORK/'robber.glb'))
    character=list(bpy.context.selected_objects)
    root=next(o for o in character if o.parent is None)
    root.location=(.70,-.83,0)
    scene=bpy.context.scene
    bpy.data.objects['review.ground'].location.z=-.307
    cam=bpy.data.objects['review.board'];cam.location=(7,-11,12);aim(cam,(0,0,.45));cam.data.ortho_scale=8.4
    for o in bpy.data.collections['REVIEW_ONLY'].objects:
        if o.type=='LIGHT':o.location*=3;o.data.energy*=9;o.data.size*=3
    ivory=material('test.number.ivory',(.69,.57,.36));ink=material('test.number.ink',(.045,.05,.05))
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.46,depth=.075,location=(-.55,-.72,.0375))
    obj=bpy.context.object;obj.name='TEST_ONLY.number-base';obj.data.materials.append(ivory)
    mod=obj.modifiers.new('rounded token','BEVEL');mod.width=.018;mod.segments=3
    bpy.ops.object.text_add(location=(-.55,-.72,.079));obj=bpy.context.object;obj.name='TEST_ONLY.number'
    obj.data.body='8';obj.data.align_x=obj.data.align_y='CENTER';obj.data.size=.5;obj.data.extrude=.001;obj.data.materials.append(ink)
    reports=[]
    for tile in ['forest','brick','stone','wheat','sheep','desert']:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets'/f'{tile}-tile'/'model.glb'))
        objects=list(bpy.context.selected_objects)
        anchor=next(o for o in objects if o.name=='anchor_robber')
        bpy.context.view_layer.update()
        if (anchor.matrix_world.translation-root.location).length>1e-5:raise ValueError('mount mismatch')
        reports.append(dict(tile=tile,anchor=list(anchor.matrix_world.translation),same_transform=True))
        render('board',WORK/('mount-'+tile+'.png'))
        for o in objects:bpy.data.objects.remove(o,do_unlink=True)
    (WORK/'mount-check.json').write_text(json.dumps(reports,indent=2))


if ARGS.mode=='build':build()
elif ARGS.mode=='export':export()
else:composition()
