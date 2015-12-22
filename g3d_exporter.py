import bpy
import mathutils
from bpy_extras.io_utils import ExportHelper

from io_scene_g3d.util import Util
from io_scene_g3d.util import ROUND_STRING
from io_scene_g3d.g3d_model import G3DModel
from io_scene_g3d.mesh import Mesh
from io_scene_g3d.mesh_part import MeshPart
from io_scene_g3d.vertex import Vertex
from io_scene_g3d.vertex_attribute import VertexAttribute


from bpy.props import BoolProperty

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
    
    
    bonesPerVertex = 4
    
    exportArmature = True
    
    exportAnimation = True
    
    generateTangentBinormal = True
    
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
        self.generateMeshes(context)
        
        # Export the nodes
        
        return result
    
    
    def generateMeshes(self, context):
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or (self.useSelection and not obj.select):
                continue
            
            # If we already processed the mesh data associated with this object, continue (ex: multiple objects pointing to same mesh data)
            if self.g3dModel.hasMesh(obj.data.name):
                Util.debug(None, "Skipping mesh for node %s (already exported from another node)" % obj.name)
                continue
            
            Util.debug(None, "Writing mesh from node %s" % obj.name)
            
            # This is the mesh object we are generating
            generatedMesh = Mesh()
            currentBlMeshName = obj.data.name
            generatedMesh.id = currentBlMeshName
            
            # Clone mesh to a temporary object. Wel'll apply modifiers and triangulate the
            # clone before exporting.
            currentBlMesh = obj.to_mesh(context.scene , False, 'PREVIEW', calc_tessface=False)
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
                            self.warn("    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
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
                                    self.warn("    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                                    
                                binormal = [None] * 3
                                binormal[0], binormal[1], binormal[2] = blLoop.bitangent
                                attribute = VertexAttribute(name=VertexAttribute.BINORMAL,value=self.convertVector3Coordinate(binormal) )
                                
                                if not currentVertex.add(attribute):
                                    self.warn("    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                                    
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
                            self.warn("    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                        ############
                        
                        ############
                        # Defining vertex color
                        colorMap = currentBlMesh.vertex_colors.active
                        if colorMap != None:
                            color = [None] * 3
                            color[0], color[1], color[2] = colorMap.data[loopIndex].color
                            color = Util.roundLists(None, color)
                            
                            attribute = VertexAttribute(name=VertexAttribute.COLOR, value=color)
                            
                            if not currentVertex.add(attribute):
                                self.warn("    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                            
                        ############
                        
                        ############
                        # Exporting UV coordinates
                        if currentBlMesh.uv_layers != None and len(currentBlMesh.uv_layers) > 0:
                            texCoordCount = 0
                            for uv in currentBlMesh.uv_layers:
                                # We need to flip UV's because Blender use bottom-left as Y=0 and G3D use top-left
                                flippedUV = [ uv.data[ loopIndex ].uv[0] , 1.0 - uv.data[ loopIndex ].uv[1] ]
                                
                                texCoordAttrName = VertexAttribute.TEXCOORD + str(texCoordCount)
                                attribute = VertexAttribute(texCoordAttrName, Util.roundLists(None, flippedUV))
                                
                                
                                texCoordCount = texCoordCount + 1
                                
                                if not currentVertex.add(attribute):
                                    self.warn("    Duplicate attribute found in vertex %d (%r), ignoring..." % (id(currentVertex),attribute))
                        ############
                            
                        
                        currentVertex = generatedMesh.addVertex(currentVertex)
                        
                        Util.debug(None, "Adding vertex (obj id %d) on material %d to mesh part (obj id %d)" % (id(currentVertex),blMaterialIndex,id(currentMeshPart)))
                        currentMeshPart.addVertex(currentVertex)
                
                # Add current part to final mesh
                generatedMesh.addPart(currentMeshPart)
                    
            # Clean cloned mesh
            bpy.data.meshes.remove(currentBlMesh)
            
            Util.debug(None, "==== GENERATED MESH IS \n %s" % generatedMesh)
                    
                    
            
            
    ### UTILITY METHODS
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
        
        newCo = [None] * 3
        
        valX = float(ROUND_STRING % (co[ self.vector3AxisMapper["x"]["coPos"] ] * self.vector3AxisMapper["x"]["sign"]))
        valY = float(ROUND_STRING % (co[ self.vector3AxisMapper["y"]["coPos"] ] * self.vector3AxisMapper["y"]["sign"]))
        valZ = float(ROUND_STRING % (co[ self.vector3AxisMapper["z"]["coPos"] ] * self.vector3AxisMapper["z"]["sign"]))
        
        newCo[0] = valX
        newCo[1] = valY
        newCo[2] = valZ
        
        Util.debug(None, "|=[Converting coordinates from [%s, %s, %s] to [%s, %s, %s]]=|" \
                   % (ROUND_STRING % co[0],ROUND_STRING % co[1],ROUND_STRING % co[2] \
                      , ROUND_STRING % valX, ROUND_STRING % valY, ROUND_STRING % valZ))
        
        return newCo