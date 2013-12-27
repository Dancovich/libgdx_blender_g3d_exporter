bl_info = {
    "name":         "LibGDX G3D Exporter",
    "author":       "Danilo Costa Viana",
    "blender":      (2,6,9),
    "version":      (0,0,1),
    "location":     "File > Import-Export",
    "description":  "Export scene to G3D (LibGDX) format",
    "category":     "Import-Export"
}
        
import bpy
from bpy_extras.io_utils import ExportHelper

class G3DExporter(bpy.types.Operator, ExportHelper):
    """Export scene to G3D (LibGDX) format"""

    bl_idname       = "export_json_g3d.g3dj"
    bl_label        = "G3D Exporter"
    bl_options      = {'PRESET'}
    
    filename_ext    = ".g3dj"

    def execute(self, context):
        """Main method run by Blender to export a G3D file"""

        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # define our return state
        result = {'FINISHED'}

        output_file = open(self.filepath , 'w')
        self.write_header(output_file)
        output_file.close()

        return result

    def write_header(self, file):
        """Writes the header of a G3D file"""
        file.write('{\n')
        file.write('	"version": [  0,   1],\n')
        file.write('	"id": "",\n')
        
        for o in bpy.data.objects
            print(o)

class Mesh(object):
    def __init__(self, s):
        self.s = s
    def __repr__(self):
        return '<Mesh(%s)>' % self.s

def menu_func(self, context):
    self.layout.operator(G3DExporter.bl_idname, text="LibGDX G3D text format(.g3dj)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)
    
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()