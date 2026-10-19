"""Deterministic forest sample. Run with Blender --background --python this_file.

Writes a NEW blend; never replaces an existing source. Review first,
then use --export with the reviewed blend. Studio objects are not exported.
"""
import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, help='Optional temporary draft .blend; defaults to canonical source')
parser.add_argument('--review-dir', required=True)
parser.add_argument('--export', action='store_true')
parser.add_argument('--render', action='store_true')
ARGS = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
SOURCE = (ARGS.source or ROOT / 'assets/forest-tile/model.blend').resolve()
PREVIEW = Path(ARGS.review_dir).resolve()
if not str(PREVIEW).startswith(('/private/tmp/', '/tmp/')):
    raise ValueError('Review output must be temporary, outside the project')
MODEL = ROOT / 'assets/forest-tile/model.glb'
RNG = random.Random(271828)
NUMBER = (-0.55, -0.72, 0.0)
ROBBER = (0.70, -0.83, 0.0)
APOTHEM = 3 * math.sqrt(3) / 2


def material(name, color, roughness=0.8):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Specular IOR Level'].default_value = 0.18
    return mat


def mesh(name, verts, faces, mats, indices=None, collection=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    for mat in mats:
        data.materials.append(mat)
    obj = bpy.data.objects.new(name, data)
    (collection or ASSET).objects.link(obj)
    if indices:
        for poly, index in zip(data.polygons, indices):
            poly.material_index = index
    return obj


class Geometry:
    def __init__(self):
        self.vertices, self.faces, self.indices = [], [], []

    def face(self, points, mat=0):
        base = len(self.vertices)
        self.vertices.extend(points)
        self.faces.append(tuple(range(base, base + len(points))))
        self.indices.append(mat)

    def tube(self, start, end, r1, r2, sides=9, mat=0):
        start, end = Vector(start), Vector(end)
        direction = (end - start).normalized()
        u = direction.cross(Vector((0, 1, 0))).normalized()
        if u.length < 0.5:
            u = direction.cross(Vector((1, 0, 0))).normalized()
        v = direction.cross(u).normalized()
        rings = [[p + r * (u * math.cos(a * math.tau / sides) + v * math.sin(a * math.tau / sides))
                  for a in range(sides)] for p, r in [(start, r1), (end, r2)]]
        for i in range(sides):
            j = (i + 1) % sides
            self.face([rings[0][i], rings[0][j], rings[1][j], rings[1][i]], mat + i % 2)
        self.face(list(reversed(rings[0])), mat)
        self.face(rings[1], mat)

    def leaf(self, center, direction, length, width, mat):
        c, d = Vector(center), Vector(direction).normalized()
        side = d.cross(Vector((0.12, 0, 1))).normalized() * width
        tip, root = c + d * length * 0.55, c - d * length * 0.45
        ridge = c + Vector((0, 0, length * 0.055))
        outline=[root,c-d*length*0.20+side*0.8,c+d*length*0.18+side,tip,c+d*length*0.18-side,c-d*length*0.20-side*0.8]
        for i in range(6):
            self.face([outline[i],outline[(i+1)%6],ridge],mat)

    def object(self, name, mats, collection=None):
        return mesh(name, self.vertices, self.faces, mats, self.indices, collection)


def inside(x, y, margin=0.28):
    return all(x * math.cos(math.pi / 6 + n * math.pi / 3) +
               y * math.sin(math.pi / 6 + n * math.pi / 3) <= APOTHEM - margin
               for n in range(6))


def clear(x, y, extra=0):
    return math.hypot(x-NUMBER[0], y-NUMBER[1]) > 0.5 + extra and math.hypot(x-ROBBER[0], y-ROBBER[1]) > 0.34 + extra


def elevation(x, y):
    # The lattice edge is 3/24 = .125; protect whole triangles, not only vertices.
    if not inside(x, y, 0.42) or not clear(x, y, 0.14):
        return 0
    return 0.026 * (1 + math.sin(x * 3.1 + y) * math.cos(y * 2.7))


def blob(name, location, scale, mat, subdivisions=2, collection=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=location)
    obj = bpy.context.object
    obj.name = name
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    (collection or ASSET).objects.link(obj)
    for vert in obj.data.vertices:
        vert.co *= RNG.uniform(0.89, 1.08)
    obj.scale = scale
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def tree_mesh(seed):
    local = random.Random(seed)
    wood, leaves = Geometry(), Geometry()
    # Bending stem, roots and visible forks, not a stack of primitive cones.
    spine = [(0, 0, 0), (0.035, -0.015, 0.45), (-0.015, 0.02, 0.95), (0.035, 0.035, 1.55)]
    rings=[]
    for center,radius in zip(spine,[0.12,0.084,0.049,0.015]):
        rings.append([Vector(center)+Vector((math.cos(n*math.tau/16)*radius,math.sin(n*math.tau/16)*radius,0)) for n in range(16)])
    for ring in range(3):
        for n in range(16):
            nxt=(n+1)%16
            wood.face([rings[ring][n],rings[ring][nxt],rings[ring+1][nxt],rings[ring+1][n]],n%2)
    for i in range(6):
        a = i * math.tau / 6 + local.uniform(-0.25, 0.25)
        wood.tube((math.cos(a)*0.23, math.sin(a)*0.23, -0.018), (0, 0, 0.12), 0.009, 0.056, 9)
    # Overlapping asymmetric boughs carrying many individually folded leaves.
    centers = []
    for level, count, radius, height in [(0, 5, 0.32, 1.17), (1, 4, 0.29, 1.45), (2, 2, 0.12, 1.66)]:
        for i in range(count):
            a = i * math.tau / count + level * 0.9 + local.uniform(-0.45, 0.45)
            c = Vector((math.cos(a)*radius, math.sin(a)*radius, height + local.uniform(-0.15, 0.15)))
            centers.append((c, (0.31, 0.29, 0.26)))
            fork = (c.x * 0.45, c.y * 0.45, c.z - 0.30)
            wood.tube((0.01, 0, max(0.6, c.z-0.65)), fork, 0.043, 0.023, 7)
            wood.tube(fork, c, 0.023, 0.006, 7)
            for j in range(32):
                # A few leaf accents complement the crown, not a cloud of micro-leaves.
                u, a2 = local.uniform(-1, 1), local.uniform(0, math.tau)
                shell = local.uniform(0.94, 1.10)
                q = Vector((math.sqrt(1-u*u)*math.cos(a2)*0.31,
                            math.sqrt(1-u*u)*math.sin(a2)*0.29, u*0.26)) * shell
                p = c + q
                direction = (math.cos(a2+local.uniform(-1, 1)), math.sin(a2+local.uniform(-1, 1)), local.uniform(-0.4, 0.7))
                shade = local.choices(range(5), [2, 5, 5, 3, 1])[0]
                leaves.leaf(p, direction, local.uniform(0.16, 0.23), local.uniform(0.05, 0.07), shade)
    trunk = wood.object('oak-trunk-prototype', BARK)
    for polygon in trunk.data.polygons:
        polygon.use_smooth = True
    accents = leaves.object('oak-leaves-prototype', LEAF)
    lobes=[]
    for i,(center,scale) in enumerate(centers):
        obj=blob('canopy-lobe',center,scale,LEAF[2],subdivisions=2)
        lobes.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in lobes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=lobes[0]
    bpy.ops.object.join()
    canopy=bpy.context.object
    canopy.name='oak-canopy-prototype'
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    remesh=canopy.modifiers.new('continuous-organic-crown','REMESH')
    remesh.mode='VOXEL'
    remesh.voxel_size=0.055
    remesh.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=canopy.modifiers.new('soft-sculpted-volume','SMOOTH')
    smooth.factor,smooth.iterations=0.6,3
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    # Paint broad, coherent color patches directly into exportable vertex colors.
    canopy.data.materials.clear()
    painted=material('foliage.painted-volume',(1,1,1),1.0)
    canopy.data.materials.append(painted)
    attr=canopy.data.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER')
    for poly in canopy.data.polygons:
        poly.material_index=0
        poly.use_smooth=True
        for idx in poly.loop_indices:
            p=canopy.matrix_world @ canopy.data.vertices[canopy.data.loops[idx].vertex_index].co
            light=max(0,min(1,(p.z-0.92)/1.08+0.10*math.sin(p.x*8+p.y*5)))
            dark=Vector((0.014,0.11,0.020))
            mid=Vector((0.045,0.28,0.019))
            bright=Vector((0.26,0.47,0.040))
            color=dark.lerp(mid,min(1,light*1.8)) if light<0.55 else mid.lerp(bright,(light-0.55)/0.45)
            attr.data[idx].color=(*color,1)
    node=painted.node_tree.nodes.new('ShaderNodeVertexColor')
    node.layer_name='COLOR_0'
    painted.node_tree.links.new(node.outputs['Color'],painted.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    # Bring prototype geometry to a shared local origin before instancing.
    for v in canopy.data.vertices:
        v.co=canopy.matrix_world @ v.co
    canopy.location=(0,0,0)
    return trunk, accents, canopy


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    global STUDIO
    STUDIO = bpy.data.collections.new('REVIEW_ONLY — excluded from GLB')
    bpy.context.scene.collection.children.link(STUDIO)
    backdrop = material('review.backdrop', (0.19, 0.205, 0.18))
    mesh('review.ground', [(-200,-200,-0.315),(200,-200,-0.315),(200,200,-0.315),(-200,200,-0.315)], [(0,1,2,3)], [backdrop], collection=STUDIO)
    for name, pos, power, size in [('key',(-4,-6,9),1600,7),('fill',(5,-1,6),850,6),('rim',(0,6,7),1300,5)]:
        light = bpy.data.lights.new('review.'+name, 'AREA')
        light.energy, light.shape, light.size = power, 'DISK', size
        obj = bpy.data.objects.new(light.name, light)
        STUDIO.objects.link(obj)
        obj.location = pos
        aim(obj, (0,0,0))
    for name, pos, target, scale in [('board',(5,-9,10),(0,0,0.5),7.6),('close',(4,-7,6),(0,0.35,0.95),5.8),('side',(5,-10,3.2),(0,0,0.65),7.4)]:
        camera = bpy.data.cameras.new('review.'+name)
        camera.type, camera.ortho_scale = 'ORTHO', scale
        obj = bpy.data.objects.new(camera.name, camera)
        STUDIO.objects.link(obj)
        obj.location = pos
        aim(obj,target)
    scene = bpy.context.scene
    scene.camera = bpy.data.objects['review.board']
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1200, 1000, 100
    scene.world = bpy.data.worlds.new('review.neutral-world')
    scene.world.color = (0.25, 0.25, 0.25)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
                area.spaces.active.shading.type = 'MATERIAL'
                area.spaces.active.overlay.show_overlays = False


def build():
    global ASSET, BARK, LEAF
    if SOURCE.exists():
        raise FileExistsError(f'Refusing to overwrite {SOURCE}; use --source for a temporary draft')
    # Only the new background process is reset; user's open scene is untouched.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ASSET = bpy.data.collections.new('ASSET_forest_tile')
    bpy.context.scene.collection.children.link(ASSET)
    root = bpy.data.objects.new('forest_tile', None)
    ASSET.objects.link(root)
    root['contract'] = 'catan.hex.v1'
    root['hex_radius'] = 3.0
    root['front'] = '-Y'
    soil = [material('soil.umber',(0.125,0.075,0.035)),material('soil.cut',(0.20,0.125,0.06)),material('soil.lower',(0.095,0.056,0.028))]
    ground = [material('ground.moss',(0.19,0.245,0.066)),material('ground.fern',(0.22,0.28,0.078)),material('ground.earth',(0.265,0.20,0.104)),material('ground.worn',(0.30,0.245,0.139)),material('ground.sage',(0.245,0.29,0.09))]
    BARK = [material('oak.bark',(0.27,0.105,0.028)),material('oak.bark-ridge',(0.37,0.17,0.044)),material('oak.endgrain',(0.61,0.38,0.12)),material('oak.growth-ring',(0.39,0.20,0.05))]
    LEAF = [material('foliage.deep',(0.022,0.155,0.033)), material('foliage.forest',(0.055,0.28,0.035)),material('foliage.moss',(0.115,0.39,0.037)),material('foliage.sunlit',(0.30,0.51,0.044)),material('foliage.new',(0.42,0.60,0.07))]
    stone = material('stone.warm-grey',(0.31,0.30,0.24),0.94)
    # Exact hex boundary, layered soil edge, no bevel that opens a seam.
    g = Geometry()
    for i in range(6):
        a,b = i*math.pi/3,(i+1)*math.pi/3
        for j,(lo,hi) in enumerate([(-0.30,-0.22),(-0.22,-0.055),(-0.055,0)]):
            g.face([(3*math.cos(a),3*math.sin(a),lo),(3*math.cos(b),3*math.sin(b),lo),(3*math.cos(b),3*math.sin(b),hi),(3*math.cos(a),3*math.sin(a),hi)], [2,0,1][j])
    g.face([(3*math.cos(i*math.pi/3),3*math.sin(i*math.pi/3),-0.30) for i in reversed(range(6))],2)
    g.object('terrain.soil-cut',soil)
    # Triangular lattice across each hex sector; slight interior relief only.
    g = Geometry()
    def point(i,j,a,b):
        x,y = (a[0]*i+b[0]*j)/24,(a[1]*i+b[1]*j)/24
        return (x,y,elevation(x,y))
    for sector in range(6):
        a=(3*math.cos(sector*math.pi/3),3*math.sin(sector*math.pi/3))
        b=(3*math.cos((sector+1)*math.pi/3),3*math.sin((sector+1)*math.pi/3))
        for i in range(24):
            for j in range(24-i):
                triangles=[(point(i,j,a,b),point(i+1,j,a,b),point(i,j+1,a,b))]
                if i+j<23:
                    triangles.append((point(i+1,j,a,b),point(i+1,j+1,a,b),point(i,j+1,a,b)))
                for tri in triangles:
                    x,y=sum(p[0] for p in tri)/3,sum(p[1] for p in tri)/3
                    path=abs(x+0.45-0.22*math.sin(y*1.7))<0.27 and y<0.5
                    index=RNG.choice([2,3,3]) if path or not clear(x,y) else RNG.choices([0,1,2,4],[6,5,1,2])[0]
                    g.face(tri,index)
    floor = g.object('terrain.forest-floor',ground)
    # Continuous vertex color survives GLB; no renderer-specific noise shader.
    floor.data.materials.clear()
    floor_mat=material('ground.continuous', (1,1,1),0.97)
    floor.data.materials.append(floor_mat)
    colors=floor.data.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER')
    for polygon in floor.data.polygons:
        polygon.material_index=0
        for loop_index in polygon.loop_indices:
            x,y,z=floor.data.vertices[floor.data.loops[loop_index].vertex_index].co
            variation=0.5+0.25*math.sin(x*5+y*3)+0.15*math.cos(x*11-y*8)
            green=Vector((0.075,0.20,0.028)).lerp(Vector((0.18,0.34,0.05)),variation)
            distance=abs(x+0.45-0.22*math.sin(y*1.7))
            path=math.exp(-((distance/0.30)**4)) * max(0,min(1,(0.75-y)*2))
            clearing=max(math.exp(-(math.hypot(x-NUMBER[0],y-NUMBER[1])/0.54)**6),math.exp(-(math.hypot(x-ROBBER[0],y-ROBBER[1])/0.38)**6))
            color=green.lerp(Vector((0.38,0.245,0.085)),max(path,clearing*0.85))
            colors.data[loop_index].color=(*color,1)
    attr=floor_mat.node_tree.nodes.new('ShaderNodeVertexColor')
    attr.layer_name='COLOR_0'
    floor_mat.node_tree.links.new(attr.outputs['Color'],floor_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    proto=tree_mesh(45)
    positions=[(-1.30,0.25,1.0,0.3),(-0.65,1.15,1.1,1.6),(0.78,1.30,0.99,3.0),(1.55,0.30,0.86,4.1),(-1.73,-0.68,0.57,2.0),(1.60,-0.70,0.49,0.8)]
    for i,(x,y,scale,angle) in enumerate(positions):
        for part in proto:
            obj=bpy.data.objects.new(f'tree.{i+1:02}.{part.name.split("-")[1]}',part.data)
            ASSET.objects.link(obj)
            obj.location=(x,y,elevation(x,y))
            obj.scale=(scale,scale,scale * [1,1.03,0.96,1.05,1,1][i])
            obj.rotation_euler.z=angle
    for obj in proto:
        bpy.data.objects.remove(obj,do_unlink=True)
    # Rocks, leaf litter and sparse understory remain inside build clearances.
    for i,(x,y,s) in enumerate([(-1.80,0.25,0.19),(1.22,0.80,0.16),(1.70,-0.32,0.12),(-0.10,1.74,0.12),(-1.68,-1.1,0.095)]):
        blob(f'detail.stone.{i}',(x,y,elevation(x,y)+s*0.35),(s,s*0.78,s*0.55),stone)
    grass=Geometry()
    for i in range(450):
        x,y=RNG.uniform(-2.5,2.5),RNG.uniform(-2.25,2.25)
        if not inside(x,y,0.4) or not clear(x,y,0.17) or abs(x+0.45-0.22*math.sin(y*1.7))<0.35:
            continue
        for j in range(RNG.randint(3,6)):
            a=RNG.uniform(0,math.tau)
            length=RNG.uniform(0.055,0.14)
            grass.leaf((x,y,elevation(x,y)+0.035),(math.cos(a)*0.6,math.sin(a)*0.6,0.7),length,0.012,RNG.choice([1,2,3]))
    grass.object('detail.understory',LEAF)
    fern=Geometry()
    for x,y in [(-1.2,-0.05),(1.4,-0.3),(-0.15,1.53),(0.95,0.52),(-1.82,-0.35)]:
        for n in range(7):
            a=n*math.tau/7
            d=Vector((math.cos(a),math.sin(a),0))
            s=Vector((-d.y,d.x,0))
            for j in range(1,8):
                t=j/8
                c=Vector((x,y,elevation(x,y)))+d*t*0.23+Vector((0,0,math.sin(t*math.pi)*0.12))
                for sign in [-1,1]:
                    fern.leaf(c,d*0.35+s*sign,0.07*(1-t)+0.024,0.014,2+(n%2))
    fern.object('detail.ferns',LEAF)
    # A small split-log stack reads as timber; kept separate from number content.
    logs=Geometry()
    for i,(x,y,z) in enumerate([(0.65,-1.70,0.085),(0.86,-1.70,0.085),(0.75,-1.70,0.225)]):
        logs.tube((x,y-0.28,z),(x+0.055,y+0.28,z+0.025),0.087,0.078,11)
        logs.tube((x,y-0.284,z),(x,y-0.287,z),0.071,0.071,11,2)
    logs.object('detail.timber',BARK)
    for name,pos,radius,height in [('anchor_number',NUMBER,0.50,0.40),('anchor_robber',ROBBER,0.34,1.15)]:
        obj=bpy.data.objects.new(name,None)
        ASSET.objects.link(obj)
        obj.location=pos
        obj.empty_display_type='CIRCLE'
        obj.empty_display_size=radius
        obj['clearance_radius'],obj['clearance_height']=radius,height
    for obj in ASSET.objects:
        if obj != root:
            obj.parent=root
    studio()
    bpy.ops.object.select_all(action='DESELECT')
    SOURCE.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    print('FOREST_SOURCE',SOURCE)


def render_reviews():
    PREVIEW.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene
    for name in ['board','close','side']:
        scene.camera=bpy.data.objects['review.'+name]
        scene.render.filepath=str(PREVIEW/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    scene.camera=bpy.data.objects['review.board']
    scene.render.resolution_x=scene.render.resolution_y=1024
    bpy.data.objects['review.ground'].hide_render=True
    scene.render.film_transparent=True
    scene.render.image_settings.color_mode='RGBA'
    scene.render.filepath=str(PREVIEW/'icon.png')
    bpy.ops.render.render(write_still=True)


def export():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.collections['ASSET_forest_tile'].objects:
        obj.select_set(True)
    MODEL.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(MODEL),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False)
    print('FOREST_GLB',MODEL)


if ARGS.export:
    export()
else:
    build()
if ARGS.render:
    render_reviews()
