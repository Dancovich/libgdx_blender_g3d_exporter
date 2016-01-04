import bpy
import mathutils

from bpy_extras.io_utils import ExportHelper, orientation_helper_factory

from io_scene_g3d.util import Util
from io_scene_g3d.domain_classes import G3DModel \
    , Mesh \
    , MeshPart \
    , Vertex \
    , VertexAttribute \
    , Node \
    , NodePart \
    , Bone \
    , Material \
    , Texture \
    , Animation \
    , NodeAnimation \
    , Keyframe \

from io_scene_g3d.profile import profile, print_stats
from io_scene_g3d.g3dj_exporter import G3DJExporter


from bpy.props import BoolProperty, IntProperty, EnumProperty

IOG3DOrientationHelper = orientation_helper_factory("IOG3DOrientationHelper", axis_forward='-Z', axis_up='Y')

class G3DExporter(bpy.types.Operator, ExportHelper, IOG3DOrientationHelper):
    """Export scene to G3D (LibGDX) format"""
    
    bl_idname     = "export_json_g3d.g3d"
    bl_label      = "G3D Exporter"
    bl_options    = {'PRESET'}
    
    filename_ext    = ".g3d"
    
    # This is our model
    g3dModel = None
    
    # Exporter options
    fileFormat = EnumProperty(
            name="File Format",
            items=(('G3DJ', "Text Format (G3DJ)", "3D Model exported as text in the JSON format"),
                   ('G3DB', "Binary Format (G3DB)", "3D Model exported as a binary file")),
            default='G3DJ',
            )
    
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
            default=4, \
            soft_min=1, soft_max=8 \
            )
    
    exportAnimation = BoolProperty( \
            name="Export Actions as Animations", \
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
    
    # Constants
    P_LOCATION = 'location'
    P_ROTATION = 'rotation_quaternion'
    P_SCALE    = 'scale'
    
    
    def execute(self, context):
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
        self.g3dModel.meshes = self.generateMeshes(context)
        
        # Generate the materials used in the model
        self.g3dModel.materials = self.generateMaterials(context)
        
        # Generate the nodes binding mesh parts, materials and bones
        self.g3dModel.nodes = self.generateNodes(context)
        
        # Convert action curves to animations
        self.g3dModel.animations = self.generateAnimations(context)
        
        # Export to the final file
        exporter = G3DJExporter()
        exporter.export(self.g3dModel)
        
        # Clean up after export
        self.g3dModel = None
        
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
                                boneIndex = -1
                                blendWeightIndex = 0

                                for vertexGroupIndex in range(0, len(currentObjNode.vertex_groups)):
                                    vertexGroup = currentObjNode.vertex_groups[vertexGroupIndex]
                                    
                                    # We can only export this ammount of bones per vertex
                                    if blendWeightIndex >= self.bonesPerVertex:
                                        break
                                    
                                    # Search for a bone with the same name as a vertex group
                                    bone = None
                                    try:
                                        Util.debug(None, "        Looking for bone with name %s" % vertexGroup.name)
                                        bone = armatureObj.data.bones[vertexGroup.name]
                                    except:
                                        bone = None
                                        pass
                                    
                                    if bone != None:
                                        Util.debug(None, "        Found bone %s" % vertexGroup.name)
                                        boneIndex = boneIndex + 1
                                        
                                        try:
                                            # We get the weight associated with this vertex group. Zeros are ignored
                                            boneWeight = vertexGroup.weight(blLoop.vertex_index)
                                            
                                            Util.debug(None, "        Bone weight for vertex %d in group %s is %f" % (blLoop.vertex_index,vertexGroup.name,vertexGroup.weight(blLoop.vertex_index)))

                                            if Util.floatToString(None, boneWeight) != zeroWeight:
                                                blendWeightValue = [float(boneIndex), boneWeight]
                                                attribute = VertexAttribute((blendWeightAttrName % blendWeightIndex), blendWeightValue)
                                                
                                                if not currentVertex.add(attribute):
                                                    Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                                                else:
                                                    blendWeightIndex = blendWeightIndex + 1

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
            
            # Normalize attributes so mesh has same number of them for all vertices
            generatedMesh.normalizeAttributes()
            
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
    def generateNodes(self, context, parent=None, parentName=""):
        """Generates object nodes that attach mesh parts, materials and bones together"""
        generatedNodes = []
        
        Util.debug(None, "Generating nodes")
        
        listOfBlenderObjects = None
        
        if parent == None:
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
                if parent != None and not isinstance(parent, bpy.types.Bone) and parent.type == 'ARMATURE':
                    if blNode.parent != None:
                        continue
            
            Util.debug(None, "Exporting node %s" % blNode.name)
            
            currentNode = Node()
            
            if isinstance(blNode, bpy.types.Bone):
                currentNode.id = ("%s__%s" % (parentName , blNode.name))
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
                        
                        for texIndex in range(len(currentBlMesh.materials[blMaterialIndex].texture_slots)):
                            blTexSlot = currentBlMesh.materials[blMaterialIndex].texture_slots[texIndex]
                            
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
                                    pass
                                except:
                                    Util.error(None, "Unexpected error exporting bone: %s" % blVertexGroup.name)
                                    pass
                
                    # Adding this node part to the current node
                    currentNode.addPart(nodePart)
            
            # If this node is a parent, export it's children
            if blNode.children != None and len(blNode.children) > 0:
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
                
                Util.debug(None,"Writing animation for action %s" % blAction.name)
                
                currentAnimation = Animation()
                
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
                        currentBone.boneId = ("%s__%s" % (blArmature.name , blBone.name))
                        
                        translationFCurve = self.findFCurve(blAction, blBone, self.P_LOCATION)
                        rotationFCurve = self.findFCurve(blAction, blBone, self.P_ROTATION)
                        scaleFCurve = self.findFCurve(blAction, blBone, self.P_SCALE)
                        
                        # Rest transform of this bone, used as reference to calculate frames
                        restTransform = self.getTransformFromBone(blBone)
                        
                        frameStart = context.scene.frame_start
                        for currentFrameNumber in range(int(blAction.frame_range[0]) , int(blAction.frame_range[1]+1)):
                            currentKeyframe = Keyframe()
                            
                            translationVector = [0.0] * 3
                            rotationVector = [0.0] * 4
                            rotationVector[0] = 1.0
                            scaleVector = [1.0] * 3
                            
                            if translationFCurve != None and translationFCurve != ( [None] * 3 ) and self.mustEvaluateKeyframe(translationFCurve, float(currentFrameNumber)):
                                if translationFCurve[0] != None:
                                    translationVector[0] = translationFCurve[0].evaluate(currentFrameNumber)
                                if translationFCurve[1] != None:
                                    translationVector[1] = translationFCurve[1].evaluate(currentFrameNumber)
                                if translationFCurve[2] != None:
                                    translationVector[2] = translationFCurve[2].evaluate(currentFrameNumber)
                                    
                            if rotationFCurve != None and rotationFCurve != ( [None] * 4 )  and self.mustEvaluateKeyframe(rotationFCurve, float(currentFrameNumber)):
                                if rotationFCurve[0] != None:
                                    rotationVector[0] = rotationFCurve[0].evaluate(currentFrameNumber)
                                if rotationFCurve[1] != None:
                                    rotationVector[1] = rotationFCurve[1].evaluate(currentFrameNumber)
                                if rotationFCurve[2] != None:
                                    rotationVector[2] = rotationFCurve[2].evaluate(currentFrameNumber)
                                if rotationFCurve[3] != None:
                                    rotationVector[3] = rotationFCurve[3].evaluate(currentFrameNumber)
                            
                            if scaleFCurve != None and scaleFCurve != ( [None] * 3 )  and self.mustEvaluateKeyframe(scaleFCurve, float(currentFrameNumber)):
                                if scaleFCurve[0] != None:
                                    scaleVector[0] = scaleFCurve[0].evaluate(currentFrameNumber)
                                if scaleFCurve[1] != None:
                                    scaleVector[1] = scaleFCurve[1].evaluate(currentFrameNumber)
                                if scaleFCurve[2] != None:
                                    scaleVector[2] = scaleFCurve[2].evaluate(currentFrameNumber)
                                    
                            poseTransform = self.createTransformMatrix(translationVector, rotationVector, scaleVector)
                            translationVector, rotationVector, scaleVector = (restTransform * poseTransform).decompose()
                            
                            currentKeyframe.translation = list(translationVector)
                            currentKeyframe.rotation = list(rotationVector)
                            currentKeyframe.scale = list(scaleVector)
                                
                            # If we have at least one attribute changed in that currentFrameNumber, we store it
                            if currentKeyframe.translation != None \
                                    or currentKeyframe.rotation != None \
                                    or currentKeyframe.scale != None:
                                currentKeyframe.keytime = (currentFrameNumber - frameStart) * frameTime
                                currentBone.addKeyframe(currentKeyframe)
                                
                        # If there is at least one currentFrameNumber for this bone, add it's data
                        if currentBone.keyframes != None and len(currentBone.keyframes) > 0:
                            # We operated with Blender coordinates the entire time, now we convert
                            # to the target coordinates
                            for currentFrameNumber in currentBone.keyframes:
                                if currentFrameNumber.translation != None:
                                    currentFrameNumber.translation = self.convertVectorCoordinate(currentFrameNumber.translation)
                                
                                if currentFrameNumber.rotation != None:
                                    currentFrameNumber.rotation = self.convertQuaternionCoordinate(currentFrameNumber.rotation)
                                    
                                if currentFrameNumber.scale != None:
                                    currentFrameNumber.scale = self.convertScaleCoordinate(currentFrameNumber.scale)
                            
                            # Finally add bone node to animation
                            currentAnimation.addBone(currentBone)
                
                # If this action animates at least one bone, add it to the list of actions
                if currentAnimation.bones != None and len(currentAnimation.bones) > 0:
                    generatedAnimations.append(currentAnimation)

        # Finally return the generated animations
        return generatedAnimations
            
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
    
    def findFCurve(self, action , bone , prop):
        """
        Find a fcurve for the given action, bone and property. Returns an array with as many fcurves
        as there are indices in the property.
        Ex: The returned value for the location property will have 3 fcurves, one for each of the X, Y and Z coordinates
        """
        
        returnedFCurves = None
        
        dataPath = ("pose.bones[\"%s\"].%s" % (bone.name , prop))
        if prop == self.P_LOCATION:
            returnedFCurves = [None , None , None]
        elif prop == self.P_ROTATION:
            returnedFCurves = [None , None , None, None]
        elif prop == self.P_SCALE:
            returnedFCurves = [None , None , None]
        else:
            self.error("FCurve Property not supported")
            raise Exception("FCurve Property not supported")

        for fcurve in action.fcurves:
            if fcurve.data_path == dataPath:
                returnedFCurves[fcurve.array_index] = fcurve

        return returnedFCurves
    
    def mustEvaluateKeyframe(self, fCurves, frame):
        """
        Returns True if you should evaluate the coordinates for this frame on this curve
        """
        isKeyframe = False
        hasNonLinearCurve= False
        
        if fCurves != None:
            for curve in fCurves:
                if curve != None:
                    selectedKeyframe = None
                    
                    for keyframe in curve.keyframe_points:
                        if keyframe.co[0] <= frame and (selectedKeyframe==None or keyframe.co[0] > selectedKeyframe.co[0]):
                            selectedKeyframe = keyframe
                            
                    if selectedKeyframe != None:
                        if selectedKeyframe.co[0] == frame:
                            isKeyframe = True
                            break
                        elif selectedKeyframe.interpolation != "LINEAR":
                            hasNonLinearCurve = True
                            break
                        
        return isKeyframe or hasNonLinearCurve
                        
                    
        
    
    def createTransformMatrix(self , locationVector , quaternionVector, scaleVector):
        """Create a transform matrix from a location vector, a rotation quaternion and a scale vector"""
        
        if isinstance(quaternionVector, mathutils.Quaternion):
            quat = quaternionVector.normalized()
        else:
            quat = mathutils.Quaternion(quaternionVector).normalized()
            
        translationMatrix = mathutils.Matrix(( (0,0,0,locationVector[0]) \
                                     , (0,0,0,locationVector[1]) \
                                     , (0,0,0,locationVector[2]) \
                                     , (0,0,0,0) ))
        
        rotationMatrix = quat.to_matrix().to_4x4()
        
        scaleMatrix = mathutils.Matrix(( (scaleVector[0],0,0,0) \
                                     , (0,scaleVector[1],0,0) \
                                     , (0,0,scaleVector[2],0) \
                                     , (0,0,0,1) ))
        
        matrix = (rotationMatrix * scaleMatrix) + translationMatrix
        
        Util.debug(None, "Creating matrix from location, rotation and scale")
        Util.debug(None, "INPUT: Location = %s; Quaternion = %s; Scale = %s" % (str(locationVector), str(quat), str(scaleVector)))
        Util.debug(None, "OUTPUT: %s" % str(matrix))
        
        return matrix
    
    def compareVector(self,v1,v2):
        a1 = [ Util.floatToString(self, v1[0]) , Util.floatToString(self, v1[1]) , Util.floatToString(self, v1[2]) ]
        a2 = [ Util.floatToString(self, v2[0]) , Util.floatToString(self, v2[1]) , Util.floatToString(self, v2[2]) ]
        return a1 == a2
    
    def compareQuaternion(self,q1,q2):
        a1 = [ Util.floatToString(self, q1[0]) , Util.floatToString(self, q1[1]) , Util.floatToString(self, q1[2]) , Util.floatToString(self, q1[3]) ]
        a2 = [ Util.floatToString(self, q2[0]) , Util.floatToString(self, q2[1]) , Util.floatToString(self, q2[2]) , Util.floatToString(self, q2[3]) ]
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
        Util.debug(None, "Converting axis using forward as '%s' and up as '%s'" % (axisForward, axisUp))
        
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
        
        Util.debug(None, "Axis conversion configuration for vectors is {%r}" % self.vector3AxisMapper)
        Util.debug(None, "Axis conversion configuration for quaternions is {%r}" % self.vector4AxisMapper)