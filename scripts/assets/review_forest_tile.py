"""只读检查几何体，并创建独立的组合与 GLB 评审场景。

用法：Blender --background model.blend --python this_file -- --review-dir /tmp/...
添加 --glb 可在同一源摄影棚中检查导出文件。
不会保存或修改磁盘上已打开的源文件。
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import closest_point_on_tri

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_tile_anchors import inspect
parser = argparse.ArgumentParser()
parser.add_argument('--glb', action='store_true')
parser.add_argument('--review-dir', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
IS_GLB = args.glb
REVIEW = Path(args.review_dir).resolve()
if not str(REVIEW).startswith(('/private/tmp/', '/tmp/')):
    raise ValueError('Review output must be temporary, outside the project')
if IS_GLB:
    for obj in list(bpy.data.collections['ASSET_forest_tile'].objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/forest-tile/model.glb'))
    assets = list(bpy.context.selected_objects)
else:
    assets = list(bpy.data.collections['ASSET_forest_tile'].objects)
bpy.context.view_layer.update()
report = {'stage':'GLB reimport' if IS_GLB else 'source','errors':[]}
points, triangles, meshes = [],0,set()
for obj in assets:
    if obj.type != 'MESH':
        continue
    meshes.add(obj.data.name)
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
    world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    points.extend(world)
    if obj.name.startswith(('tree.','detail.')):
        if any(any(p.x*math.cos(math.pi/6+n*math.pi/3)+p.y*math.sin(math.pi/6+n*math.pi/3)>3*math.sqrt(3)/2-0.28+1e-5 for n in range(6)) for p in world):
            report['errors'].append(obj.name+': crosses reserved edge strip')
        for name, radius, height in [('anchor_number',0.50,0.40),('anchor_robber',0.34,1.15)]:
            anchor = bpy.data.objects[name].matrix_world.translation
            test=Vector((anchor.x,anchor.y,0))
            for tri in obj.data.loop_triangles:
                xyz=[world[v] for v in tri.vertices]
                if max(p.z for p in xyz)<anchor.z or min(p.z for p in xyz)>anchor.z+height:
                    continue
                xy=[Vector((p.x,p.y,0)) for p in xyz]
                if (closest_point_on_tri(test,*xy)-test).length < radius-1e-5:
                    report['errors'].append(obj.name+': intersects '+name)
                    break
report['bounds_blender']=[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
report['triangles_instances_included']=triangles
report['mesh_objects']=sum(o.type=='MESH' for o in assets)
report['unique_meshes']=len(meshes)
report['materials']=len({m.name for o in assets if o.type=='MESH' for m in o.data.materials})
report['anchors']={name:list(bpy.data.objects[name].matrix_world.translation) for name in ['anchor_number','anchor_robber']}
report['unexpected_camera_lights']=[o.name for o in assets if o.type in {'CAMERA','LIGHT'}]
# 将实际地面纳入检查，并按高度裁剪三角面。
# 旧版仅检查树木和细节，会漏掉侵入挂点圆柱的地形。
report['errors'].extend(inspect(assets)['errors'])
REVIEW.mkdir(parents=True,exist_ok=True)
(REVIEW/('glb-check.json' if IS_GLB else 'source-check.json')).write_text(json.dumps(report,indent=2))
print('FOREST_CHECK',json.dumps(report))
if report['errors']:
    raise RuntimeError(report['errors'])

scene=bpy.context.scene
if IS_GLB:
    # 单独保存评审场景，原始摄影棚不进入运行时 GLB。
    scene.camera=bpy.data.objects['review.board']
    scene.render.filepath=str(REVIEW/'glb-board.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(REVIEW/'glb-review.blend'))
    bpy.ops.render.render(write_still=True)

# 测试挂载物不作为森林资产的一部分导出。
def mat(name,color):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    bsdf=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Roughness'].default_value=0.75
    return m

ivory=mat('test.ivory',(0.69,0.57,0.36))
dark=mat('test.charcoal',(0.048,0.058,0.065))
number=bpy.data.objects['anchor_number'].matrix_world.translation
robber=bpy.data.objects['anchor_robber'].matrix_world.translation
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=0.46,depth=0.075,location=(number.x,number.y,number.z+0.0375))
token=bpy.context.object
token.name='TEST_ONLY.number-base'
token.data.materials.append(ivory)
bevel=token.modifiers.new('edge-softening','BEVEL')
bevel.width,bevel.segments=0.018,3
bpy.ops.object.text_add(location=(number.x,number.y,number.z+0.079))
text=bpy.context.object
text.name='TEST_ONLY.number-content'
text.data.body='8'
text.data.align_x,text.data.align_y='CENTER','CENTER'
text.data.size,text.data.extrude=0.50,0.001
text.data.materials.append(dark)
bpy.ops.mesh.primitive_cone_add(vertices=48,radius1=0.23,radius2=0.11,depth=0.58,location=(robber.x,robber.y,robber.z+0.29))
bpy.context.object.name='TEST_ONLY.robber-body'
bpy.context.object.data.materials.append(dark)
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=0.16,location=(robber.x,robber.y,robber.z+0.71))
bpy.context.object.name='TEST_ONLY.robber-head'
bpy.context.object.data.materials.append(dark)
for p in bpy.context.object.data.polygons:
    p.use_smooth=True
scene.camera=bpy.data.objects['review.board']
scene.render.filepath=str(REVIEW/('glb-composition.png' if IS_GLB else 'composition.png'))
bpy.ops.render.render(write_still=True)
# 相邻基座用于验证共边接缝是否精确，不依赖树木摆放。
for x,y in [(4.5,3*math.sqrt(3)/2),(-4.5,3*math.sqrt(3)/2)]:
    for name in ['terrain.soil-cut','terrain.forest-floor']:
        src=bpy.data.objects[name]
        duplicate=src.copy()
        duplicate.data=src.data
        duplicate.parent=None
        duplicate.matrix_world=src.matrix_world.copy()
        duplicate.location+=Vector((x,y,0))
        bpy.context.scene.collection.objects.link(duplicate)
scene.camera.data.ortho_scale=14
scene.render.filepath=str(REVIEW/('glb-seams.png' if IS_GLB else 'seams.png'))
bpy.ops.render.render(write_still=True)
print('REVIEW_COMPLETE', REVIEW)
