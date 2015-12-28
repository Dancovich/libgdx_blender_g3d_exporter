import bpy
from bpy_extras.io_utils import ExportHelper

from io_scene_g3d.util import Util
from io_scene_g3d.g3d_model import G3DModel
from io_scene_g3d.mesh import Mesh
from io_scene_g3d.mesh_part import MeshPart
from io_scene_g3d.vertex import Vertex
from io_scene_g3d.vertex_attribute import VertexAttribute
from io_scene_g3d.material import Material
from io_scene_g3d.texture import Texture


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
        
        # Export the nodes
        # TODO Do the export
        
        return result
    
    
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
            
            #currentUVLayer = currentBlMesh.uv_layers[0].data
            #currentBlMesh.calc_tangents(currentBlMesh.uv_layers[0].name)
            
            if currentBlMesh.materials != None:
                for mat in currentBlMesh.materials:
                    Util.debug(None, "Found this material in mesh: %r" % mat)
            
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
                                                    self.convertVector3Coordinate( blVertex.co ))
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
                                attribute = VertexAttribute(name=VertexAttribute.TANGENT,value=self.convertVector3Coordinate(tangent) )
                                
                                if not currentVertex.add(attribute):
                                    Util.warn(None,"    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                                    
                                binormal = [None] * 3
                                binormal[0], binormal[1], binormal[2] = blLoop.bitangent
                                attribute = VertexAttribute(name=VertexAttribute.BINORMAL,value=self.convertVector3Coordinate(binormal) )
                                
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
                            attribute.value = self.convertVector3Coordinate(splitNormalValue)
                        elif poly.use_smooth:
                            Util.debug(None, "    Uses smooth shading: True")
                            attribute.value = self.convertVector3Coordinate(blVertex.normal)
                        else:
                            Util.debug(None, "    Uses smooth shading: False")
                            attribute.value = self.convertVector3Coordinate(poly.normal)
                            
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
                    
                    currentMaterial.ambient = [blMaterial.ambient, blMaterial.ambient, blMaterial.ambient, 1.0]
                    
                    currentMaterial.diffuse = [blMaterial.diffuse_color[0] \
                                                    ,blMaterial.diffuse_color[1] \
                                                    ,blMaterial.diffuse_color[2]]
                    
                    currentMaterial.specular = [blMaterial.specular_color[0] * blMaterial.specular_intensity \
                                                    ,blMaterial.specular_color[1] * blMaterial.specular_intensity \
                                                    ,blMaterial.specular_color[2] * blMaterial.specular_intensity \
                                                    ,blMaterial.specular_alpha]
                    
                    currentMaterial.emissive = [blMaterial.emit\
                                                    , blMaterial.emit\
                                                    , blMaterial.emit]
                    
                    currentMaterial.shininess = blMaterial.specular_hardness
                    
                    if blMaterial.raytrace_mirror.use:
                        currentMaterial.reflection = [blMaterial.raytrace_mirror.reflect_factor \
                                                      ,blMaterial.raytrace_mirror.reflect_factor \
                                                      ,blMaterial.raytrace_mirror.reflect_factor]
                    
                    if blMaterial.use_transparency:
                        currentMaterial.opacity = blMaterial.alpha
                        
                    if len(blMaterial.texture_slots)  > 0:
                        Util.debug(None, "Exporting textures for material %s" % blMaterial.name)
                        materialTextures = []
    
                        for slot in blMaterial.texture_slots:
                            currentTexture = Texture()
        
                            if slot is not None:
                                Util.debug(None,"Found texture %s. Texture coords are %s, texture type is %s" % (slot.name, slot.texture_coords , slot.texture.type) )
                            
                            if (slot is None or slot.texture_coords != 'UV' or slot.texture.type != 'IMAGE' or slot.texture.__class__ is not bpy.types.ImageTexture):
                                if slot is not None:
                                    Util.debug(None,"Texture type not supported, skipping" )
                                else:
                                    Util.debug(None,"Texture slot is empty, skipping" )
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
        
    def convertVector3Coordinate(self, co):
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