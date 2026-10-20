"""金色条带麦田与小型半木构风磨，遵循共享六边形契约。

麦穗以可复用的三株草丛沿弧形田垄种植。
优先保证大块暖色分组和低缓地形起伏，再考虑单株谷粒密度。
"""
import math
import random

import bpy
from mathutils import Vector


def path_x(y):
    return .05 + .72 * math.sin((y + 1.4) * .65)


def ground_color(x, y):
    wave = .5 + .19 * math.sin(x*1.8+y) + .12*math.cos(y*2.2)
    color = Vector((.26,.15,.041)).lerp(Vector((.44,.295,.10)), wave)
    road = max(0, min(1, (.43-abs(x-path_x(y)))/.22))
    return color.lerp(Vector((.57,.41,.225)), road*.66)


def edge(x, y):
    return max(x*math.cos(math.pi/6+j*math.pi/3)+y*math.sin(math.pi/6+j*math.pi/3) for j in range(6))


def terrain_height(x, y):
    h = .32*math.exp(-((x+1.15)/1.4)**2-((y-.85)/1.25)**2)
    h += .15*math.exp(-((x-1.65)/.7)**2-((y+.15)/1.0)**2)
    for cx,cy,r in [(-.55,-.72,.50),(.70,-.83,.34)]:
        t=max(0,min(1,(math.hypot(x-cx,y-cy)-r-.15)/.28))
        h*=t*t*(3-2*t)
    # 风磨使用独立平整地基，地块接缝保持平整。
    t=max(0,min(1,(math.hypot(x-1.13,y-1.20)-.65)/.3))
    h*=t*t*(3-2*t)
    return h*max(0,min(1,(2.31-edge(x,y))/.18))


def build_quarry(asset, root, mat, box, mesh, link):
    rng=random.Random(20261014)
    straw=[mat('wheat.'+str(i),c) for i,c in enumerate([
        (.26,.14,.022),(.47,.235,.025),(.67,.36,.043),(.78,.48,.095)])]
    wood=mat('mill.weathered-oak',(.245,.145,.073))
    grain=mat('mill.honey-oak',(.39,.26,.12))
    plaster=mat('mill.warm-lime',(.66,.57,.405))
    stone=mat('mill.sandstone',(.38,.35,.25))
    roofm=[mat('mill.shingle.'+str(i),c) for i,c in enumerate([
        (.105,.095,.049),(.13,.115,.060),(.145,.127,.070)])]
    linen=mat('mill.flax-sails',(.75,.675,.49))
    dark=mat('mill.recess',(.052,.04,.029))
    herb=mat('field.olive-grass',(.235,.285,.075))
    sack=mat('harvest.woven-flax',(.49,.375,.22))

    def beam(name,a,b,width,material,depth=None):
        a,b=Vector(a),Vector(b)
        ob=box(name,(a+b)/2,(width,depth or width,(b-a).length),material,.008)
        ob.rotation_mode='QUATERNION'
        ob.rotation_quaternion=(b-a).to_track_quat('Z','Y')
        return ob

    floor=bpy.data.objects['terrain.wheat-floor']
    colors=floor.data.color_attributes['COLOR_0']
    for v in floor.data.vertices:
        v.co.z=terrain_height(v.co.x,v.co.y)
    for p in floor.data.polygons:
        p.use_smooth=True
        for idx in p.loop_indices:
            x,y,_=floor.data.vertices[floor.data.loops[idx].vertex_index].co
            colors.data[idx].color=(*ground_color(x,y),1)

    # 三种原型在整片麦田中共享网格，避免每个麦穗独立创建对象。
    prototypes=[]
    for variant in range(3):
        verts,faces,indices=[],[],[]

        def shape(v,f,index):
            start=len(verts)
            verts.extend(v)
            faces.extend(tuple(start+i for i in face) for face in f)
            indices.extend([index]*len(f))

        def stem(a,b,r,index=0):
            a,b=Vector(a),Vector(b)
            v=[a+Vector((math.cos(k*math.pi/2)*r,math.sin(k*math.pi/2)*r,0)) for k in range(4)]
            v += [b+Vector((math.cos(k*math.pi/2)*r*.65,math.sin(k*math.pi/2)*r*.65,0)) for k in range(4)]
            shape(v,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],index)

        def kernel(a,b,width,index):
            a,b=Vector(a),Vector(b)
            axis=(b-a).normalized()
            u=axis.cross(Vector((0,1,0))).normalized()*width
            v=axis.cross(u).normalized()*width*.62
            c=a.lerp(b,.48)
            shape([a,c+u,c+v,c-u,c-v,b],
                  [(0,2,1),(0,3,2),(0,4,3),(0,1,4),(5,1,2),(5,2,3),(5,3,4),(5,4,1)],index)

        for s,(x,y) in enumerate([(-.065,-.03),(.063,.01),(0,.085)]):
            h=.31+.047*((s+variant)%3)
            lean=Vector((.061+.012*variant,.018,0))
            base=Vector((x,y,0))
            tip=base+lean+Vector((0,0,h))
            stem(base,tip,.012)
            # 使用宽阔尖叶和饱满整齐的麦穗，避免密集细芒产生毛糙噪点。
            mid=base.lerp(tip,.43)
            shape([mid,mid+Vector((-.11,-.015,.09)),mid+Vector((-.16,0,.14)),mid+Vector((-.07,.024,.09))],[(0,1,2),(0,2,3)],1)
            for k in range(3):
                for side in [-1,1]:
                    a=tip+Vector((0,0,k*.052))
                    b=a+Vector((side*(.064-.007*k),.004,.075))
                    kernel(a,b,.030,2 if variant<2 else 1)
            kernel(tip+Vector((0,0,.136)),tip+Vector((.014,0,.222)),.028,3 if variant<2 else 2)
        ob=mesh('wheat.prototype',verts,faces,straw,indices)
        prototypes.append(ob.data)
        bpy.data.objects.remove(ob,do_unlink=True)

    # 流动的条带田垄延伸到边缘，同时保留一条农路和挂点净空区。
    # 为整簇弯曲麦株预留足够边距。
    planted=0
    for row in range(23):
        x=-2.40+row*.215
        for col in range(27):
            y=-2.04+col*.16
            xx=x+.17*math.sin(y*1.6+x*.7)+rng.uniform(-.05,.05)
            yy=y+.05*math.sin(x*3)+rng.uniform(-.04,.04)
            if edge(xx,yy)>2.035:
                continue
            if abs(xx-path_x(yy))<.29+.045*math.sin(yy*3):
                continue
            if math.hypot(xx-1.13,yy-1.20)<.78:
                continue
            if any(math.hypot(xx-cx,yy-cy)<r+.28 for cx,cy,r in [(-.55,-.72,.5),(.70,-.83,.34)]):
                continue
            # 前景表现为已收割的场地，避免围满无关道具。
            if math.hypot((xx+.14)*1.1,yy+1.65)<.46:
                continue
            band=math.sin(xx*1.6+yy*1.8)
            ob=bpy.data.objects.new('wheat.clump',prototypes[2 if band<-.55 else (row%2)])
            asset.objects.link(ob)
            ob.parent=root
            ob.location=(xx,yy,terrain_height(xx,yy)-.007)
            ob.rotation_euler.z=.35*math.sin(yy*2+xx)+rng.uniform(-.45,.45)
            scale=.94+.14*rng.random()+.15*math.sin(xx*1.5+yy*1.8)
            ob.scale=(min(scale,1.1),min(scale,1.1),scale)
            planted+=1
    print('WHEAT_CLUMPS',planted)

    # 小型柱式风磨采用石基、收尖木构屋体、暖色木瓦顶和四片覆亚麻布的格架风翼。
    # 风磨作为辅助元素，麦田仍是主体。
    cx,cy=1.13,1.20
    box('mill.footing',(cx,cy,.09),(.91,.82,.18),stone,.055)
    box('mill.house',(cx,cy,.80),(.73,.65,1.24),plaster,.025)
    for x in [cx-.365,cx+.365]:
        for y in [cy-.33,cy+.33]:
            beam('mill.corner',(x,y,.17),(x,y,1.44),.053,wood)
    for z in [.24,1.38]:
        for y in [cy-.34,cy+.34]:
            beam('mill.rail',(cx-.40,y,z),(cx+.40,y,z),.052,wood)
        for x in [cx-.38,cx+.38]:
            beam('mill.side-rail',(x,cy-.34,z),(x,cy+.34,z),.052,wood)
    for x in [cx-.38,cx+.38]:
        beam('mill.diagonal',(x,cy-.30,.75),(x,cy+.29,1.34),.040,wood)
    box('mill.door-recess',(cx,cy-.337,.44),(.26,.022,.43),dark,.035)
    for i in range(3):
        box('mill.door-plank',(cx-.081+i*.081,cy-.356,.43),(.074,.026,.38),grain,.004)
    beam('mill.door-brace',(cx-.11,cy-.38,.27),(cx+.11,cy-.38,.57),.033,wood)
    box('mill.step',(cx,cy-.47,.055),(.39,.22,.11),stone,.025)
    box('mill.window',(cx+.383,cy,1.07),(.022,.21,.23),dark,.025)
    beam('mill.window-mullion',(cx+.40,cy,.96),(cx+.40,cy,1.18),.025,grain)

    # 坡屋顶具有真实厚度，并铺设四层木瓦。
    v=[(cx-.49,cy-.45,1.40),(cx+.49,cy-.45,1.40),(cx+.49,cy+.45,1.40),(cx-.49,cy+.45,1.40),
       (cx,cy-.45,1.78),(cx,cy+.45,1.78)]
    mesh('mill.roof-core',v,[(0,1,4),(3,5,2),(0,4,5,3),(1,2,5,4),(0,3,2,1)],roofm,[0,0,1,0,0])
    def roof_point(side,t,y):
        # 檐口轻微下垂以柔化轮廓，颜色变化保持克制。
        return (cx+side*.53*(1-t),y,1.425+.47*t-.055*math.sin(math.pi*t)+.009)

    for side in [-1,1]:
        for course in range(4):
            t0=course/4
            t1=(course+1)/4+.025
            for j in range(5):
                ya=cy-.47+j*.19+rng.uniform(-.006,.006)
                yb=ya+.187
                pts=[roof_point(side,t,y) for t,y in [(t0,ya),(t0,yb),(t1,yb),(t1,ya)]]
                tile=mesh('mill.shingle',pts,[(0,1,2,3) if side>0 else (3,2,1,0)],
                          [roofm[rng.choices([0,1,2],[1,5,1])[0]]])
                bpy.context.view_layer.objects.active=tile
                solid=tile.modifiers.new('shingle-thickness','SOLIDIFY')
                solid.thickness=.032
                bpy.ops.object.modifier_apply(modifier=solid.name)
    beam('mill.ridge',(cx,cy-.49,1.91),(cx,cy+.49,1.91),.054,wood)

    hub=Vector((cx,cy-.65,1.62))
    beam('mill.axle',(cx,cy-.26,1.62),hub+Vector((0,-.07,0)),.13,wood)
    for i in range(4):
        angle=math.pi/5+i*math.pi/2
        radial=Vector((math.cos(angle),0,math.sin(angle)))
        tangent=Vector((-math.sin(angle),0,math.cos(angle)))
        beam('mill.sail-spar',hub+radial*.08,hub+radial*1.02,.038,wood)
        a=hub+radial*.38
        b=hub+radial*1.00
        # 布片略微偏置，使支撑帆杆仍然可见。
        pts=[a+tangent*.035,b+tangent*.035,b+tangent*.215,a+tangent*.215,
             a.lerp(b,.5)+tangent*.125-Vector((0,.035,0))]
        cloth=mesh('mill.sail-linen',pts,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],[linen])
        bpy.context.view_layer.objects.active=cloth
        solid=cloth.modifiers.new('sail-thickness','SOLIDIFY')
        solid.thickness=.012
        bpy.ops.object.modifier_apply(modifier=solid.name)
        beam('mill.sail-edge',a+tangent*.22,b+tangent*.22,.022,grain)
        for k in range(3):
            p=a.lerp(b,k/2)+Vector((0,.015,0))
            beam('mill.sail-rib',p,p+tangent*.23,.016,grain)
    box('mill.hub',hub-Vector((0,.05,0)),(.15,.10,.15),grain,.028,angle=0)

    # 成组麦捆为前景提供用途，同时避开数字牌与强盗净空区。
    # 通过不同轮廓表现变化，避免散乱摆放。
    for x,y,s in [(-.39,-1.65,.94),(-.14,-1.79,.82),(-.10,-1.52,1.02)]:
        z=terrain_height(x,y)
        for j in range(7):
            a=j*math.tau/7
            foot=(x+math.cos(a)*.15*s,y+math.sin(a)*.15*s,z)
            waist=(x+math.cos(a)*.045*s,y+math.sin(a)*.045*s,z+.25*s)
            top=(x+math.cos(a)*.12*s,y+math.sin(a)*.12*s,z+.49*s)
            beam('harvest.sheaf',foot,waist,.048*s,straw[1])
            beam('harvest.sheaf',waist,top,.062*s,straw[2])
        bpy.ops.mesh.primitive_torus_add(major_radius=.061*s,minor_radius=.018*s,major_segments=12,minor_segments=4,location=(x,y,z+.25*s))
        belt=link(bpy.context.object)
        belt.name='harvest.binding'
        belt.data.materials.append(wood)

    # 风磨旁的软布袋通过逐渐收紧的截面环表现扎口袋颈。
    for x,y,s in [(1.62,.81,1),(1.65,1.10,.79)]:
        z=terrain_height(x,y)
        vv=[]
        profile=[(.0,.10),(.06,.16),(.22,.155),(.32,.095),(.36,.048),(.40,.075)]
        for k,(height,radius) in enumerate(profile):
            for j in range(12):
                a=j*math.tau/12
                r=radius*(1+.07*math.sin(a*3+k))
                vv.append((x+s*r*math.cos(a),y+s*r*.83*math.sin(a),z+s*height))
        ff=[tuple(range(11,-1,-1)),tuple(range(60,72))]
        ff += [(k*12+j,k*12+(j+1)%12,(k+1)*12+(j+1)%12,(k+1)*12+j) for k in range(5) for j in range(12)]
        ob=mesh('harvest.grain-sack',vv,ff,[sack])
        for p in ob.data.polygons:
            p.use_smooth=True
        bpy.ops.mesh.primitive_torus_add(major_radius=.05*s,minor_radius=.012*s,major_segments=12,minor_segments=4,location=(x,y,z+.355*s))
        link(bpy.context.object).data.materials.append(wood)
        bpy.context.object.name='harvest.sack-tie'

    # 两段短旧木栏间隔布置，避免完整围圈的玩具感。
    for points in [[(-2.05,.27),(-1.99,.73),(-1.80,1.18)],[(-.70,1.92),(-.23,2.02),(.23,1.98)]]:
        for x,y in points:
            z=terrain_height(x,y)
            beam('field.fence-post',(x,y,z-.015),(x+.018,y,z+.55),.056,wood)
        for (x,y),(u,v) in zip(points,points[1:]):
            for h in [.22,.48]:
                beam('field.fence-rail',(x,y,terrain_height(x,y)+h),(u,v,terrain_height(u,v)+h-.02),.040,grain)

    # 少量过渡位置使用低饱和橄榄色叶片，避免将资源地面铺成绿色。
    for x,y in [(-2.10,-.30),(-1.85,.87),(-.63,1.89),(.30,1.97),(1.67,.64),(1.80,.10),(1.39,-1.36),(-1.18,-1.78)]:
        z=terrain_height(x,y)
        vv,ff=[],[]
        for j in range(5):
            a=j*2.4
            d=Vector((math.cos(a),math.sin(a),0))
            u=Vector((-math.sin(a),math.cos(a),0))*.028
            base=Vector((x,y,z-.008))
            mid=base+d*.09+Vector((0,0,.12+rng.random()*.05))
            tip=base+d*.18+Vector((0,0,.12))
            n=len(vv)
            vv.extend([base,mid+u,tip,mid-u])
            ff.extend([(n,n+1,n+2),(n,n+2,n+3)])
        mesh('field.margin-leaves',vv,ff,[herb])

    # 割下的麦秆仅在麦捆周围按少量方向性条带铺放。
    for j in range(26):
        x=rng.uniform(-.70,.16)
        y=rng.uniform(-2.04,-1.52)
        if math.hypot(x+.55,y+.72)<.58:
            continue
        z=terrain_height(x,y)+.014
        beam('harvest.cut-straw',(x,y,z),(x+.10,y+.05,z+.004),.013,straw[1])

    for prefix in ['mill.','harvest.','field.']:
        parts=[o for o in asset.objects if o.type=='MESH' and o.name.startswith(prefix)]
        bpy.ops.object.select_all(action='DESELECT')
        for ob in parts:
            ob.select_set(True)
        bpy.context.view_layer.objects.active=parts[0]
        bpy.ops.object.join()
        parts[0].name=prefix+'assembly'
        if prefix=='mill.':
            # 以地基为中心整体压缩组件，包括风翼，避免梁、门和屋顶发生独立错位。
            ob=parts[0]
            inv=ob.matrix_world.inverted()
            for v in ob.data.vertices:
                p=ob.matrix_world @ v.co
                p.x=cx+(p.x-cx)*1.035
                p.z*=.90
                v.co=inv @ p
