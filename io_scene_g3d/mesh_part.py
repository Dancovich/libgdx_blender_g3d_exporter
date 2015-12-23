import io_scene_g3d.mesh
from io_scene_g3d.vertex import Vertex
from io_scene_g3d.util import Util

class MeshPart(object):
    """Represents a mesh part"""

    _id = ""
    
    _type = "TRIANGLES"
    
    _vertices = None
    
    _parentMesh = None
    
    def __init__(self, meshPartId="", meshType="TRIANGLES", vertices=None, parentMesh=None):
        self._id = meshPartId
        self._type = meshType
        self._vertices = vertices
        self._parentMesh = parentMesh

    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, partId):
        self._id = partId
        
    @property
    def type(self):
        return self._type
    
    @type.setter
    def type(self, partType):
        self._type = partType
        
    @property
    def parentMesh(self):
        return self._parentMesh
    
    @parentMesh.setter
    def parentMesh(self, parentMesh):
        if parentMesh == None or not isinstance(parentMesh, io_scene_g3d.mesh.Mesh):
            raise TypeError("'parentMesh' must be of type Mesh")

        self._parentMesh = parentMesh
        
    def addVertex(self, vertex):
        if vertex == None or not isinstance(vertex, Vertex):
            raise TypeError("'vertex' must be of type Vertex")
        
        if self._vertices == None:
            self._vertices = []
        
        self._vertices.append(vertex)
    
    def __repr__(self):
        reprStr = "{\n    ID: %s\n    TYPE: %s\n" % (self.id,self.type)
        
        if self.parentMesh != None:
            reprStr = reprStr + ("    INDICES (total of %d): [" % len(self._vertices))
            
            firstTime = True
            for ver in self._vertices:
                index = -1
                try:
                    index = self.parentMesh.vertices.index(ver)
                except:
                    Util.warn(None, "Vertex [%r] (obj id: %d) in part %s is not in mesh vertex list" % (ver,id(ver),self._id))
                    Util.warn(None, "All mesh vertices below:")
                    
                    for meshVer in self.parentMesh.vertices:
                        Util.warn(None,"   Found vertex with obj id %d in mesh" % id(meshVer))
                    
                    index = -1
                
                if firstTime:
                    reprStr = reprStr + " "
                    firstTime = False
                else:
                    reprStr = reprStr + ", "
                reprStr = reprStr + ("%d" % index)
            
            reprStr = reprStr + " ]\n"
        
        reprStr = reprStr + "}\n"
        
        return reprStr