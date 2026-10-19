"""Quiet warm-sand tile: continuous curved dunes, no props or vegetation.

Uses geometry and vertex colors only so the sculpted surface survives GLB.
Mounting clearings and the reserved edge strip remain exactly at z=0.
"""
import math

import bpy
from mathutils import Vector


def smooth(t):
    t=max(0,min(1,t))
    return t*t*(3-2*t)


def edge(x,y):
    return max(x*math.cos(math.pi/6+j*math.pi/3)+y*math.sin(math.pi/6+j*math.pi/3) for j in range(6))


def main_crest(x):
    return 1.10+.22*math.sin(x*1.15)-.10*x


def dune_profile(distance,windward,leeward):
    # Broad windward ramp and shorter lee slope; a gently rounded crest rather
    # than a spherical mound or a knife-edged rocky ridge.
    width=windward+(leeward-windward)*smooth((distance+.035)/.07)
    return math.exp(-abs(distance/width)**1.65)


def terrain_height(x,y):
    rear=.81*math.exp(-(x/1.96)**6)*dune_profile(y-main_crest(x),.73,.34)
    left=.36*math.exp(-((y+.30)/1.27)**4)*dune_profile(x+1.72-.16*math.sin(y*1.8),.33,.60)
    right=.34*math.exp(-((x-1.50)/.88)**4)*dune_profile(y-.05-.25*math.sin((x-1)*1.7),.56,.30)
    front=.16*math.exp(-(x/1.66)**6)*dune_profile(y+1.85-.12*math.cos(x*1.8),.24,.36)
    h=rear+left+right+front
    # A handful of shallow wind ripples on one broad slope, not full-tile noise.
    ripple_mask=math.exp(-((x+.35)/1.15)**4-((y-.38)/.45)**4)
    h+=.008*ripple_mask*(.5+.5*math.sin(y*18+.9*math.sin(x*1.8)))
    for cx,cy,r in [(-.55,-.72,.50),(.70,-.83,.34)]:
        h*=smooth((math.hypot(x-cx,y-cy)-r-.16)/.32)
    return h*smooth((2.318-edge(x,y))/.49)


def ground_color(x,y):
    h=terrain_height(x,y)
    # Muted amber hollows, sun-warm sand crests; no green floor or dark grime.
    t=max(0,min(1,.39+.34*h+.095*math.sin(x*1.3+y*.6)))
    return Vector((.47,.285,.115)).lerp(Vector((.72,.535,.285)),t)


def build_quarry(asset,root,mat,box,mesh,link):
    floor=bpy.data.objects['terrain.desert-floor']
    colors=floor.data.color_attributes['COLOR_0']
    for v in floor.data.vertices:
        v.co.z=terrain_height(v.co.x,v.co.y)
    for p in floor.data.polygons:
        p.use_smooth=True
        for idx in p.loop_indices:
            x,y,_=floor.data.vertices[floor.data.loops[idx].vertex_index].co
            colors.data[idx].color=(*ground_color(x,y),1)
    floor.data.update()
    floor['design']='Continuous wind-shaped sand; intentionally empty, no props'
