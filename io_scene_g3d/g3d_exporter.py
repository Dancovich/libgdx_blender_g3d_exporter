# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import bpy
import mathutils
from bpy.props import BoolProperty, IntProperty
from bpy_extras.io_utils import ExportHelper, orientation_helper_factory, path_reference

from io_scene_g3d import g3d_file_writer
from .profile import profile, print_stats
from . import util
from .util import Util
from .domain_classes import (Texture,
                             Animation,
                             NodeAnimation,
                             NodePart,
                             Node,
                             Bone,
                             Keyframe,
                             Material,
                             VertexAttribute,
                             Vertex,
                             MeshPart,
                             Mesh,
                             G3DModel)
from io_scene_g3d.util import FLOAT_ROUND

IOG3DOrientationHelper = orientation_helper_factory("IOG3DOrientationHelper", axis_forward='-Z', axis_up='Y')


class G3DBaseExporterOperator(ExportHelper, IOG3DOrientationHelper):
    # This is our model
    g3dModel = None

    filename_ext = ""

    useSelection = BoolProperty(
        name="Selection Only",
        description="Export only selected objects",
        default=False
    )
    
    applyModifiers = BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to each mesh before exporting, doesn't affect original meshes",
        default=True
    )

    exportArmature = BoolProperty(
        name="Export Armatures",
        description="Export armature nodes (bones)",
        default=True
    )

    bonesPerVertex = IntProperty(
        name="Bone Weights per Vertex",
        description="Maximum number of BLENDWEIGHT attributes per vertex. LibGDX default is 4.",
        default=4,
        soft_min=1, soft_max=8
    )

    exportAnimation = BoolProperty(
        name="Export Actions as Animations",
        description="Export bone actions as animations",
        default=True,
    )

    generateTangentBinormal = BoolProperty(
        name="Calculate Tangent and Binormal Vectors",
        description="Calculate and export tangent and binormal vectors for normal mapping. Requires UV mapping the mesh.",
        default=False
    )
    
    # This is overriden by the G3DB subclass of this exporter. For the G3DJ this isn't
    # used and is here with it's default value to pass to methods.
    oldFormatJson = True

    order = [
        "filepath",
        "check_existing",
        "useSelection",
        "applyModifiers",
        "exportArmature",
        "bonesPerVertex",
        "exportAnimation",
        "generateTangentBinormal",
    ]

    vector3AxisMapper = {}

    vector4AxisMapper = {}

    # Constants
    P_LOCATION = 'location'
    P_ROTATION = 'rotation_quaternion'
    P_SCALE = 'scale'

    def execute(self, context):
        return self.startExport(context)

    @profile('totalAddonExecution')
    def startExport(self, context):
        """Main method run by Blender to export a G3D file"""

        # Defines our mapping from Blender Z-Up to whatever the user selected
        self.setupAxisConversion(self.axis_forward, self.axis_up)

        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # define our return state
        result = {'FINISHED'}

        # Initialize our model
        self.g3dModel = G3DModel()
        
        # Generate the mesh list of the model
        meshes = self.generateMeshes(context)
        if meshes is not None:
            self.g3dModel.meshes = meshes

        # Generate the materials used in the model
        materials = self.generateMaterials(context)
        if materials is not None:
            self.g3dModel.materials = materials

        # Generate the nodes binding mesh parts, materials and bones
        nodes = self.generateNodes(context)
        if nodes is not None:
            self.g3dModel.nodes = nodes

        # Convert action curves to animations
        animations = self.generateAnimations(context)
        if animations is not None:
            self.g3dModel.animations = animations

        # Export to the final file
        exporter = None
        if self.filename_ext == ".g3dj":
            exporter = g3d_file_writer.G3DJWriter()
        elif self.filename_ext == ".g3db":
            exporter = g3d_file_writer.G3DBWriter(old_format=self.oldFormatJson)

        if exporter is not None:
            Util.info("Writing output file")
            exporter.export(self.g3dModel, self.filepath)

        # Clean up after export
        self.g3dModel = None

        if util.LOG_LEVEL >= util._DEBUG_:
            print_stats()

        Util.info("Finished")
        return result

    @profile('generateMeshes')
    def generateMeshes(self, context):
        """Reads all MESH type objects and exported the selected ones (or all if 'only selected' isn't checked"""
        Util.info("Exporting meshes")
        generatedMeshes = []

        for currentObjNode in bpy.data.objects:
            if currentObjNode.type != 'MESH' or (self.useSelection and not currentObjNode.select):
                continue

            # If we already processed the mesh data associated with this object, continue (ex: multiple objects pointing to same mesh data)
            if self.g3dModel.hasMesh(currentObjNode.data.name):
                Util.debug("Mesh '{!s}' already exported from another object", currentObjNode.data.name)
                continue

            # This is the mesh object we are generating
            generatedMesh = Mesh()
            currentBlMeshName = currentObjNode.data.name
            generatedMesh.id = currentBlMeshName

            # Clone mesh to a temporary object. Wel'll apply modifiers and triangulate the
            # clone before exporting.
            currentObjNode = currentObjNode.copy()
            currentBlMesh = currentObjNode.to_mesh(context.scene, self.applyModifiers, 'PREVIEW', calc_tessface=False)
            self.meshTriangulate(currentBlMesh)
            currentObjNode.data = currentBlMesh

            # We can only export polygons that are associated with a material, so we loop
            # through the list of materials for this mesh

            # Loop through the polygons of this mesh
            if currentBlMesh.materials is None:
                Util.warn("Ignored mesh %r, no materials found" % currentBlMesh)
                continue

            for blMaterialIndex in range(0, len(currentBlMesh.materials)):
                if currentBlMesh.materials[blMaterialIndex].type != 'SURFACE':
                    Util.debug("Ignoring mesh part for material '{!s}', type is not SURFACE (is {!s})", currentBlMesh.materials[blMaterialIndex].name, currentBlMesh.materials[blMaterialIndex].type)
                else:
                    Util.debug("Processing mesh part for material '{!s}'", currentBlMesh.materials[blMaterialIndex].name)

                # Fills the part here
                currentMeshPart = MeshPart(meshPartId=currentBlMeshName + "_part" + str(blMaterialIndex))

                # Here we get only vertex groups used in this part
                vertexGroupsForMaterial = self.listPartVertexGroups(currentObjNode, currentBlMesh, blMaterialIndex)

                for poly in currentBlMesh.polygons:
                    if (poly.material_index != blMaterialIndex):
                        continue

                    for loopIndex in poly.loop_indices:
                        blLoop = currentBlMesh.loops[loopIndex]
                        blVertex = currentBlMesh.vertices[blLoop.vertex_index]
                        currentVertex = Vertex()

                        ############
                        # Vertex position is the minimal attribute
                        attribute = VertexAttribute(VertexAttribute.POSITION,
                                                    self.convertVectorCoordinate(blVertex.co))
                        if not currentVertex.add(attribute):
                            Util.warn("Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex), attribute))
                        ############

                        ############
                        # Exporting tangent and binormals. We calculate those prior to normals because
                        # if we want tangent and binormals then we'll be also using split normals, which
                        # will be exported next section
                        doneCalculatingTangentBinormal = False
                        splitNormalValue = None
                        if self.generateTangentBinormal and currentBlMesh.uv_layers is not None and len(currentBlMesh.uv_layers) > 0:
                            # TODO We only use first UV layer for now, might think of some way to ask the user
                            uv = currentBlMesh.uv_layers[0]

                            try:
                                currentBlMesh.calc_tangents(uvmap=uv.name)
                                doneCalculatingTangentBinormal = True
                            except:
                                doneCalculatingTangentBinormal = False

                            if doneCalculatingTangentBinormal:
                                tangent = [None] * 3
                                tangent[0], tangent[1], tangent[2] = blLoop.tangent
                                attribute = VertexAttribute(name=VertexAttribute.TANGENT, value=self.convertVectorCoordinate(tangent))

                                if not currentVertex.add(attribute):
                                    Util.warn("Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex), attribute))

                                binormal = [None] * 3
                                binormal[0], binormal[1], binormal[2] = blLoop.bitangent
                                attribute = VertexAttribute(name=VertexAttribute.BINORMAL, value=self.convertVectorCoordinate(binormal))

                                if not currentVertex.add(attribute):
                                    Util.warn("Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex), attribute))

                                splitNormalValue = [None] * 3
                                splitNormalValue[0], splitNormalValue[1], splitNormalValue[2] = blLoop.normal

                                currentBlMesh.free_tangents()

                        ############

                        ############
                        # Read normals. We also determine if we'll user per-face (flat shading)
                        # or per-vertex normals (gouraud shading) here.
                        attribute = VertexAttribute(name=VertexAttribute.NORMAL)
                        if doneCalculatingTangentBinormal and splitNormalValue is not None:

                            attribute.value = self.convertVectorCoordinate(splitNormalValue)
                        elif poly.use_smooth:

                            attribute.value = self.convertVectorCoordinate(blVertex.normal)
                        else:

                            attribute.value = self.convertVectorCoordinate(poly.normal)

                        if not currentVertex.add(attribute):
                            Util.warn("Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex), attribute))
                        ############

                        ############
                        # Defining vertex color
                        colorMap = currentBlMesh.vertex_colors.active
                        if colorMap is not None:
                            color = [None] * 4
                            color[0], color[1], color[2] = colorMap.data[loopIndex].color
                            color[3] = 1.0

                            attribute = VertexAttribute(name=VertexAttribute.COLOR, value=color)

                            if not currentVertex.add(attribute):
                                Util.warn("Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex), attribute))

                        ############

                        ############
                        # Exporting UV coordinates
                        if currentBlMesh.uv_layers is not None and len(currentBlMesh.uv_layers) > 0:
                            texCoordCount = 0
                            for uv in currentBlMesh.uv_layers:
                                # We need to flip UV's because Blender use bottom-left as Y=0 and G3D use top-left
                                flippedUV = [uv.data[loopIndex].uv[0], 1.0 - uv.data[loopIndex].uv[1]]

                                texCoordAttrName = VertexAttribute.TEXCOORD + str(texCoordCount)
                                attribute = VertexAttribute(texCoordAttrName, flippedUV)

                                texCoordCount = texCoordCount + 1

                                if not currentVertex.add(attribute):
                                    Util.warn("Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex), attribute))
                        ############

                        ############
                        # Exporting bone weights. We only export at most 'self.bonesPerVertex' bones
                        # for a single vertex.
                        if self.exportArmature:
                            zeroWeight = Util.floatToString(0.0)
                            blendWeightAttrName = VertexAttribute.BLENDWEIGHT + "%d"

                            armatureObj = currentObjNode.find_armature()
                            if armatureObj is not None:
                                boneIndex = -1
                                blendWeightIndex = 0

                                for vertexGroupIndex in range(0, len(vertexGroupsForMaterial)):
                                    vertexGroup = vertexGroupsForMaterial[vertexGroupIndex]

                                    # We can only export this ammount of bones per vertex
                                    if blendWeightIndex >= self.bonesPerVertex:
                                        break

                                    # Search for a bone with the same name as a vertex group
                                    bone = None
                                    try:
                                        bone = armatureObj.data.bones[vertexGroup.name]
                                    except:
                                        bone = None
                                        pass

                                    if bone is not None:
                                        boneIndex = boneIndex + 1

                                        try:
                                            # We get the weight associated with this vertex group. Zeros are ignored
                                            boneWeight = vertexGroup.weight(blLoop.vertex_index)

                                            if Util.floatToString(boneWeight) != zeroWeight:
                                                blendWeightValue = [float(boneIndex), boneWeight]
                                                attribute = VertexAttribute((blendWeightAttrName % blendWeightIndex), blendWeightValue)

                                                if not currentVertex.add(attribute):
                                                    Util.warn("Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex), attribute))
                                                else:
                                                    blendWeightIndex = blendWeightIndex + 1

                                        except Exception:
                                            # Util.warn("Error trying to export bone weight for vertex index %d (%r)" % (blLoop.vertex_index, boneWeightException))
                                            pass

                            # In the end we normalize the bone weights
                            currentVertex.normalizeBlendWeight()
                        ############

                        # Sort vertex attributes to match default order for some devices
                        currentVertex.sortAttributes()

                        # Adding vertex to global pool of vertices. If vertex is already added
                        # (it is shared by another polygon and has no different attributes) then the
                        # already added vertex is returned instead.
                        currentVertex = generatedMesh.addVertex(currentVertex)

                        # Make this vertex part of this mesh part.
                        currentMeshPart.addVertex(currentVertex)

                # Add current part to final mesh
                generatedMesh.addPart(currentMeshPart)
                Util.debug("\nFinished creating mesh part.\nMesh part data:\n###\n{!r}\n###", currentMeshPart)

            # Clean cloned mesh
            bpy.data.objects.remove(currentObjNode)
            bpy.data.meshes.remove(currentBlMesh)

            # Normalize attributes so mesh has same number of them for all vertices
            generatedMesh.normalizeAttributes()

            # Add generated mesh to returned list

            generatedMeshes.append(generatedMesh)

        # Return list of all meshes
        return generatedMeshes

    @profile('generateMaterials')
    def generateMaterials(self, context):
        """Read and returns all materials used by the exported objects"""
        generatedMaterials = []
        Util.info("Exporting materials")

        if bpy.data.materials is not None and len(bpy.data.materials) > 0:
            # We will set this to true if we manage to export at least one material
            atLeastOneMaterial = False

            for blMaterial in bpy.data.materials:
                if blMaterial is None or blMaterial.type != 'SURFACE':
                    Util.debug("Ignoring material '{!s}', type is not SURFACE ({!s})", blMaterial.name, blMaterial.type)
                    continue

                # If none of the objects in the scene use the material we don't export it
                materialIsUsed = False
                for currentObjNode in bpy.data.objects:
                    if currentObjNode.type != 'MESH' or (self.useSelection and not currentObjNode.select):
                        continue

                    currentMesh = currentObjNode.data
                    if currentMesh is not None and len(currentMesh.materials) > 0:
                        for searchMaterial in currentMesh.materials:
                            if searchMaterial.name == blMaterial.name:
                                materialIsUsed = True
                                break

                    if materialIsUsed:
                        break

                # We didn't find an object that uses this material. Ignoring
                if not materialIsUsed:
                    Util.debug("Ignoring unused material '{!s}'", blMaterial.name)
                    continue

                Util.debug("Exporting material '{!s}'", blMaterial.name)
                currentMaterial = Material()
                currentMaterial.id = blMaterial.name

                # We select some optional arguments that depend on the shading algorithm
                specularType = "Phong"
                if blMaterial.specular_shader not in {'COOKTORR', 'PHONG', 'BLINN'}:
                    specularType = "Lambert"

                # Ambient color is taken from world
                ambientColor = [0.0, 0.0, 0.0]
                if context is not None and context.scene is not None and context.scene.world is not None:
                    worldAmbientColor = context.scene.world.ambient_color
                    if worldAmbientColor is not None and len(worldAmbientColor) >= 3:
                        ambientColor = list(worldAmbientColor)
                currentMaterial.ambient = ambientColor

                currentMaterial.diffuse = [blMaterial.diffuse_color[0] * blMaterial.diffuse_intensity, \
                                           blMaterial.diffuse_color[1] * blMaterial.diffuse_intensity, \
                                           blMaterial.diffuse_color[2] * blMaterial.diffuse_intensity]

                currentMaterial.specular = [blMaterial.specular_color[0] * blMaterial.specular_intensity \
                                            , blMaterial.specular_color[1] * blMaterial.specular_intensity \
                                            , blMaterial.specular_color[2] * blMaterial.specular_intensity \
                                            , blMaterial.specular_alpha]

                currentMaterial.emissive = [blMaterial.diffuse_color[0], blMaterial.diffuse_color[1], blMaterial.diffuse_color[2]]

                # This is taken from Blender's FBX exporter, LibGDX fbx-conv tool seems to take from same place.
                if specularType == "Phong":
                    currentMaterial.shininess = (blMaterial.specular_hardness - 1.0) / 5.10
                else:
                    # Assumes Blender default specular hardness of 50
                    currentMaterial.shininess = 49.0 / 5.10

                currentMaterial.reflection = list(blMaterial.mirror_color)

                if blMaterial.use_transparency:
                    currentMaterial.opacity = blMaterial.alpha

                if len(blMaterial.texture_slots) > 0:

                    materialTextures = []

                    for slot in blMaterial.texture_slots:
                        currentTexture = Texture()

                        if slot is not None:
                            Util.debug("Found texture {!s}. Texture coords are {!s}, texture type is {!s}", slot.name, slot.texture_coords, slot.texture.type)

                        if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                            if slot is not None:
                                Util.warn("Texture type {!s} not supported, skipping", slot.texture.type)
                            continue

                        currentTexture.id = slot.name
                        currentTexture.filename = (self.getCompatiblePath(slot.texture.image.filepath))

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

                        currentTexture.type = usageType

                        # Ending current texture
                        materialTextures.append(currentTexture)

                    # Adding found textures to this material
                    currentMaterial.textures = materialTextures

                # Adding this material to the full list
                atLeastOneMaterial = True
                generatedMaterials.append(currentMaterial)

            # If all materials where None (unassigned material slots) then we actually didn't export materials and
            # we need to raise an exception
            if not atLeastOneMaterial:
                raise RuntimeError("Can't have a model without materials, use at least one material in your mesh objects.")
        else:
            raise RuntimeError("Can't have a model without materials, use at least one material in your mesh objects.")

        return generatedMaterials

    @profile('generateNodes')
    def generateNodes(self, context, parent=None, parentName=""):
        """Generates object nodes that attach mesh parts, materials and bones together"""
        generatedNodes = []
        Util.info("Exporting nodes")

        listOfBlenderObjects = None

        if parent is None:
            listOfBlenderObjects = bpy.data.objects
        elif isinstance(parent, bpy.types.Bone):
            listOfBlenderObjects = parent.children
        elif parent.type == 'MESH':
            listOfBlenderObjects = parent.children
        elif parent.type == 'ARMATURE':
            listOfBlenderObjects = parent.data.bones

            # If parent is an armature, we store it's name to concatenate with bone names later
            parentName = parent.name

        else:
            return None

        for blNode in listOfBlenderObjects:
            # Node must be a bone, a mesh or an armature
            if not isinstance(blNode, bpy.types.Bone):
                if blNode.type == 'MESH':
                    if (self.useSelection and not blNode.select):
                        continue
                elif blNode.type == 'ARMATURE':
                    if not self.exportArmature:
                        continue
                else:
                    continue
            else:
                # If node is a bone see if parent is the armature.
                # If is, only export the bone if it's a root bone (doesn't have
                # another bone as a parent). Otherwise wait to export it
                # when the parent bone is being exported
                if parent is not None and not isinstance(parent, bpy.types.Bone) and parent.type == 'ARMATURE':
                    if blNode.parent is not None:
                        continue

            currentNode = Node()

            if isinstance(blNode, bpy.types.Bone):
                currentNode.id = ("%s__%s" % (parentName, blNode.name))
            else:
                currentNode.id = blNode.name

            location = [0.0, 0.0, 0.0]
            rotationQuaternion = [1.0, 0.0, 0.0, 0.0]
            scale = [1.0, 1.0, 1.0]

            try:
                transformMatrix = None

                if isinstance(blNode, bpy.types.Bone):
                    transformMatrix = self.getTransformFromBone(blNode)
                elif blNode.parent is not None:
                    if (parent is None and blNode.parent.type == 'ARMATURE') \
                            or (parent is not None):
                        # Exporting a child node, so we get the local transform matrix.
                        # Obs: when exporting root mesh nodes parented to armatures, we consider it
                        # 'child' in relation to the armature so we get it's local transform, but the mesh node
                        # is still considered a root node.
                        transformMatrix = blNode.matrix_local
                    elif parent is None and blNode.parent.type == 'MESH':
                        # If this node is parented and we didn't pass a 'parent' parameter then we are only
                        # exporting root nodes at this time and we'll ignore this node.
                        continue
                else:
                    # Exporting a root node, we get it's transform matrix from the world transform matrix
                    transformMatrix = blNode.matrix_world

                location, rotationQuaternion, scale = transformMatrix.decompose()

            except:
                Util.warn("Error decomposing transform for node %s" % blNode.name)
                location = [0.0, 0.0, 0.0]
                rotationQuaternion = [1.0, 0.0, 0.0, 0.0]
                scale = [1.0, 1.0, 1.0]
                pass

            if not self.testDefaultQuaternion(rotationQuaternion):
                currentNode.rotation = self.convertQuaternionCoordinate(rotationQuaternion)

            if not self.testDefaultTransform(location):
                currentNode.translation = self.convertVectorCoordinate(location)

            if not self.testDefaultScale(scale):
                currentNode.scale = self.convertScaleCoordinate(scale)

            # If this is a mesh node, go through each part and material and associate with this node
            if not isinstance(blNode, bpy.types.Bone) and blNode.type == 'MESH':
                currentBlMesh = blNode.data

                if currentBlMesh.materials is None:
                    Util.warn("Ignored mesh %r, no materials found" % currentBlMesh)
                    continue
                
                # We apply the mesh modifiers to a cloned mesh. Modifiers that duplicate
                # vertices (like Mirror modifier) need this so when we scan vertex groups these
                # vertices are considered real and we know which vertex groups they are weighted to
                clonedAppliedModifiersNode = blNode.copy()
                clonedAppliedModifiersMesh = clonedAppliedModifiersNode.to_mesh(context.scene, self.applyModifiers, 'PREVIEW', calc_tessface=False)
                self.meshTriangulate(clonedAppliedModifiersMesh)
                clonedAppliedModifiersNode.data = clonedAppliedModifiersMesh

                for blMaterialIndex in range(0, len(currentBlMesh.materials)):
                    currentBlMaterial = currentBlMesh.materials[blMaterialIndex]
                    if currentBlMaterial is None:
                        continue

                    nodePart = NodePart()

                    currentBlMeshName = currentBlMesh.name
                    nodePart.meshPartId = currentBlMeshName + "_part" + str(blMaterialIndex)

                    nodePart.materialId = currentBlMaterial.name

                    # Maps material textures to the TEXCOORD attributes
                    for uvIndex in range(len(currentBlMesh.uv_layers)):
                        blUvLayer = currentBlMesh.uv_layers[uvIndex]
                        currentTexCoord = []

                        for texIndex in range(len(currentBlMaterial.texture_slots)):
                            blTexSlot = currentBlMaterial.texture_slots[texIndex]

                            if (blTexSlot is None or blTexSlot.texture_coords != 'UV' or blTexSlot.texture.type != 'IMAGE' or blTexSlot.texture.__class__ is not bpy.types.ImageTexture):
                                continue

                            if (blTexSlot.uv_layer == blUvLayer.name or (blTexSlot.uv_layer == "" and uvIndex == 0)):
                                currentTexCoord.append(texIndex)

                        # Adding UV mappings to this node part
                        nodePart.addUVLayer(currentTexCoord)

                    # Start writing bones
                    if self.exportArmature and len(blNode.vertex_groups) > 0:

                        # Getting only the vertex groups associated with this node part. We use our cloned mesh with applied modifiers for this
                        vertexGroupsForMaterial = self.listPartVertexGroups(clonedAppliedModifiersNode, clonedAppliedModifiersMesh, blMaterialIndex)

                        for blVertexGroup in vertexGroupsForMaterial:
                            # Try to find an armature with a bone associated with this vertex group
                            blArmature = blNode.find_armature()
                            if blArmature is not None:
                                blArmature = blNode.parent.data
                                try:
                                    bone = blArmature.bones[blVertexGroup.name]

                                    # Referencing the bone node
                                    currentBone = Bone()
                                    currentBone.node = ("%s__%s" % (blNode.parent.name, blVertexGroup.name))

                                    boneTransformMatrix = blNode.matrix_local.inverted() * bone.matrix_local
                                    boneLocation, boneQuaternion, boneScale = boneTransformMatrix.decompose()

                                    if not self.testDefaultTransform(boneLocation):
                                        currentBone.translation = self.convertVectorCoordinate(boneLocation)

                                    if not self.testDefaultQuaternion(boneQuaternion):
                                        currentBone.rotation = self.convertQuaternionCoordinate(boneQuaternion)

                                    if not self.testDefaultScale(boneScale):
                                        currentBone.scale = self.convertScaleCoordinate(boneScale)

                                    # Appending resulting bone to part
                                    nodePart.addBone(currentBone)

                                except KeyError:
                                    Util.warn("Vertex group %s has no corresponding bone" % (blVertexGroup.name))
                                    pass
                                except:
                                    Util.error("Unexpected error exporting bone: %s" % blVertexGroup.name)
                                    pass

                    # Adding this node part to the current node
                    currentNode.addPart(nodePart)
                
                # Clean up cloned meshes
                bpy.data.objects.remove(clonedAppliedModifiersNode)
                bpy.data.meshes.remove(clonedAppliedModifiersMesh)

            # If this node is a parent, export it's children
            if blNode.children is not None and len(blNode.children) > 0:
                childNodes = self.generateNodes(context, blNode, parentName)
                currentNode.children = childNodes

            # Adding the current generated node to the list of nodes
            generatedNodes.append(currentNode)

        return generatedNodes

    def generateAnimations(self, context):
        # TODO Detect if certain curve uses linear interpolation. If yes then
        # we can safely just save keyframes as LibGDX also uses linear interpolation
        """If selected by the user, generates keyframed animations for the bones"""
        generatedAnimations = []
        Util.info("Exporting animations")

        # Save our time per currentFrameNumber (in miliseconds)
        fps = context.scene.render.fps
        frameTime = (1 / fps) * 1000

        # For each action we export currentFrameNumber data.
        # We are exporting all actions, but to avoid exporting deleted actions (actions with ZERO users)
        # each action must have at least one user. In Blender user the FAKE USER option to assign at least
        # one user to each action
        if self.exportAnimation:
            for blAction in bpy.data.actions:
                if blAction.users <= 0:
                    continue

                currentAnimation = Animation()
                currentAnimation.id = blAction.name

                for blArmature in bpy.data.objects:
                    if blArmature.type != 'ARMATURE':
                        continue

                    # If armature have a selected object as a child we export it' actions regardless of it being
                    # selected and "export selected only" is checked. Otherwise it is only exported
                    # if it's selected
                    doExportArmature = False
                    if self.useSelection and not blArmature.select:
                        for child in blArmature.children:
                            if child.select:
                                doExportArmature = True
                                break
                    else:
                        doExportArmature = True

                    if not doExportArmature:
                        continue

                    for blBone in blArmature.data.bones:
                        currentBone = NodeAnimation()
                        currentBone.boneId = ("%s__%s" % (blArmature.name, blBone.name))

                        translationFCurve = self.findFCurve(blAction, blBone, self.P_LOCATION)
                        rotationFCurve = self.findFCurve(blAction, blBone, self.P_ROTATION)
                        scaleFCurve = self.findFCurve(blAction, blBone, self.P_SCALE)

                        # Rest transform of this bone, used as reference to calculate frames
                        restTransform = self.getTransformFromBone(blBone)

                        frameStart = context.scene.frame_start
                        for currentFrameNumber in range(int(blAction.frame_range[0]), int(blAction.frame_range[1] + 1)):
                            currentKeyframe = Keyframe()

                            translationVector = [0.0] * 3
                            rotationVector = [0.0] * 4
                            rotationVector[0] = 1.0
                            scaleVector = [1.0] * 3

                            mustEvaluateTranslation = self.mustEvaluateKeyframe(translationFCurve, float(currentFrameNumber))
                            if translationFCurve is not None and translationFCurve != ([None] * 3) and mustEvaluateTranslation:
                                if translationFCurve[0] is not None:
                                    translationVector[0] = translationFCurve[0].evaluate(currentFrameNumber)
                                if translationFCurve[1] is not None:
                                    translationVector[1] = translationFCurve[1].evaluate(currentFrameNumber)
                                if translationFCurve[2] is not None:
                                    translationVector[2] = translationFCurve[2].evaluate(currentFrameNumber)

                            mustEvaluateRotation = self.mustEvaluateKeyframe(rotationFCurve, float(currentFrameNumber))
                            if rotationFCurve is not None and rotationFCurve != ([None] * 4) and mustEvaluateRotation:
                                if rotationFCurve[0] is not None:
                                    rotationVector[0] = rotationFCurve[0].evaluate(currentFrameNumber)
                                if rotationFCurve[1] is not None:
                                    rotationVector[1] = rotationFCurve[1].evaluate(currentFrameNumber)
                                if rotationFCurve[2] is not None:
                                    rotationVector[2] = rotationFCurve[2].evaluate(currentFrameNumber)
                                if rotationFCurve[3] is not None:
                                    rotationVector[3] = rotationFCurve[3].evaluate(currentFrameNumber)

                            mustEvaluateScale = self.mustEvaluateKeyframe(scaleFCurve, float(currentFrameNumber))
                            if scaleFCurve is not None and scaleFCurve != ([None] * 3) and mustEvaluateScale:
                                if scaleFCurve[0] is not None:
                                    scaleVector[0] = scaleFCurve[0].evaluate(currentFrameNumber)
                                if scaleFCurve[1] is not None:
                                    scaleVector[1] = scaleFCurve[1].evaluate(currentFrameNumber)
                                if scaleFCurve[2] is not None:
                                    scaleVector[2] = scaleFCurve[2].evaluate(currentFrameNumber)

                            poseTransform = self.createTransformMatrix(translationVector, rotationVector, scaleVector)
                            translationVector, rotationVector, scaleVector = (restTransform * poseTransform).decompose()

                            # If one of the transform attributes had to be evaluated above then this
                            # is a keyframe, otherwise it's on rest pose and we don't need the keyframe
                            if mustEvaluateTranslation:
                                currentKeyframe.translation = list(translationVector)

                            if mustEvaluateScale:
                                currentKeyframe.scale = list(scaleVector)

                            if mustEvaluateRotation:
                                currentKeyframe.rotation = list(rotationVector)

                            # If we have at least one attribute changed in that currentFrameNumber, we store it
                            if currentKeyframe.translation is not None \
                                    or currentKeyframe.rotation is not None \
                                    or currentKeyframe.scale is not None:
                                currentKeyframe.keytime = (currentFrameNumber - frameStart) * frameTime
                                currentBone.addKeyframe(currentKeyframe)

                        # If there is at least one currentFrameNumber for this bone, add it's data
                        if currentBone.keyframes is not None and len(currentBone.keyframes) > 0:
                            # We operated with Blender coordinates the entire time, now we convert
                            # to the target coordinates
                            for currentFrameNumber in currentBone.keyframes:
                                if currentFrameNumber.translation is not None:
                                    currentFrameNumber.translation = self.convertVectorCoordinate(currentFrameNumber.translation)

                                if currentFrameNumber.rotation is not None:
                                    currentFrameNumber.rotation = self.convertQuaternionCoordinate(currentFrameNumber.rotation)

                                if currentFrameNumber.scale is not None:
                                    currentFrameNumber.scale = self.convertScaleCoordinate(currentFrameNumber.scale)

                            # Finally add bone node to animation
                            currentAnimation.addBone(currentBone)

                # If this action animates at least one bone, add it to the list of actions
                if currentAnimation.bones is not None and len(currentAnimation.bones) > 0:
                    generatedAnimations.append(currentAnimation)

        # Finally return the generated animations
        return generatedAnimations

    # ## UTILITY METHODS
    def getCompatiblePath(self, path):
        baseFolder = bpy.path.abspath("//")
        destFolder = bpy.path.abspath("//")
        return path_reference(filepath=path, mode='RELATIVE', base_src=baseFolder, base_dst=destFolder)

        """Return path minus the '//' prefix, for Windows compatibility"""
        """
        path = path.replace('\\', '/')
        return path[2:] if path[:2] in {"//", b"//"} else path
        """

    def meshTriangulate(self, me):
        """
        Creates a triangulated copy of a mesh.

        This copy needs to later be removed or else it will be saved as new data on the Blender file.
        """

        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        del bmesh

    def listPartVertexGroups(self, blObject, blMesh, materialIndex):
        """
        Lists all vertex groups associated with polys shaded with certain material.
        """
        vertexGroups = []

        for vertexGroupIndex in range(0, len(blObject.vertex_groups)):
            vertexGroup = blObject.vertex_groups[vertexGroupIndex]
            groupIsInPart = False

            for poly in blMesh.polygons:
                if (poly.material_index != materialIndex):
                    continue

                for loopIndex in poly.loop_indices:
                    blLoop = blMesh.loops[loopIndex]

                    try:
                        weightValue = vertexGroup.weight(blLoop.vertex_index)

                        if round(weightValue, FLOAT_ROUND) != 0.0:
                            vertexGroups.append(vertexGroup)
                            groupIsInPart = True
                            break
                    except:
                        pass

                if groupIsInPart:
                    break

        return vertexGroups

    def convertVectorCoordinate(self, co):
        """
        Converts Blender axis (Z-up) to the destination axis (usually Z-forward Y-up)

        Destination axis is defined on 'self.vector3AxisMapper' and 'self.vector4AxisMapper' attributes.
        """
        newCo = [(co[self.vector3AxisMapper["x"]["coPos"]] * self.vector3AxisMapper["x"]["sign"]), (co[self.vector3AxisMapper["y"]["coPos"]] * self.vector3AxisMapper["y"]["sign"]), (co[self.vector3AxisMapper["z"]["coPos"]] * self.vector3AxisMapper["z"]["sign"])]
        return newCo

    def convertQuaternionCoordinate(self, co):
        """
        Converts quaternions from Blender axis (Z-up) to the destination axis (usually Z-forward Y-up)

        Destination axis is defined on 'self.vector3AxisMapper' and 'self.vector4AxisMapper' attributes.
        """
        return [(co[self.vector4AxisMapper["x"]["coPos"]] * self.vector4AxisMapper["x"]["sign"]), (co[self.vector4AxisMapper["y"]["coPos"]] * self.vector4AxisMapper["y"]["sign"]),
                (co[self.vector4AxisMapper["z"]["coPos"]] * self.vector4AxisMapper["z"]["sign"]), (co[self.vector4AxisMapper["w"]["coPos"]] * self.vector4AxisMapper["w"]["sign"])]

    def convertScaleCoordinate(self, co):
        """
        Converts Blender axis (Z-up) to the destination axis (usually Z-forward Y-up)

        For scaling the range is 0.0 to 1.0 so we ignore sign and just adjust axis
        """
        return [co[self.vector3AxisMapper["x"]["coPos"]], co[self.vector3AxisMapper["y"]["coPos"]], co[self.vector3AxisMapper["z"]["coPos"]]]

    def getTransformFromBone(self, bone):
        """Create a transform matrix based on the relative rest position of a bone"""
        transformMatrix = None

        if bone.parent is None:
            transformMatrix = bone.matrix_local
        else:
            transformMatrix = bone.parent.matrix_local.inverted() * bone.matrix_local

        return transformMatrix

    def findFCurve(self, action, bone, prop):
        """
        Find a fcurve for the given action, bone and property. Returns an array with as many fcurves
        as there are indices in the property.
        Ex: The returned value for the location property will have 3 fcurves, one for each of the X, Y and Z coordinates
        """

        returnedFCurves = None

        dataPath = ("pose.bones[\"%s\"].%s" % (bone.name, prop))
        if prop == self.P_LOCATION:
            returnedFCurves = [None, None, None]
        elif prop == self.P_ROTATION:
            returnedFCurves = [None, None, None, None]
        elif prop == self.P_SCALE:
            returnedFCurves = [None, None, None]
        else:
            self.error("FCurve Property not supported")
            raise Exception("FCurve Property not supported")

        for fcurve in action.fcurves:
            if fcurve.data_path == dataPath:
                returnedFCurves[fcurve.array_index] = fcurve

        return returnedFCurves

    def mustEvaluateKeyframe(self, fCurves, frame):
        """
        Returns True if you should evaluate the coordinates for this frame on this curve.
        This happens if we are on a keyframe or if the curve type isn't LINEAR. LibGDX
        uses linear interpolation so any other kind of curve means we need to plot normal
        frames into keyframes
        """
        isKeyframe = False
        hasNonLinearCurve = False

        if fCurves is not None:
            for curve in fCurves:
                if curve is not None:
                    selectedKeyframe = None
                    selectedKeyframeIndex = None

                    for keyframeIndex in range(0, len(curve.keyframe_points)):
                        keyframe = curve.keyframe_points[keyframeIndex]
                        if keyframe.co[0] <= frame and (selectedKeyframe is None or keyframe.co[0] > selectedKeyframe.co[0]):
                            selectedKeyframe = keyframe
                            selectedKeyframeIndex = keyframeIndex
                        elif keyframe.co[0] > frame:
                            # We don't need to keep searching as we passed the current frame
                            continue

                    if selectedKeyframe is not None:
                        if selectedKeyframe.co[0] == frame:
                            isKeyframe = True
                            break
                        elif selectedKeyframe.interpolation != "LINEAR":
                            if selectedKeyframe.interpolation == "CONSTANT":
                                # For constant interpolation we need to evaluate the keyframe
                                # and one frame before the next keyframe and they need to have the
                                # same values
                                if selectedKeyframeIndex is not None and len(curve.keyframe_points) > (selectedKeyframeIndex + 1):
                                    nextKeyframe = curve.keyframe_points[selectedKeyframeIndex + 1]
                                    if nextKeyframe.co[0] == frame + 1.0:
                                        # Next frame is a keyframe for this curve, we evaluate this frame
                                        hasNonLinearCurve = True
                                        break
                            else:
                                # For any other curve that's not linear we need to evaluate the frame
                                hasNonLinearCurve = True
                                break

        return isKeyframe or hasNonLinearCurve

    def createTransformMatrix(self, locationVector, quaternionVector, scaleVector):
        """Create a transform matrix from a location vector, a rotation quaternion and a scale vector"""

        if isinstance(quaternionVector, mathutils.Quaternion):
            quat = quaternionVector.normalized()
        else:
            quat = mathutils.Quaternion(quaternionVector).normalized()

        translationMatrix = mathutils.Matrix(((0, 0, 0, locationVector[0]), (0, 0, 0, locationVector[1]), (0, 0, 0, locationVector[2]), (0, 0, 0, 0)))

        rotationMatrix = quat.to_matrix().to_4x4()

        scaleMatrix = mathutils.Matrix(((scaleVector[0], 0, 0, 0), (0, scaleVector[1], 0, 0), (0, 0, scaleVector[2], 0), (0, 0, 0, 1)))

        matrix = (rotationMatrix * scaleMatrix) + translationMatrix

        return matrix

    def compareVector(self, v1, v2):
        a1 = [Util.floatToString(self, v1[0]), Util.floatToString(self, v1[1]), Util.floatToString(self, v1[2])]
        a2 = [Util.floatToString(self, v2[0]), Util.floatToString(self, v2[1]), Util.floatToString(self, v2[2])]
        return a1 == a2

    def compareQuaternion(self, q1, q2):
        a1 = [Util.floatToString(self, q1[0]), Util.floatToString(self, q1[1]), Util.floatToString(self, q1[2]), Util.floatToString(self, q1[3])]
        a2 = [Util.floatToString(self, q2[0]), Util.floatToString(self, q2[1]), Util.floatToString(self, q2[2]), Util.floatToString(self, q2[3])]
        return a1 == a2

    def testDefaultQuaternion(self, quaternion):
        return quaternion[0] == 1.0 \
            and quaternion[1] == 0.0 \
            and quaternion[2] == 0.0 \
            and quaternion[3] == 0.0

    def testDefaultScale(self, scale):
        return scale[0] == 1.0 \
            and scale[1] == 1.0 \
            and scale[2] == 1.0

    def testDefaultTransform(self, transform):
        return transform[0] == 0.0 \
            and transform[1] == 0.0 \
            and transform[2] == 0.0

    def setupAxisConversion(self, axisForward, axisUp):

        self.vector3AxisMapper["x"] = {}
        self.vector3AxisMapper["y"] = {}
        self.vector3AxisMapper["z"] = {}
        self.vector4AxisMapper["x"] = {}
        self.vector4AxisMapper["y"] = {}
        self.vector4AxisMapper["z"] = {}
        self.vector4AxisMapper["w"] = {}

        # W for quaternions takes from blender W which is index 0
        self.vector4AxisMapper["w"]["coPos"] = 0
        self.vector4AxisMapper["w"]["sign"] = 1.0

        if axisForward == "X" or axisForward == "-X":
            self.vector3AxisMapper["x"]["coPos"] = 1
            self.vector4AxisMapper["x"]["coPos"] = 2

            if axisForward == "X":
                self.vector3AxisMapper["x"]["sign"] = 1.0
                self.vector4AxisMapper["x"]["sign"] = 1.0
            else:
                self.vector3AxisMapper["x"]["sign"] = -1.0
                self.vector4AxisMapper["x"]["sign"] = -1.0

            if axisUp == "Y" or axisUp == "-Y":
                self.vector3AxisMapper["y"]["coPos"] = 2
                self.vector4AxisMapper["y"]["coPos"] = 3

                if axisUp == "Y":
                    self.vector3AxisMapper["y"]["sign"] = 1.0
                    self.vector4AxisMapper["y"]["sign"] = 1.0
                else:
                    self.vector3AxisMapper["y"]["sign"] = -1.0
                    self.vector4AxisMapper["y"]["sign"] = -1.0

                # Z is right
                self.vector3AxisMapper["z"]["coPos"] = 0
                self.vector4AxisMapper["z"]["coPos"] = 1
                self.vector3AxisMapper["z"]["sign"] = 1.0
                self.vector4AxisMapper["z"]["sign"] = 1.0

            elif axisUp == "Z" or axisUp == "-Z":
                self.vector3AxisMapper["z"]["coPos"] = 2
                self.vector4AxisMapper["z"]["coPos"] = 3

                if axisUp == "Z":
                    self.vector3AxisMapper["z"]["sign"] = 1.0
                    self.vector4AxisMapper["z"]["sign"] = 1.0
                else:
                    self.vector3AxisMapper["z"]["sign"] = -1.0
                    self.vector4AxisMapper["z"]["sign"] = -1.0

                # Y is right
                self.vector3AxisMapper["y"]["coPos"] = 0
                self.vector4AxisMapper["y"]["coPos"] = 1
                self.vector3AxisMapper["y"]["sign"] = 1.0
                self.vector4AxisMapper["y"]["sign"] = 1.0

        elif axisForward == "Y" or axisForward == "-Y":
            self.vector3AxisMapper["y"]["coPos"] = 1
            self.vector4AxisMapper["y"]["coPos"] = 2

            if axisForward == "Y":
                self.vector3AxisMapper["y"]["sign"] = 1.0
                self.vector4AxisMapper["y"]["sign"] = 1.0
            else:
                self.vector3AxisMapper["y"]["sign"] = -1.0
                self.vector4AxisMapper["y"]["sign"] = -1.0

            if axisUp == "X" or axisUp == "-X":
                self.vector3AxisMapper["x"]["coPos"] = 2
                self.vector4AxisMapper["x"]["coPos"] = 3

                if axisUp == "X":
                    self.vector3AxisMapper["x"]["sign"] = 1.0
                    self.vector4AxisMapper["x"]["sign"] = 1.0
                else:
                    self.vector3AxisMapper["x"]["sign"] = -1.0
                    self.vector4AxisMapper["x"]["sign"] = -1.0

                # Z is right
                self.vector3AxisMapper["z"]["coPos"] = 0
                self.vector4AxisMapper["z"]["coPos"] = 1
                self.vector3AxisMapper["z"]["sign"] = 1.0
                self.vector4AxisMapper["z"]["sign"] = 1.0

            elif axisUp == "Z" or axisUp == "-Z":
                self.vector3AxisMapper["z"]["coPos"] = 2
                self.vector4AxisMapper["z"]["coPos"] = 3

                if axisUp == "Z":
                    self.vector3AxisMapper["z"]["sign"] = 1.0
                    self.vector4AxisMapper["z"]["sign"] = 1.0
                else:
                    self.vector3AxisMapper["z"]["sign"] = -1.0
                    self.vector4AxisMapper["z"]["sign"] = -1.0

                # X is right
                self.vector3AxisMapper["x"]["coPos"] = 0
                self.vector4AxisMapper["x"]["coPos"] = 1
                self.vector3AxisMapper["x"]["sign"] = 1.0
                self.vector4AxisMapper["x"]["sign"] = 1.0

        elif axisForward == "Z" or axisForward == "-Z":
            self.vector3AxisMapper["z"]["coPos"] = 1
            self.vector4AxisMapper["z"]["coPos"] = 2

            if axisForward == "Z":
                self.vector3AxisMapper["z"]["sign"] = 1.0
                self.vector4AxisMapper["z"]["sign"] = 1.0
            else:
                self.vector3AxisMapper["z"]["sign"] = -1.0
                self.vector4AxisMapper["z"]["sign"] = -1.0

            if axisUp == "Y" or axisUp == "-Y":
                self.vector3AxisMapper["y"]["coPos"] = 2
                self.vector4AxisMapper["y"]["coPos"] = 3

                if axisUp == "Y":
                    self.vector3AxisMapper["y"]["sign"] = 1.0
                    self.vector4AxisMapper["y"]["sign"] = 1.0
                else:
                    self.vector3AxisMapper["y"]["sign"] = -1.0
                    self.vector4AxisMapper["y"]["sign"] = -1.0

                # X is right
                self.vector3AxisMapper["x"]["coPos"] = 0
                self.vector4AxisMapper["x"]["coPos"] = 1
                self.vector3AxisMapper["x"]["sign"] = 1.0
                self.vector4AxisMapper["x"]["sign"] = 1.0

            elif axisUp == "X" or axisUp == "-X":
                self.vector3AxisMapper["x"]["coPos"] = 2
                self.vector4AxisMapper["x"]["coPos"] = 3

                if axisUp == "X":
                    self.vector3AxisMapper["x"]["sign"] = 1.0
                    self.vector4AxisMapper["x"]["sign"] = 1.0
                else:
                    self.vector3AxisMapper["x"]["sign"] = -1.0
                    self.vector4AxisMapper["x"]["sign"] = -1.0

                # Y is right
                self.vector3AxisMapper["y"]["coPos"] = 0
                self.vector4AxisMapper["y"]["coPos"] = 1
                self.vector3AxisMapper["y"]["sign"] = 1.0
                self.vector4AxisMapper["y"]["sign"] = 1.0


class G3DBExporterOperator(bpy.types.Operator, G3DBaseExporterOperator):
    bl_idname = "export_json_g3d.g3db"
    bl_label = "G3DB Exporter"
    bl_options = {'PRESET'}

    filename_ext = ".g3db"
    
    oldFormatJson = BoolProperty(
        name="Use Old UBJSON Datatypes",
        description="Use the old UBJSON datatype sizes. LibGDX loads the old format by default.",
        default=True
    )
    
    order = [
        "filepath",
        "check_existing",
        "useSelection",
        "applyModifiers",
        "exportArmature",
        "bonesPerVertex",
        "exportAnimation",
        "generateTangentBinormal",
        "oldFormatJson",
    ]


class G3DJExporterOperator(bpy.types.Operator, G3DBaseExporterOperator):
    bl_idname = "export_json_g3d.g3dj"
    bl_label = "G3DJ Exporter"
    bl_options = {'PRESET'}

    filename_ext = ".g3dj"
