"""Startup.blend에서 매핑된 근육 오브젝트만 골라 Decimate 후 glTF(.glb)로 내보내기.
blender --background --python blender_export_muscles.py -- <blend_path> <mapping_json> <out_glb> <decimate_ratio>
"""
import bpy
import sys
import json

argv = sys.argv[sys.argv.index("--") + 1:]
blend_path = argv[0]
mapping_path = argv[1]
out_glb = argv[2]
decimate_ratio = float(argv[3]) if len(argv) > 3 else 0.2

print("opening", blend_path)
bpy.ops.wm.open_mainfile(filepath=blend_path)

mapping = json.load(open(mapping_path, encoding="utf-8"))
wanted_names = set()
for z, names in mapping.items():
    wanted_names.update(names)

print("wanted objects:", len(wanted_names))

found = []
missing = list(wanted_names)
for obj in list(bpy.data.objects):
    if obj.name in wanted_names:
        found.append(obj)
        missing.remove(obj.name)

print("found:", len(found), "missing:", len(missing))
if missing:
    print("MISSING_NAMES:", missing[:20])

# 선택 안 된 오브젝트는 전부 삭제 (씬을 근육만 남기기 위해)
# view layer 밖에 있는 오브젝트도 있어 select_set/ops.delete 대신 직접 remove 사용
found_set = set(found)
to_delete = [o for o in list(bpy.data.objects) if o not in found_set]
print("deleting non-target objects:", len(to_delete))
for o in to_delete:
    bpy.data.objects.remove(o, do_unlink=True)

# 부모가 지워졌을 수 있으니 남은 오브젝트의 parent를 끊어 world 좌표 유지
bpy.context.view_layer.update()
for obj in found:
    if obj.parent is not None and obj.parent not in found_set:
        mw = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = mw

# 총 버텍스 수 (decimate 전)
total_before = sum(len(o.data.vertices) for o in found if o.type == "MESH" and o.data)
print("total verts before decimate:", total_before)

# Decimate 적용 (좌우 대칭 근육이 mesh data를 공유(multi-user)하는 경우가 많아 먼저 single-user로 분리)
for obj in found:
    if obj.type != "MESH" or not obj.data:
        continue
    if len(obj.data.vertices) < 50:
        continue  # 너무 작은 메시는 생략(품질 저하 방지)
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    mod = obj.modifiers.new(name="Decimate", type="DECIMATE")
    mod.ratio = decimate_ratio
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

total_after = sum(len(o.data.vertices) for o in found if o.type == "MESH" and o.data)
print("total verts after decimate:", total_after)

# glTF exporter가 오브젝트명의 공백/마침표를 정규화하면서 이름 충돌(001, _1 접미사)이 생겨
# 원본명 복원이 불가능해지는 문제가 있었음 -> export 직전에 고유 안전 ID로 개명하고 대응표를 별도 저장.
id_map = {}  # safe_id -> original object name
for i, obj in enumerate(found):
    safe_id = "muscle_%04d" % i
    id_map[safe_id] = obj.name
    obj.name = safe_id
    if obj.data:
        obj.data.name = safe_id + "_data"

idmap_path = out_glb.rsplit(".", 1)[0] + "_idmap.json"
json.dump(id_map, open(idmap_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ID_MAP_SAVED", idmap_path, len(id_map))

# 남은 오브젝트가 근육뿐이므로 selection 없이 씬 전체 export
bpy.ops.export_scene.gltf(
    filepath=out_glb,
    export_format="GLB",
    use_selection=False,
    export_apply=True,
    export_yup=True,
)

print("EXPORT_DONE", out_glb)
