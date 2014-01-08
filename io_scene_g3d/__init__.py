bl_info = {
    "name":      "LibGDX G3D Exporter",
    "author":      "Danilo Costa Viana",
    "blender":    (2,6,9),
    "version":    (0,0,1),
    "location":  "File > Import-Export",
    "description":  "Export scene to G3D (LibGDX) format",
    "category":  "Import-Export"
}
        
import bpy
import io_scene_g3d
from io_scene_g3d.g3d_exporter import G3DExporter

class Mesh(object):
    def __init__(self, s):
        self.s = s
    def __repr__(self):
        return '<Mesh(%s)>' % self.s

def menu_func(self, context):
    self.layout.operator(G3DExporter.bl_idname, text="LibGDX G3D text format (.g3dj)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)
    
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()

