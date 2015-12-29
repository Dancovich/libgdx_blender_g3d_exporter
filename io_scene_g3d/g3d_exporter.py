import bpy

from bpy_extras.io_utils import ExportHelper

from io_scene_g3d.util import Util, LOG_LEVEL, _DEBUG_
from io_scene_g3d.g3d_model import G3DModel
from io_scene_g3d.mesh import Mesh
from io_scene_g3d.mesh_part import MeshPart
from io_scene_g3d.vertex import Vertex
from io_scene_g3d.vertex_attribute import VertexAttribute
from io_scene_g3d.node import Node, NodePart, Bone
from io_scene_g3d.material import Material
from io_scene_g3d.texture import Texture

from io_scene_g3d.profile import profile, print_stats


from bpy.props import BoolProperty, IntProperty

class G3DExporter(bpy.types.Operator, ExportHelper):
    """Export scene to G3D (LibGDX) format"""
    
    bl_idname     = "export_json_g3d.g3dj"
    bl_label      = "G3D Exporter"
    bl_options    = {'PRESET'}
    
    filename_ext    = ".g3dj"
    
    # This is our model
    g3dModel = None
    
    # Exporter options
    useSelection = BoolProperty( \
            name="Selection Only", \
            description="Export only selected objects", \
            default=False, \
            )
    
    
    exportArmature = BoolProperty( \
            name="Export Armature", \
            description="Export armature nodes (bones)", \
            default=False, \
            )
    
    bonesPerVertex = IntProperty( \
            name="Bone Weights per Vertex", \
            description="Maximum number of BLENDWEIGHT attributes per vertex. LibGDX default is 4.", \
            default=4 \
            )
    
    exportAnimation = BoolProperty( \
            name="Export Actions as Animation", \
            description="Export bone actions as animations", \
            default=False, \
            )
    
    generateTangentBinormal = BoolProperty( \
            name="Calculate Tangent and Binormal Vectors", \
            description="Calculate and export tangent and binormal vectors for normal mapping. Requires UV mapping the mesh.", \
            default=False, \
            )
    
    vector3AxisMapper = {}
    
    vector4AxisMapper = {}
    
    
    def execute(self, context):
        """Main method run by Blender to export a G3D file"""
        
        # Defines our mapping from Blender Z-Up to whatever the user selected
        self.vector3AxisMapper["x"] = {}
        self.vector3AxisMapper["x"]["axis"] = "x"
        self.vector3AxisMapper["x"]["coPos"] = 0
        self.vector3AxisMapper["x"]["sign"] = 1.0
        
        self.vector3AxisMapper["y"] = {}
        self.vector3AxisMapper["y"]["axis"] = "z"
        self.vector3AxisMapper["y"]["coPos"] = 2
        self.vector3AxisMapper["y"]["sign"] = 1.0
        
        self.vector3AxisMapper["z"] = {}
        self.vector3AxisMapper["z"]["axis"] = "y"
        self.vector3AxisMapper["z"]["coPos"] = 1
        self.vector3AxisMapper["z"]["sign"] = -1.0
        
        self.vector4AxisMapper["x"] = {}
        self.vector4AxisMapper["x"]["axis"] = "x"
        self.vector4AxisMapper["x"]["coPos"] = 1
        self.vector4AxisMapper["x"]["sign"] = 1.0
        
        self.vector4AxisMapper["y"] = {}
        self.vector4AxisMapper["y"]["axis"] = "z"
        self.vector4AxisMapper["y"]["coPos"] = 3
        self.vector4AxisMapper["y"]["sign"] = 1.0
        
        self.vector4AxisMapper["z"] = {}
        self.vector4AxisMapper["z"]["axis"] = "y"
        self.vector4AxisMapper["z"]["coPos"] = 2
        self.vector4AxisMapper["z"]["sign"] = -1.0
        
        self.vector4AxisMapper["w"] = {}
        self.vector4AxisMapper["w"]["axis"] = "w"
        self.vector4AxisMapper["w"]["coPos"] = 0
        self.vector4AxisMapper["w"]["sign"] = 1.0
        
        # Changes Blender to "object" mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # define our return state
        result = {'FINISHED'}
        
        # Initialize our model
        self.g3dModel = G3DModel()
        
        # Generate the mesh list of the model
        self.g3dModel.meshes = self.generateMeshes(context)
        
        # Generate the materials used in the model
        self.g3dModel.materials = self.generateMaterials(context)
        
        # Generate the nodes binding mesh parts, materials and bones
        self.g3dModel.nodes = self.generateNodes(context)
        
        # Export the nodes
        # TODO Do the export
        
        #if LOG_LEVEL == _DEBUG_:
        print_stats()
        
        return result
    
    @profile('generateMeshes')
    def generateMeshes(self, context):
        """Reads all MESH type objects and exported the selected ones (or all if 'only selected' isn't checked"""
        
        generatedMeshes = []
        
        for currentObjNode in bpy.data.objects:
            if currentObjNode.type != 'MESH' or (self.useSelection and not currentObjNode.select):
                continue
            
            # If we already processed the mesh data associated with this object, continue (ex: multiple objects pointing to same mesh data)
            if self.g3dModel.hasMesh(currentObjNode.data.name):
                Util.debug(None, "Skipping mesh for node %s (already exported from another node)" % currentObjNode.name)
                continue
            
            Util.debug(None, "Writing mesh from node %s" % currentObjNode.name)
            
            # This is the mesh object we are generating
            generatedMesh = Mesh()
            currentBlMeshName = currentObjNode.data.name
            generatedMesh.id = currentBlMeshName
            
            # Clone mesh to a temporary object. Wel'll apply modifiers and triangulate the
            # clone before exporting.
            currentBlMesh = currentObjNode.to_mesh(context.scene , False, 'PREVIEW', calc_tessface=False)
            self.meshTriangulate(currentBlMesh)
            
            # We can only export polygons that are associated with a material, so we loop
            # through the list of materials for this mesh  
            
            # Loop through the polygons of this mesh
            if currentBlMesh.materials == None:
                Util.warn(None, "Ignored mesh %r, no materials found" % currentBlMesh)
                continue
            
            for blMaterialIndex in range(0,len(currentBlMesh.materials)):
                
                # Fills the part here
                currentMeshPart = MeshPart(meshPartId=currentBlMeshName+"_part"+str(blMaterialIndex))
                
                for poly in currentBlMesh.polygons:
                    Util.debug(None, "  Processing material index %d" % blMaterialIndex)
                    if (poly.material_index != blMaterialIndex):
                        Util.debug(None, "  Skipping polygon associated with another material (current index:%d, poly index: %d)" % (blMaterialIndex, poly.material_index) )
                        continue
                    
                    Util.debug(None, "Polygon index: %d, length: %d, material id: %d" % (poly.index, poly.loop_total, poly.material_index))
                    for loopIndex in poly.loop_indices:
                        blLoop = currentBlMesh.loops[loopIndex]
                        blVertex = currentBlMesh.vertices[blLoop.vertex_index]
                        currentVertex = Vertex()
                                           
                        Util.debug(None, "    Reading vertex")
                        Util.debug(None, "    Vertex Index: %d" % currentBlMesh.loops[loopIndex].vertex_index)
                        Util.debug(None, "    Vertex Coord: %r" % blVertex.co)
                        Util.debug(None, "    Normal: %r" % blVertex.normal)
                        Util.debug(None, "    Split Normal: %r" % currentBlMesh.loops[loopIndex].normal)
                        
                        ############
                        # Vertex position is the minimal attribute
                        attribute = VertexAttribute(VertexAttribute.POSITION, \
                                                    self.convertVectorCoordinate( blVertex.co ))
                        if not currentVertex.add(attribute):
                            Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                        ############
                        
                        ############
                        # Exporting tangent and binormals. We calculate those prior to normals because
                        # if we want tangent and binormals then we'll be also using split normals, which
                        # will be exported next section
                        doneCalculatingTangentBinormal = False
                        splitNormalValue = None
                        if self.generateTangentBinormal and currentBlMesh.uv_layers != None and len(currentBlMesh.uv_layers) > 0:
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
                                attribute = VertexAttribute(name=VertexAttribute.TANGENT,value=self.convertVectorCoordinate(tangent) )
                                
                                if not currentVertex.add(attribute):
                                    Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                                    
                                binormal = [None] * 3
                                binormal[0], binormal[1], binormal[2] = blLoop.bitangent
                                attribute = VertexAttribute(name=VertexAttribute.BINORMAL,value=self.convertVectorCoordinate(binormal) )
                                
                                if not currentVertex.add(attribute):
                                    Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                                    
                                splitNormalValue = [None] * 3
                                splitNormalValue[0], splitNormalValue[1], splitNormalValue[2] = blLoop.normal
                                
                                currentBlMesh.free_tangents()
                                                        
                        ############
                        
                        ############
                        # Read normals. We also determine if we'll user per-face (flat shading)
                        # or per-vertex normals (gouraud shading) here.
                        attribute = VertexAttribute(name=VertexAttribute.NORMAL)
                        if doneCalculatingTangentBinormal and splitNormalValue != None:
                            Util.debug(None, "    Using split normals: True")
                            attribute.value = self.convertVectorCoordinate(splitNormalValue)
                        elif poly.use_smooth:
                            Util.debug(None, "    Uses smooth shading: True")
                            attribute.value = self.convertVectorCoordinate(blVertex.normal)
                        else:
                            Util.debug(None, "    Uses smooth shading: False")
                            attribute.value = self.convertVectorCoordinate(poly.normal)
                            
                        if not currentVertex.add(attribute):
                            Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                        ############
                        
                        ############
                        # Defining vertex color
                        colorMap = currentBlMesh.vertex_colors.active
                        if colorMap != None:
                            color = [None] * 3
                            color[0], color[1], color[2] = colorMap.data[loopIndex].color
                            
                            attribute = VertexAttribute(name=VertexAttribute.COLOR, value=color)
                            
                            if not currentVertex.add(attribute):
                                Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                            
                        ############
                        
                        ############
                        # Exporting UV coordinates
                        if currentBlMesh.uv_layers != None and len(currentBlMesh.uv_layers) > 0:
                            texCoordCount = 0
                            for uv in currentBlMesh.uv_layers:
                                # We need to flip UV's because Blender use bottom-left as Y=0 and G3D use top-left
                                flippedUV = [ uv.data[ loopIndex ].uv[0] , 1.0 - uv.data[ loopIndex ].uv[1] ]
                                
                                texCoordAttrName = VertexAttribute.TEXCOORD + str(texCoordCount)
                                attribute = VertexAttribute(texCoordAttrName, flippedUV)
                                
                                
                                texCoordCount = texCoordCount + 1
                                
                                if not currentVertex.add(attribute):
                                    Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                        ############
                        
                        ############
                        # Exporting bone weights. We only export at most 'self.bonesPerVertex' bones
                        # for a single vertex.
                        if self.exportArmature:
                            Util.debug(None, "    Exporting blend weights for current vertex index %d" % blLoop.vertex_index)
                            
                            zeroWeight = Util.floatToString(None,0.0)
                            blendWeightAttrName = VertexAttribute.BLENDWEIGHT + "%d"
                            
                            if currentObjNode.parent != None and currentObjNode.parent.type == 'ARMATURE':
                                armatureObj = currentObjNode.parent
                                boneIndex = 0

                                for vertexGroup in currentObjNode.vertex_groups:
                                    # We can only export this ammount of bones per vertex
                                    if boneIndex >= self.bonesPerVertex:
                                        break
                                    
                                    # Search for a bone with the same name as a vertex group
                                    bone = None
                                    try:
                                        Util.debug(None, "        Looking for bone with name %s" % vertexGroup.name)
                                        bone = armatureObj.data.bones[vertexGroup.name]
                                    except:
                                        bone = None
                                    
                                    if bone != None:
                                        Util.debug(None, "        Found bone %s" % vertexGroup.name)
                                        
                                        try:
                                            # We get the weight associated with this vertex group. Zeros are ignored
                                            boneWeight = vertexGroup.weight(blLoop.vertex_index)
                                            
                                            Util.debug(None, "        Bone weight for vertex %d in group %s is %f" % (blLoop.vertex_index,vertexGroup.name,vertexGroup.weight(blLoop.vertex_index)))

                                            if Util.floatToString(None, boneWeight) != zeroWeight:
                                                blendWeightValue = [float(boneIndex), boneWeight]
                                                attribute = VertexAttribute((blendWeightAttrName % boneIndex), blendWeightValue)
                                                
                                                if not currentVertex.add(attribute):
                                                    Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                                                else:
                                                    boneIndex = boneIndex + 1

                                        except Exception as boneWeightException:
                                            Util.warn(None, "        Error trying to export bone weight for vertex index %d (%r)" % (blLoop.vertex_index,boneWeightException))
                                            pass
                            
                            # In the end we normalize the bone weights
                            currentVertex.normalizeBlendWeight()
                        ############
                            
                        
                        # Adding vertex to global pool of vertices. If vertex is already added
                        # (it is shared by another polygon and has no different attributes) then the
                        # already added vertex is returned instead.
                        currentVertex = generatedMesh.addVertex(currentVertex)
                        
                        # Make this vertex part of this mesh part.
                        Util.debug(None, "Adding vertex (currentObjNode id %d) on material %d to mesh part (currentObjNode id %d)" % (id(currentVertex),blMaterialIndex,id(currentMeshPart)))
                        currentMeshPart.addVertex(currentVertex)
                
                # Add current part to final mesh
                generatedMesh.addPart(currentMeshPart)
                    
            # Clean cloned mesh
            bpy.data.meshes.remove(currentBlMesh)
            
            # Add generated mesh to returned list
            Util.debug(None, "==== GENERATED MESH IS \n %s" % generatedMesh)
            generatedMeshes.append(generatedMesh)
                    
        # Return list of all meshes
        return generatedMeshes
    
    @profile('generateMaterials')
    def generateMaterials(self, context):
        """Read and returns all materials used by the exported objects"""
        generatedMaterials = []
        
        Util.debug(None, "Generating materials")
        
        for currentObjNode in bpy.data.objects:
            if currentObjNode.type != 'MESH' or (self.useSelection and not currentObjNode.select):
                continue
            
            currentMesh = currentObjNode.data
            
            if currentMesh != None and len(currentMesh.materials) > 0:
                for blMaterial in currentMesh.materials:
                    currentMaterial = Material()
                    
                    currentMaterial.id = blMaterial.name
                    
                    Util.debug(None, "Exporting material %s" % blMaterial.name)
                    
                    currentMaterial.ambient = [blMaterial.ambient, blMaterial.ambient, blMaterial.ambient, 1.0]
                    Util.debug(None, "    Ambient: %r" % currentMaterial.ambient)
                    
                    currentMaterial.diffuse = [blMaterial.diffuse_color[0] \
                                                    ,blMaterial.diffuse_color[1] \
                                                    ,blMaterial.diffuse_color[2]]
                    Util.debug(None, "    Diffuse: %r" % currentMaterial.diffuse)
                    
                    currentMaterial.specular = [blMaterial.specular_color[0] * blMaterial.specular_intensity \
                                                    ,blMaterial.specular_color[1] * blMaterial.specular_intensity \
                                                    ,blMaterial.specular_color[2] * blMaterial.specular_intensity \
                                                    ,blMaterial.specular_alpha]
                    Util.debug(None, "    Specular: %r" % currentMaterial.specular)
                    
                    currentMaterial.emissive = [blMaterial.emit\
                                                    , blMaterial.emit\
                                                    , blMaterial.emit]
                    Util.debug(None, "    Emissive: %r" % currentMaterial.emissive)
                    
                    currentMaterial.shininess = blMaterial.specular_hardness
                    Util.debug(None, "    Shininess: %r" % currentMaterial.shininess)
                    
                    if blMaterial.raytrace_mirror.use:
                        currentMaterial.reflection = [blMaterial.raytrace_mirror.reflect_factor \
                                                      ,blMaterial.raytrace_mirror.reflect_factor \
                                                      ,blMaterial.raytrace_mirror.reflect_factor]
                        Util.debug(None, "    Reflection: %r" % currentMaterial.reflection)
                    
                    if blMaterial.use_transparency:
                        currentMaterial.opacity = blMaterial.alpha
                        Util.debug(None, "    Opacity: %r" % currentMaterial.opacity)
                        
                    if len(blMaterial.texture_slots)  > 0:
                        Util.debug(None, "    Exporting textures for material %s" % blMaterial.name)
                        materialTextures = []
    
                        for slot in blMaterial.texture_slots:
                            currentTexture = Texture()
        
                            if slot is not None:
                                Util.debug(None,"    Found texture %s. Texture coords are %s, texture type is %s" % (slot.name, slot.texture_coords , slot.texture.type) )
                            
                            if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                                if slot is not None:
                                    Util.debug(None,"    Texture type not supported, skipping" )
                                else:
                                    Util.debug(None,"    Texture slot is empty, skipping" )
                                continue

                            currentTexture.id = slot.name
                            currentTexture.filename = ( self.getCompatiblePath(slot.texture.image.filepath) )

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
                            materialTextures.append( currentTexture )
                            
                        # Adding found textures to this material
                        currentMaterial.textures = materialTextures
                    
                    # Adding this material to the full list
                    generatedMaterials.append(currentMaterial)
            else:
                raise RuntimeError("Can't export nodes without materials. Add at least one material to node '%s'." % currentObjNode.name)
            
            
        
        return generatedMaterials
        
    @profile('generateNodes')
    def generateNodes(self, context, parent=None):
        """Generates object nodes that attach mesh parts, materials and bones together"""
        generatedNodes = []
        
        Util.debug(None, "Generating nodes")
        
        listOfBlenderObjects = None
        
        if parent == None:
            listOfBlenderObjects = bpy.data.objects
        elif parent.type == 'MESH':
            listOfBlenderObjects = parent.children
        elif parent.type == 'ARMATURE':
            listOfBlenderObjects = parent.data.bones
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
            
            Util.debug(None, "Exporting node %s" % blNode.name)
            
            currentNode = Node()
            
            if isinstance(blNode, bpy.types.Bone):
                currentNode.id = ("%s__%s" % (parent.name , blNode.name))
            else:
                currentNode.id = blNode.name
            
            location = [0.0,0.0,0.0]
            rotationQuaternion = [1.0,0.0,0.0,0.0]
            scale = [1.0,1.0,1.0]
            
            try:
                transformMatrix = None
                
                if isinstance(blNode, bpy.types.Bone):
                    transformMatrix = self.getTransformFromBone(blNode)
                elif blNode.parent != None:
                    if (parent==None and blNode.parent.type == 'ARMATURE') \
                            or (parent != None):
                        # Exporting a child node, so we get the local transform matrix.
                        # Obs: when exporting root mesh nodes parented to armatures, we consider it
                        # 'child' in relation to the armature so we get it's local transform, but the mesh node
                        # is still considered a root node.
                        transformMatrix = blNode.matrix_local
                    elif parent==None and blNode.parent.type == 'MESH':
                        # If this node is parented and we didn't pass a 'parent' parameter then we are only
                        # exporting root nodes at this time and we'll ignore this node.
                        continue
                else:
                    # Exporting a root node, we get it's transform matrix from the world transform matrix
                    transformMatrix = blNode.matrix_world
                    
                location, rotationQuaternion, scale = transformMatrix.decompose()
                Util.debug(None,"Node transform is %s" % str(transformMatrix))
                Util.debug(None,"Decomposed node transform is %s" % str(transformMatrix.decompose()))
            except:
                Util.warn(None,"Error decomposing transform for node %s" % blNode.name)
                location = [0.0,0.0,0.0]
                rotationQuaternion = [1.0,0.0,0.0,0.0]
                scale = [1.0,1.0,1.0]
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
                
                if currentBlMesh.materials == None:
                    Util.warn(None, "Ignored mesh %r, no materials found" % currentBlMesh)
                    continue
                
                for blMaterialIndex in range(0,len(currentBlMesh.materials)):
                    nodePart = NodePart()
                    
                    currentBlMeshName = currentBlMesh.name
                    nodePart.meshPartId = currentBlMeshName+"_part"+str(blMaterialIndex)
                    
                    nodePart.materialId = currentBlMesh.materials[blMaterialIndex].name
                    
                    # Maps material textures to the TEXCOORD attributes
                    for uvIndex in range(len(currentBlMesh.uv_layers)):
                        blUvLayer = currentBlMesh.uv_layers[uvIndex]
                        currentTexCoord = []
                        
                        for texIndex in range(len(currentBlMesh.materials.texture_slots)):
                            blTexSlot = currentBlMesh.materials.texture_slots[texIndex]
                            
                            if (blTexSlot is None \
                                    or blTexSlot.texture_coords != 'UV' \
                                    or blTexSlot.texture.type != 'IMAGE' \
                                    or blTexSlot.texture.__class__ is not bpy.types.ImageTexture):
                                continue
                            
                            if (blTexSlot.uv_layer == blUvLayer.name or (blTexSlot.uv_layer == "" and uvIndex == 0)):
                                currentTexCoord.append( texIndex )
                        
                        # Adding UV mappings to this node part
                        nodePart.addUVLayer(currentTexCoord)
                        
                    # Start writing bones
                    if self.exportArmature and len(blNode.vertex_groups) > 0:
                        Util.debug(None, "Writing bones for node %s" % blNode.name)
                        
                        for blVertexGroup in blNode.vertex_groups:
                            #Try to find an armature with a bone associated with this vertex group
                            if blNode.parent != None and blNode.parent.type == 'ARMATURE':
                                blArmature = blNode.parent.data
                                try:
                                    bone = blArmature.bones[blVertexGroup.name]
                                    
                                    #Referencing the bone node
                                    currentBone = Bone()
                                    currentBone.node = ("%s__%s" % (blNode.parent.name , blVertexGroup.name))
                                    
                                    boneTransformMatrix = blNode.matrix_local.inverted() * bone.matrix_local
                                    boneLocation, boneQuaternion, boneScale = boneTransformMatrix.decompose()
                                    
                                    Util.debug(None, "Appending pose bone %s with transform %s" % (blVertexGroup.name , str(boneTransformMatrix)))
                                    
                                    if not self.testDefaultTransform(boneLocation):
                                        currentBone.translation = self.convertVectorCoordinate(boneLocation)
                                    
                                    if not self.testDefaultQuaternion(boneQuaternion):
                                        currentBone.rotation = self.convertQuaternionCoordinate(boneQuaternion)
                                    
                                    if not self.testDefaultScale(boneScale):
                                        currentBone.scale = self.convertScaleCoordinate(boneScale)
                                    
                                    # Appending resulting bone to part
                                    nodePart.addBone(currentBone)
    
                                except KeyError:
                                    Util.warn(None, "Vertex group %s has no corresponding bone" % (blVertexGroup.name))
                                except:
                                    Util.debug(None, "Unexpected error exporting bone: %s" % blVertexGroup.name)
                
                    # Adding this node part to the current node
                    currentNode.addPart(nodePart)
            
            # If this node is a parent, export it's children
            if blNode.children != None and len(blNode.children) > 0:
                childNodes = self.generateNodes(context, blNode)
                currentNode.children = childNodes
            
            # Adding the current generated node to the list of nodes
            generatedNodes.append(currentNode)
            
        return generatedNodes
            
    ### UTILITY METHODS
    def getCompatiblePath(self,path):
        """Return path minus the '//' prefix, for Windows compatibility"""
        path = path.replace('\\', '/')
        return path[2:] if path[:2] in {"//", b"//"} else path
    
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
        
    def convertVectorCoordinate(self, co):
        """
        Converts Blender axis (Z-up) to the destination axis (usually Z-forward Y-up)
        
        Destination axis is defined on 'self.vector3AxisMapper' and 'self.vector4AxisMapper' attributes. 
        """
        
        newCo = [ (co[ self.vector3AxisMapper["x"]["coPos"] ] * self.vector3AxisMapper["x"]["sign"]) \
                 , (co[ self.vector3AxisMapper["y"]["coPos"] ] * self.vector3AxisMapper["y"]["sign"]) \
                 , (co[ self.vector3AxisMapper["z"]["coPos"] ] * self.vector3AxisMapper["z"]["sign"]) ]
        
        Util.debug(None, "|=[Converting coordinates from [%s, %s, %s] to [%s, %s, %s]]=|" \
                   % (Util.floatToString(None, co[0]),Util.floatToString(None, co[1]),Util.floatToString(None, co[2]) \
                      , Util.floatToString(None, newCo[0]), Util.floatToString(None, newCo[1]), Util.floatToString(None, newCo[2])))
        
        return newCo
    
    def convertQuaternionCoordinate(self, co):
        """
        Converts quaternions from Blender axis (Z-up) to the destination axis (usually Z-forward Y-up)
        
        Destination axis is defined on 'self.vector3AxisMapper' and 'self.vector4AxisMapper' attributes. 
        """
        
        newCo = [ (co[ self.vector4AxisMapper["x"]["coPos"] ] * self.vector4AxisMapper["x"]["sign"]) \
                 , (co[ self.vector4AxisMapper["y"]["coPos"] ] * self.vector4AxisMapper["y"]["sign"]) \
                 , (co[ self.vector4AxisMapper["z"]["coPos"] ] * self.vector4AxisMapper["z"]["sign"]) \
                 , (co[ self.vector4AxisMapper["w"]["coPos"] ] * self.vector4AxisMapper["w"]["sign"]) ]
        
        Util.debug(None, "|=[Converting quaternion from format [w, x, y, z] [%s, %s, %s, %s] to format [x, y, z, w] [%s, %s, %s, %s]]=|" \
                   % (Util.floatToString(None, co[0]),Util.floatToString(None, co[1]),Util.floatToString(None, co[2]),Util.floatToString(None, co[3]) \
                      , Util.floatToString(None, newCo[0]), Util.floatToString(None, newCo[1]), Util.floatToString(None, newCo[2]), Util.floatToString(None, newCo[3])))
        
        return newCo
    
    def convertScaleCoordinate(self, co):
        """
        Converts Blender axis (Z-up) to the destination axis (usually Z-forward Y-up)
        
        For scaling the range is 0.0 to 1.0 so we ignore sign and just adjust axis 
        """
        
        newCo = [ co[ self.vector3AxisMapper["x"]["coPos"] ] \
                 , co[ self.vector3AxisMapper["y"]["coPos"] ] \
                 , co[ self.vector3AxisMapper["z"]["coPos"] ] ]
        
        Util.debug(None, "|=[Converting scaling coordinates from [%s, %s, %s] to [%s, %s, %s]]=|" \
                   % (Util.floatToString(None, co[0]),Util.floatToString(None, co[1]),Util.floatToString(None, co[2]) \
                      , Util.floatToString(None, newCo[0]), Util.floatToString(None, newCo[1]), Util.floatToString(None, newCo[2])))
        
        return newCo
    
    def getTransformFromBone(self, bone):
        """Create a transform matrix based on the relative rest position of a bone"""
        transformMatrix = None
            
        if bone.parent == None:
            transformMatrix = bone.matrix_local
        else:
            transformMatrix = bone.parent.matrix_local.inverted() * bone.matrix_local
        
        return transformMatrix

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
                