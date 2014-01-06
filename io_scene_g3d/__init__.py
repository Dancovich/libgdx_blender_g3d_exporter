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
import mathutils
from bpy_extras.io_utils import ExportHelper

class G3DExporter(bpy.types.Operator, ExportHelper):
    """Export scene to G3D (LibGDX) format"""

    bl_idname     = "export_json_g3d.g3dj"
    bl_label      = "G3D Exporter"
    bl_options    = {'PRESET'}
    float_to_str  = "{:8.6f}"
    
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
        self.write_materials(output_file)
        self.write_nodes(output_file)
        self.write_animations(output_file)
        self.write_footer(output_file)
        output_file.close()

        return result

    def write_header(self, file):
        """Writes the header of a G3D file"""
        file.write("{\n")
        file.write("    \"version\": [  0,   1],\n")
        file.write("    \"id\": "",\n")
        
    def write_footer(self, file):
        """Writes a footer section before closing the file"""
        file.write("}")
        
    def write_nodes(self, file):
        """Writes a 'nodes' section, the section that will relate meshes to objects and materials"""
        
        # Starting nodes section
        file.write("    ,\"nodes\": [\n")
        
        firstNode = True
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            
            if firstNode:
                firstNode = False
                file.write("        {\n")
            else:
                file.write("        ,{\n")
                
            file.write("            \"id\": \"%s\"\n" % (obj.name))
            
            old_rot_mode = obj.rotation_mode
            obj.rotation_mode = 'QUATERNION'
            if ( not self.test_default_quaternion( obj.rotation_quaternion )):
                rtq = obj.rotation_quaternion
                file.write("            ,\"rotation\": [ %s , %s , %s , %s ]\n" % ( self.float_to_str.format(rtq[0]) , self.float_to_str.format(rtq[1]) , self.float_to_str.format(rtq[2]) , self.float_to_str.format(rtq[3]) ))
                
            obj.rotation_mode = old_rot_mode
                
            if ( not self.test_default_scale( obj.scale )):
                sql = obj.scale
                file.write('            ,"scale": ['+self.float_to_str.format(sql[0])+', '+self.float_to_str.format(sql[1])+', '+self.float_to_str.format(sql[2])+']\n')
                
            if ( not self.test_default_transform( obj.location )):
                loc = obj.location
                file.write('            ,"translation": ['+self.float_to_str.format(loc[0])+', '+self.float_to_str.format(loc[1])+', '+self.float_to_str.format(loc[2])+']\n')
                
            file.write('            ,"parts": [\n')
            
            firstMaterial = True
            for mat in obj.data.materials:
                if firstMaterial:
                    firstMaterial = False
                    file.write('                {\n')
                else:
                    file.write('                ,{\n')
                    
                file.write('                    "meshpartid": "Meshpart__'+obj.data.name+'__'+mat.name+'",\n')
                file.write('                    "materialid": "Material__'+mat.name+'",\n')
                
                # Start writing uv mapping
                file.write('                    "uvMapping": [')
                
                firstUV = True
                for uvidx in range(len(obj.data.uv_layers)):
                    uv = obj.data.uv_layers[uvidx]
                    
                    if firstUV:
                        firstUV = False
                    else:
                        file.write(',')
                    
                    file.write('[')
                    firstSlot = True
                    for slotidx in range(len(mat.texture_slots)):
                        
                        slot = mat.texture_slots[slotidx]
                        if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                            continue
                        
                        if (slot.uv_layer == uv.name or (slot.uv_layer == "" and uvidx == 0)):
                            if firstSlot:
                                firstSlot = False
                            else:
                                file.write(', ')
                                
                            file.write(str(slotidx))
                        
                    file.write(']')
                        
                # End write uv mapping
                file.write(']\n')

                file.write('                }\n')
                
            file.write('            ]\n')
            file.write('        }\n')
        
        # Ending nodes section
        file.write('    ]\n')
        
    def write_materials(self, file):
        """Write a 'material' section for each material attached to at least a mesh in the scene"""
        
        # Starting materials section
        file.write('    ,"materials": [\n')
        
        firstMaterial = True
        for m in bpy.data.meshes:
            if ( m.users <= 0 ):
                continue
            
            for mat in m.materials:
                if firstMaterial:
                    firstMaterial = False
                    file.write('        ')
                else:
                    file.write('        ,')
                
                file.write('{\n')
                file.write('            "id": "Material__'+ mat.name +'",\n')
                file.write('            "ambient": ['+self.float_to_str.format(mat.ambient)+', '+self.float_to_str.format(mat.ambient)+', '+self.float_to_str.format(mat.ambient)+'],\n')
                file.write('            "diffuse": ['+self.float_to_str.format(mat.diffuse_color[0])+', '+self.float_to_str.format(mat.diffuse_color[1])+', '+self.float_to_str.format(mat.diffuse_color[2])+'],\n')
                file.write('            "emit": ['+self.float_to_str.format(mat.emit)+', '+self.float_to_str.format(mat.emit)+', '+self.float_to_str.format(mat.emit)+']\n')
                
                foundTexture = False
                for slot in mat.texture_slots:
                    if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                        continue
                    
                    if not foundTexture:
                        foundTexture = True
                        file.write('            ,"textures": [\n')
                        file.write('                ')
                    else:
                        file.write('                ,')
                    
                    file.write('{\n')
                    file.write('                    "id": "'+slot.name+'",\n')
                    file.write('                    "filename": "' + slot.texture.image.filepath.replace("//", "", 1) + '",\n')
                    
                    usageType = ""
                    
                    if slot.use_map_color_diffuse:
                        usageType = "DIFFUSE"
                    elif slot.use_map_normal and slot.texture.use_normal_map:
                        usageType = "NORMAL"
                    elif slot.use_map_normal and not slot.texture.use_normal_map:
                        usageType = "BUMP"
                    elif slot.use_map_ambient:
                        usageType = "AMBIENT"
                    elif slot.use_map_emit:
                        usageType = "EMISSIVE"
                    elif slot.use_map_diffuse:
                        usageType = "REFLECTION"
                    elif slot.use_map_alpha:
                        usageType = "TRANSPARENCY"
                    elif slot.use_map_color_spec:
                        usageType = "SPECULAR"
                    elif slot.use_map_specular:
                        usageType = "SHININESS"
                    else:
                        usageType = "UNKNOWN"
                    
                    file.write('                    "type": "'+usageType+'"\n')
                    
                    # Ending current texture
                    file.write('                }\n')
                
                # Ending texture section inside material
                if foundTexture:
                    file.write('            ]\n')
                    
                # Ending current material
                file.write('        }\n')
                    
        # Ending materials section
        file.write('    ]\n')
            
    def write_meshes(self, file):
        """Write a 'mesh' section for each mesh in the scene, or each mesh on the selected objects."""
        
        # Starting meshes section
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
                    
                    # UNCOMMENT IF USING VERTEX NORMALS
                    v_normal = m.vertices[vi].normal
                    
                    # UNCOMMENT IF USING FACE NORMALS
                    #v_normal = pol.normal
                    
                    vertex = []
                    vertex.append(m.vertices[vi].co)
                    vertex.append(v_normal)

                    for uv in m.uv_layers:
                        vertex.append(uv.data[ pol.loop_indices[vPos] ].uv)
                        
                    newPos = 0
                    try:
                        newPos = vertices.index(vertex)
                        # print("FOUND VERTEX AT "+str(newPos))
                    except Exception:
                        vertices.append(vertex)
                        newPos = len(vertices)-1
                        # print("CREATED VERTEX AT "+str(newPos))

                    savedFace.append(newPos)
                    
                savedFaces.append(savedFace)
             
            # Now we write those vertices to the "vertices" section of the file
            for vPos in range(len(vertices)):
                v = vertices[vPos]
                file.write('                ')
                file.write(self.float_to_str.format(v[0][0])+', '+self.float_to_str.format(v[0][1])+', '+self.float_to_str.format(v[0][2])+', ')
                file.write(self.float_to_str.format(v[1][0])+', '+self.float_to_str.format(v[1][1])+', '+self.float_to_str.format(v[1][2]))
                
                if (len(v) > 2):
                    for uvpos in range(2 , len(v)):
                        file.write(', '+self.float_to_str.format(v[uvpos][0])+', '+self.float_to_str.format(v[uvpos][1]))
                
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
                file.write('                    "id": "Meshpart__' + str(m.name) + '__' + str(material.name) +'",\n')
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

        # Ending meshes section
        file.write('    ]\n')
        
    def write_animations(self, file):
        """Write an 'animations' section for each animation in the scene"""
        
        # Starting animations section
        file.write('    ,"animations": [\n')
        
        # Ending animations section
        file.write('    ]\n')
        
    def test_default_quaternion(self, quaternion):
        return quaternion[0] == 1.0 and quaternion[1] == 0.0 and quaternion[2] == 0.0 and quaternion[3] == 0.0
    
    def test_default_scale(self, scale):
        return scale[0] == 1.0 and scale[1] == 1.0 and scale[2] == 1.0
    
    def test_default_transform(self, transform):
        return transform[0] == 0.0 and transform[1] == 0.0 and transform[2] == 0.0


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