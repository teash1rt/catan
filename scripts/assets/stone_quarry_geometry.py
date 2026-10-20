"""蓝色石灰岩采场：台阶状切面、木制起重架与石材交易区。

共享地块契约，石料地块的轮廓与建筑几何体独立于砖土地块。
"""
import math

import bpy
from mathutils import Vector


def ground_color(x, y):
    variation = .5 + .18*math.sin(x*2.1+y) + .12*math.cos(y*2.4-x)
    color = Vector((.12,.16,.18)).lerp(Vector((.26,.30,.31)),variation)
    # 暖色运输路径沿采场下方通向交易区，避开道具。
    distance = abs(y - (-1.55 + .25*math.sin(x*1.6)))
    weight = max(0,min(1,(.34-distance)/.20))
    return color.lerp(Vector((.48,.40,.28)),weight*.6)


def build_quarry(asset, root, mat, box, mesh, link):
    stone = [mat('stone.'+str(i),c) for i,c in enumerate([
        (.055,.085,.12),(.10,.16,.22),(.135,.205,.265),(.24,.30,.34),(.39,.43,.43)])]
    wood = mat('timber.honey-oak',(.25,.105,.033))
    endgrain = mat('timber.worn-edges',(.40,.22,.075))
    iron = mat('iron.blue-black',(.055,.075,.085))
    rope = mat('rope.flax',(.47,.36,.20))
    cloth = mat('canvas.teal',(.018,.17,.22))
    trim = mat('canvas.linen',(.63,.58,.41))

    def beam(name,a,b,width,material,depth=None):
        a,b=Vector(a),Vector(b)
        ob=box(name,(a+b)/2,(width,depth or width,(b-a).length),material,.012)
        ob.rotation_mode='QUATERNION'
        ob.rotation_quaternion=(b-a).to_track_quat('Z','Y')
        return ob

    def cylinder(name,pos,radius,depth,material,axis='Z',vertices=16):
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=pos)
        ob=link(bpy.context.object)
        ob.name=name
        ob.data.materials.append(material)
        if axis=='Y':
            ob.rotation_euler.x=math.pi/2
        return ob

    # 单个不对称阶梯岩壁以宽阔平台表现已开采石材。
    # 轮廓区别于砖土地块的尖锐富铁山脊和封闭窑场。
    stations=[(-2.57,-.30,.68,.43),(-2.34,-.94,1.10,1.08),
              (-2.06,-1.25,1.45,1.64),(-1.73,-1.20,1.76,2.08),
              (-1.39,-.62,2.00,2.24),(-1.04,-.11,2.18,2.04),
              (-.62,.02,2.29,2.32),(-.18,.04,2.31,2.21),
              (.28,.14,2.29,2.00),(.70,.46,2.24,2.18),
              (1.10,1.00,2.12,1.86),(1.47,1.30,1.95,1.63),
              (1.83,1.31,1.72,1.04),(2.13,1.10,1.39,.38)]
    # 截面参数分别为 y 插值与相对高度；近垂直切面、宽平台、破碎山顶和陡峭背坡组成封闭岩体。
    # 宽阔自然山顶下方设置两层不规则作业台阶，避免每个截面都重复三条薄带而呈现折纸感。
    profile=[(0,0),(.08,.12),(.15,.36),(.27,.38),
             (.34,.66),(.45,.69),(.58,.92),(.73,1),(.88,.89),(1,0)]
    vertices,faces,indices=[],[],[]
    for i,(x,front,back,h) in enumerate(stations):
        for j,(t,z) in enumerate(profile):
            shape=math.sin(math.pi*t)
            yy=front+(back-front)*t+.12*math.sin(i*1.7+j*.9)*shape
            xx=x+.10*math.sin(i*1.6+j*.7)*shape
            # 独立错开切割高度，增大裸露岩面，并用少量斜平台连接未开采的山肩。
            zz=max(0,h*z+.13*math.sin(i*1.9+j*1.2)*shape)
            vertices.append((xx,yy,zz))
    n=len(profile)
    for i in range(len(stations)-1):
        for j in range(n-1):
            quad=(i*n+j,(i+1)*n+j,(i+1)*n+j+1,i*n+j+1)
            shade=2 if j in [0,2,4,6,7,8] else 1
            if j in [2,4] and i in [2,5,8,10]:
                shade=3
            # 岩面采用宽阔连续配色，避免三角面颜色交替。
            faces.append(quad)
            indices.append(shade)
    faces.extend([tuple(reversed(range(n))),tuple((len(stations)-1)*n+j for j in range(n))])
    indices.extend([1,1])
    # 仅约束自然岩体的边界，建筑按空间设计，避免通过挤压变形适配。
    # 贴附岩面的裂缝也使用同一组受约束坐标。
    for k,(x,y,z) in enumerate(vertices):
        support=max(x*math.cos(math.pi/6+j*math.pi/3)+y*math.sin(math.pi/6+j*math.pi/3) for j in range(6))
        scale=min(1,2.29/max(support,1e-6))
        vertices[k]=(x*scale,y*scale,z)
    cliff=mesh('quarry.stepped-limestone',vertices,faces,stone,indices)
    bpy.context.view_layer.objects.active=cliff
    bevel=cliff.modifiers.new('soft-rock-edges','BEVEL')
    bevel.width,bevel.segments=.035,2
    bpy.ops.object.modifier_apply(modifier=bevel.name)

    # 已开采岩面仅添加稀疏收尖的裂纹，避免铺满网格噪点。
    for i,j,t in [(3,1,.34),(5,1,.63),(7,3,.45),(9,3,.62),(6,5,.24),(2,3,.55)]:
        lo=Vector(vertices[i*n+j]).lerp(Vector(vertices[(i+1)*n+j]),t)
        hi=Vector(vertices[i*n+j+1]).lerp(Vector(vertices[(i+1)*n+j+1]),t+.035)
        offset=Vector((0,-.016,0))
        lo+=offset
        hi+=offset
        mid=lo.lerp(hi,.55)+Vector((.018,0,0))
        mesh('quarry.cut-fissure',[lo,mid+Vector((.012,0,0)),hi,mid-Vector((.009,0,0))],
             [(0,1,2,3)],[stone[0]])

    # 地面缓坡衔接岩壁，并保护两个可拆卸玩法标记的净空。
    def apron_height(x,y):
        kernels=[(-1.96,-.56,.65,1.23,.32),(-1.33,.13,.87,.87,.28),
                 (-.20,.54,1.3,.68,.24),(.82,1.41,1.13,.63,.25)]
        z=sum((h*max(0,1-((x-cx)/rx)**2-((y-cy)/ry)**2)**2)**4
              for cx,cy,rx,ry,h in kernels)**.25
        for cx,cy,r in [(-.55,-.72,.50),(.70,-.83,.34)]:
            t=max(0,min(1,(math.hypot(x-cx,y-cy)-r-.16)/.3))
            z*=t*t*(3-2*t)
        edge=max(x*math.cos(math.pi/6+j*math.pi/3)+y*math.sin(math.pi/6+j*math.pi/3) for j in range(6))
        return z*max(0,min(1,(2.31-edge)/.16))

    floor=bpy.data.objects['terrain.stone-floor']
    for v in floor.data.vertices:
        v.co.z=apron_height(v.co.x,v.co.y)
    colors=floor.data.color_attributes['COLOR_0']
    for p in floor.data.polygons:
        p.use_smooth=True
        for idx in p.loop_indices:
            x,y,z=floor.data.vertices[floor.data.loops[idx].vertex_index].co
            colors.data[idx].color=(*ground_color(x,y).lerp(Vector((.14,.22,.28)),min(1,z*3)),1)

    # 木制起重架由三角支撑、卷扬轮和悬挂吊索组成。
    # 放在右侧空旷装卸区，避开两个标记。
    for x,y in [(1.31,.54),(1.31,1.30)]:
        box('crane.stone-foot',(x,y,.10),(.32,.31,.20),stone[2],.04)
    beam('crane.mast',(1.31,.92,.06),(1.31,.92,2.09),.16,wood)
    beam('crane.rear-brace',(1.31,1.30,.20),(1.31,.92,1.53),.11,wood)
    beam('crane.front-brace',(1.31,.54,.20),(1.31,.92,1.53),.11,wood)
    beam('crane.jib',(1.31,.97,1.82),(.42,.19,1.99),.13,endgrain)
    beam('crane.jib-brace',(1.31,.92,1.04),(.44,.21,1.94),.105,wood)
    cylinder('crane.pulley',(.46,.225,1.92),.105,.085,iron,'Y')
    beam('crane.hoist',(.46,.19,1.91),(.46,.19,.63),.025,rope)
    box('crane.lift-stone',(.46,.19,.39),(.49,.38,.35),stone[3],.055)
    for dx in [-.25,.25]:
        beam('crane.sling',(.46,.19,.68),(.46+dx,.19,.54),.023,rope)
        beam('crane.sling-wrap',(.46+dx,.19,.54),(.46+dx,.19,.20),.023,rope)
    beam('crane.sling-under',(.21,.19,.20),(.71,.19,.20),.023,rope)
    # 开放式八辐木制卷扬轮保持前工业时代造型。
    center=Vector((1.51,.67,.66))
    for i in range(12):
        a,b=i*math.tau/12,(i+1)*math.tau/12
        p=center+Vector((.34*math.cos(a),0,.34*math.sin(a)))
        q=center+Vector((.34*math.cos(b),0,.34*math.sin(b)))
        beam('crane.winch-rim',p,q,.065,endgrain)
        if i%2==0:
            beam('crane.winch-spoke',center,p,.04,wood)
    beam('crane.winch-axle',(1.51,.53,.66),(1.51,.98,.66),.09,iron)
    beam('crane.axle-support',(1.51,.92,.06),(1.51,.92,.71),.10,wood)
    beam('crane.winding-rope',(1.51,.86,.66),(1.31,.92,2.0),.022,rope)

    # 右下方的小型石商棚作为交易区，避免形成第二座工厂。
    # 真实石料置于棚下，配合石样招牌表达贸易。
    for x in [1.27,2.07]:
        for y in [-.56,.17]:
            beam('market.post',(x,y,0),(x,y,1.04 if y<0 else 1.20),.065,wood)
    beam('market.front-header',(1.22,-.56,1.04),(2.12,-.56,1.04),.065,endgrain)
    beam('market.back-header',(1.22,.17,1.20),(2.12,.17,1.20),.065,endgrain)
    for x in [1.27,2.07]:
        # 支撑肋顺着帆布下垂形状布置，顶部略低于布面。
        for a,b in [(0,.33),(.33,.66),(.66,1)]:
            beam('market.roof-rib',
                 (x,-.65+.91*a,1.007+.19*a-.045*math.sin(math.pi*a)),
                 (x,-.65+.91*b,1.007+.19*b-.045*math.sin(math.pi*b)),.04,wood)
    for k in range(5):
        x0=1.19+k*.192
        verts=[]
        for x in [x0,x0+.192]:
            for t in [0,.33,.66,1]:
                verts.append((x,-.65+.91*t,1.04+.19*t-.045*math.sin(math.pi*t)))
        roof=mesh('market.canvas',verts,[(j,j+4,j+5,j+1) for j in range(3)],[trim if k==2 else cloth])
        bpy.context.view_layer.objects.active=roof
        solid=roof.modifiers.new('canvas-thickness','SOLIDIFY')
        solid.thickness=.018
        bpy.ops.object.modifier_apply(modifier=solid.name)
    box('market.sign',(1.69,-.605,.87),(.29,.045,.20),wood,.025)
    box('market.stone-emblem',(1.69,-.635,.875),(.12,.026,.09),stone[4],.01,angle=.1)

    # 共用的成品石块采用比砖料更大的长方体。
    prototype=box('stock.prototype',(0,0,0),(.39,.30,.24),stone[3],.032)
    data=prototype.data
    bpy.data.objects.remove(prototype,do_unlink=True)
    for x,y,layers in [(1.48,-.30,2),(1.88,-.28,2),(-1.39,-1.48,2),(-1.08,-1.78,1)]:
        for layer in range(layers):
            ob=bpy.data.objects.new('stock.dressed-stone',data)
            asset.objects.link(ob)
            ob.parent=root
            ob.location=(x,y,apron_height(x,y)+.12+layer*.243)
    # 少量大型楔形边角料和石板接缝沿作业路径集中布置。
    for i,(x,y,s) in enumerate([(-1.8,-.98,.20),(-1.27,-1.68,.11),(-.96,-1.82,.09),
                               (.22,-1.78,.10),(1.46,-1.13,.17),(1.61,-1.24,.10)]):
        z=apron_height(x,y)
        v=[(x-s,y-s*.6,z),(x+s,y-s*.5,z),(x+s*.6,y+s*.7,z),(x-s*.8,y+s*.5,z),
           (x-s*.5,y-s*.25,z+s*.6),(x+s*.5,y+s*.15,z+s*.45)]
        mesh('quarry.offcut',v,[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4),(0,3,2,1)],stone,[2,3,1,2,1])
    # 合并固定组件，保留可复用的石料网格实例。
    for prefix in ['quarry.','crane.','market.']:
        parts=[o for o in asset.objects if o.type=='MESH' and o.name.startswith(prefix)]
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active=parts[0]
        bpy.ops.object.join()
        parts[0].name=prefix+'assembly'
