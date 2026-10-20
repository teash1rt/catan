"""模块化承托、海岸与海面；组合样板仅用于 Blender，不参与游戏运行。

Blender --background --python-exit-code 1 --python scripts/assets/create_map_base.py
  -- --work-dir /private/tmp/<fresh-directory> --mode build|preview|export|composition
制作完成后先评审再导出；脚本不覆盖正式资产。
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / 'assets'
IDS = ['map-support-hex', 'coast-edge', 'coast-edge-harbor', 'coast-corner-convex',
       'coast-corner-concave', 'sea-surface']
TILES = ['forest-tile', 'brick-tile', 'stone-tile', 'wheat-tile', 'sheep-tile', 'desert-tile']
# 局部 X 沿顺时针海岸边界，+Y 指向海洋；所有端点共用此精确截面。
PROFILE = [(0, -.54), (0, 0), (.18, 0), (.28, 0), (.36, -.10),
           (.44, -.25), (.46, -.35), (.46, -.48), (.44, -.54)]
TRIM = .28
COL = None
M = {}


def material(name, color, rough=.84):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.diffuse_color = (*color, 1)
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Specular IOR Level'].default_value = .22
    return m


def mesh(name, vertices, faces, materials, indices=None):
    d = bpy.data.meshes.new(name); d.from_pydata(vertices, [], faces); d.update()
    o = bpy.data.objects.new(name, d); COL.objects.link(o)
    for m in materials: d.materials.append(m)
    if indices:
        for p, index in zip(d.polygons, indices): p.material_index = index
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
    return o


def reset(asset_id):
    global COL, M
    bpy.ops.wm.read_factory_settings(use_empty=True)
    COL = bpy.data.collections.new('ASSET_' + asset_id)
    bpy.context.scene.collection.children.link(COL)
    M = {k: material('base.' + k, c) for k, c in {
        'sand': (.48, .34, .18), 'sand-light': (.55, .40, .23),
        'sand-shade': (.40, .28, .15), 'wet-stone': (.23, .25, .22),
        'walnut': (.115, .065, .033), 'edge-inlay': (.29, .18, .080),
        'bottom': (.055, .042, .029), 'sea': (.032, .255, .33),
    }.items()}


def sweep(asset_id, sections, lowered=None):
    # 每个截面由中心与向外的斜接方向组成，宽度沿各边法线测量。
    lowered = lowered or set()
    verts = [(c.x+n.x*w, c.y+n.y*w, -.04 if i in lowered and j in [1,2,3] else z)
             for i,(c,n) in enumerate(sections) for j,(w,z) in enumerate(PROFILE)]
    count = len(PROFILE); faces = []; indices = []
    palette = [M[k] for k in ['sand', 'sand-light', 'sand-shade', 'wet-stone', 'walnut', 'edge-inlay', 'bottom']]
    for i in range(len(sections)-1):
        for j in range(count):
            f=(i*count+j, i*count+(j+1)%count, (i+1)*count+(j+1)%count, (i+1)*count+j)
            ps=[Vector(verts[k]) for k in f]
            area=(ps[1]-ps[0]).cross(ps[2]-ps[0]).length+(ps[2]-ps[0]).cross(ps[3]-ps[0]).length
            if area>1e-9:
                faces.append(f); indices.append([4, 1, 0, 2, 3, 3, 4, 5, 6][j])
    faces += [tuple(reversed(range(count))), tuple(range(len(verts)-count, len(verts)))]
    indices += [4, 4]
    mesh(asset_id + '.shore-profile', verts, faces, palette, indices)


def make_asset(asset_id):
    anchors = {}
    if asset_id == 'map-support-hex':
        # 完整半径的顶面贴合现有地形底部，不在其上叠加地形或基座。
        rings = [(3, -.30), (3, -.465), (2.985, -.495), (2.97, -.54)]
        verts = [(r*math.cos(i*math.tau/6), r*math.sin(i*math.tau/6), z)
                 for r,z in rings for i in range(6)]
        faces = [tuple(range(6))]; indices = [0]
        for row in range(3):
            for i in range(6):
                faces.append((row*6+i, row*6+(i+1)%6, (row+1)*6+(i+1)%6, (row+1)*6+i))
                indices.append([0, 1, 2][row])
        faces.append(tuple(reversed(range(18,24)))); indices.append(2)
        mesh(asset_id+'.body', verts, faces, [M['walnut'], M['edge-inlay'], M['bottom']], indices)
        anchors = {'anchor_tile': (0,0,0)}
    elif asset_id == 'sea-surface':
        mesh(asset_id+'.body', [(-1,-1,0), (1,-1,0), (1,1,0), (-1,1,0)], [(0,1,2,3)], [M['sea']])
    elif asset_id in ['coast-edge','coast-edge-harbor']:
        xs=[-1.5+TRIM, 1.5-TRIM]; lowered=set()
        if asset_id=='coast-edge-harbor':
            xs=[-1.22,-1.211,-1.211,-.869,-.869,.869,.869,1.211,1.211,1.22]
            lowered={2,3,6,7}
        sweep(asset_id, [(Vector((x,0)), Vector((0,1))) for x in xs],lowered)
        anchors = {'anchor_edge_a': (-1.5,0,0), 'anchor_edge_b': (1.5,0,0),
                   'anchor_join_a': (-1.22,0,0), 'anchor_join_b': (1.22,0,0), 'anchor_harbor': (0,0,0)}
    else:
        angle = math.radians(-60 if asset_id.endswith('convex') else 60)
        t = Vector((math.cos(angle), math.sin(angle)))
        n = Vector((-t.y, t.x)); miter = (Vector((0,1)) + n) / (1+n.y)
        sweep(asset_id, [(Vector((-TRIM,0)), Vector((0,1))), (Vector((0,0)),miter), (t*TRIM,n)])
        anchors = {'anchor_join_in': (-TRIM,0,0), 'anchor_join_out': (t.x*TRIM,t.y*TRIM,0)}
    root = bpy.data.objects.new(asset_id, None); COL.objects.link(root)
    root['contract'] = 'modular-map-base-v1'
    for o in list(COL.objects):
        if o != root: o.parent = root
    for name, pos in anchors.items():
        o = bpy.data.objects.new(name,None); COL.objects.link(o); o.parent=root; o.location=pos
    return root


def aim(o, target):
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()


def studio(large=False):
    c=bpy.data.collections.new('REVIEW_ONLY'); bpy.context.scene.collection.children.link(c)
    for name,pos,power,size in [('key',(-7,-10,15),2100,9), ('fill',(10,-2,10),1200,9), ('rim',(1,12,12),1700,8)]:
        d=bpy.data.lights.new('review.'+name,'AREA'); d.energy=power; d.size=size
        o=bpy.data.objects.new(d.name,d); c.objects.link(o); o.location=pos; aim(o,(0,0,0))
    views = [('board',(10,-17,26),23,(0,-.4,0)), ('close',(4,-9,7),9,(0,-2,0)),
             ('side',(7,-12,4),18,(0,0,-.2)), ('top',(0,0,26),21,(0,0,0))] if large else [
             ('board',(3,-5,7),7,(0,0,-.2)), ('close',(3,-4,3),4,(0,.15,-.2)),
             ('side',(2,-5,1),6,(0,0,-.2)), ('top',(0,0,8),7,(0,0,0))]
    for name,pos,scale,target in views:
        d=bpy.data.cameras.new('review.'+name); d.type='ORTHO'; d.ortho_scale=scale
        o=bpy.data.objects.new(d.name,d); c.objects.link(o); o.location=pos; aim(o,target)
    sc=bpy.context.scene; sc.camera=bpy.data.objects['review.board']
    sc.world=bpy.data.worlds.new('review.world'); sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes.get('Background'); bg.inputs[0].default_value=(.52,.56,.60,1); bg.inputs[1].default_value=.55
    sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=1500; sc.render.resolution_y=1200
    sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'


def save(path):
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                s=a.spaces.active; s.shading.type='RENDERED'; s.overlay.show_overlays=False
                s.region_3d.view_perspective='CAMERA'; s.region_3d.view_camera_zoom=0
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def stats(objects):
    bpy.context.view_layer.update(); pts=[]; tris=0; mats=set(); anchors={}
    for o in objects:
        if o.type=='MESH':
            o.data.calc_loop_triangles(); tris+=len(o.data.loop_triangles)
            pts += [o.matrix_world@v.co for v in o.data.vertices]
            mats.update(m.name for m in o.data.materials)
            assert all(math.isfinite(v) for p in o.data.vertices for v in p.normal)
        elif o.name.startswith('anchor_'): anchors[o.name]=list(o.matrix_world.translation)
        assert o.type in {'MESH','EMPTY'}
    assert pts and all(math.isfinite(v) for p in pts for v in p)
    return {'bounds':[[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]],
            'triangles':tris,'materials':sorted(mats),'anchors':anchors}


def verify_contract(asset_id, objects):
    objects=list(objects); meshes=[o for o in objects if o.type=='MESH']
    assert len(meshes)==1
    o=meshes[0]; bpy.context.view_layer.update()

    def height(x,y):
        hit,point,normal,_=o.ray_cast((x,y,2),(0,0,-1))
        assert hit, (asset_id,x,y,'missing support')
        assert normal.z>.99, (asset_id,x,y,'wrong top normal')
        return point.z

    if asset_id=='map-support-hex':
        assert abs(height(0,0)+.30)<1e-5
    elif asset_id=='sea-surface':
        assert abs(height(0,0))<1e-5
    elif asset_id.startswith('coast-edge'):
        for x in [-1.219,-.86,0,.86,1.219]:
            for y in [.01,.17,.279]: assert abs(height(x,y))<1e-5
        for x in [-1.04,1.04]:
            for y in [.01,.17,.279]:
                expected=-.04 if asset_id.endswith('harbor') else 0
                assert abs(height(x,y)-expected)<1e-5
        assert max(v.co.z for v in o.data.vertices)<=1e-6
    else:
        angle=math.radians(-60 if asset_id.endswith('convex') else 60)
        n=Vector((-math.sin(angle),math.cos(angle)))
        for i in range(72):
            p=Vector((.279*math.cos(i*math.tau/72),.279*math.sin(i*math.tau/72)))
            outside=(p.y>1e-6 or p.dot(n)>1e-6) if angle<0 else (p.y>1e-6 and p.dot(n)>1e-6)
            if outside: assert abs(height(*p))<1e-5
    return {'single_mesh':True,'ground_contact_rays':True}


def build(work):
    report={}
    for asset_id in IDS:
        dest=work/(asset_id+'.blend')
        if dest.exists(): raise FileExistsError(dest)
        reset(asset_id); make_asset(asset_id); report[asset_id]=stats(COL.objects)
        verify_contract(asset_id,COL.objects)
        studio(); save(dest)
    (work/'source-check.json').write_text(json.dumps(report,indent=2))
    print('BASE_BUILD',json.dumps(report))


def import_asset(path):
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(path))
    obs=set(bpy.data.objects)-before; roots=[o for o in obs if o.parent not in obs]
    assert len(roots)==1
    return roots[0],obs


def export(work):
    report={}; source=json.loads((work/'source-check.json').read_text())
    for asset_id in IDS:
        bpy.ops.wm.open_mainfile(filepath=str(work/(asset_id+'.blend')))
        col=bpy.data.collections['ASSET_'+asset_id]
        bpy.ops.object.select_all(action='DESELECT')
        for o in col.objects: o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(work/(asset_id+'.glb')),export_format='GLB',use_selection=True,
                                  export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _,obs=import_asset(work/(asset_id+'.glb')); got=stats(obs); expected=source[asset_id]
        verify_contract(asset_id,obs)
        assert got['triangles']==expected['triangles']
        assert set(got['anchors'])==set(expected['anchors'])
        for name, pos in got['anchors'].items(): assert (Vector(pos)-Vector(expected['anchors'][name])).length<1e-5
        assert max(abs(a-b) for a,b in zip(sum(got['bounds'],[]),sum(expected['bounds'],[])))<1e-5
        report[asset_id]=got; studio(); save(work/('review-reimport-'+asset_id+'.blend'))
    (work/'glb-check.json').write_text(json.dumps(report,indent=2))
    print('BASE_EXPORT',json.dumps(report))


def topology(cells):
    assert len(cells)==len(set(cells)), 'Duplicate axial cells'
    edges=defaultdict(list); vertices=defaultdict(set); centers=[]
    for index,(q,r) in enumerate(cells):
        center=Vector((4.5*q,3*math.sqrt(3)*(r+q/2),0)); centers.append(center)
        # 使用整数格点标识，避免独立构建的地块之间产生 float32 漂移。
        keys=[(round((3*q+x)*1.5,6), round((2*r+q+y)*1.5*math.sqrt(3),6))
              for x,y in [(2,0),(1,1),(-1,1),(-2,0),(-1,-1),(1,-1)]]
        for key in keys: vertices[key].add(index)
        for i in range(6):
            a,b=keys[(i+1)%6], keys[i]  # 顺时针定向；局部 +Y 指向外侧。
            edges[tuple(sorted([a,b]))].append((a,b,index))
    boundary=[v[0] for v in edges.values() if len(v)==1]
    assert all(len(v) in [1,2] for v in edges.values())
    assert len(edges)==6*len(cells)-sum(len(v)==2 for v in edges.values())
    incoming={b:(a,b,i) for a,b,i in boundary}; outgoing={a:(a,b,i) for a,b,i in boundary}
    assert len(incoming)==len(outgoing)==len(boundary) and set(incoming)==set(outgoing)
    corners=[]
    for key,(a,b,_) in incoming.items():
        _,end,_=outgoing[key]
        tin=(Vector(b)-Vector(a)).normalized(); tout=(Vector(end)-Vector(b)).normalized()
        turn=math.atan2(tin.x*tout.y-tin.y*tout.x,tin.dot(tout))
        assert abs(abs(turn)-math.pi/3)<1e-5
        convex=turn<0; assert len(vertices[key])==(1 if convex else 2)
        corners.append((key,tin,tout,'coast-corner-convex' if convex else 'coast-corner-concave'))
    return centers,edges,vertices,boundary,corners


def composition(work, source=False):
    bpy.ops.wm.read_factory_settings(use_empty=True); studio(True)
    cells=[(0,0),(1,0),(1,-1),(0,-1),(-1,0),(-1,1)]
    centers,edges,vertices,boundary,corners=topology(cells)
    cache={}

    def place(asset_id,pos=(0,0,0),angle=0):
        if asset_id not in cache:
            if source and asset_id in IDS:
                with bpy.data.libraries.load(str(work/(asset_id+'.blend')),link=False) as (_,dst):
                    dst.collections=['ASSET_'+asset_id]
                col=dst.collections[0]; bpy.context.scene.collection.children.link(col)
                obs=list(col.objects); root=next(o for o in obs if o.parent is None)
            else:
                path=work/(asset_id+'.glb') if asset_id in IDS else MODELS/asset_id/'model.glb'
                root,obs=import_asset(path); obs=list(obs)
            cache[asset_id]=(root,obs)
        else:
            original,obs=cache[asset_id]; mapping={o:o.copy() for o in obs}
            for old,new in mapping.items():
                bpy.context.scene.collection.objects.link(new)
                new.parent=mapping.get(old.parent)
            root=mapping[original]
        root.location=pos; root.rotation_mode='XYZ'; root.rotation_euler=(0,0,angle)
        return root

    for asset_id,center in zip(TILES,centers):
        place('map-support-hex',center); tile=place(asset_id,center)
        if asset_id!='desert-tile':
            anchor=next(o for o in tile.children_recursive if o.name.startswith('anchor_number'))
            bpy.context.view_layer.update(); place('number-token',anchor.matrix_world.translation)
    place('robber',centers[5]+Vector((.70,-.83,0)))
    port_edge=min((e for e in boundary if abs(e[0][1]-e[1][1])<1e-5),key=lambda e:e[0][1])
    edge_roots={}
    for a,b,index in boundary:
        va,vb=Vector((*a,0)),Vector((*b,0)); t=(vb-va).normalized()
        edge_roots[(a,b)]=place('coast-edge-harbor' if (a,b,index)==port_edge else 'coast-edge',(va+vb)/2,math.atan2(t.y,t.x))
    bpy.context.view_layer.update()
    def mesh_points(root):
        return [o.matrix_world@v.co for o in root.children_recursive if o.type=='MESH' for v in o.data.vertices]
    for key,tin,tout,asset_id in corners:
        corner=place(asset_id,(*key,0),math.atan2(tin.y,tin.x)); bpy.context.view_layer.update()
        actual_corner=mesh_points(corner)
        # 截面上的每个顶点都必须出现在两个资产经过变换后的实际网格中。
        n1=Vector((-tin.y,tin.x)); n2=Vector((-tout.y,tout.x)); v=Vector(key)
        for t,n,sign in [(tin,n1,-1),(tout,n2,1)]:
            corner_end=v+t*TRIM*sign
            edge_center=v+t*1.5*sign
            edge_end=edge_center-t*(1.5-TRIM)*sign
            assert (corner_end-edge_end).length<1e-5
            edge_root=next(root for (a,b),root in edge_roots.items() if (b if sign<0 else a)==key)
            actual_edge=mesh_points(edge_root)
            for w,z in PROFILE:
                xy=corner_end+n*w; expected=Vector((xy.x,xy.y,z))
                assert min((p-expected).length for p in actual_corner)<2e-5
                assert min((p-expected).length for p in actual_edge)<2e-5
    sea=place('sea-surface',(0,0,-.22)); sea.scale=(18,16,1)
    # 北侧凹湾刻意不自动填入港口。
    # 选择无遮挡的南侧水平海岸作为测量用的有效样例。
    a,b,index=port_edge
    va,vb=Vector((*a,0)),Vector((*b,0)); t=(vb-va).normalized(); mid=(va+vb)/2
    angle=math.atan2(t.y,t.x); harbor=place('harbor',mid,angle)
    bpy.context.view_layer.update()
    anchor=next(o for o in harbor.children_recursive if o.name.startswith('anchor_trade'))
    place('harbor-marker-generic',anchor.matrix_world.translation,angle)
    place('road',mid,angle); place('settlement',va); place('city',vb)
    # 对凸多边形占地执行精确的分离轴检测，允许边界接触。
    def overlaps(poly_a,poly_b):
        for polygon in [poly_a,poly_b]:
            for p,q in zip(polygon,polygon[1:]+polygon[:1]):
                d=q-p; axis=Vector((-d.y,d.x,0)).normalized()
                aa=[v.dot(axis) for v in poly_a]; bb=[v.dot(axis) for v in poly_b]
                if max(aa)<=min(bb)+1e-5 or max(bb)<=min(aa)+1e-5: return False
        return True
    polygons=[[center+Vector((3*math.cos(i*math.tau/6),3*math.sin(i*math.tau/6),0)) for i in range(6)] for center in centers]
    def harbor_footprint(edge):
        a,b,_=edge; a,b=Vector((*a,0)),Vector((*b,0)); tangent=(b-a).normalized(); middle=(a+b)/2
        return [middle+tangent*x+Vector((-tangent.y,tangent.x,0))*y for x,y in [(-1.24,0),(1.24,0),(1.24,1.975),(-1.24,1.975)]]
    def harbor_clear(edge):
        return not any(overlaps(harbor_footprint(edge),polygon) for polygon in polygons)
    assert harbor_clear(port_edge)
    harbor_rejected=sum(not harbor_clear(edge) for edge in boundary)
    footprints=[harbor_footprint(edge) for edge in boundary]
    harbor_conflicts=sum(overlaps(a,b) for i,a in enumerate(footprints) for b in footprints[i+1:])
    assert harbor_conflicts>0, 'Fixture must reject conflicting simultaneous ports'
    close=bpy.data.objects['review.close']; close.location=mid+Vector((3,-5,5)); aim(close,mid+Vector((0,-.6,0))); close.data.ortho_scale=6
    # 将专用接缝检查相机对准凹角顶点。
    key,*_=next(c for c in corners if c[3]=='coast-corner-concave')
    c=bpy.data.cameras.new('review.concave'); c.type='ORTHO'; c.ortho_scale=6
    o=bpy.data.objects.new(c.name,c); bpy.context.scene.collection.objects.link(o)
    o.location=Vector((*key,0))+Vector((1,2,6)); aim(o,(*key,0))
    save(work/('review-source-map.blend' if source else 'review-map.blend'))
    # 额外的纯拓扑样例覆盖带孔地图、分离岛屿与 19 地块地图。
    fixtures={'six':cells,'single':[(0,0)],'pair':[(0,0),(1,0)],
              'ring':[(1,0),(1,-1),(0,-1),(-1,0),(-1,1),(0,1)],
              'islands':[(0,0),(3,0)],
              'nineteen':[(q,r) for q in range(-2,3) for r in range(-2,3) if abs(q+r)<=2]}
    checks={'harbor_clearance':{'accepted_selected_port':True,'rejected_coast_edges':harbor_rejected,
                               'method':'convex footprint SAT against terrain and other ports',
                               'conflicting_port_pairs':harbor_conflicts,'adjacent_ports_visual_tested':False}}
    for name,shape in fixtures.items():
        _,es,vs,bs,cs=topology(shape)
        checks[name]={'cells':len(shape),'unique_edges':len(es),'unique_vertices':len(vs),
                      'coast_edges':len(bs),'convex':sum(c[3].endswith('convex') for c in cs),
                      'concave':sum(c[3].endswith('concave') for c in cs)}
    (work/('source-composition-check.json' if source else 'composition-check.json')).write_text(json.dumps(checks,indent=2))
    print('BASE_COMPOSITION',json.dumps(checks))


def main():
    p=argparse.ArgumentParser(); p.add_argument('--work-dir',type=Path,required=True)
    p.add_argument('--mode',choices=['build','export','composition','preview'],default='build')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]); work=args.work_dir.resolve()
    if not str(work).startswith(('/private/tmp/','/tmp/')): raise ValueError('Use an external temporary directory')
    work.mkdir(parents=True,exist_ok=True)
    if args.mode=='build': build(work); composition(work,source=True)
    elif args.mode=='export': export(work)
    else: composition(work,source=args.mode=='preview')


if __name__=='__main__': main()
