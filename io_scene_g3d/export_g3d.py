# <pep8 compliant>

import bpy
import mathutils
import json
from io_scene_g3d.normal_map_helper import NormalMapHelper
from bpy_extras.io_utils import ExportHelper
from bpy.props import (BoolProperty,EnumProperty)

DEBUG = False

class G3DExporter(bpy.types.Operator, ExportHelper):
    """Export scene to G3D (LibGDX) format"""

    bl_idname     = "export_json_g3d.g3dj"
    bl_label      = "G3D Exporter"
    bl_options    = {'PRESET'}
    
    P_LOCATION = 'location'
    P_ROTATION = 'rotation_quaternion'
    P_SCALE    = 'scale'
    
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
        self.write_armatures()
        self.write_animations(context)
        #output_file.close()
        
        if DEBUG:
            print("Resulting output")
            print(str(self.output))
            print("Writing file")
        
        output_file = open(self.filepath , 'w')
        json_output = json.dumps(self.output , indent=4, sort_keys=True)
        output_file.write(json_output)
        output_file.close()

        return result
    
    def _write_node_child_object(self, parent):
        """Return an array with all children of the parent object. Parent object must be a mesh object"""
        
        #
        # This code can be improved. Currently this method is essentialy the same as the
        # "write_nodes" method, but was separated to not overwelm the original method with specific
        # logic to diferentiate a root node from a child node.
        #
        
        if parent == None or parent.type != 'MESH':
            raise Exception("Parent must be a mesh type object")
        
        children = []
        
        for obj in parent.children:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            current_node = {}
            
            current_node["id"] = obj.name
            
            # Get the transformation relative to the parent and decompose it
            location = [0,0,0]
            rotation_quaternion = [1,0,0,0]
            scale = [1,1,1]
            try:
                location, rotation_quaternion, scale = obj.matrix_local.decompose()
            except:
                pass

            # Export rotation
            if ( not self.test_default_quaternion( rotation_quaternion )):
                # Do this so that json module can export
                current_node["rotation"] = self.adjust_quaternion(rotation_quaternion)
                self.fmtl(current_node["rotation"])

            # Exporting scale if there is one
            if ( not self.test_default_scale( scale )):
                current_node["scale"] = []
                current_node["scale"].extend( scale )
                self.fmtl(current_node["scale"])

            # Exporting translation if there is one
            if ( not self.test_default_transform( location )):
                current_node["translation"] = []
                current_node["translation"].extend(location)
                self.fmtl(current_node["translation"])
                
            # Exporting node children
            child_list = self._write_node_child_object(obj)
            if child_list != None and len(child_list) > 0:
                current_node["children"] = child_list
                
            # Exporting node parts
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
            
            # Appending current node to children list
            children.append(current_node)
            
        # At the end return the exported children
        return children
        

    def write_nodes(self):
        """Writes a 'nodes' section, the section that will relate meshes to objects and materials"""
        
        if DEBUG: print("Writing nodes")
        
        # Let's export our objects as nodes
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            # If this object has a parent and the parent is selected, we will export it as a child and skip it here.
            # Otherwise we ignore the parenting and export it as a standalone object.
            if obj.parent != None and obj.parent.type == 'MESH' and ((self.use_selection and obj.parent.select) or not self.use_selection):
                continue
            
            current_node = {}
            
            current_node["id"] = obj.name

            location = [0,0,0]
            rotation_quaternion = [1,0,0,0]
            scale = [1,1,1]
            try:
                location, rotation_quaternion, scale = obj.matrix_world.decompose()
            except:
                pass
            
            # Exporting rotation if there is one
            if ( not self.test_default_quaternion( rotation_quaternion )):
                # Do this so that json module can export
                current_node["rotation"] = self.adjust_quaternion(rotation_quaternion)
                self.fmtl(current_node["rotation"])
                
            # Exporting scale if there is one
            if ( not self.test_default_scale( scale )):
                current_node["scale"] = []
                current_node["scale"].extend(scale)
                self.fmtl(current_node["scale"])

            # Exporting translation if there is one
            if ( not self.test_default_transform( location )):
                current_node["translation"] = []
                current_node["translation"].extend(location)
                self.fmtl(current_node["translation"])

            # Exporting node children
            child_list = self._write_node_child_object(obj)
            if child_list != None and len(child_list) > 0:
                current_node["children"] = child_list

            # Exporting node parts
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
                
                # Start writing bones
                if len(obj.vertex_groups) > 0:
                    for vgroup in obj.vertex_groups:
                        #Try to find an armature with a bone associated with this vertex group
                        if obj.parent != None and obj.parent.type == 'ARMATURE':
                            armature = obj.parent.data
                            try:
                                bone = armature.bones[vgroup.name]
                                
                                #Referencing the bone node
                                current_bone = {}
                                current_bone["node"] = ("%s__%s" % (obj.parent.name , vgroup.name))
                                if DEBUG: print("Exporting bone %s" % (vgroup.name))
                                
                                #transform_matrix = self.get_transform_from_bone(bone)
                                transform_matrix = bone.matrix_local
                                
                                bone_location, bone_quaternion, bone_scale = transform_matrix.decompose()
                                
                                current_bone["translation"] = []
                                current_bone["translation"].extend(bone_location)
                                self.fmtl(current_bone["translation"])
                                
                                current_bone["rotation"] = self.adjust_quaternion(bone_quaternion)
                                self.fmtl(current_bone["rotation"])
                                
                                current_bone["scale"] = []
                                current_bone["scale"].extend(bone_scale)
                                self.fmtl(current_bone["scale"])
                                
                                # Appending resulting bone to part
                                try:
                                    current_part["bones"].append( current_bone )
                                except:
                                    current_part["bones"] = [current_bone]

                            except KeyError:
                                if DEBUG: print("Vertex group %s has no corresponding bone" % (vgroup.name))
                            except:
                                if DEBUG: print("Unexpected error exporting bone:" , vgroup.name)

                # Appending this part to the current node
                current_node["parts"].append( current_part )
            
            # Finish this node and append it to the nodes section
            self.output["nodes"].append( current_node )
            
    def write_armatures(self):
        """Writes armatures as invisible nodes (armatures have no parts)"""
        
        if DEBUG: print("Writing armature nodes")
        
        for armature in bpy.data.objects:
            if armature.type != 'ARMATURE':
                continue
            
            # If armature have a selected object as a child we export it regardless of it being
            # selected and "export selected only" is checked. Otherwise it is only exported
            # if it's selected
            export_armature = False
            if self.use_selection and not armature.select:
                for child in armature.children:
                    if child.select:
                        export_armature = True
                        break
            else:
                export_armature = True

            if not export_armature:
                continue
                
            # If this armature has a parent and the parent is selected, we will export it as a child and skip it here.
            # Otherwise we ignore the parenting and export it as a standalone object.
            if armature.parent != None and ((self.use_selection and armature.parent.select) or not self.use_selection):
                continue
            
            current_node = {}
            current_node["id"] = armature.name
            
            location = [0,0,0]
            rotation_quaternion = [1,0,0,0]
            scale = [1,1,1]
            try:
                location, rotation_quaternion, scale = armature.matrix_world.decompose()
            except:
                pass
            
            # Exporting rotation if there is one
            if ( not self.test_default_quaternion( rotation_quaternion )):
                # Do this so that json module can export
                current_node["rotation"] = self.adjust_quaternion(rotation_quaternion)
                self.fmtl(current_node["rotation"])
                
            # Exporting scale if there is one
            if ( not self.test_default_scale( scale )):
                current_node["scale"] = []
                current_node["scale"].extend(scale)
                self.fmtl(current_node["scale"])

            # Exporting translation if there is one
            if ( not self.test_default_transform( location )):
                current_node["translation"] = []
                current_node["translation"].extend(location)
                self.fmtl(current_node["translation"])
                
            # Exporting child armatures
            if len(armature.children) > 0:
                armature_children = self._write_armature_children(armature)
                if len(armature_children) > 0:
                    current_node["children"] = armature_children
                
            # Exporting bones as childs
            bone_children = self.write_bone_nodes(armature)
            if len(bone_children) > 0:
                try:
                    current_node["children"].extend(bone_children)
                except:
                    current_node["children"] = bone_children
        
        # Finish this node and append it to the nodes section
        self.output["nodes"].append( current_node )
        
    def _write_armature_children(self, parent_armature):
        armature_nodes = []

        for armature in parent_armature.children:
            if armature.type != 'ARMATURE':
                continue
            
            # If armature have a selected object as a child we export it regardless of it being
            # selected and "export selected only" is checked. Otherwise it is only exported
            # if it's selected
            export_armature = False
            if self.use_selection and not armature.select:
                for child in armature.children:
                    if child.select:
                        export_armature = True
                        break
            else:
                export_armature = True

            if not export_armature:
                continue
                
            current_node = {}
            current_node["id"] = armature.name
            
            location = [0,0,0]
            rotation_quaternion = [1,0,0,0]
            scale = [1,1,1]
            try:
                location, rotation_quaternion, scale = armature.matrix_local.decompose()
            except:
                pass
            
            # Exporting rotation if there is one
            if ( not self.test_default_quaternion( rotation_quaternion )):
                # Do this so that json module can export
                current_node["rotation"] = self.adjust_quaternion(rotation_quaternion)
                self.fmtl(current_node["rotation"])
                
            # Exporting scale if there is one
            if ( not self.test_default_scale( scale )):
                current_node["scale"] = []
                current_node["scale"].extend(scale)
                self.fmtl(current_node["scale"])

            # Exporting translation if there is one
            if ( not self.test_default_transform( location )):
                current_node["translation"] = []
                current_node["translation"].extend(location)
                self.fmtl(current_node["translation"])
                
            # Exporting child armatures
            if len(armature.children) > 0:
                armature_children = self._write_armature_children(armature)
                if len(armature_children) > 0:
                    current_node["children"] = armature_children
                
            # Exporting bones as childs
            bone_children = self.write_bone_nodes(armature)
            if len(bone_children) > 0:
                try:
                    current_node["children"].extend(bone_children)
                except:
                    current_node["children"] = bone_children
            
            armature_nodes.append(current_node)
        
        return armature_nodes
                
    def write_bone_nodes(self, armature, parent_bone = None):
        bone_nodes = []
        
        for bone in armature.data.bones:
            if bone.parent != parent_bone:
                continue
            
            current_bone = {}
            current_bone["id"] = ("%s__%s" % (armature.name , bone.name))

            transform_matrix = self.get_transform_from_bone(bone)

            bone_location, bone_quaternion, bone_scale = transform_matrix.decompose()
            
            current_bone["translation"] = []
            current_bone["translation"].extend(bone_location)
            self.fmtl(current_bone["translation"])
            
            current_bone["rotation"] = self.adjust_quaternion(bone_quaternion)
            self.fmtl(current_bone["rotation"])
            
            current_bone["scale"] = []
            current_bone["scale"].extend(bone_scale)
            self.fmtl(current_bone["scale"])
            
            if len(bone.children) > 0:
                bone_children = self.write_bone_nodes(armature , parent_bone = bone)
                if len(bone_children) > 0:
                    current_bone["children"] = bone_children
            
            bone_nodes.append(current_bone)
            
        return bone_nodes

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
                self.fmtl(current_material["ambient"])
                
                current_material["diffuse"] = []
                current_material["diffuse"].extend(mat.diffuse_color)
                self.fmtl(current_material["diffuse"])
                
                current_material["specular"] = []
                current_material["specular"].extend(mat.specular_color)
                self.fmtl(current_material["specular"])
                
                current_material["emissive"] = [mat.emit , mat.emit , mat.emit]
                self.fmtl(current_material["emissive"])
                
                current_material["shininess"] = self.fmtf(mat.specular_intensity)

                if mat.raytrace_mirror.use:
                    current_material["reflection"] = self.fmtf(mat.raytrace_mirror.reflect_factor)

                if mat.use_transparency:
                    current_material["opacity"] = self.fmtf(mat.alpha)
                    
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
                self.fmtl( current_mesh["vertices"] )
             
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
        
    def write_animations(self,context):
        """Write an 'animations' section for each animation in the scene"""
        if DEBUG: print("Writing animations")
        
        # Save our time per frame (in miliseconds)
        fps = context.scene.render.fps
        frame_time = (1 / fps) * 1000
        
        # For each action we export keyframe data.
        # We don't need to attach the action to the object, we are exporting all actions.
        for action in bpy.data.actions:
            current_action = {}
            current_action["id"] = action.name
            current_action["bones"] = []
            
            for armature in bpy.data.objects:
                if armature.type != 'ARMATURE':
                    continue
                
                # If armature have a selected object as a child we export it' actions regardless of it being
                # selected and "export selected only" is checked. Otherwise it is only exported
                # if it's selected
                export_armature = False
                if self.use_selection and not armature.select:
                    for child in armature.children:
                        if child.select:
                            export_armature = True
                            break
                else:
                    export_armature = True
    
                if not export_armature:
                    continue

                for bone in armature.data.bones:
                    current_bone = {}
                    current_bone["boneId"] = ("%s__%s" % (armature.name , bone.name))
                    current_bone["keyframes"] = []
                    
                    #pose_transform_matrix = self.get_transform_from_bone(bone)
                    
                    location = self.find_fcurve(action,bone,self.P_LOCATION)
                    rotation = self.find_fcurve(action,bone,self.P_ROTATION)
                    scale = self.find_fcurve(action,bone,self.P_SCALE)
                    
                    for keyframe in range(int(action.frame_range[0]) , int(action.frame_range[1]+1)):
                        current_keyframe = {}
                        
                        location_value = mathutils.Vector( ([0.0] * 3) )
                        rotation_value = mathutils.Quaternion([1,0,0,0])
                        scale_value = mathutils.Vector([1.0] * 3)
                        
                        if location != None and location != ( [None] * 3 ):
                            if location[0] != None:
                                location_value[0] = location[0].evaluate(keyframe)
                            if location[1] != None:
                                location_value[1] = location[1].evaluate(keyframe)
                            if location[2] != None:
                                location_value[2] = location[2].evaluate(keyframe)
                            
                        if rotation != None and rotation != ( [None] * 4 ):
                            if rotation[0] != None:
                                rotation_value[0] = rotation[0].evaluate(keyframe)
                            if rotation[1] != None:
                                rotation_value[1] = rotation[1].evaluate(keyframe)
                            if rotation[2] != None:
                                rotation_value[2] = rotation[2].evaluate(keyframe)
                            if rotation[3] != None:
                                rotation_value[3] = rotation[3].evaluate(keyframe)
                            
                        if scale != None and scale != ( [None] * 3 ):
                            if scale[0] != None:
                                scale_value[0] = scale[0].evaluate(keyframe)
                            if scale[1] != None:
                                scale_value[1] = scale[1].evaluate(keyframe)
                            if scale[2] != None:
                                scale_value[2] = scale[2].evaluate(keyframe)
                            
                        current_transform = self.create_matrix(location_value , rotation_value , scale_value)
                        
                        # If bone have a parent, we need to make the transform relative to the parent
                        matrix_relative = self.get_transform_from_bone(bone)
                        final_transform = matrix_relative * current_transform
                        
                        location_value , rotation_value , scale_value = final_transform.decompose()
                        
                        #loc = mathutils.Vector( location_value )
                        #rot = mathutils.Quaternion( rotation_value )
                        #sca = mathutils.Vector( scale_value )
                        
                        if not self.test_default_transform(location_value):
                            current_keyframe["translation"] = []
                            current_keyframe["translation"].extend(location_value)
                            self.fmtl(current_keyframe["translation"])
                            
                        if not self.test_default_quaternion(rotation_value):
                            current_keyframe["rotation"] = self.adjust_quaternion(rotation_value)
                            self.fmtl(current_keyframe["rotation"])
                            
                        if not self.test_default_scale(scale_value):
                            current_keyframe["scale"] = []
                            current_keyframe["scale"].extend(scale_value)
                            self.fmtl(current_keyframe["scale"])
                            
                        # We need to find at least one of those curves to create a keyframe
                        if "translation" in current_keyframe or "rotation" in current_keyframe or "scale" in current_keyframe:
                            current_keyframe["keytime"] = keyframe * frame_time
                            
                            # If current frame has the same data as the previous one, ignore it
                            #different_frame = True
                            #if len(current_bone["keyframes"]) >= 1:
                            #    previous_keyframe = current_bone["keyframes"][ len(current_bone["keyframes"])-1 ]
                            #    loc1 = [0.0] * 3
                            #    loc2 = [0.0] * 3
                            #    rot1 = [0.0,0.0,0.0,1.0]
                            #    rot2 = [0.0,0.0,0.0,1.0]
                            #    sca1 = [1.0] * 3
                            #    sca2 = [1.0] * 3
                            #    
                            #    if "translation" in previous_keyframe:
                            #        loc1 = previous_keyframe["translation"]
                            #    if "rotation" in previous_keyframe:
                            #        rot1 = previous_keyframe["rotation"]
                            #    if "scale" in previous_keyframe:
                            #        sca1 = previous_keyframe["scale"]
                            #    
                            #    if "translation" in current_keyframe:
                            #        loc2 = current_keyframe["translation"]
                            #    if "rotation" in current_keyframe:
                            #        rot2 = current_keyframe["rotation"]
                            #    if "scale" in current_keyframe:
                            #        sca2 = current_keyframe["scale"]
                            #        
                            #    if loc1 == loc2 and rot1 == rot2 and sca1 == sca2:
                            #        different_frame = False
                                
                            #if different_frame:
                            current_bone["keyframes"].append(current_keyframe)
                    
                    # If there is at least one keyframe for this bone, add it's data
                    if len(current_bone["keyframes"]) > 0:
                        current_action["bones"].append(current_bone)

            # If this action animates at least one bone, add it to the list of actions
            if len(current_action["bones"]) > 0:
                self.output["animations"].append(current_action)
                    

    def find_fcurve(self, action , bone , property):
        """
        Find a fcurve for the given action, bone and property. Returns an array with as many fcurves
        as there are indices in the property.
        Ex: The returned value for the location property will have 3 fcurves, one for each of the X, Y and Z coordinates
        """
        
        returned_fcurves = None
        
        data_path = ("pose.bones[\"%s\"].%s" % (bone.name , property))
        if property == self.P_LOCATION:
            returned_fcurves = [None , None , None]
        elif property == self.P_ROTATION:
            returned_fcurves = [None , None , None, None]
        elif property == self.P_SCALE:
            returned_fcurves = [None , None , None]
        else:
            raise Exception("FCurve Property not supported")

        for fcurve in action.fcurves:
            if fcurve.data_path == data_path:
                returned_fcurves[fcurve.array_index] = fcurve

        return returned_fcurves
            
    def mesh_triangulate(self, me):
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        
    def create_matrix(self , location_vector , quaternion_vector, scale_vector):
        """Create a transform matrix from a location vector, a rotation quaternion and a scale vector"""
        
        loc = mathutils.Vector(location_vector)
        
        if quaternion_vector.__class__ is mathutils.Quaternion:
            quat = quaternion_vector
        else:
            quat = mathutils.Quaternion(quaternion_vector)
        
        matrix = mathutils.Matrix.Translation(loc) \
                   * quat.to_matrix().to_4x4() \
                   * mathutils.Matrix(( (scale_vector[0],0,0,0) , (0,scale_vector[1],0,0) , (0,0,scale_vector[2],0) , (0,0,0,1) ))
        
        return matrix
    
    def get_transform_from_bone(self, bone):
        """Create a transform matrix based on the relative rest position of a bone"""
        transform_matrix = mathutils.Matrix.Identity(4)
            
        if bone.parent == None:
            transform_matrix = bone.matrix_local
        else:
            bone_parenting = [bone]
            child_bone = bone
            while child_bone.parent != None:
                bone_parenting.insert(0 , child_bone.parent)
                child_bone = child_bone.parent
            
            transform_matrix = bone_parenting[0].matrix_local
            for bone_pos in range(1,len(bone_parenting)):
                transform_matrix = transform_matrix.inverted() * bone_parenting[bone_pos].matrix_local
        
        return transform_matrix
    
    def adjust_quaternion(self, quaternion):
        adjusted_quaternion = [ quaternion.x , quaternion.y , quaternion.z , quaternion.w ]
        return adjusted_quaternion
        
        
    def test_default_quaternion(self, quaternion):
        return quaternion[0] == 1.0 and quaternion[1] == 0.0 and quaternion[2] == 0.0 and quaternion[3] == 0.0
    
    def test_default_scale(self, scale):
        return scale[0] == 1.0 and scale[1] == 1.0 and scale[2] == 1.0
    
    def test_default_transform(self, transform):
        return transform[0] == 0.0 and transform[1] == 0.0 and transform[2] == 0.0
    
    def fmtf(self,value):
        """Format a float to only consider a certain number of decimal digits"""
        return value
    
    def fmtl(self,value):
        """Format a list of floats to only consider a certain number of decimal digits"""
        return None
        #for i in range(len(value)):
        #    value[i] = self.fmtf( value[i] )
