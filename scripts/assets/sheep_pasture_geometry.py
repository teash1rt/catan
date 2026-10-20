"""起伏的春季牧场，包含可复用羊群、茅草羊圈与干砌石墙。

遵循共享的平顶六边形与挂点契约，不包含玩法或展示辅助节点。
以大块连续草地为主体，畜牧细节成组布置并作为辅助。
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector
from mathutils.noise import noise


FLOCK = [
    (-1.18, .73, -.65, 1.04, 0),
    (-.32, .64, .28, .98, 1),
    (-1.68, -.13, -1.15, 1.00, 1),
    (-.25, 1.52, 2.8, .94, 0),
    (-1.45, -1.43, -.50, .95, 0),
    (1.63, -.19, 1.35, 1.03, 1),
    (.06, .02, 1.6, .65, 0),
    (.00, -1.78, -.35, .67, 1),
    (-1.91, .85, .90, .65, 0),
]


def edge(x, y):
    return max(x*math.cos(math.pi/6+j*math.pi/3)+y*math.sin(math.pi/6+j*math.pi/3) for j in range(6))


def lane_x(y):
    return .40 + .49*math.sin(y*.92)


def ground_color(x, y):
    wave = .48 + .22*math.sin(x*1.6+y*.8) + .15*math.cos(y*2.5-x*.4)
    green = Vector((.060,.160,.021)).lerp(Vector((.27,.39,.058)), wave)
    road = max(0, min(1, (.22-abs(x-lane_x(y)))/.15))
    return green.lerp(Vector((.44,.335,.165)), road*.85)


def raw_height(x, y):
    return (.62*math.exp(-((x+1.0)/1.40)**2-((y-.95)/1.12)**2)
            +.22*math.exp(-((x-1.65)/.78)**2-((y+.05)/1.5)**2)
            +.22*math.exp(-((x+1.35)/.95)**2-((y+1.5)/.75)**2))


def smooth(t):
    t = max(0,min(1,t))
    return t*t*(3-2*t)


def terrain_height(x, y):
    h=raw_height(x,y)
    # 轻微平整的落脚区使每个共享动物实例的四蹄都能贴地。
    for cx,cy,_,scale,_ in FLOCK:
        w=1-smooth((math.hypot(x-cx,y-cy)-.28*scale)/.22)
        h=h*(1-w)+raw_height(cx,cy)*w
    h*=smooth((math.hypot(x-1.04,y-1.10)-.72)/.28)
    for cx,cy,r in [(-.55,-.72,.50),(.70,-.83,.34)]:
        h*=smooth((math.hypot(x-cx,y-cy)-r-.15)/.24)
    return h*smooth((2.318-edge(x,y))/.24)


def build_quarry(asset, root, mat, box, mesh, link):
    rng=random.Random(20261015)
    wool=mat('flock.ivory-fleece',(.72,.68,.535))
    skin=mat('flock.warm-slate',(.115,.102,.075))
    hoof=mat('flock.hooves-eyes',(.025,.028,.022))
    ear=mat('flock.ear-inner',(.34,.225,.17))
    wood=mat('fold.weathered-oak',(.225,.14,.065))
    timber=mat('fold.honey-timber',(.355,.25,.125))
    plaster=mat('fold.warm-lime',(.56,.51,.355))
    recess=mat('fold.interior',(.073,.066,.038))
    thatch=[mat('fold.thatch.'+str(i),c) for i,c in enumerate([
        (.32,.235,.087),(.37,.28,.115),(.42,.325,.145)])]
    stones=[mat('pasture.limestone.'+str(i),c) for i,c in enumerate([
        (.30,.32,.22),(.38,.39,.285),(.43,.43,.31)])]
    grass=[mat('pasture.blades.'+str(i),c) for i,c in enumerate([
        (.11,.23,.026),(.23,.36,.050),(.38,.46,.10)])]
    flowers=mat('pasture.buttercups',(.82,.51,.045))
    water=mat('fold.water',(.12,.245,.21))

    def beam(name,a,b,width,material,depth=None):
        a,b=Vector(a),Vector(b)
        ob=box(name,(a+b)/2,(width,depth or width,(b-a).length),material,.008)
        ob.rotation_mode='QUATERNION'
        ob.rotation_quaternion=(b-a).to_track_quat('Z','Y')
        return ob

    def ellipsoid(name, pos, scale, material, fleece=False):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32 if fleece else 16,
                                           ring_count=20 if fleece else 10, radius=1, location=pos)
        ob=link(bpy.context.object)
        ob.name=name
        for v in ob.data.vertices:
            p=v.co.copy()
            # 羊毛使用连续表皮与浅而圆润的卷纹，避免球体堆叠、写实毛发或大量独立毛卷。
            puff=1+.15*noise(p*7.5)+.04*noise(p*16) if fleece else 1
            v.co=Vector((p.x*scale[0],p.y*scale[1],p.z*scale[2]))*puff
        ob.data.materials.append(material)
        for p in ob.data.polygons:
            p.use_smooth=True
        return ob

    def join_parts(parts,name):
        bpy.ops.object.select_all(action='DESELECT')
        for ob in parts:
            ob.select_set(True)
        bpy.context.view_layer.objects.active=parts[0]
        bpy.ops.object.join()
        ob=parts[0]
        ob.name=name
        return ob

    floor=bpy.data.objects['terrain.sheep-floor']
    colors=floor.data.color_attributes['COLOR_0']
    for v in floor.data.vertices:
        v.co.z=terrain_height(v.co.x,v.co.y)
    for p in floor.data.polygons:
        p.use_smooth=True
        for idx in p.loop_indices:
            x,y,_=floor.data.vertices[floor.data.loops[idx].vertex_index].co
            colors.data[idx].color=(*ground_color(x,y),1)

    # 轮廓包含饱满羊毛躯干、狭窄裸脸、侧耳、四条独立腿、小分蹄和短尾。
    prototypes=[]
    for pose in range(2):
        before=set(asset.objects)
        ellipsoid('sheep.body',(0,0,.355),(.32,.21,.245),wool,True)
        ellipsoid('sheep.chest',(.20,0,.36),(.155,.175,.205),wool,True)
        for x in [-.195,.185]:
            for y in [-.125,.125]:
                beam('sheep.leg',(x,y,.028),(x+.013,y,.29),.047,skin)
                for dy in [-.014,.014]:
                    box('sheep.split-hoof',(x+.008,y+dy,.032),(.082,.025,.064),hoof,.013)
        head=Vector((.315,0,.465 if pose==0 else .22))
        face=ellipsoid('sheep.face',head,(.12,.084,.16),skin)
        face.rotation_euler.y=.35 if pose==0 else -.65
        ellipsoid('sheep.forelock',head+Vector((-.035,0,.11)),(.105,.092,.08),wool,True)
        for side in [-1,1]:
            e=ellipsoid('sheep.ear',head+Vector((-.008,side*.112,.066)),(.088,.047,.024),skin)
            e.rotation_euler.z=side*.7
            e=ellipsoid('sheep.ear-inner',head+Vector((.003,side*.12,.083)),(.055,.027,.006),ear)
            e.rotation_euler.z=side*.7
            ellipsoid('sheep.eye',head+Vector((.073,side*.072,.040)),(.014,.010,.015),hoof)
        ellipsoid('sheep.muzzle',head+Vector((.040,0,-.106)),(.083,.066,.052),skin)
        tail=ellipsoid('sheep.tail',(-.29,0,.30),(.10,.058,.10),wool,True)
        tail.rotation_euler.y=-.6
        ob=join_parts(list(set(asset.objects)-before),'sheep.prototype')
        # 烘焙原型的原点和变换，使关联实例的结果保持可预测。
        transform=ob.matrix_world.copy()
        for v in ob.data.vertices:
            v.co=transform @ v.co
        ob.matrix_world.identity()
        prototypes.append(ob.data)
        bpy.data.objects.remove(ob,do_unlink=True)
    for i,(x,y,angle,scale,pose) in enumerate(FLOCK):
        ob=bpy.data.objects.new('flock.sheep.%02d'%i,prototypes[pose])
        asset.objects.link(ob)
        ob.parent=root
        ob.location=(x,y,terrain_height(x,y)-.008)
        ob.rotation_euler.z=angle
        ob.scale=(scale,scale,scale)

    # 羊圈采用低矮宽阔的中世纪造型，以小占地辅助牧场场景，避免高塔或工业棚屋轮廓。
    cx,cy=1.04,1.10
    box('fold.foundation',(cx,cy,.065),(1.17,.94,.13),stones[1],.04)
    box('fold.house',(cx,cy,.405),(1.04,.80,.68),plaster,.025)
    for x in [cx-.52,cx+.52]:
        for y in [cy-.405,cy+.405]:
            beam('fold.post',(x,y,.10),(x,y,.77),.065,wood)
    for z in [.16,.73]:
        for y in [cy-.412,cy+.412]:
            beam('fold.rail',(cx-.55,y,z),(cx+.55,y,z),.060,wood)
    box('fold.shadow-door',(cx-.12,cy-.417,.36),(.42,.025,.50),recess,.07)
    # 半开的低门与铰链露出内部暗处，门体使用真实几何结构。
    for i in range(4):
        box('fold.gate-plank',(cx-.27+i*.10,cy-.451,.255),(.088,.035,.28),timber,.008)
    beam('fold.gate-brace',(cx-.31,cy-.48,.15),(cx+.03,cy-.48,.36),.036,wood)
    for z in [.19,.34]:
        box('fold.hinge',(cx-.30,cy-.475,z),(.12,.019,.023),skin,.005)
    box('fold.side-window',(cx+.531,cy,.48),(.025,.27,.27),recess,.025)
    for yy in [cy-.08,cy,cy+.08]:
        beam('fold.window-slat',(cx+.55,yy,.36),(cx+.55,yy,.60),.026,timber)

    # 茅草屋顶采用连续微弯的厚曲面与真实厚檐。
    # 细草纹沿坡向排列，避免形成棋盘式瓦格。
    for side in [-1,1]:
        vv=[]
        for j in range(17):
            y=cy-.56+j*.07
            for k in range(9):
                t=k/8
                x=cx+side*.66*(1-t)
                z=.76+.43*t-.065*math.sin(math.pi*t)+.012*math.cos(j*.55)
                vv.append((x,y,z))
        ff=[(j*9+k,j*9+k+1,(j+1)*9+k+1,(j+1)*9+k) for j in range(16) for k in range(8)]
        ob=mesh('fold.thatch-cap',vv,ff,thatch,[1]*len(ff))
        bm=bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(ob.data); bm.free()
        # 添加厚度前，先校正两侧开放坡面的朝向。
        if sum(p.normal.z for p in ob.data.polygons)<0:
            for p in ob.data.polygons:
                p.flip()
        for p in ob.data.polygons:
            p.use_smooth=True
        bpy.context.view_layer.objects.active=ob
        mod=ob.modifiers.new('thick-thatch-eave','SOLIDIFY'); mod.thickness=.085
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for j in range(31):
            yy=cy-.54+j*.035
            t0=rng.uniform(.04,.16); t1=rng.uniform(.70,.96)
            pts=[]
            for k in range(5):
                t=t0+(t1-t0)*k/4
                pts.append((cx+side*.66*(1-t),yy,.775+.43*t-.065*math.sin(math.pi*t)+.01*math.cos((yy-cy+.56)/.07*.55)))
            for a,b in zip(pts,pts[1:]):
                beam('fold.thatch-straw',a,b,.012,thatch[0 if j%3==0 else 2])
    beam('fold.bound-ridge',(cx,cy-.56,1.192),(cx,cy+.56,1.192),.065,thatch[0])
    # 每个山墙下方添加小型三角填充面。
    for yy in [cy-.408,cy+.408]:
        mesh('fold.gable',[(cx-.50,yy,.73),(cx+.50,yy,.73),(cx,yy,1.12)],[(0,1,2)],[plaster])
        beam('fold.gable-tie',(cx-.49,yy,.74),(cx+.49,yy,.74),.055,wood)
        beam('fold.gable-post',(cx,yy,.75),(cx,yy,1.10),.044,wood)

    # 蜿蜒的低矮干砌石墙嵌入同一坡地，避免围绕整个地块悬浮成圈。
    wall=[(-1.94,.91),(-1.67,1.37),(-1.22,1.76),(-.68,1.94),(-.10,1.98)]
    for (x,y),(u,v) in zip(wall,wall[1:]):
        length=math.hypot(u-x,v-y); angle=math.atan2(v-y,u-x)
        n=max(2,round(length/.29))
        for course in range(2):
            for j in range(n):
                t=(j+.5+course*.19)/n
                px=x+(u-x)*t; py=y+(v-y)*t
                z=terrain_height(px,py)+.085+course*.125
                ob=box('pasture.wall-stone',(px,py,z),(length/n-.009,.205-course*.024,.15+rng.uniform(-.02,.02)),
                       stones[rng.choice([0,1,1,2])],.026,angle+rng.uniform(-.08,.08))
                for vert in ob.data.vertices:
                    vert.co*=1+.12*noise(vert.co*14+Vector((j,course,2)))

    # 羊圈附近设置分段木栏，并保留通向放牧区的可用开口。
    for points in [[(1.90,.56),(2.04,.09),(1.99,-.35)], [(-2.06,-.63),(-1.92,-1.12)]]:
        for x,y in points:
            z=terrain_height(x,y)
            beam('pasture.fence-post',(x,y,z-.025),(x+.008,y,z+.43),.065,wood)
        for (x,y),(u,v) in zip(points,points[1:]):
            for h in [.19,.37]:
                beam('pasture.fence-rail',(x,y,terrain_height(x,y)+h),(u,v,terrain_height(u,v)+h),.045,timber)

    # 雕刻水槽与草料架，表现羊圈旁的小型作业场地。
    x,y=1.27,.46; z=terrain_height(x,y)
    box('fold.trough-base',(x,y,z+.09),(.50,.26,.12),stones[0],.035)
    for yy in [y-.12,y+.12]:
        box('fold.trough-rim',(x,yy,z+.175),(.52,.058,.13),stones[1],.025)
    for xx in [x-.24,x+.24]:
        box('fold.trough-end',(xx,y,z+.175),(.064,.26,.13),stones[1],.025)
    box('fold.drinking-water',(x,y,z+.153),(.39,.16,.008),water,.004)
    for xx in [1.66,1.85]:
        beam('fold.hayrack-leg',(xx,.74,.03),(xx,.74,.36),.038,wood)
    for yy in [.65,.84]:
        for xx in [1.66,1.75,1.85]:
            beam('fold.hayrack-slat',(xx,.74,.16),(xx,yy,.37),.028,timber)
    ellipsoid('fold.fodder',(1.75,.74,.28),(.17,.075,.11),thatch[2])

    # 可复用草丛在选定弧形区域密集分布，羊群和路径周围保持低矮。
    # 使用宽叶片保证轮廓清晰，避免粒子草坪式噪点。
    tufts=[]
    for variant in range(3):
        vv=[]; ff=[]; ids=[]
        for j in range(7):
            a=j*2.4+variant*.7
            d=Vector((math.cos(a),math.sin(a),0))
            side=Vector((-d.y,d.x,0))*.025
            base=d*.035
            mid=base+d*.07+Vector((0,0,.10+.02*((j+variant)%3)))
            tip=base+d*.15+Vector((0,0,.14+.025*(j%2)))
            n=len(vv); vv.extend([base,mid+side,tip,mid-side])
            ff.extend([(n,n+1,n+2),(n,n+2,n+3)]); ids.extend([j%3]*2)
        ob=mesh('pasture.tuft-prototype',vv,ff,grass,ids)
        tufts.append(ob.data); bpy.data.objects.remove(ob,do_unlink=True)
    for i in range(470):
        x=rng.uniform(-2.35,2.35); y=rng.uniform(-2.18,2.18)
        if edge(x,y)>2.11 or abs(x-lane_x(y))<.25:
            continue
        if math.hypot(x-1.04,y-1.10)<.87:
            continue
        if any(math.hypot(x-cx,y-cy)<r+.20 for cx,cy,r in [(-.55,-.72,.5),(.70,-.83,.34)]):
            continue
        if any(math.hypot(x-cx,y-cy)<.43*s for cx,cy,_,s,_ in FLOCK):
            continue
        if math.sin(x*3+y*1.9)+math.cos(y*3.8-x)<-.25:
            continue
        ob=bpy.data.objects.new('pasture.grass-tuft',tufts[i%3]); asset.objects.link(ob)
        ob.parent=root; ob.location=(x,y,terrain_height(x,y)-.012)
        ob.rotation_euler.z=rng.random()*math.tau
        s=rng.uniform(.65,1.20); ob.scale=(s,s,s)

    # 毛茛集中生长在三处避风区域，避免均匀散布。
    for cx,cy in [(-1.74,.28),(-.83,1.77),(1.33,-1.58)]:
        for j in range(7):
            x=cx+rng.uniform(-.15,.15); y=cy+rng.uniform(-.13,.13)
            z=terrain_height(x,y)
            beam('pasture.flower-stem',(x,y,z),(x+.012,y,z+.13),.012,grass[0])
            for k in range(5):
                a=k*math.tau/5
                c=Vector((x+.025*math.cos(a),y+.025*math.sin(a),z+.14))
                vv=[c+Vector(p) for p in [(-.029,0,0),(0,-.021,0),(.029,0,0),(0,.021,0),(0,0,.013),(0,0,-.009)]]
                mesh('pasture.buttercup',vv,[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)],[flowers])

    for prefix in ['fold.','pasture.wall','pasture.fence','pasture.flower','pasture.buttercup']:
        parts=[o for o in asset.objects if o.type=='MESH' and o.name.startswith(prefix)]
        if parts:
            join_parts(parts,prefix+'assembly')
    # 所有封闭自定义组件的法线保持一致朝外。
    for data in {o.data for o in asset.objects if o.type=='MESH' and not o.name.startswith('terrain.')}:
        bm=bmesh.new(); bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(data); bm.free()
