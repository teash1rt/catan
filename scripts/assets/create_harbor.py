"""Stylized base-game harbor and interchangeable trade plaques.

Blender --background --python-exit-code 1 --python scripts/assets/create_harbor.py
    -- --work-dir /private/tmp/... --mode build|preview|export|composition
Build in a new temporary directory; visually review before export/promotion.
No official images/textures or external fonts are redistributed.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--mode', choices=['build', 'preview', 'export', 'composition'], default='build')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
WORK = args.work_dir.resolve()
if not str(WORK).startswith(('/private/tmp/', '/tmp/')):
    raise ValueError('Drafts must be outside the project in a temporary directory')
WORK.mkdir(parents=True, exist_ok=True)
KINDS = ['generic', 'lumber', 'brick', 'ore', 'grain', 'wool']
IDS = ['harbor'] + ['harbor-marker-' + k for k in KINDS]
TRADE = (-.79, 1.64, .095)
COL = None
M = {}


def mat(name, color, rough=.83):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.diffuse_color = (*color, 1)
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Specular IOR Level'].default_value = .24
    return m


def collection(name):
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c


def assign(o, name, material):
    o.name = name
    for c in list(o.users_collection): c.objects.unlink(o)
    COL.objects.link(o)
    if material: o.data.materials.append(material)
    return o


def bevel(o, width=.008, segments=2):
    b = o.modifiers.new('soft carved edges', 'BEVEL'); b.width = width; b.segments = segments
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=b.name)
    return o


def box(name, loc, dims, material, edge=.006):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = assign(bpy.context.object, name, material); o.scale = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return bevel(o, edge) if edge else o


def mesh(name, vertices, faces, material):
    data = bpy.data.meshes.new(name); data.from_pydata(vertices, [], faces); data.update()
    o = bpy.data.objects.new(name, data); COL.objects.link(o)
    if material: data.materials.append(material)
    return o


def line(name, points, radius, material, closed=False):
    data = bpy.data.curves.new(name, 'CURVE'); data.dimensions = '3D'
    data.bevel_depth = radius; data.bevel_resolution = 1; data.resolution_u = 1
    s = data.splines.new('POLY'); s.points.add(len(points)-1)
    for p, xyz in zip(s.points, points): p.co = (*xyz, 1)
    s.use_cyclic_u = closed
    o = bpy.data.objects.new(name, data); COL.objects.link(o); data.materials.append(material)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o; bpy.ops.object.convert(target='MESH')
    return bpy.context.object


def cylinder(name, loc, radius, depth, material, vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    return bevel(assign(bpy.context.object, name, material), .003)


def beam(name, a, b, radius, material):
    a, b = Vector(a), Vector(b)
    o = cylinder(name, (a+b)/2, radius, (b-a).length, material)
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return o


def reset(asset_id):
    global COL, M
    bpy.ops.wm.read_factory_settings(use_empty=True)
    COL = collection('ASSET_' + asset_id)
    palette = {
        'oak': (.31,.145,.047), 'oak-light': (.43,.245,.099),
        'oak-shade': (.23,.096,.027), 'dark-wood': (.115,.049,.019),
        'linen': (.79,.70,.49), 'linen-shade': (.64,.54,.35),
        'rope': (.46,.32,.14), 'iron': (.075,.093,.102),
        'ivory': (.82,.74,.54), 'ink': (.074,.055,.026),
        'brick': (.43,.11,.054), 'ore': (.25,.33,.39),
        'grain': (.77,.45,.075), 'wool': (.87,.81,.65),
        'leaf': (.17,.31,.07),
    }
    M = {k: mat('harbor.' + k, v) for k,v in palette.items()}


def aim(o, target):
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()


def studio(asset_id):
    global COL
    saved = COL; COL = collection('REVIEW_ONLY')
    box('review.ground', (0,0,-.355), (200,200,.02), mat('review.neutral',(.26,.29,.30)), 0)
    for name,pos,power,size in [('key',(-3,-4,7),600,5),('fill',(4,-1,4),260,4),('rim',(1,5,5),380,4)]:
        d = bpy.data.lights.new('review.'+name, 'AREA'); d.energy=power; d.size=size
        o = bpy.data.objects.new(d.name,d); COL.objects.link(o); o.location=pos; aim(o,(0,1,0))
    for name,pos,scale in [('close',(3,-4,4),3.6),('side',(3,-4,1.25),3.7),('board',(1,-3,6),5),('top',(0,1,7),3.5)]:
        d=bpy.data.cameras.new('review.'+name); d.type='ORTHO'; d.ortho_scale=scale
        o=bpy.data.objects.new(d.name,d); COL.objects.link(o); o.location=pos; aim(o,(0,1.05,.22))
    sc=bpy.context.scene; sc.camera=bpy.data.objects['review.close']
    sc.world=bpy.data.worlds.new('review.world'); sc.world.use_nodes=True
    bg=next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND')
    bg.inputs[0].default_value=(.52,.56,.60,1); bg.inputs[1].default_value=.45
    sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=1400; sc.render.resolution_y=1100
    sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'
    if asset_id != 'harbor':
        sc.camera.location=(.4,-.7,1.5); aim(sc.camera,(0,0,.05)); sc.camera.data.ortho_scale=1.0
    COL=saved


def configure_ui():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                s=area.spaces.active; s.shading.type='RENDERED'; s.overlay.show_overlays=False
                s.region_3d.view_perspective='CAMERA'; s.region_3d.view_camera_zoom=5


def root_and_anchors(asset_id):
    root=bpy.data.objects.new(asset_id,None); COL.objects.link(root)
    root['asset_id']=asset_id; root['contract']='coast-harbor-v1' if asset_id=='harbor' else 'harbor-marker-v1'
    for o in list(COL.objects):
        if o != root:
            o.parent=root
            bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
            bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    if asset_id=='harbor':
        root['sea_direction']='+Y'; root['sea_level']=-.22
        points={'anchor_edge_a':(-1.5,0,0),'anchor_edge_b':(1.5,0,0),'anchor_trade':TRADE}
    else:
        root['content_is_visual_only']=True
        points={}
    for name,loc in points.items():
        o=bpy.data.objects.new(name,None); COL.objects.link(o); o.parent=root; o.location=loc
    bpy.context.view_layer.update()
    return root


def harbor():
    # Two inward-set fingers make the association with both coast vertices legible.
    # Low landing tongues touch the terrain at y=0. Under the road strip their
    # top stays at z=0, so an optional road rests above them without intersection.
    for x in [-1.04,1.04]:
        v=[(x+dx,y,z) for dx in [-.17,.17] for y,z in [(0,0),(.18,0),(.30,.065),(.30,.022),(.18,-.038),(0,-.038)]]
        f=[tuple(reversed(range(6))),tuple(range(6,12))]
        f += [(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)]
        mesh('pier.shore-landing',v,f,M['oak'])
        for side in [-1,1]:
            box('pier.longitudinal-beam',(x+side*.125,.74,-.024),(.060,.88,.075),M['dark-wood'])
        for j in range(9):
            y=.30+(j+.5)*.09
            box('pier.deck-plank',(x,y,.035),(.38,.082,.065),M['oak-light'] if j%3==0 else M['oak'],.007)
        for y in [.39,1.01]:
            for sign in [-1,1]:
                px=x+sign*.145
                cylinder('pier.pile',(px,y,-.085),.047,.43,M['oak-shade'])
                cylinder('pier.endgrain-cap',(px,y,.137),.051,.020,M['oak-light'])
                for z in [.071,.091]:
                    line('pier.lashing',[(px+.05*math.cos(t*math.tau/16),y+.05*math.sin(t*math.tau/16),z) for t in range(16)],.005,M['rope'],True)
    for x in [-.82,-.3,.3,.82]:
        cylinder('quay.support',(x,1.02,-.16),.042,.34,M['oak-shade'])
    for y in [.91,1.15]:
        box('quay.cross-beam',(0,y,-.006),(2.22,.064,.075),M['dark-wood'])
    for i in range(23):
        x=-1.13+(i+.5)*2.26/23
        box('quay.cross-plank',(x,1.035,.047),(2.26/23-.008,.36,.07),M['oak-light'] if i%5==0 else M['oak'],.007)
        if i%3==0:
            # Restrained incised-grain rhythm, not a full noisy surface texture.
            line('quay.grain',[(x-.02, .94,.083),(x-.014,1.02,.084),(x-.022,1.12,.083)],.0018,M['oak-shade'])
    # Small bracket holds a removable plaque; no label is baked into the pier.
    box('trade.bracket',(-.79,1.43,.012),(.12,.75,.11),M['dark-wood'])
    box('trade.platform',(-.79,1.64,.067),(.76,.67,.056),M['oak'],.035)
    # Rounded lapstrake merchant hull, long axis X, pointed ends, open interior.
    cx,cy=.36,1.61
    n=40
    rings=[(.55,.12,-.225),(.68,.237,-.115),(.77,.277,.04),(.77,.277,.16)]
    verts=[]
    for a,b,z in rings:
        for i in range(n):
            t=math.tau*i/n
            verts.append((cx+a*math.cos(t),cy+b*math.sin(t),z+.085*abs(math.cos(t))**5))
    faces=[tuple(reversed(range(n)))]
    for r in range(len(rings)-1):
        for i in range(n): faces.append((r*n+i,r*n+(i+1)%n,(r+1)*n+(i+1)%n,(r+1)*n+i))
    o=mesh('ship.hull',verts,faces,M['oak-shade'])
    solid=o.modifiers.new('solid timber hull','SOLIDIFY'); solid.thickness=.025
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=solid.name)
    bevel(o,.008)
    for p in o.data.polygons: p.use_smooth=True
    for k in range(1,4):
        a,b,z=rings[k]
        pts=[(cx+a*math.cos(t*math.tau/n),cy+b*math.sin(t*math.tau/n),z+.085*abs(math.cos(t*math.tau/n))**5) for t in range(n)]
        line('ship.strake' if k<3 else 'ship.gunwale',pts,.012 if k<3 else .021,M['oak-light'],True)
    for i in range(11):
        x=(i-5)*.107
        half=.205*math.sqrt(max(0,1-(x/.71)**2))
        box('ship.deck',(cx+x,cy,-.002),(.10,half*2,.035),M['oak-light'] if i%4==0 else M['oak'],.004)
    for x in [cx-.40,cx+.42]:
        box('ship.thwart',(x,cy,.105),(.087,.46,.04),M['oak-light'])
    mastx=cx-.08
    beam('ship.mast',(mastx,cy,-.01),(mastx,cy,1.15),.025,M['dark-wood'])
    beam('ship.yard',(mastx-.46,cy,1.00),(mastx+.46,cy,1.00),.017,M['oak'])
    # Broad, gently billowed square linen sail with shaped foot and panel seams.
    def sail_point(u,v):
        w=.42+.065*math.sin(math.pi*v)
        x=mastx+(2*u-1)*w
        y=cy-.032-.12*math.sin(math.pi*u)*math.sin(math.pi*v)
        z=1.00-.57*v+.045*math.sin(math.pi*u)*v
        return (x,y,z)
    nu,nv=12,8
    vs=[sail_point(i/nu,j/nv) for j in range(nv+1) for i in range(nu+1)]
    fs=[(j*(nu+1)+i,j*(nu+1)+i+1,(j+1)*(nu+1)+i+1,(j+1)*(nu+1)+i) for j in range(nv) for i in range(nu)]
    o=mesh('ship.linen-sail',vs,fs,M['linen']); o.data.materials.append(M['linen-shade'])
    for j,p in enumerate(o.data.polygons): p.use_smooth=True; p.material_index=1 if j%nu in [0,11] else 0
    mod=o.modifiers.new('woven cloth thickness','SOLIDIFY'); mod.thickness=.006
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    for u in [0,.25,.5,.75,1]: line('sail.panel-seam',[sail_point(u,j/16) for j in range(17)],.0025,M['linen-shade'])
    for v in [0,1]: line('sail.hem',[sail_point(i/24,v) for i in range(25)],.006,M['rope'])
    for x in [cx-.65,cx+.65]:
        line('ship.stay',[(mastx,cy,1.13),(x,cy,.18)],.005,M['rope'])
    # Single subdued pennant; no player ownership color on a shared harbor.
    flag=mesh('ship.pennant',[(mastx,cy,1.14),(mastx+.24,cy+.025,1.11),(mastx+.17,cy,1.05),(mastx,cy,1.07)],[(0,1,2,3)],M['linen-shade'])
    mod=flag.modifiers.new('pennant thickness','SOLIDIFY'); mod.thickness=.004
    bpy.context.view_layer.objects.active=flag; bpy.ops.object.modifier_apply(modifier=mod.name)
    for x in [cx-.55,cx+.52]:
        line('ship.mooring',[(x,cy-.22,.14),(x,1.31,.085),(x,1.16,.09)],.007,M['rope'])
    # Only two low-profile cargo parcels, to express trade without clutter.
    for x,y,s in [(cx+.21,cy+.07,.13),(cx+.40,cy+.02,.10)]:
        box('ship.cargo',(x,y,.08),(s,s,.12),M['oak-light'])
        box('ship.cargo-strap',(x,y,.143),(.018,s+.003,.012),M['dark-wood'],.002)
    # Rivets stay sparse and larger than texture noise.
    for x in [-1.04,1.04]:
        for y in [.51,.87]:
            for dx in [-.12,.12]: cylinder('pier.peg',(x+dx,y,.069),.009,.006,M['dark-wood'],8)


def text_mesh(body, loc, size, material, name):
    d=bpy.data.curves.new(name,'FONT'); d.body=body; d.align_x='CENTER'; d.align_y='CENTER'
    d.size=size; d.extrude=.0015; d.bevel_depth=.0005; d.resolution_u=6
    o=bpy.data.objects.new(name,d); COL.objects.link(o); o.location=loc; d.materials.append(material)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target='MESH'); return bpy.context.object


def pebble(name, loc, scale, material, subdiv=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv,radius=1,location=loc)
    o=assign(bpy.context.object,name,material); o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return bevel(o,.007)


def marker(kind):
    box('marker.walnut-frame',(0,0,.025),(.72,.62,.05),M['dark-wood'],.065)
    box('marker.parchment',(0,0,.055),(.667,.567,.025),M['ivory'],.058)
    text_mesh('3:1' if kind=='generic' else '2:1',(0,-.143,.07),.205,M['ink'],'marker.ratio')
    if kind=='generic':
        text_mesh('?',(0,.115,.07),.225,M['ink'],'marker.generic')
    elif kind=='lumber':
        for x,y in [(-.115,.08),(0,.13),(.12,.10)]:
            beam('icon.log',(x-.05,y-.045,.1),(x+.04,y+.07,.1),.041,M['oak-shade'])
            beam('icon.endgrain',(x-.054,y-.05,.1),(x-.045,y-.039,.1),.032,M['oak-light'])
    elif kind=='brick':
        for x,y in [(-.12,.055),(.07,.055),(-.025,.15)]:
            box('icon.brick',(x,y,.105),(.17,.085,.068),M['brick'],.012)
    elif kind=='ore':
        for x,y,s in [(-.11,.075,.075),(.09,.08,.09),(-.015,.17,.06)]:
            pebble('icon.ore',(x,y,.103),(s,s*.78,s*.66),M['ore'])
    elif kind=='grain':
        for x in [-.11,0,.11]:
            line('icon.stem',[(x-.025,.00,.081),(x,.22,.081)],.008,M['grain'])
            for j in range(3):
                for s in [-1,1]:
                    o=pebble('icon.kernel',(x+s*.027,.10+j*.04,.094),(.023,.036,.015),M['grain'],2)
                    o.rotation_euler.z=s*-.55
        box('icon.tie',(0,.025,.09),(.29,.025,.018),M['rope'])
    else:
        for x,y,s in [(-.09,.10,.071),(0,.10,.089),(.09,.1,.071),(0,.17,.058)]:
            o=pebble('icon.fleece',(x,y,.102),(s,s*.8,.036),M['wool'],2)
            for p in o.data.polygons: p.use_smooth=True
        pebble('icon.sheep-face',(.163,.09,.095),(.047,.035,.027),M['oak-shade'],2)
        for x in [-.08,.08]: box('icon.hoof',(x,.029,.086),(.023,.05,.018),M['oak-shade'])


def bounds_check(objects,asset_id):
    pts=[]; tris=0; mats=set()
    for o in objects:
        assert o.type in {'EMPTY','MESH'}, (o.name,o.type)
        if o.type!='MESH': continue
        o.data.calc_loop_triangles(); tris+=len(o.data.loop_triangles)
        pts.extend(o.matrix_world@v.co for v in o.data.vertices)
        assert all(math.isfinite(c) for v in o.data.vertices for c in (*v.co,*v.normal))
        mats.update(m.name for m in o.data.materials if m)
    lo=[min(p[i] for p in pts) for i in range(3)]; hi=[max(p[i] for p in pts) for i in range(3)]
    if asset_id=='harbor':
        assert lo[0]>=-1.3 and hi[0]<=1.3 and lo[1]>=-1e-6 and hi[1]<=2.02
        assert lo[2]>=-.33 and hi[2]<=1.2
        for name,expected in {'anchor_edge_a':(-1.5,0,0),'anchor_edge_b':(1.5,0,0),'anchor_trade':TRADE}.items():
            a=next(o for o in objects if o.name==name)
            assert (a.matrix_world.translation-Vector(expected)).length<1e-5
        # Conservative triangle AABBs guarantee endpoint-cylinder exclusion,
        # including triangle interiors, not only vertices.
        for o in objects:
            if o.type!='MESH': continue
            for tri in o.data.loop_triangles:
                ps=[o.matrix_world@o.data.vertices[i].co for i in tri.vertices]
                xmin,xmax=min(p.x for p in ps),max(p.x for p in ps)
                ymin,ymax=min(p.y for p in ps),max(p.y for p in ps)
                for endpoint in [-1.5,1.5]:
                    dx=max(xmin-endpoint,0,endpoint-xmax); dy=max(ymin,0,-ymax)
                    assert math.hypot(dx,dy)>=.27999
                # Clip triangles to the road footprint, so crossings of a
                # triangle interior cannot be missed by a vertex-only test.
                clipped=ps
                for axis,bound,sign in [(0,1.2,1),(0,-1.2,-1),(1,.18,1),(1,-.18,-1)]:
                    out=[]
                    for a,b in zip(clipped,clipped[1:]+clipped[:1]):
                        da=(a[axis]-bound)*sign; db=(b[axis]-bound)*sign
                        if da<=0: out.append(a)
                        if (da<=0)!=(db<=0): out.append(a+(b-a)*(da/(da-db)))
                    clipped=out
                if clipped: assert max(p.z for p in clipped)<=1e-6
    else:
        assert lo[0]>=-.3601 and hi[0]<=.3601 and lo[1]>=-.3101 and hi[1]<=.3101
        assert abs(lo[2])<1e-5 and hi[2]<.2
    return dict(bounds=[lo,hi],triangles=tris,materials=sorted(mats),meshes=sum(o.type=='MESH' for o in objects))


def save(path):
    configure_ui(); bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def build():
    report={}
    for asset_id in IDS:
        path=WORK/(asset_id+'.blend')
        if path.exists(): raise FileExistsError(path)
        reset(asset_id)
        harbor() if asset_id=='harbor' else marker(asset_id.removeprefix('harbor-marker-'))
        root_and_anchors(asset_id); report[asset_id]=bounds_check(list(COL.objects),asset_id)
        studio(asset_id); save(path)
    (WORK/'source-check.json').write_text(json.dumps(report,indent=2))
    print('HARBOR_BUILD',json.dumps(report))


def import_asset(path):
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(path))
    objects=set(bpy.data.objects)-before
    roots=[o for o in objects if o.parent not in objects]; assert len(roots)==1
    return roots[0],objects


def preview():
    bpy.ops.wm.read_factory_settings(use_empty=True); studio('harbor')
    for i,kind in enumerate(KINDS):
        asset_id='harbor-marker-'+kind
        with bpy.data.libraries.load(str(WORK/(asset_id+'.blend')),link=False) as (_,dest):
            dest.collections=['ASSET_'+asset_id]
        bpy.context.scene.collection.children.link(dest.collections[0])
        root=next(o for o in dest.collections[0].objects if o.parent is None)
        root.location=((i%3-1)*.88,(i//3)*.85,0)
    cam=bpy.data.objects['review.close']; cam.location=(.2,-2,5); aim(cam,(0,.43,0)); cam.data.ortho_scale=3.3
    bpy.data.objects['review.ground'].location.z=-.01
    save(WORK/'review-source-markers.blend')


def export():
    report={}
    for asset_id in IDS:
        bpy.ops.wm.open_mainfile(filepath=str(WORK/(asset_id+'.blend')))
        col=bpy.data.collections['ASSET_'+asset_id]
        items=[o for o in col.objects if o.type=='MESH']
        bpy.ops.object.select_all(action='DESELECT')
        for o in items: o.select_set(True)
        bpy.context.view_layer.objects.active=items[0]; bpy.ops.object.join()
        o=bpy.context.object; o.name=asset_id+'.body'
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for o in col.objects: o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(WORK/(asset_id+'.glb')),export_format='GLB',use_selection=True,
                                  export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
        # Truly independent import: factory reset removes original data and names.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        root,objects=import_asset(WORK/(asset_id+'.glb'))
        bpy.context.view_layer.update(); report[asset_id]=bounds_check(objects,asset_id)
        studio(asset_id); save(WORK/('review-reimport-'+asset_id+'.blend'))
    source=json.loads((WORK/'source-check.json').read_text())
    for k in IDS:
        for a,b in zip(sum(source[k]['bounds'],[]),sum(report[k]['bounds'],[])): assert abs(a-b)<1e-5
        assert source[k]['triangles']==report[k]['triangles']
    (WORK/'glb-check.json').write_text(json.dumps(report,indent=2))
    print('HARBOR_EXPORT',json.dumps(report))


def composition():
    global COL
    bpy.ops.wm.read_factory_settings(use_empty=True); studio('harbor'); COL=collection('REVIEW_CONTEXT')
    sea=mat('review.sea',(.027,.245,.32),.72)
    box('review.sea', (0,1,-.26),(28,24,.08),sea,0)
    model_dir=ROOT/'assets'
    r,_=import_asset(model_dir/'wheat-tile'/'model.glb'); r.location=(0,-3*math.sqrt(3)/2,0)
    for asset,x in [('settlement',-1.5),('city',1.5)]:
        r,_=import_asset(model_dir/asset/'model.glb'); r.location=(x,0,0)
    import_asset(model_dir/'road'/'model.glb')
    harbor_root,harbor_objects=import_asset(WORK/'harbor.glb')
    rotations=[]
    vertices=[Vector((3*math.cos(i*math.pi/3),3*math.sin(i*math.pi/3),0)) for i in range(6)]
    for i in range(6):
        a,b=vertices[i],vertices[(i+1)%6]; center=(a+b)/2
        # Order the tangent clockwise, so local +Y is the outward sea normal.
        tangent=(a-b).normalized()
        harbor_root.rotation_mode='XYZ'; harbor_root.rotation_euler.z=math.atan2(tangent.y,tangent.x)
        harbor_root.location=center; bpy.context.view_layer.update()
        ends=[o.matrix_world.translation.copy() for o in harbor_objects if o.name.startswith('anchor_edge_')]
        assert all(min((p-v).length for v in [a,b])<1e-5 for p in ends)
        outward=harbor_root.matrix_world.to_3x3()@Vector((0,1,0))
        assert outward.dot(center.normalized())>.99999
        rotations.append({'edge':i,'endpoints_aligned':True,'faces_sea':True})
    harbor_root.location=(0,0,0); harbor_root.rotation_euler=(0,0,0)
    r,_=import_asset(WORK/'harbor-marker-generic.glb'); r.location=TRADE
    r,objects=import_asset(model_dir/'number-token'/'model.glb'); r.location=(-.55,-3*math.sqrt(3)/2-.72,0)
    text_mesh('8',(-.55,-3*math.sqrt(3)/2-.72+.055,.103),.4,mat('review.number',(.42,.025,.018)),'review.digit')
    cam=bpy.data.objects['review.close']; cam.location=(3,8,10); aim(cam,(0,-1.15,.15)); cam.data.ortho_scale=8.5
    save(WORK/'review-coast.blend')
    # All six interchangeable plaques at one scale and one neutral light setup.
    bpy.ops.wm.read_factory_settings(use_empty=True); studio('harbor')
    for i,kind in enumerate(KINDS):
        r,_=import_asset(WORK/('harbor-marker-'+kind+'.glb')); r.location=((i%3-1)*.88,(i//3)*.85,0)
    cam=bpy.data.objects['review.close']; cam.location=(.2,-2,5); aim(cam,(0,.43,0)); cam.data.ortho_scale=3.3
    bpy.data.objects['review.ground'].location.z=-.01
    save(WORK/'review-markers.blend')
    # Source preview combines authored parts without writing anything to exports.
    bpy.ops.wm.open_mainfile(filepath=str(WORK/'harbor.blend'))
    r,_=import_asset(WORK/'harbor-marker-generic.glb'); r.location=TRADE
    save(WORK/'review-assembled.blend')
    (WORK/'composition-check.json').write_text(json.dumps({'six_edge_transforms':rotations,
        'sea_level':-.22,'road_strip_no_positive_geometry':True,
        'convex_single_coast_visual_review_required':True,'concave_bay_collision_tested':False,
        'runtime_tested':False},indent=2))


{'build':build,'preview':preview,'export':export,'composition':composition}[args.mode]()
