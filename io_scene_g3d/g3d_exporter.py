import bpy
import mathutils
from io_scene_g3d.normal_map_helper import NormalMapHelper
from bpy_extras.io_utils import ExportHelper
from bpy.props import (BoolProperty,EnumProperty)

class G3DExporter(bpy.types.Operator, ExportHelper):
    """Export scene to G3D (LibGDX) format"""

    bl_idname     = "export_json_g3d.g3dj"
    bl_label      = "G3D Exporter"
    bl_options    = {'PRESET'}
    
    # Exporter options
    use_selection = BoolProperty( \
            name="Selection Only", \
            description="Export only selected objects", \
            default=False, \
            )
            
    use_normals = EnumProperty(
            name="Normals To Use",
            items=(('BLENDER', "Blender Normals", "Use shading option (flat or smooth) defined in Blender to decide what normals to export"),
                   ('VERTEX', "Vertex Normals", "Export normals for each vertex"),
                   ('FACE', "Face Normals", "Each three vertices that compose a face will get the face's normals")),
            default='BLENDER',
            )
            
    use_tangent_binormal = BoolProperty( \
            name="Export Tangent and Binormal Vectors", \
            description="Export tangent and binormal vectors for each vertex", \
            default=False, \
            )
    
    filename_ext    = ".g3dj"
    float_to_str  = "{:8.6f}"
    
    def execute(self, context):
        """Main method run by Blender to export a G3D file"""

        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # define our return state
        result = {'FINISHED'}

        output_file = open(self.filepath , 'w')
        self.write_header(output_file)
        self.write_meshes(output_file , context)
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
        file.write("    \"id\": \"\",\n")
        
    def write_footer(self, file):
        """Writes a footer section before closing the file"""
        file.write("}")
        
    def write_nodes(self, file):
        """Writes a 'nodes' section, the section that will relate meshes to objects and materials"""
        
        # Starting nodes section
        file.write("    ,\"nodes\": [\n")
        
        firstNode = True
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
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
                file.write("            ,\"rotation\": [ %s , %s , %s , %s ]\n" \
                    % ( self.float_to_str.format(rtq[0]) , self.float_to_str.format(rtq[1]) \
                    , self.float_to_str.format(rtq[2]) , self.float_to_str.format(rtq[3]) ))
                
            obj.rotation_mode = old_rot_mode
                
            if ( not self.test_default_scale( obj.scale )):
                sql = obj.scale
                file.write("            ,\"scale\": [ %s , %s , %s ]\n" \
                    % ( self.float_to_str.format(sql[0]) , self.float_to_str.format(sql[1]) , self.float_to_str.format(sql[2]) ) )
                
            if ( not self.test_default_transform( obj.location )):
                loc = obj.location
                file.write("            ,\"translation\": [ %s , %s , %s ]\n" \
                    % ( self.float_to_str.format(loc[0]) , self.float_to_str.format(loc[1]) , self.float_to_str.format(loc[2]) ) )
                
            file.write("            ,\"parts\": [\n")
            
            firstMaterial = True
            for mat in obj.data.materials:
                if firstMaterial:
                    firstMaterial = False
                    file.write("                {\n")
                else:
                    file.write("                ,{\n")
                    
                file.write("                    \"meshpartid\": \"Meshpart__%s__%s\",\n" % (obj.data.name , mat.name) )
                file.write("                    \"materialid\": \"Material__%s\"\n" % (mat.name) )
                
                # Start writing uv mapping
                if len(obj.data.uv_layers) > 0:
                    file.write("                    ,\"uvMapping\": [")
                
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
                                file.write(", ")
                                
                            file.write(str(slotidx))
                        
                    file.write("]")
                        
                # End write uv mapping
                if len(obj.data.uv_layers) > 0:
                    file.write("]\n")

                file.write("                }\n")
                
            file.write("            ]\n")
            file.write("        }\n")
        
        # Ending nodes section
        file.write("    ]\n")
        
    def write_materials(self, file):
        """Write a 'material' section for each material attached to at least a mesh in the scene"""
        
        # Starting materials section
        file.write("    ,\"materials\": [\n")
        
        firstMaterial = True
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            # Define 'm' as our mesh
            m = obj.data
            
            for mat in m.materials:
                if firstMaterial:
                    firstMaterial = False
                    file.write("        ")
                else:
                    file.write("        ,")
                
                file.write("{\n")
                file.write("            \"id\": \"Material__%s\",\n" % (mat.name) )
                file.write("            \"ambient\": [%s, %s, %s],\n" \
                    % (self.float_to_str.format(mat.ambient) , self.float_to_str.format(mat.ambient) , self.float_to_str.format(mat.ambient)) )
                file.write("            \"diffuse\": [%s, %s, %s],\n" \
                    % ( self.float_to_str.format(mat.diffuse_color[0]) , self.float_to_str.format(mat.diffuse_color[1]) , self.float_to_str.format(mat.diffuse_color[2]) ) )
                file.write("            \"specular\": [%s, %s, %s],\n" \
                    % ( self.float_to_str.format(mat.specular_color[0]) , self.float_to_str.format(mat.specular_color[1]) , self.float_to_str.format(mat.specular_color[2]) ) )
                file.write("            \"emissive\": [%s, %s, %s],\n" \
                    % ( self.float_to_str.format(mat.emit) , self.float_to_str.format(mat.emit) , self.float_to_str.format(mat.emit) ) )
                file.write("            \"shininess\": %s\n" \
                    % ( self.float_to_str.format(mat.specular_intensity) ) )

                if mat.raytrace_mirror.use:
                    file.write("            ,\"reflection\": %s\n" \
                        % ( self.float_to_str.format(mat.raytrace_mirror.reflect_factor) ) )

                if mat.use_transparency:
                    file.write("            ,\"opacity\": %s\n" \
                        % ( self.float_to_str.format(mat.alpha) ) )
                
                foundTexture = False
                for slot in mat.texture_slots:
                    if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                        continue
                    
                    if not foundTexture:
                        foundTexture = True
                        file.write("            ,\"textures\": [\n")
                        file.write("                ")
                    else:
                        file.write("                ,")
                    
                    file.write("{\n")
                    file.write("                    \"id\": \"%s\",\n" % (slot.name) )
                    file.write("                    \"filename\": \"%s\",\n" % (slot.texture.image.filepath.replace("//", "", 1)) )
                    
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
                    
                    file.write("                    \"type\": \"%s\"\n" % (usageType))
                    
                    # Ending current texture
                    file.write("                }\n")
                
                # Ending texture section inside material
                if foundTexture:
                    file.write("            ]\n")
                    
                # Ending current material
                file.write("        }\n")
                    
        # Ending materials section
        file.write("    ]\n")
            
    def write_meshes(self, file, context):
        """Write a 'mesh' section for each mesh in the scene, or each mesh on the selected objects."""
        
        # Starting meshes section
        file.write("    \"meshes\": [\n")
        
        # Select what meshes to export (all or only selected) and triangulate meshes prior to exporting.
        # We clone the mesh when triangulating, so we need to clean up after this
        tri_meshes = []
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            current_mesh = obj.to_mesh(context.scene , True, 'PREVIEW', calc_tessface=False)
            self.mesh_triangulate(current_mesh)
            
            # Generate tangent and binormal vectors for this mesh, for this we need at least one UV layer
            if len(current_mesh.uv_layers) > 0:
                uv_layer_name = ""
                if len(current_mesh.uv_layers) > 1:
                    # Search for a texture with normal mapping, if one doesn't exist use the first UV layer available
                    for mat in current_mesh.materials:
                        for slot in mat.texture_slots:
                            if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                                continue
                            elif slot.use_map_normal:
                                uv_layer_name = slot.uv_layer
                                break

                        if uv_layer_name != "":
                            break
                        

                face_tangent_binormal = [None] * len(current_mesh.polygons)
                vertex_tangent_binormal = [None] * len(current_mesh.vertices)
                NormalMapHelper.generate_tangent_binormal(None,current_mesh,face_tangent_binormal,vertex_tangent_binormal,uv_layer_name)
            else:
                face_tangent_binormal = None
                vertex_tangent_binormal = None

            tri_meshes.append( [obj.data.name,current_mesh,face_tangent_binormal,vertex_tangent_binormal] )

        # Now we have triangulated our meshes and generated tangent and binormal vectors. Export them.
        firstMesh = True
        for tri_mesh in tri_meshes:
            m_name = tri_mesh[0]
            m = tri_mesh[1]
            face_tangent_binormal = tri_mesh[2]
            vertex_tangent_binormal = tri_mesh[3]
            savedFaces = []
            
            if (firstMesh):
                firstMesh=False
                file.write("        {\n")
            else:
                file.write("        ,{\n")
            
            # We will have at least the position and normal of each vertex
            file.write("            \"attributes\": [\"POSITION\", \"NORMAL\"")

            # If requested, we will have tangent and binormal attributes
            export_tangent = False
            if self.use_tangent_binormal and face_tangent_binormal != None and vertex_tangent_binormal != None:
                file.write(", \"TANGENT\", \"BINORMAL\"")
                export_tangent = True
            
            # If we have at least one uvmap, we will have the TEXCOORD attribute.
            uv_count = 0
            export_texture = False
            for uv in m.uv_layers:
                export_texture = True
                file.write(", \"TEXCOORD%d\"" % (uv_count))
                uv_count = uv_count+1
                
                
            # Start writing vertices of this mesh
            file.write("],\n")
            file.write("            \"vertices\": [\n")
            
            # First we collect vertices from the mesh's faces.
            vertices = []
            for faceIdx in range(len(m.polygons)):
                pol = m.polygons[faceIdx]
                savedFace = []

                for vPos in range(len(pol.vertices)):
                    vi = pol.vertices[vPos]
                    
                    if self.use_normals == 'FACE' or (self.use_normals == 'BLENDER' and not pol.use_smooth):
                        v_normal = pol.normal
                    elif self.use_normals == 'VERTEX' or (self.use_normals == 'BLENDER' and pol.use_smooth):
                        v_normal = m.vertices[vi].normal

                    if export_tangent and self.use_normals == 'FACE' or (self.use_normals == 'BLENDER' and not pol.use_smooth):
                        v_tangent = face_tangent_binormal[faceIdx][0]
                        v_binormal = face_tangent_binormal[faceIdx][1]
                    elif export_tangent and self.use_normals == 'VERTEX' or (self.use_normals == 'BLENDER' and pol.use_smooth):
                        v_tangent = vertex_tangent_binormal[vi][0]
                        v_binormal = vertex_tangent_binormal[vi][1]

                    vertex = []
                    vertex.append(m.vertices[vi].co)
                    vertex.append(v_normal)

                    if export_tangent:
                        vertex.append(v_tangent)
                        vertex.append(v_binormal)

                    for uv in m.uv_layers:
                        vertex.append(uv.data[ pol.loop_indices[vPos] ].uv)
                        
                    newPos = 0
                    try:
                        newPos = vertices.index(vertex)
                    except Exception:
                        vertices.append(vertex)
                        newPos = len(vertices)-1

                    savedFace.append(newPos)
                    
                savedFaces.append(savedFace)
             
            # Now we write those vertices to the "vertices" section of the file
            for vPos in range(len(vertices)):
                v = vertices[vPos]
                file.write("                ")
                file.write("%s, %s, %s, " % (self.float_to_str.format(v[0][0]) , self.float_to_str.format(v[0][1]) , self.float_to_str.format(v[0][2])))
                file.write("%s, %s, %s" % (self.float_to_str.format(v[1][0]) , self.float_to_str.format(v[1][1]) , self.float_to_str.format(v[1][2])))

                if export_tangent:
                    file.write(", %s, %s, %s" % (self.float_to_str.format(v[2][0]) , self.float_to_str.format(v[2][1]), self.float_to_str.format(v[2][2])))
                    file.write(", %s, %s, %s" % (self.float_to_str.format(v[3][0]) , self.float_to_str.format(v[3][1]), self.float_to_str.format(v[3][2])))
                
                if export_texture:
                    start_pos = 2
                    if export_tangent:
                        start_pos = 4

                    for uvpos in range(start_pos , len(v)):
                        file.write(", %s, %s" % (self.float_to_str.format(v[uvpos][0]) , self.float_to_str.format(v[uvpos][1])))
                
                if (vPos < len(vertices)-1):
                    file.write(",\n")
                else:
                    file.write("\n            ],\n")
             
            # Now we write the "parts" section, one part for every material
            file.write("            \"parts\": [\n")
            firstPart = True
            for mPos in range(len(m.materials)):
                material = m.materials[mPos]
                
                if (material.__class__.__name__ == 'NoneType'):
                    continue
                
                if (firstPart):
                    firstPart = False
                    file.write("                ")
                else:
                    file.write("                ,")
                    
                
                file.write("{\n")
                file.write("                    \"id\": \"Meshpart__%s__%s\",\n" % (m_name , material.name) )
                file.write("                    \"type\": \"TRIANGLES\",\n")
                file.write("                    \"indices\": [ ")
                
                firstFace = True
                for faceIdx in range(len(m.polygons)):
                    savedFace = savedFaces[faceIdx]
                    pol = m.polygons[faceIdx]

                    if (pol.material_index == mPos):
                        if (firstFace):
                            firstFace = False
                        else:
                            file.write(", ")
                        file.write("%d, %d, %d" % (savedFace[0] , savedFace[1] , savedFace[2]))

                file.write(" ]\n")
                file.write("                }\n")
                
            file.write("            ]\n")
            file.write("        }\n")

        # Ending meshes section
        file.write("    ]\n")
        
        # Cleaning up
        for tri_mesh in tri_meshes:
            bpy.data.meshes.remove(tri_mesh[1])
        tri_meshes = None
        
    def write_animations(self, file):
        """Write an 'animations' section for each animation in the scene"""
        
        # Starting animations section
        file.write("    ,\"animations\": [\n")
        
        # Ending animations section
        file.write("    ]\n")
        
    def mesh_triangulate(self, me):
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        
    def test_default_quaternion(self, quaternion):
        return quaternion[0] == 1.0 and quaternion[1] == 0.0 and quaternion[2] == 0.0 and quaternion[3] == 0.0
    
    def test_default_scale(self, scale):
        return scale[0] == 1.0 and scale[1] == 1.0 and scale[2] == 1.0
    
    def test_default_transform(self, transform):
        return transform[0] == 0.0 and transform[1] == 0.0 and transform[2] == 0.0
