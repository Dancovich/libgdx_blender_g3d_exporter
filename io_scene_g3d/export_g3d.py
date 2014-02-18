#################################################################################
# Copyright 2014 See AUTHORS file.
#
# Licensed under the GNU General Public License Version 3.0 (the "LICENSE");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.gnu.org/licenses/gpl-3.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#################################################################################

import bpy
import mathutils
import json
from io_scene_g3d.normal_map_helper import NormalMapHelper
from bpy_extras.io_utils import ExportHelper
from bpy.props import (BoolProperty,EnumProperty)
from io_scene_g3d.g3d_json_encoder import G3DJsonEncoder
from io_scene_g3d.mesh_vertex import MeshVertex

_DEBUG_ = 3
_WARN_ = 2
_ERROR_ = 1

LOG_LEVEL = _WARN_

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
    
    export_armatures = BoolProperty( \
            name="Export Armatures", \
            description="Export armature bones and associated bone weights for each vertex", \
            default=True, \
            )
    
    export_animations = BoolProperty( \
            name="Export Actions as Animations", \
            description="Export each action as an animation section (ignored if Export Armatures is not checked)", \
            default=True, \
            )
            
    use_tangent_binormal = BoolProperty( \
            name="Export Tangent and Binormal Vectors", \
            description="Export tangent and binormal vectors for each vertex", \
            default=False, \
            )
    
    filename_ext    = ".g3dj"
    
    # Our output file. We save as a python dictionary and then use the JSON module to export it as a JSON file
    output = None
    
    # Global rounding factor for floats
    float_round = 6
    round_string = None
    
    def execute(self, context):
        """Main method run by Blender to export a G3D file"""
        
        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # define our return state
        result = {'FINISHED'}
        
        self.output = { "version" : [0,1] , "id" : "" , "meshes":[] , "materials":[] , "nodes":[] , "animations":[] }
        
        # We use this format string to round floats for exibition
        self.round_string = "%" + str(self.float_round+3) + "." + str(self.float_round) + "f"
        
        #output_file = open(self.filepath , 'w')
        self.write_meshes(context)
        self.write_materials()
        self.write_nodes()
        
        if self.export_armatures:
            self.write_armatures()
        
        if self.can_export_animations():
            self.write_animations(context)
        
        #output_file.close()
        
        output_file = open(self.filepath , 'w')
        json_output = json.dumps(self.output , indent=2, sort_keys=True , cls=G3DJsonEncoder, float_round = self.float_round)
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
        
        self.debug("Writing child nodes for node %s" % parent.name)
        
        children = []
        
        for obj in parent.children:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            self.debug("Current child node is %s" % obj.name)
            
            current_node = {}
            
            current_node["id"] = obj.name
            
            # Get the transformation relative to the parent and decompose it
            location = [0,0,0]
            rotation_quaternion = [1,0,0,0]
            scale = [1,1,1]
            try:
                location, rotation_quaternion, scale = obj.matrix_local.decompose()
                self.debug("Node transform is %s" % str(obj.matrix_local))
                self.debug("Decomposed node transform is %s" % str(obj.matrix_local.decompose()))
            except:
                self.warn("[WARN] Problem trying to decompose the transform for node %s" % obj.name)
                pass

            # Export rotation
            if ( not self.test_default_quaternion( rotation_quaternion )):
                # Do this so that json module can export
                current_node["rotation"] = self.adjust_quaternion(rotation_quaternion)

            # Exporting scale if there is one
            if ( not self.test_default_scale( scale )):
                current_node["scale"] = list(scale)

            # Exporting translation if there is one
            if ( not self.test_default_transform( location )):
                current_node["translation"] = list(location)
                
            # Exporting node children
            child_list = self._write_node_child_object(obj)
            if child_list != None and len(child_list) > 0:
                current_node["children"] = child_list
                
            # Exporting node parts
            current_node["parts"] = []
                
            # Export a default node part
            if obj.data.materials == None or len(obj.data.materials) == 0:
                self.warn("[WARN] Node %s doesn't have a material, attaching default material" % obj.name)
                current_part = {}
                
                current_part["meshpartid"] = ( "Meshpart__%s__%s" % (obj.data.name , "default") )
                current_part["materialid"] = ( "Material__default"  )

                # Start writing bones
                if self.export_armatures and len(obj.vertex_groups) > 0:
                    for vgroup in obj.vertex_groups:
                        #Try to find an armature with a bone associated with this vertex group
                        if obj.parent != None and obj.parent.type == 'ARMATURE':
                            armature = obj.parent.data
                            try:
                                bone = armature.bones[vgroup.name]
                                
                                #Referencing the bone node
                                current_bone = {}
                                current_bone["node"] = ("%s__%s" % (obj.parent.name , vgroup.name))
                                
                                transform_matrix = obj.matrix_local.inverted() * bone.matrix_local
                                bone_location, bone_quaternion, bone_scale = transform_matrix.decompose()
                                
                                current_bone["translation"] = list(bone_location)
                                
                                current_bone["rotation"] = self.adjust_quaternion(bone_quaternion)
                                
                                current_bone["scale"] = list(bone_scale)
                                
                                # Appending resulting bone to part
                                try:
                                    current_part["bones"].append( current_bone )
                                except:
                                    current_part["bones"] = [current_bone]

                            except KeyError:
                                self.warn("Vertex group %s has no corresponding bone" % (vgroup.name))
                            except:
                                self.debug("Unexpected error exporting bone: %s" % vgroup.name)

                # Appending this part to the current node
                current_node["parts"].append( current_part )
                
            for mat in obj.data.materials:
                self.debug("Attaching material %s to node %s" % (mat.name, obj.name))
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
        self.debug("Writing nodes")
        # Let's export our objects as nodes
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            self.debug("Writing node %s" % obj.name)
            
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
                if obj.parent != None and obj.parent.type == 'ARMATURE' and self.export_armatures:
                    transform_matrix = obj.matrix_local
                else:
                    transform_matrix = obj.matrix_world
                    
                location, rotation_quaternion, scale = transform_matrix.decompose()
                self.debug("Node transform is %s" % str(transform_matrix))
                self.debug("Decomposed node transform is %s" % str(transform_matrix.decompose()))
            except:
                self.warn("[WARN] Error decomposing transform for node %s" % obj.name)
                pass
            
            # Exporting rotation if there is one
            if ( not self.test_default_quaternion( rotation_quaternion )):
                # Do this so that json module can export
                current_node["rotation"] = self.adjust_quaternion(rotation_quaternion)
                
            # Exporting scale if there is one
            if ( not self.test_default_scale( scale )):
                current_node["scale"] = list(scale)

            # Exporting translation if there is one
            if ( not self.test_default_transform( location )):
                current_node["translation"] = list(location)

            # Exporting node children
            child_list = self._write_node_child_object(obj)
            if child_list != None and len(child_list) > 0:
                current_node["children"] = child_list

            # Exporting node parts
            current_node["parts"] = []
            
            # Export a default node part
            if obj.data.materials == None or len(obj.data.materials) == 0:
                self.warn("[WARN] Node %s doesn't have a material, attaching default material" % obj.name)
                
                current_part = {}
                
                current_part["meshpartid"] = ( "Meshpart__%s__%s" % (obj.data.name , "default") )
                current_part["materialid"] = ( "Material__default"  )

                # Start writing bones
                if self.export_armatures and len(obj.vertex_groups) > 0:
                    for vgroup in obj.vertex_groups:
                        #Try to find an armature with a bone associated with this vertex group
                        if obj.parent != None and obj.parent.type == 'ARMATURE':
                            armature = obj.parent.data
                            try:
                                bone = armature.bones[vgroup.name]
                                
                                #Referencing the bone node
                                current_bone = {}
                                current_bone["node"] = ("%s__%s" % (obj.parent.name , vgroup.name))
                                
                                transform_matrix = obj.matrix_local.inverted() * bone.matrix_local
                                bone_location, bone_quaternion, bone_scale = transform_matrix.decompose()
                                
                                current_bone["translation"] = list(bone_location)
                                
                                current_bone["rotation"] = self.adjust_quaternion(bone_quaternion)
                                
                                current_bone["scale"] = list(bone_scale)
                                
                                # Appending resulting bone to part
                                try:
                                    current_part["bones"].append( current_bone )
                                except:
                                    current_part["bones"] = [current_bone]

                            except KeyError:
                                self.warn("Vertex group %s has no corresponding bone" % (vgroup.name))
                            except:
                                self.debug("Unexpected error exporting bone: %s" % vgroup.name)

                # Appending this part to the current node
                current_node["parts"].append( current_part )
            
            # If we have materials export one node part for each material
            for mat in obj.data.materials:
                self.debug("Attaching material %s to node %s" % (mat.name , obj.name))
                
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
                if self.export_armatures and len(obj.vertex_groups) > 0:
                    self.debug("Writing bones for node %s" % obj.name)
                    
                    for vgroup in obj.vertex_groups:
                        #Try to find an armature with a bone associated with this vertex group
                        if obj.parent != None and obj.parent.type == 'ARMATURE':
                            armature = obj.parent.data
                            try:
                                bone = armature.bones[vgroup.name]
                                
                                #Referencing the bone node
                                current_bone = {}
                                current_bone["node"] = ("%s__%s" % (obj.parent.name , vgroup.name))
                                
                                transform_matrix = obj.matrix_local.inverted() * bone.matrix_local
                                bone_location, bone_quaternion, bone_scale = transform_matrix.decompose()
                                
                                self.debug("Appending pose bone %s with transform %s" % (vgroup.name , str(transform_matrix)))
                                
                                current_bone["translation"] = list(bone_location)
                                
                                current_bone["rotation"] = self.adjust_quaternion(bone_quaternion)
                                
                                current_bone["scale"] = list(bone_scale)
                                
                                # Appending resulting bone to part
                                try:
                                    current_part["bones"].append( current_bone )
                                except:
                                    current_part["bones"] = [current_bone]

                            except KeyError:
                                self.warn("[WARN] Vertex group %s has no corresponding bone" % (vgroup.name))
                            except:
                                self.debug("Unexpected error exporting bone: %s" % vgroup.name)

                # Appending this part to the current node
                current_node["parts"].append( current_part )
            
            # Finish this node and append it to the nodes section
            self.output["nodes"].append( current_node )
            
    def write_armatures(self):
        """Writes armatures as invisible nodes (armatures have no parts)"""
        for armature in bpy.data.objects:
            self.debug("Writing armature node %s" % armature.name)
            
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
                
            # Exporting scale if there is one
            if ( not self.test_default_scale( scale )):
                current_node["scale"] = list(scale)

            # Exporting translation if there is one
            if ( not self.test_default_transform( location )):
                current_node["translation"] = list(location)
                
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
            self.debug("Writing child armature %s for armature %s" % (armature.name, parent_armature.name))
            
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
                
            # Exporting scale if there is one
            if ( not self.test_default_scale( scale )):
                current_node["scale"] = list(scale)

            # Exporting translation if there is one
            if ( not self.test_default_transform( location )):
                current_node["translation"] = list(location)
                
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
            
            if (parent_bone == None):
                self.debug("Writing bone node %s for armature %s" % (bone.name , armature.name))
            else:
                self.debug("Writing bone node %s attached to bone %s" % (bone.name , parent_bone.name))
            
            current_bone = {}
            current_bone["id"] = ("%s__%s" % (armature.name , bone.name))

            transform_matrix = self.get_transform_from_bone(bone)

            bone_location, bone_quaternion, bone_scale = transform_matrix.decompose()
            
            current_bone["translation"] = list(bone_location)
            
            current_bone["rotation"] = self.adjust_quaternion(bone_quaternion)
            
            current_bone["scale"] = list(bone_scale)
            
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
            
            if m.materials != None and len(m.materials) > 0:
                for mat in m.materials:
                    self.debug("Writing material %s" % mat.name)
                    
                    current_material = {}
                    
                    if mat.name in processed_materials:
                        continue
                    else:
                        processed_materials.append(mat.name)
                    
                    current_material["id"] = ( "Material__%s" % (mat.name) )
                    current_material["ambient"] = [ mat.ambient , mat.ambient , mat.ambient ]
                    
                    current_material["diffuse"] = list(mat.diffuse_color)
                    
                    current_material["specular"] = list(mat.specular_color * mat.specular_intensity)
    
                    current_material["emissive"] = [mat.emit , mat.emit , mat.emit]
                    
                    current_material["shininess"] = mat.specular_hardness
    
                    if mat.raytrace_mirror.use:
                        current_material["reflection"] = mat.raytrace_mirror.reflect_factor
    
                    if mat.use_transparency:
                        current_material["opacity"] = mat.alpha
                        
                    if len(mat.texture_slots)  > 0:
                        self.debug("Exporting textures for material %s" % mat.name)
                        current_material["textures"] = []
    
                        for slot in mat.texture_slots:
                            current_texture = {}
        
                            if slot is not None:
                                self.debug("Found texture %s. Texture coords are %s, texture type is %s" % (slot.name, slot.texture_coords , slot.texture.type) )
                            
                            if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                                if slot is not None:
                                    self.debug("Texture type not supported, skipping" )
                                else:
                                    self.debug("Texture slot is empty, skipping" )
                                continue

                            current_texture["id"] = slot.name
                            current_texture["filename"] = ( self.get_compatible_path(slot.texture.image.filepath) )

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
            else:
                # We don't have materials, export a default one
                need_export = True
                for exported_material in self.output["materials"]:
                    if exported_material["id"] == "Material__default":
                        need_export = False
                        break
                
                if need_export:
                    current_material = {}
                    
                    current_material["id"] = ( "Material__default" )
                    current_material["ambient"] = [ 1.0, 1.0, 1.0 ]
                    current_material["diffuse"] = [ 0.8, 0.8, 0.8 ]
                    current_material["specular"] = [ 0.5, 0.5, 0.5 ]
                    current_material["emissive"] = [ 0.0, 0.0, 0.0 ]
                    self.output["materials"].append( current_material )

    def write_meshes(self, context):
        """Write a 'mesh' section for each mesh in the scene, or each mesh on the selected objects."""
        # Select what meshes to export (all or only selected) and triangulate meshes prior to exporting.
        # We clone the mesh when triangulating, so we need to clean up after this
        tri_meshes = {}
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.use_selection and not obj.select):
                continue
            
            # If we already processed the mesh data associated with this object, continue (ex: multiple objects pointing to same mesh data)
            if obj.data.name in tri_meshes.keys():
                self.debug("Skipping mesh for node %s (was previously exported)" % obj.name)
                continue
            
            self.debug("Writing mesh for node %s" % obj.name)
            
            # We can't apply modifiers here because armatures are modifiers, applyig them will screw up the animation
            current_mesh = obj.to_mesh(context.scene , False, 'PREVIEW', calc_tessface=False)
            self.mesh_triangulate(current_mesh)
            
            # Generate tangent and binormal vectors for this mesh, for this we need at least one UV layer
            if self.use_tangent_binormal and len(current_mesh.uv_layers) > 0:
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

            tri_meshes[obj.data.name] = [current_mesh,face_tangent_binormal,vertex_tangent_binormal]
        
        # Now for each mesh we export a "mesh" section
        for mesh_name in tri_meshes.keys():
            tri_mesh = tri_meshes[mesh_name][0]
            original_mesh = bpy.data.meshes[mesh_name]
            face_tangent_binormal = tri_meshes[mesh_name][1]
            vertex_tangent_binormal = tri_meshes[mesh_name][2]
            
            current_mesh = {}
            current_mesh["attributes"] = []
            current_mesh["vertices"] = []
            current_mesh["parts"] = []
            
            # We will store vertices prior to exporting here
            vertices = [None] * len(tri_mesh.vertices)
            
            # We store some variables to later export attributes
            total_weight_amount = 0
            total_uv_amount = 0
            has_tangent = False
            has_binormal = False
            has_color = False
            
            # For each face we export it's vertices
            saved_faces = []
            for face_index in range(len(tri_mesh.polygons)):
                face = tri_mesh.polygons[face_index]
                saved_face = [None] * 3
                
                for face_vertex in range(len(face.vertices)):
                    vertex_index = face.vertices[face_vertex]
                    vertex = tri_mesh.vertices[vertex_index]
                    
                    # We will store out new vertex data here
                    new_vertex = MeshVertex( mathutils.Vector((1,1,1)) , mathutils.Vector((1,1,1)) )
                    
                    # Defining position
                    new_vertex.position = vertex.co
                    
                    # Defining normals
                    if self.use_normals == 'FACE' or (self.use_normals == 'BLENDER' and not face.use_smooth):
                        v_normal = face.normal
                    elif self.use_normals == 'VERTEX' or (self.use_normals == 'BLENDER' and face.use_smooth):
                        v_normal = vertex.normal
                    new_vertex.normal = v_normal
                    
                    # Defining vertex color
                    color_map = tri_mesh.vertex_colors.active
                    if color_map != None:
                        color_index = face.loop_indices[face_vertex]
                        new_vertex.color = color_map.data[color_index].color
                        has_color = True
                    
                    # Defining tangent and binormals
                    v_tangent = None
                    v_binormal = None
                    
                    if face_tangent_binormal != None and vertex_tangent_binormal != None:
                        if (self.use_normals == 'FACE' or (self.use_normals == 'BLENDER' and not face.use_smooth)):
                            v_tangent = face_tangent_binormal[face_index][0]
                            v_binormal = face_tangent_binormal[face_index][1]
                        elif (self.use_normals == 'VERTEX' or (self.use_normals == 'BLENDER' and face.use_smooth)):
                            v_tangent = vertex_tangent_binormal[vertex_index][0]
                            v_binormal = vertex_tangent_binormal[vertex_index][1]
                    
                    new_vertex.tangent = v_tangent
                    new_vertex.binormal = v_binormal
                    has_tangent = new_vertex.tangent != None
                    has_binormal = new_vertex.binormal != None
                    
                    # Defining UV coordinates
                    uv_amount = 0
                    if tri_mesh.uv_layers != None and len(tri_mesh.uv_layers) > 0:
                        new_vertex.texcoord = []
                        for uv in tri_mesh.uv_layers:
                            # We need to flip UV's because Blender use bottom-left as Y=0 and G3D use top-left
                            flipped_uv = mathutils.Vector(( uv.data[ face.loop_indices[face_vertex] ].uv[0] \
                                                            , 1.0 - uv.data[ face.loop_indices[face_vertex] ].uv[1] ))
                            new_vertex.texcoord.append(flipped_uv)
                            uv_amount = uv_amount + 1
                    if uv_amount > total_uv_amount:
                        total_uv_amount = uv_amount
                            
                            
                    # Defining bone weights
                    if self.export_armatures:
                        new_vertex.blendweight , blend_weight_amount = self.get_bone_weights(original_mesh, vertex_index)
                        #print(str(new_vertex.blendweight))
                        if blend_weight_amount > total_weight_amount:
                            total_weight_amount = blend_weight_amount

                    # We grab a possible existing vertex at the same vertex position as this
                    old_vertex = vertices[vertex_index]

                    # Now we store our vertex
                    if old_vertex == None:
                        # This is a new vertex, save it at its index position
                        vertices[vertex_index] = new_vertex
                        saved_face[face_vertex] = vertex_index
                    elif old_vertex.compare(new_vertex):
                        # We created the same vertex, ignore it
                        saved_face[face_vertex] = vertex_index
                    else:
                        # We created a vertex with the same position as an old one, but different
                        # attributes, we need to create it at another position
                        vertices.append(new_vertex)
                        saved_face[face_vertex] = len(vertices) - 1
                        
                # We just finished processing a face, store it.
                saved_faces.append(saved_face)
                
            # We have extracted all our vertices, store them into the final list
            for current_vertex_index in range(len(vertices)):
                current_vertex = vertices[current_vertex_index]
                
                # If we have an empty space in this list means this vertex is not used in any faces. We can't allow that
                if current_vertex==None:
                    bpy.ops.object.mode_set(mode = 'EDIT')
                    bpy.ops.mesh.select_all(action = 'DESELECT')
                    bpy.ops.object.mode_set(mode = 'OBJECT')
                    original_mesh.vertices[current_vertex_index].select = True
                    bpy.ops.object.mode_set(mode = 'EDIT')
                    raise Exception("Can't export vertices not associated with any faces.")
                
                # First attributes are position and normal
                current_mesh["vertices"].extend(current_vertex.position)
                current_mesh["vertices"].extend(current_vertex.normal)
                
                # If we have color for this vertex, apply it now
                if has_color:
                    if current_vertex.color != None:
                        # Blender doesn't support vertex colors with alpha, so we add the alpha component as 1.0
                        current_mesh["vertices"].extend(current_vertex.color)
                        current_mesh["vertices"].append(1.0)
                    else:
                        current_mesh["vertices"].extend(mathutils.Vector((1.0,1.0,1.0,1.0)))
                
                # If we have tangent and binormal, they are next
                if current_vertex.tangent != None:
                    current_mesh["vertices"].extend(current_vertex.tangent)
                if current_vertex.binormal != None:
                    current_mesh["vertices"].extend(current_vertex.binormal)
                    
                # Now the UV coordinates
                if current_vertex.texcoord != None:
                    for i in range(total_uv_amount):
                        try:
                            uv_texcoord = current_vertex.texcoord[i]
                            if uv_texcoord != None:
                                current_mesh["vertices"].extend(uv_texcoord)
                            else:
                                current_mesh["vertices"].extend([0.0,0.0])
                        except:
                            current_mesh["vertices"].extend([0.0,0.0])
                elif total_uv_amount > 0:
                    for i in range(total_uv_amount):
                        current_mesh["vertices"].extend([0.0,0.0])
                    
                # Lastly bone weights
                if self.export_armatures:
                    if current_vertex.blendweight != None:
                        current_vertex.normalize_weights()
                        for i in range(total_weight_amount):
                            try:
                                blendweight = current_vertex.blendweight[i]
                                if blendweight != None:
                                    current_mesh["vertices"].extend(blendweight)
                                else:
                                    current_mesh["vertices"].extend([0.0,0.0])
                            except:
                                current_mesh["vertices"].extend([0.0,0.0])
                    elif total_weight_amount > 0:
                        self.warn("[WARN] Found vertex with empty bone weights at (%d, %d, %d)" \
                              % ( current_vertex.position[0] \
                                  , current_vertex.position[1] \
                                  , current_vertex.position[2] ) )
                        
                        for i in range(total_weight_amount):
                            current_mesh["vertices"].extend([0.0,0.0])
                
            # Let's create our attributes, we must respect the same order above
            current_mesh["attributes"].append("POSITION")
            current_mesh["attributes"].append("NORMAL")
            
            if has_color:
                current_mesh["attributes"].append("COLOR")
            
            if has_tangent:
                current_mesh["attributes"].append("TANGENT")
            if has_binormal:
                current_mesh["attributes"].append("BINORMAL")
                
            for i in range(total_uv_amount):
                current_mesh["attributes"].append( "TEXCOORD%d" % i )
                
            if self.export_armatures:
                for i in range(total_weight_amount):
                    current_mesh["attributes"].append( "BLENDWEIGHT%d" % i )
                
            # Now let's export all mesh parts. We create a part for each material that is
            # attached to some vertices, or just one part if we have one material for all vertices
            current_mesh["parts"] = []
            if tri_mesh.materials != None and len(tri_mesh.materials) > 0:
                for mPos in range(len(tri_mesh.materials)):
                    material = tri_mesh.materials[mPos]
                    if (material == None):
                        continue
                    
                    current_part = {}
                    
                    current_part["id"] = ("Meshpart__%s__%s" % (mesh_name , material.name))
                    current_part["type"] = "TRIANGLES"
                    current_part["indices"] = []
                    
                    for faceIdx in range(len(tri_mesh.polygons)):
                        saved_face = saved_faces[faceIdx]
                        pol = tri_mesh.polygons[faceIdx]
    
                        if (pol.material_index == mPos):
                            current_part["indices"].extend(saved_face)
    
                    # Ending current part
                    current_mesh["parts"].append( current_part )
            else:
                # Create a default part because we don't have a material
                current_part = {}
                    
                current_part["id"] = ("Meshpart__%s__%s" % (mesh_name , "default"))
                current_part["type"] = "TRIANGLES"
                current_part["indices"] = []
                
                for faceIdx in range(len(tri_mesh.polygons)):
                    saved_face = saved_faces[faceIdx]
                    pol = tri_mesh.polygons[faceIdx]

                    current_part["indices"].extend(saved_face)

                # Ending current part
                current_mesh["parts"].append( current_part )
        
            # Append the created mesh to the list
            self.output["meshes"].append( current_mesh )
            
        # Clean up all triangulated meshes
        for mesh_key in tri_meshes:
            tri_mesh = tri_meshes[mesh_key][0]
            bpy.data.meshes.remove(tri_mesh)
        tri_meshes = None

    def write_animations(self,context):
        """Write an 'animations' section for each animation in the scene"""
        # Save our time per frame (in miliseconds)
        fps = context.scene.render.fps
        frame_time = (1 / fps) * 1000
        
        # For each action we export keyframe data.
        # We are exporting all actions, but to avoid exporting deleted actions (actions with ZERO users)
        # each action must have at least one user. In Blender user the FAKE USER option to assign at least
        # one user to each action
        for action in bpy.data.actions:
            if action.users <= 0:
                continue
            
            self.debug("Writing animation for action %s" % action.name)
            
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
                    
                    # Rest transform to apply relative pose transform for each frame
                    rest_transform = self.get_transform_from_bone(bone)
                    
                    # Decomposed rest transform
                    pre_loc,pre_rot,pre_sca = rest_transform.decompose()
                    
                    frame_start = context.scene.frame_start
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
                        
                        pose_transform = self.create_matrix(location_value , rotation_value , scale_value)
                        location_value, rotation_value, scale_value = (rest_transform * pose_transform).decompose()

                        # Compare current frame to previous one (or to rest position) to optimize keyframes
                        if len(current_bone["keyframes"]) > 0:
                            previous_frame = current_bone["keyframes"][ len(current_bone["keyframes"])-1 ]
                            if "translation" in previous_frame:
                                pre_loc = mathutils.Vector(previous_frame["translation"])
                            if "rotation" in previous_frame:
                                # We store the W position at the end, but Blender use it as the first element. We need to switch back
                                pre_rot = mathutils.Quaternion( ( previous_frame["rotation"][3] , previous_frame["rotation"][0] , previous_frame["rotation"][1] , previous_frame["rotation"][2] ) )
                            if "scale" in previous_frame:
                                pre_sca = mathutils.Vector(previous_frame["scale"])

                        if not self.compare_vector(location_value, pre_loc):
                            current_keyframe["translation"] = list(location_value)
                            
                        if not self.compare_quaternion(rotation_value, pre_rot):
                            current_keyframe["rotation"] = self.adjust_quaternion(rotation_value)
                            
                        if not self.compare_vector(scale_value, pre_sca):
                            current_keyframe["scale"] = list(scale_value)
                            
                        # We need to find at least one of those curves to create a keyframe
                        if "translation" in current_keyframe or "rotation" in current_keyframe or "scale" in current_keyframe:
                            current_keyframe["keytime"] = (keyframe - frame_start) * frame_time
                            current_bone["keyframes"].append(current_keyframe)
                    
                    # If there is at least one keyframe for this bone, add it's data
                    if len(current_bone["keyframes"]) > 0:
                        current_action["bones"].append(current_bone)

            # If this action animates at least one bone, add it to the list of actions
            if len(current_action["bones"]) > 0:
                self.output["animations"].append(current_action)
                    

    def find_fcurve(self, action , bone , prop):
        """
        Find a fcurve for the given action, bone and property. Returns an array with as many fcurves
        as there are indices in the property.
        Ex: The returned value for the location property will have 3 fcurves, one for each of the X, Y and Z coordinates
        """
        
        returned_fcurves = None
        
        data_path = ("pose.bones[\"%s\"].%s" % (bone.name , prop))
        if prop == self.P_LOCATION:
            returned_fcurves = [None , None , None]
        elif prop == self.P_ROTATION:
            returned_fcurves = [None , None , None, None]
        elif prop == self.P_SCALE:
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
        
        if quaternion_vector.__class__ is mathutils.Quaternion:
            quat = quaternion_vector.normalized()
        else:
            quat = mathutils.Quaternion(quaternion_vector).normalized()
            
        loc_mat = mathutils.Matrix(( (0,0,0,location_vector[0]) \
                                     , (0,0,0,location_vector[1]) \
                                     , (0,0,0,location_vector[2]) \
                                     , (0,0,0,0) ))
        
        rot_mat = quat.to_matrix().to_4x4()
        
        sca_mat = mathutils.Matrix(( (scale_vector[0],0,0,0) \
                                     , (0,scale_vector[1],0,0) \
                                     , (0,0,scale_vector[2],0) \
                                     , (0,0,0,1) ))
        
        matrix = (rot_mat * sca_mat) + loc_mat
        
        self.debug("Creating matrix from location, rotation and scale")
        self.debug("INPUT: Location = %s; Quaternion = %s; Scale = %s" % (str(location_vector), str(quat), str(scale_vector)))
        self.debug("OUTPUT: %s" % str(matrix))
        
        return matrix
    
    def get_transform_from_bone(self, bone):
        """Create a transform matrix based on the relative rest position of a bone"""
        transform_matrix = None
            
        if bone.parent == None:
            transform_matrix = bone.matrix_local
        else:
            transform_matrix = bone.parent.matrix_local.inverted() * bone.matrix_local
        
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
    
    def compare_vector(self,v1,v2):
        a1 = [ (self.round_string % v1[0]) , (self.round_string % v1[1]) , (self.round_string % v1[2]) ]
        a2 = [ (self.round_string % v2[0]) , (self.round_string % v2[1]) , (self.round_string % v2[2]) ]
        return a1 == a2
    
    def compare_quaternion(self,q1,q2):
        a1 = [ (self.round_string % q1[0]) , (self.round_string % q1[1]) , (self.round_string % q1[2]) , (self.round_string % q1[3]) ]
        a2 = [ (self.round_string % q2[0]) , (self.round_string % q2[1]) , (self.round_string % q2[2]) , (self.round_string % q2[3]) ]
        return a1 == a2
    
    def can_export_animations(self):
        return self.export_armatures and self.export_animations
    
    def get_compatible_path(self,path):
        """Return path minus the '//' prefix, for Windows compatibility"""
        return path[2:] if path[:2] in {"//", b"//"} else path
    
    def get_bone_weights(self,mesh,vertex_index):
        blend_weights = []
        blend_weight_amount = 0
        
        for obj in bpy.data.objects:
            if obj.type=='MESH' and obj.data.name == mesh.name and obj.parent != None and obj.parent.type == 'ARMATURE':
                arm_obj = obj.parent
                bone_index = 0
                for vertex_group in obj.vertex_groups:
                    bone = None
                    try:
                        bone = arm_obj.data.bones[vertex_group.name]
                    except:
                        bone = None
                    
                    if bone != None:
                        try:
                            bone_weight = vertex_group.weight(vertex_index)
        
                            #print("Bone weight for vertex %d in group %s is %d" % (vertex_index,vertex_group.name,vertex_group.weight(vertex_index)))
                            
                            blend_weight = mathutils.Vector(( float(bone_index) , bone_weight ))
                            blend_weights.append(blend_weight)
                            blend_weight_amount = blend_weight_amount + 1
                        except:
                            pass
                        finally:
                            bone_index = bone_index + 1

                # Only one object with armature is supporter per mesh
                break

        if len(blend_weights) > 0:
            return blend_weights, blend_weight_amount
        else:
            return None, 0

    def debug(self, message):
        if LOG_LEVEL >= _DEBUG_: print(message)
    
    def warn(self, message):
        if LOG_LEVEL >= _WARN_: print(message)

    def error(self, message):
        if LOG_LEVEL >= _ERROR_: print(message)
