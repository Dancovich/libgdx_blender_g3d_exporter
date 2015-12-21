from io_scene_g3d.vertex import Vertex
from io_scene_g3d.mesh_part import MeshPart

class Mesh(object):
    
    _id = ""
    
    _vertices = []
    
    _parts = []
    
    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self,meshId):
        self._id = meshId
    
    def addVertex(self,vertex):
        """
        Adds a vertex if it has not been added before.
        A vertex is considered 'already added' if all it's vertex
        attributes have the same value.
        
        Returns the added vertex if it's new or a pointer
        to the already present vertex if there is one.  
        """
        
        if vertex == None or not isinstance(vertex, Vertex):
            raise TypeError("'vertex' must be of type Vertex")
        
        alreadyAdded = False
        foundVertex = None
        
        for vtx in self._vertices:
            if vtx.compare(vertex):
                alreadyAdded = True
                foundVertex = vtx
                break
            
        if not alreadyAdded:
            self._vertices.append(vertex)
            return vertex
        else:
            return foundVertex
            
    def addPart(self, meshPart):
        if meshPart == None or not isinstance(meshPart, MeshPart):
            raise TypeError("'meshPart' must be of type MeshPart")
        
        self._parts.append(meshPart)
        
    def __repr__(self):
        value = "VERTICES:\n%r" % self._vertices
        
        return value