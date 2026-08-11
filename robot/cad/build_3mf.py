"""Build a print-ready 3MF with all 8 QBIT parts.
3MF preserves shared vertex indices, so part_18's arm stays intact."""
import zipfile
import os
import xml.etree.ElementTree as ET

print_ready = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready"
out_3mf = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\QBIT_body.3mf"

# The original3MF has proper vertex sharing — extract parts from it
src_3mf = r"C:\Users\elsay\Downloads\3D Model.3mf"

# Map: original3MF object_id -> our part name
# From the earlier analysis:
# Object 1 (8v,12t) = part_3
# Object 3 (17v,30t) = ???  (not in our print set)
# Object 5 (7311v,14650t) = part_5
# Object 7 (8v,12t) = part_3 duplicate?
# Object 8 (1149v,2306t) = part_8
# Object 10 (7999v,16026t) = part_10
# Object 12 (990v,1988t) = part_12
# Object 14 (1077v,2162t) = part_14
# Object 15 (8v,12t) = small cube
# Object 17 (2880v,5760t) = part_17
# Object 18 (7731v,15486t) = part_18

part_map = {
    '1': 'part_3',
    '5': 'part_5',
    '8': 'part_8',
    '10': 'part_10',
    '12': 'part_12',
    '14': 'part_14',
    '17': 'part_17',
    '18': 'part_18',
}

# Read source3MF
with zipfile.ZipFile(src_3mf, 'r') as z:
    with z.open('3D/3dmodel.model') as f:
        content = f.read()

root = ET.fromstring(content)
ns = {'3mf': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

# Build new model with only the 8 parts
model_root = ET.Element('model')
model_root.set('xmlns', ns['3mf'])
model_root.set('unit', 'millimeter')
model_root.set('xml:lang', 'en-US')

resources = ET.SubElement(model_root, 'resources')

build = ET.SubElement(model_root, 'build')

new_id = 1
id_map = {}  # old_id -> new_id

for obj in root.findall('.//3mf:object', ns):
    old_id = obj.get('id')
    if old_id not in part_map:
        continue

    part_name = part_map[old_id]
    mesh = obj.find('3mf:mesh', ns)
    if mesh is not None:
        new_obj = ET.SubElement(resources, 'object')
        new_obj.set('id', str(new_id))
        new_obj.set('type', 'model')
        new_obj.set('name', part_name)
        # Copy mesh directly
        new_mesh = ET.SubElement(new_obj, 'mesh')
        new_mesh.append(mesh.find('3mf:vertices', ns))
        new_mesh.append(mesh.find('3mf:triangles', ns))

        # Add to build
        item = ET.SubElement(build, 'item')
        item.set('objectid', str(new_id))

        id_map[old_id] = new_id
        new_id += 1
        print("  %s (obj %s) -> new id %s" % (part_name, old_id, id_map[old_id]))

# Write3MF
model_xml = ET.tostring(model_root, encoding='unicode', xml_declaration=False)
model_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + model_xml

with zipfile.ZipFile(out_3mf, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>''')
    z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>''')
    z.writestr('3D/3dmodel.model', model_xml)

print("\nWrote:", out_3mf)
print("Size:", os.path.getsize(out_3mf), "bytes")
