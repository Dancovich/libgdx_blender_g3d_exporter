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
from bpy_extras.io_utils import ExportHelper

class G3DExporter(bpy.types.Operator, ExportHelper):
    """Export scene to G3D (LibGDX) format"""

    bl_idname      = "export_json_g3d.g3dj"
    bl_label        = "G3D Exporter"
    bl_options    = {'PRESET'}
    
    filename_ext    = ".g3dj"

    def execute(self, context):
        """Main method run by Blender to export a G3D file"""

        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # define our return state
        result = {'FINISHED'}

        output_file = open(self.filepath , 'w')
        self.write_header(output_file)
        self.write_meshes(output_file)
        output_file.close()

        return result

    def write_header(self, file):
        """Writes the header of a G3D file"""
        file.write('{\n')
        file.write('    "version": [  0,   1],\n')
        file.write('    "id": "",\n')
        
    def write_meshes(self, file):
        """Write a 'mesh' section for each mesh in the scene, or each mesh on the selected objects."""
        file.write('    "meshes": [\n')
        
        firstMesh = True
        for m in bpy.data.meshes:
            savedFaces = []
            
            if ( m.users <= 0 ):
                continue
            
            if (firstMesh):
                firstMesh=False
                file.write('        {\n')
            else:
                file.write('        ,{\n')
            
            # We will have at least the position and normal of each vertex
            file.write('            "attributes": ["POSITION", "NORMAL"')
            
            # If we have at least one uvmap, we will have the TEXCOORD attribute.
            uv_count = 0
            for uv in m.uv_layers:
                file.write(', "TEXCOORD'+str(uv_count)+'"')
                uv_count = uv_count+1
                
            # Start writing vertices of this mesh
            file.write('],\n')
            file.write('            "vertices": [\n')
            
            # First we collect vertices from the mesh's faces.
            vertices = []
            for faceIdx in range(len(m.polygons)):
                pol = m.polygons[faceIdx]
                savedFace = []

                for vPos in range(len(pol.vertices)):
                    vi = pol.vertices[vPos]
                    vertex = []
                    vertex.append(m.vertices[vi].co)
                    vertex.append(m.vertices[vi].normal)
                    vertex.append(pol.normal)

                    for uv in m.uv_layers:
                        vertex.append(uv.data[ pol.loop_indices[vPos] ].uv)
                        
                    newPos = 0
                    try:
                        newPos = vertices.index(vertex)
                        print("FOUND VERTEX AT "+str(newPos))
                    except Exception:
                        vertices.append(vertex)
                        newPos = len(vertices)-1
                        print("CREATED VERTEX AT "+str(newPos))

                    savedFace.append(newPos)
                    
                savedFaces.append(savedFace)
             
            # Now we write those vertices to the "vertices" section of the file
            for vPos in range(len(vertices)):
                v = vertices[vPos]
                file.write('                ')
                file.write("{:8.6f}".format(v[0][0])+', '+"{:8.6f}".format(v[0][1])+', '+"{:8.6f}".format(v[0][2])+', ')
                file.write("{:8.6f}".format(v[1][0])+', '+"{:8.6f}".format(v[1][1])+', '+"{:8.6f}".format(v[1][2]))
                
                if (len(v) > 3):
                    for uvpos in range(3 , len(v)):
                        file.write(', '+"{:8.6f}".format(v[uvpos][0])+', '+"{:8.6f}".format(v[uvpos][1]))
                
                if (vPos < len(vertices)-1):
                    file.write(',\n')
                else:
                    file.write('\n            ],\n')
             
            # Now we write the "parts" section, one part for every material
            file.write('            "parts": [\n')
            firstPart = True
            for mPos in range(len(m.materials)):
                material = m.materials[mPos]
                
                if (material.__class__.__name__ == 'NoneType'):
                    continue
                
                if (firstPart):
                    firstPart = False
                    file.write('                ')
                else:
                    file.write('                ,')
                    
                
                file.write('{\n')
                file.write('                    "id": "meshpart_'+ str(material.name) +'",\n')
                file.write('                    "type": "TRIANGLES",\n')
                file.write('                    "indices": [ ')
                
                firstFace = True
                for faceIdx in range(len(m.polygons)):
                    savedFace = savedFaces[faceIdx]
                    pol = m.polygons[faceIdx]

                    if (pol.material_index == mPos):
                        if (firstFace):
                            firstFace = False
                        else:
                            file.write(', ')
                        file.write(str(savedFace[0])+', '+str(savedFace[1])+', '+str(savedFace[2]))

                file.write(' ]\n')
                file.write('                }\n')
                
            file.write('            ]\n')
            file.write('        }\n')

        file.write('    ]\n')


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