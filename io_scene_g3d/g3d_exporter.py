# <pep8 compliant>

import bpy
import mathutils
import json
from io_scene_g3d.normal_map_helper import NormalMapHelper
from bpy_extras.io_utils import ExportHelper
from bpy.props import (BoolProperty,EnumProperty)

DEBUG = True

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
    
    # Our output file. We save as a python dictionary and then use the JSON module to export it as a JSON file
    output = None
    
    def execute(self, context):
        """Main method run by Blender to export a G3D file"""

        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # define our return state
        result = {'FINISHED'}
        
        self.output = { "version" : [0,1] , "id" : "" , "meshes":[] , "materials":[] , "nodes":[] , "animations":[] }

        #output_file = open(self.filepath , 'w')
        self.write_meshes(context)
        self.write_materials()
        self.write_nodes()
        self.write_animations()
        #output_file.close()
        
        if DEBUG:
            print("Resulting output")
            print(str(self.output))
            print("Writing file")
        
        output_file = open(self.filepath , 'w')
        json_output = json.dumps(self.output , indent=4)
        output_file.write(json_output)
        output_file.close()

        return result

    def write_nodes(self):
        """Writes a 'nodes' section, the section that will relate meshes to objects and materials"""
        
        if DEBUG: print("Writing nodes")
        
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            current_node = {}
            
            current_node["id"] = obj.name

            # Convert our rotation to a quaternion, after exporting we go back to the old value
            old_rot_mode = obj.rotation_mode
            obj.rotation_mode = 'QUATERNION'
            if ( not self.test_default_quaternion( obj.rotation_quaternion )):
                # Do this so that json module can export
                current_node["rotation"] = []
                current_node["rotation"].extend(obj.rotation_quaternion)
            obj.rotation_mode = old_rot_mode
                
            # Exporting scale if there is one
            if ( not self.test_default_scale( obj.scale )):
                current_node["scale"] = []
                current_node["scale"].extend(obj.scale)

            # Exporting translation if there is one
            if ( not self.test_default_transform( obj.location )):
                current_node["translation"] = []
                current_node["translation"].extend(obj.location)

            current_node["parts"] = []
            
            for mat in obj.data.materials:
                current_part = {}
                
                current_part["meshpartid"] = ( "Meshpart__%s__%s" % (obj.data.name , mat.name) )
                current_part["materialid"] = ( "Material__%s" % (mat.name) )
                    
                # Start writing uv mapping
                if len(obj.data.uv_layers) > 0:
                    current_part["uvMapping"] = []
                
                for uvidx in range(len(obj.data.uv_layers)):
                    uv = obj.data.uv_layers[uvidx]
                    current_slot = []

                    for slotidx in range(len(mat.texture_slots)):
                        slot = mat.texture_slots[slotidx]
                        if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                            continue
                        
                        if (slot.uv_layer == uv.name or (slot.uv_layer == "" and uvidx == 0)):
                            current_slot.append( slotidx )
                    
                    current_part["uvMapping"].append( current_slot )

                # Appending this part to the current node
                current_node["parts"].append( current_part )
            
            # Finish this node and append it to the nodes section
            self.output["nodes"].append( current_node )

    def write_materials(self):
        """Write a 'material' section for each material attached to at least a mesh in the scene"""
        
        processed_materials = []
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            # Define 'm' as our mesh
            m = obj.data
            
            for mat in m.materials:
                current_material = {}
                
                if mat.name in processed_materials:
                    continue
                else:
                    processed_materials.append(mat.name)
                
                current_material["id"] = ( "Material__%s" % (mat.name) )
                current_material["ambient"] = [ mat.ambient , mat.ambient , mat.ambient ]
                
                current_material["diffuse"] = []
                current_material["diffuse"].extend(mat.diffuse_color)
                
                current_material["specular"] = []
                current_material["specular"].extend(mat.specular_color)
                
                current_material["emissive"] = [mat.emit , mat.emit , mat.emit]
                
                current_material["shininess"] = mat.specular_intensity

                if mat.raytrace_mirror.use:
                    current_material["reflection"] = mat.raytrace_mirror.reflect_factor

                if mat.use_transparency:
                    current_material["opacity"] = mat.alpha
                    
                if len(mat.texture_slots)  > 0:
                    current_material["textures"] = []

                for slot in mat.texture_slots:
                    current_texture = {}

                    if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                        continue
                    
                    current_texture["id"] = slot.name
                    current_texture["filename"] = (slot.texture.image.filepath.replace("//", "", 1))
                    
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
                    
                    current_texture["type"] = usageType
                    
                    # Ending current texture
                    current_material["textures"].append( current_texture )
                
                # Ending current material
                self.output["materials"].append( current_material )
            
    def write_meshes(self, context):
        """Write a 'mesh' section for each mesh in the scene, or each mesh on the selected objects."""
        
        if DEBUG: print("Writing \"meshes\" section")
        
        # Select what meshes to export (all or only selected) and triangulate meshes prior to exporting.
        # We clone the mesh when triangulating, so we need to clean up after this
        tri_meshes = {}
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            # If we already processed the mesh data associated with this object, continue (ex: multiple objects pointing to same mesh data)
            if obj.data.name in tri_meshes.keys():
                continue
            
            if DEBUG: print("Writing mesh data for object %s" % (obj.name))
            
            current_mesh = obj.to_mesh(context.scene , True, 'PREVIEW', calc_tessface=False)
            self.mesh_triangulate(current_mesh)
            
            # Generate tangent and binormal vectors for this mesh, for this we need at least one UV layer
            if len(current_mesh.uv_layers) > 0:
                uv_layer_name = ""
                if len(current_mesh.uv_layers) > 1:
                    if DEBUG: print("Generating tangent and binormal vectors")
                    
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

            tri_meshes[obj.data.name] = [current_mesh,face_tangent_binormal,vertex_tangent_binormal]

        # Now we have triangulated our meshes and generated tangent and binormal vectors. Export them.
        firstMesh = True
        for m_name in tri_meshes.keys():
            tri_mesh = tri_meshes[m_name]
            m = tri_mesh[0]
            face_tangent_binormal = tri_mesh[1]
            vertex_tangent_binormal = tri_mesh[2]
            
            savedFaces = []
            
            current_mesh = {}
            current_mesh["attributes"] = []
            
            # We will have at least the position and normal of each vertex
            current_mesh["attributes"].append("POSITION")
            current_mesh["attributes"].append("NORMAL")

            # If requested, we will have tangent and binormal attributes
            export_tangent = False
            if self.use_tangent_binormal and face_tangent_binormal != None and vertex_tangent_binormal != None:
                if DEBUG: print("Writing tangent and binormal attribute headers")
                current_mesh["attributes"].append("TANGENT")
                current_mesh["attributes"].append("BINORMAL")
                export_tangent = True
                
            # If we have at least one uvmap, we will have the TEXCOORD attribute.
            uv_count = 0
            export_texture = 0
            for uv in m.uv_layers:
                if DEBUG: print("Writing attribute headers for texture coordinate %d" % (uv_count))
                export_texture = uv_count + 1
                current_mesh["attributes"].append( ("TEXCOORD%d" % (uv_count)) )
                uv_count = uv_count + 1

            # If we have bones and weight associated to our vertices, export weight information
            weight_count = 0
            for vertex in m.vertices:
                if len(vertex.groups) > weight_count:
                    weight_count = len(vertex.groups)
            
            for wc in range(weight_count):
                if DEBUG: print("Writing attribute headers bone weight %d" % (wc))
                current_mesh["attributes"].append( ("BLENDWEIGHT%d" % (wc)) )

            # Start writing vertices of this mesh
            current_mesh["vertices"] = []

            # First we collect vertices from the mesh's faces.
            vertices = []
            for faceIdx in range(len(m.polygons)):
                pol = m.polygons[faceIdx]
                savedFace = []

                for vPos in range(len(pol.vertices)):
                    vi = pol.vertices[vPos]
                    
                    if self.use_normals == 'FACE' or (self.use_normals == 'BLENDER' and not pol.use_smooth):
                        if DEBUG: print("Writing face normals for current vertex")
                        v_normal = pol.normal
                    elif self.use_normals == 'VERTEX' or (self.use_normals == 'BLENDER' and pol.use_smooth):
                        if DEBUG: print("Writing vertex normals for current vertex")
                        v_normal = m.vertices[vi].normal

                    if export_tangent and (self.use_normals == 'FACE' or (self.use_normals == 'BLENDER' and not pol.use_smooth)):
                        v_tangent = face_tangent_binormal[faceIdx][0]
                        v_binormal = face_tangent_binormal[faceIdx][1]
                    elif export_tangent and (self.use_normals == 'VERTEX' or (self.use_normals == 'BLENDER' and pol.use_smooth)):
                        v_tangent = vertex_tangent_binormal[vi][0]
                        v_binormal = vertex_tangent_binormal[vi][1]

                    vertex = []
                    vertex.extend(m.vertices[vi].co)
                    vertex.extend(v_normal)

                    if export_tangent:
                        vertex.extend(v_tangent)
                        vertex.extend(v_binormal)

                    for uv in m.uv_layers:
                        vertex.extend(uv.data[ pol.loop_indices[vPos] ].uv)
                        
                    if weight_count > 0:
                        if DEBUG: print("Writing bone weight for this vertex")
                        weight_data = [[0.000000 , 0.000000]] * weight_count

                        for user in bpy.data.objects:
                            if user.type == 'MESH' and user.data.name == m_name and user.parent != None and user.parent.type == 'ARMATURE':
                                weight_index = 0
                                for vgroup_idx in range(len(user.vertex_groups)):
                                    vgroup = user.vertex_groups[vgroup_idx]
                                    try:
                                        weight_value = vgroup.weight(vi)
                                        if DEBUG: print("Found weight for this vertex at vertex group %s (%d). Weight is %f" % (vgroup.name, vgroup.index , weight_value))
                                        weight_data[ weight_index ] = [ vgroup.index , weight_value ]
                                        weight_index = weight_index + 1
                                    except:
                                        if DEBUG: print("No weight associated for vertex group %s (%d)." % (vgroup.name , vgroup.index))

                                    if weight_index >= weight_count:
                                        break

                        if DEBUG: print("Resulting weight data: %s" % (str(weight_data)))
                        for wd in weight_data:
                            vertex.extend( wd )
                            if DEBUG: print("Appended weight information for vertex. Current vertex data is %s" % (str(vertex)))

                    newPos = 0
                    try:
                        # A vertex with those exact same values was found, only get it's index and append to the current face
                        newPos = vertices.index(vertex)
                    except Exception:
                        # A new vertex was created, append it to our vertex list
                        vertices.append(vertex)
                        newPos = len(vertices)-1

                    savedFace.append(newPos)
                savedFaces.append(savedFace)
                
            # Now we write those vertices to the "vertices" section of the file
            for vertex in vertices:
                current_mesh["vertices"].extend(vertex)
             
            # Now we write the "parts" section, one part for every material
            current_mesh["parts"] = []
            for mPos in range(len(m.materials)):
                material = m.materials[mPos]
                if (material.__class__.__name__ == 'NoneType'):
                    continue
                
                current_part = {}
                
                current_part["id"] = ("Meshpart__%s__%s" % (m_name , material.name))
                current_part["type"] = "TRIANGLES"
                current_part["indices"] = []
                
                for faceIdx in range(len(m.polygons)):
                    savedFace = savedFaces[faceIdx]
                    pol = m.polygons[faceIdx]

                    if (pol.material_index == mPos):
                        current_part["indices"].extend(savedFace)

                # Ending current part
                current_mesh["parts"].append( current_part )
                
            # Ending current mesh
            self.output["meshes"].append( current_mesh )

        # Cleaning up
        for m_name in tri_meshes.keys():
            tri_mesh = tri_meshes[m_name]
            bpy.data.meshes.remove(tri_mesh[0])
        tri_meshes = None
        
    def write_animations(self):
        """Write an 'animations' section for each animation in the scene"""
        if DEBUG: print("Writing animations")
        
    def has_bone(self , armature , bone_name):
        """Return if the given armature has a bone with the given name"""
        found_bone = False
        try:
            armature[bone_name]
            found_bone = True
        except:
            found_bone = False
            
        return found_bone
    
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