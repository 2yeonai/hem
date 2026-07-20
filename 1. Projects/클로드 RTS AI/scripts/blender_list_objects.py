"""Startup.blend을 열어 모든 오브젝트 이름/타입/버텍스 수를 텍스트로 덤프.
blender --background --python blender_list_objects.py -- <blend_path> <out_path>
"""
import bpy
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
blend_path = argv[0]
out_path = argv[1]

bpy.ops.wm.open_mainfile(filepath=blend_path)

with open(out_path, "w", encoding="utf-8") as f:
    f.write(f"total objects: {len(bpy.data.objects)}\n")
    f.write(f"total collections: {len(bpy.data.collections)}\n\n")
    f.write("=== collections ===\n")
    for c in bpy.data.collections:
        f.write(f"{c.name} | objects={len(c.objects)}\n")
    f.write("\n=== objects (name | type | verts | parent | collection) ===\n")
    for obj in bpy.data.objects:
        verts = len(obj.data.vertices) if obj.type == "MESH" and obj.data else 0
        parent = obj.parent.name if obj.parent else ""
        cols = ",".join(c.name for c in obj.users_collection)
        f.write(f"{obj.name}\t{obj.type}\t{verts}\t{parent}\t{cols}\n")

print("DONE_LISTING", len(bpy.data.objects))
