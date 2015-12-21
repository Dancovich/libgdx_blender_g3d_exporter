import bpy
from bpy_extras.io_utils import ExportHelper
from io_scene_g3d.g3d_model import G3DModel
from io_scene_g3d.mesh import Mesh
from io_scene_g3d.mesh_part import MeshPart
from io_scene_g3d.vertex import Vertex
from io_scene_g3d.vertex_attribute import VertexAttribute
from bpy.props import BoolProperty

_DEBUG_ = 3
_WARN_ = 2
_ERROR_ = 1

#LOG_LEVEL = _WARN_
LOG_LEVEL = _DEBUG_

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
    
    vector3AxisMapper = {}
    
    vector4AxisMapper = {}
    
    
    def execute(self, context):
        """Main method run by Blender to export a G3D file"""
        
        # Defines our mapping from Blender Z-Up to whatever the user selected
        self.vector3AxisMapper["x"] = {}
        self.vector3AxisMapper["x"]["axis"] = "x"
        self.vector3AxisMapper["x"]["coPos"] = 0
        self.vector3AxisMapper["x"]["sign"] = 1
        
        self.vector3AxisMapper["y"] = {}
        self.vector3AxisMapper["y"]["axis"] = "z"
        self.vector3AxisMapper["y"]["coPos"] = 2
        self.vector3AxisMapper["y"]["sign"] = -1
        
        self.vector3AxisMapper["z"] = {}
        self.vector3AxisMapper["z"]["axis"] = "y"
        self.vector3AxisMapper["z"]["coPos"] = 1
        self.vector3AxisMapper["z"]["sign"] = 1
        
        self.vector4AxisMapper["x"] = {}
        self.vector4AxisMapper["x"]["axis"] = "x"
        self.vector4AxisMapper["x"]["coPos"] = 1
        self.vector4AxisMapper["x"]["sign"] = 1
        
        self.vector4AxisMapper["y"] = {}
        self.vector4AxisMapper["y"]["axis"] = "z"
        self.vector4AxisMapper["y"]["coPos"] = 3
        self.vector4AxisMapper["y"]["sign"] = -1
        
        self.vector4AxisMapper["z"] = {}
        self.vector4AxisMapper["z"]["axis"] = "y"
        self.vector4AxisMapper["z"]["coPos"] = 2
        self.vector4AxisMapper["z"]["sign"] = 1
        
        self.vector4AxisMapper["w"] = {}
        self.vector4AxisMapper["w"]["axis"] = "w"
        self.vector4AxisMapper["w"]["coPos"] = 0
        self.vector4AxisMapper["w"]["sign"] = 1
        
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
                self.debug("Skipping mesh for node %s (already exported from another node)" % obj.name)
                continue
            
            self.debug("Writing mesh from node %s" % obj.name)
            
            # This is the mesh object we are generating
            generatedMesh = Mesh()
            
            # Clone mesh to a temporary object. Wel'll apply modifiers and triangulate the
            # clone before exporting.
            currentBlMesh = obj.to_mesh(context.scene , False, 'PREVIEW', calc_tessface=False)
            self.meshTriangulate(currentBlMesh)
            
            #currentUVLayer = currentBlMesh.uv_layers[0].data
            #currentBlMesh.calc_tangents(currentBlMesh.uv_layers[0].name)
            
            if currentBlMesh.materials != None:
                for mat in currentBlMesh.materials:
                    self.debug("Found this material in mesh: %r" % mat)
            
            # We can only export polygons that are associated with a material, so we loop
            # through the list of materials for this mesh  
            
            # Loop through the polygons of this mesh
            if currentBlMesh.materials == None:
                self.warn("Ignored mesh %r, no materials found" % currentBlMesh)
                continue
            
            blMaterialIndex = 0
            for blMaterial in currentBlMesh.materials:
                
                # Fills the part here
                currentMeshPart = MeshPart()
                
                for poly in currentBlMesh.polygons:
                    if (poly.material_index != blMaterialIndex):
                        continue
                    
                    self.debug("Polygon index: %d, length: %d, material id: %d" % (poly.index, poly.loop_total, poly.material_index))
                    for loopIndex in poly.loop_indices:
                        currentVertex = Vertex()
                        
                        blVertex = currentBlMesh.vertices[currentBlMesh.loops[loopIndex].vertex_index]
                                           
                        self.debug("    Vertex Index: %d" % currentBlMesh.loops[loopIndex].vertex_index)
                        self.debug("    Vertex Coord: %r" % blVertex.co)
                        self.debug("    Normal: %r" % blVertex.normal)
                        self.debug("    Split Normal: %r" % currentBlMesh.loops[loopIndex].normal)
                        
                        # Vertex position is the minimal attribute
                        attribute = VertexAttribute(VertexAttribute.POSITION, \
                                                    self.convertVector3Coordinate( blVertex.co ))
                        currentVertex.add(attribute)
                        
                        currentVertex = generatedMesh.addVertex(currentVertex)
                        currentMeshPart.addVertex(currentVertex)
                
                # Increment material index
                blMaterialIndex = blMaterialIndex + 1
                
                # Add current part to final mesh
                generatedMesh.addPart(currentMeshPart)
                    
            # Clean cloned mesh
            bpy.data.meshes.remove(currentBlMesh)
            
            self.debug("==== GENERATED MESH IS %s" % generatedMesh)
                    
                    
            
            
    ### UTILITY METHODS
    def meshTriangulate(self, me):
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        
    def convertVector3Coordinate(self, co):
        newCo = []
        
        newCo.append(co[ self.vector3AxisMapper["x"]["coPos"] ] * self.vector3AxisMapper["x"]["sign"])
        newCo.append(co[ self.vector3AxisMapper["y"]["coPos"] ] * self.vector3AxisMapper["y"]["sign"])
        newCo.append(co[ self.vector3AxisMapper["z"]["coPos"] ] * self.vector3AxisMapper["z"]["sign"])
        
        self.debug("Converting coordinates from %r to %r" % (co, newCo))
        
        return newCo
            
    ### DEBUG METHODS ###
    
    def debug(self, message):
        if LOG_LEVEL >= _DEBUG_: print("[DEBUG] %s" % message)
    
    def warn(self, message):
        if LOG_LEVEL >= _WARN_: print("[WARN] %s" % message)

    def error(self, message):
        if LOG_LEVEL >= _ERROR_: print("[ERROR] %s" % message)