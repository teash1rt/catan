"""宽阔的手绘黏土采场，以中世纪野外砖窑作为辅助元素。"""
import math
import random

import bpy
from mathutils import Vector


def ground_color(x, y):
    """地面与场地共用的配色；运输路径只通过颜色表现，不抬高几何体。"""
    variation = .5+.22*math.sin(x*2+y*3)+.10*math.cos(x*5-y*2)
    # 资源配色延伸到地块边缘，避免出现森林式的绿色边框。
    color = Vector((.30,.092,.043)).lerp(Vector((.44,.17,.077)),variation)
    route=[(-1.22,-.03),(-1.20,-.62),(-1.13,-1.24),(-.58,-1.56),
           (.02,-1.54),(.37,-1.32),(1.08,-.40),(1.25,-.12)]
    p=Vector((x,y))
    distance=10
    for a,b in zip(route,route[1:]):
        a,b=Vector(a),Vector(b)
        t=max(0,min(1,(p-a).dot(b-a)/(b-a).length_squared))
        distance=min(distance,(p-a-(b-a)*t).length)
    weight=max(0,min(1,(.26-distance)/.11))
    return color.lerp(Vector((.50,.25,.105)),weight*.65)


def build_quarry(asset, root, mat, box, mesh, link):
    clay = [mat('quarry.clay.'+str(i), c) for i, c in enumerate([
        (.15,.029,.014), (.23,.044,.020), (.31,.067,.031),
        (.39,.100,.046), (.28,.053,.022)])]
    kiln_mat = mat('kiln.fired-clay',(.52,.115,.041))
    cut = mat('kiln.cut-brick',(.64,.25,.09))
    dark = mat('kiln.interior',(.055,.025,.013))
    def ridge(name, stations):
        # 山脊、鞍部和不对称支脉组成连续岩体，横截面采用分层台阶。
        profile=[(-1,0),(-.82,.25),(-.59,.64),(-.28,.89),
                 (0,1),(.18,.85),(.39,.58),(.45,.55),
                 (.57,.33),(.78,.13),(1,0)]
        vertices,faces,indices=[],[],[]
        for i,(x,y,h,w) in enumerate(stations):
            prev=Vector(stations[max(0,i-1)][:2])
            nxt=Vector(stations[min(len(stations)-1,i+1)][:2])
            tangent=(nxt-prev).normalized()
            inward=Vector((tangent.y,-tangent.x))
            for j,(q,z) in enumerate(profile):
                width=w*(1+.17*math.sin(i*1.8+j*.75))
                # 宽阔的内向支脉沿山脊错落分布，避免形成齐整的墙面。
                if q>0:
                    width*=1.20+.23*math.sin(i*2.1)
                xy=Vector((x,y))+inward*q*width
                xy+=tangent*.055*math.sin(i*2.3+j*1.8)*math.sin(math.pi*(q+1)/2)
                # 倾斜且连续的岩层保留不规则变化，同时控制视觉噪点。
                height=h*z+.085*math.sin(i*1.7+j*.65)*math.sin(math.pi*(q+1)/2)
                vertices.append((xy.x,xy.y,max(0,height)))
        n=len(profile)
        for i in range(len(stations)-1):
            for j in range(n-1):
                faces.append((i*n+j,i*n+j+1,(i+1)*n+j+1,(i+1)*n+j))
                indices.append(2)
        faces.extend([tuple(reversed(range(n))),tuple((len(stations)-1)*n+j for j in range(n))])
        indices.extend([1,1])
        obj=mesh(name,vertices,faces,clay,indices)
        for face in obj.data.polygons:
            # 配色跟随大块岩面，避免形成连续的彩色条纹。
            light=face.normal.dot(Vector((-.4,-.6,.7)))
            face.material_index=3 if light>.65 else (2 if light>-.15 else 1)
        # 将较大且不共面的岩面拆分为稳定的三角面，保证导出可靠。
        bpy.context.view_layer.objects.active=obj
        bevel=obj.modifiers.new('worn-rock-arris','BEVEL')
        bevel.width,bevel.segments=.012,2
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        return obj

    ridge('quarry.continuous-ridge',[
        (-.95,-2.03,.025,.28),(-1.44,-1.76,.30,.45),
        (-1.87,-1.28,.49,.48),(-2.07,-.73,.78,.51),
        (-2.12,-.12,1.13,.56),(-1.97,.39,.86,.63),
        (-1.64,.84,1.36,.82),(-1.27,1.15,1.94,.90),
        (-.88,1.48,1.50,.93),(-.47,1.71,1.14,.88),
        (-.01,1.66,1.81,.86),(.35,1.73,1.56,.76),
        (.79,1.70,1.08,.65),(1.18,1.52,1.38,.54),
        (1.57,1.30,.95,.44),(1.92,.99,.33,.32),
        (2.05,.61,.015,.20)])
    ridge('quarry.front-outcrop',[
        (.95,-2.02,.015,.19),(1.34,-1.88,.19,.25),
        (1.70,-1.54,.30,.31),(2.06,-1.08,.22,.28),
        (2.30,-.61,.02,.18)])

    def boulder(name,pos,scale,materials,seed):
        local=random.Random(seed)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=pos)
        obj=link(bpy.context.object)
        obj.name=name
        for v in obj.data.vertices:
            v.co *= local.uniform(.91,1.07)
            v.co.x *= scale[0]
            v.co.y *= scale[1]
            v.co.z *= scale[2]
            if v.co.z+pos[2]<.01:
                v.co.z=-pos[2]
        for m in materials:
            obj.data.materials.append(m)
        for p in obj.data.polygons:
            p.material_index = 1 if len(materials)>1 and p.center.z>.1 else 0
        return obj

    # 低矮砖窑采用简洁拱壳，避免整墙铺满细小砖格。
    cx,cy=1.25,.45
    box('kiln.foot',(cx,cy,.055),(1.32,1.22,.11),clay[0],.045)
    profile=[(-.60,.08),(.60,.08),(.60,.52)]
    profile += [(.60*math.cos(i*math.pi/12),.52+.43*math.sin(i*math.pi/12)) for i in range(1,13)]
    count=len(profile)
    v=[(cx+x,y,z) for y in [-.11,1.01] for x,z in profile]
    f=[tuple(range(count)),tuple(reversed(range(count,2*count)))]
    f += [(i,i+count,(i+1)%count+count,(i+1)%count) for i in range(count)]
    kiln=mesh('kiln.vaulted-body',v,f,[kiln_mat])
    # 窑口采用真实凹陷，主体保持连续，不依赖细小砂浆缝表现结构。
    aperture=[(cx-.23,.035),(cx+.23,.035)]
    aperture += [(cx+.23*math.cos(i*math.pi/16),.31+.23*math.sin(i*math.pi/16)) for i in range(17)]
    ndoor=len(aperture)
    cutter=mesh('temporary.door',[(x,y,z) for y in [-.3,.78] for x,z in aperture],
                [tuple(range(ndoor)),tuple(reversed(range(ndoor,2*ndoor)))]+
                [(i,i+ndoor,(i+1)%ndoor+ndoor,(i+1)%ndoor) for i in range(ndoor)],[dark])
    bpy.context.view_layer.objects.active=kiln
    mod=kiln.modifiers.new('arched-firemouth','BOOLEAN')
    mod.operation,mod.solver,mod.object='DIFFERENCE','EXACT',cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    bevel=kiln.modifiers.new('soft-plastered-clay','BEVEL')
    bevel.width,bevel.segments=.025,2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    box('kiln.dark-back',(cx,.72,.28),(.46,.035,.46),dark,.005)
    box('kiln.hearth',(cx,.25,.06),(.50,.85,.06),clay[0],.01)
    # 用七块较大的拱券石和两侧门柱表现砌筑结构。
    for i in range(7):
        a0,a1=i*math.pi/7+.007,(i+1)*math.pi/7-.007
        verts=[(cx+r*math.cos(a),y,.31+r*math.sin(a))
               for y in [-.17,-.08] for r in [.23,.33] for a in [a0,a1]]
        mesh('kiln.arch',verts,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],[cut])
    for sign in [-1,1]:
        box('kiln.jamb',(cx+sign*.28,-.125,.20),(.10,.12,.25),cut,.012)
    # 宽口带盖排气口低于山体，避免现代高烟囱的轮廓。
    for sign in [-1,1]:
        box('kiln.vent',(cx+sign*.145,.76,1.03),(.09,.38,.39),kiln_mat,.014)
        box('kiln.vent',(cx,.76+sign*.145,1.03),(.20,.09,.39),kiln_mat,.014)
        box('kiln.cap',(cx+sign*.16,.76,1.24),(.10,.42,.065),cut,.012)
        box('kiln.cap',(cx,.76+sign*.16,1.24),(.23,.10,.065),cut,.012)
    box('kiln.vent-shadow',(cx,.76,1.02),(.22,.22,.02),dark,0)

    # 少量大块烧制砖紧凑堆放，砖块之间仅留少量间隙。
    prototype=box('brick.prototype',(0,0,0),(.29,.19,.12),cut,.016)
    data=prototype.data
    bpy.data.objects.remove(prototype,do_unlink=True)
    for layer in range(3):
        for col in range(2):
            for row in range(2):
                obj=bpy.data.objects.new('brick.stock',data)
                asset.objects.link(obj)
                obj.parent=root
                obj.location=(1.57+(col-.5)*.295,-.65+(row-.5)*.195,.06+layer*.12)

    # 保留六边形完整的边缘带，包括后侧的斜边。
    for obj in asset.objects:
        if obj.type=='MESH' and obj.name.startswith('quarry.'):
            for v in obj.data.vertices:
                x,y=obj.location.x+v.co.x,obj.location.y+v.co.y
                support=max(x*math.cos(math.pi/6+j*math.pi/3)+y*math.sin(math.pi/6+j*math.pi/3) for j in range(6))
                if support>2.31:
                    v.co.x=x*2.31/support-obj.location.x
                    v.co.y=y*2.31/support-obj.location.y
    # 连续碎石坡掩埋山脚，使山脊与地面衔接。
    # 网格采样在两个挂点圆柱周围预留保护带。
    kernels=[(-.65,1.0,1.8,1.25,.48),(-.45,.34,1.25,.78,.35),
             (-1.55,.12,.90,1.18,.48),
             (-1.48,-.72,.88,.95,.32),(-1.15,-1.46,.88,.65,.19),
             (.55,1.38,1.22,.81,.37),(1.46,1.05,.68,.77,.24),
             (1.48,-1.19,.72,.67,.16),(1.02,-1.63,.63,.44,.10)]

    def apron_height(x,y):
        heights=[h*max(0,1-((x/1.04-cx)/rx)**2-((y/1.04-cy)/ry)**2)**2
                 for cx,cy,rx,ry,h in kernels]
        z=sum(h**4 for h in heights)**.25
        for cx,cy,r in [(-.55,-.72,.50),(.70,-.83,.34)]:
            t=max(0,min(1,(math.hypot(x-cx,y-cy)-r-.16)/.32))
            z*=t*t*(3-2*t)
        # 保持窑口门槛和生产场地平整。
        d=max(abs(x-1.25)-.73,abs(y-.45)-.72)
        z*=max(0,min(1,d/.27))
        edge=max(x*math.cos(math.pi/6+j*math.pi/3)+y*math.sin(math.pi/6+j*math.pi/3) for j in range(6))
        z*=max(0,min(1,(2.31-edge)/.16))
        return z

    # 直接雕刻已有地面，避免叠加表皮或产生共面接缝。
    apron=bpy.data.objects['terrain.clay-floor']
    for v in apron.data.vertices:
        v.co.z=apron_height(v.co.x,v.co.y)
    colors=apron.data.color_attributes['COLOR_0']
    for p in apron.data.polygons:
        p.use_smooth=True
        for idx in p.loop_indices:
            x,y,z=apron.data.vertices[apron.data.loops[idx].vertex_index].co
            color=ground_color(x,y).lerp(Vector((.26,.065,.028)),min(.82,z*2.5))
            colors.data[idx].color=(*color,1)
    apron.data.update()

    # 作业痕迹采用稀疏的成组分布，避免均匀散布。
    for i,(x,y,s) in enumerate([(-1.17,-.05,.13),(-1.27,-.25,.08),
            (-1.50,-.93,.10),(-1.31,-1.18,.07),(-.88,-1.79,.10),
            (-.62,-1.84,.06),(.04,-1.82,.07),(1.30,-1.42,.09)]):
        boulder('quarry.scree',(x,y,apron_height(x,y)+s*.15),
                (s,s*.78,s*.60),clay[1:3],120+i)
    for i,(x,y,a) in enumerate([(.06,-1.81,.25),(.30,-1.69,-.3),(1.65,-.99,.12)]):
        obj=bpy.data.objects.new('brick.loose',data)
        asset.objects.link(obj)
        obj.parent=root
        obj.location=(x,y,apron_height(x,y)+.06)
        obj.rotation_euler.z=a
    straw=mat('quarry.dry-grass',(.43,.34,.12))
    for i,(x,y) in enumerate([(-1.21,-1.70),(-.25,-1.84),(1.52,-1.50),(-1.98,-.45)]):
        v,f=[],[]
        z=apron_height(x,y)
        for k in range(5):
            a=k*2.4+i
            dx,dy=math.cos(a),math.sin(a)
            height=.11+.035*(k%3)
            start=len(v)
            v.extend([(x-dy*.018,y+dx*.018,z),(x+dy*.018,y-dx*.018,z),
                      (x+dx*.065,y+dy*.065,z+height)])
            f.append((start,start+1,start+2))
        mesh('quarry.dry-tuft',v,f,[straw])

    # 合并固定组件，同时保留可复用的砖料几何体。
    for prefix in ['quarry.','kiln.']:
        parts=[o for o in asset.objects if o.type=='MESH' and o.name.startswith(prefix)]
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active=parts[0]
        bpy.ops.object.join()
        parts[0].name=prefix+'assembly'
