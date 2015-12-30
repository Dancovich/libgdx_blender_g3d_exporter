from io_scene_g3d.vertex import Vertex
from io_scene_g3d.mesh_part import MeshPart

class Mesh(object):
    
    _id = ""
    
    _vertices = []
    
    _parts = []
    
    # This is a cache so we know all attributes this mesh has.
    # All the real attributes are in the vertices
    _attributes = []
    
    def __init__(self):
        self._id = ""
        self._vertices = []
        self._parts = []
    
    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self,meshId):
        self._id = meshId
        
    @property
    def vertices(self):
        return self._vertices
    
    def getAttributes(self):
        return self._attributes
    
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
            
            # Add this vertice's attributes to the attribute name cache
            for attr in vertex.attributes:
                if not attr.name in self._attributes:
                    self._attributes.append(attr.name)
            
            return vertex
        else:
            return foundVertex
            
    def addPart(self, meshPart):
        if meshPart == None or not isinstance(meshPart, MeshPart):
            raise TypeError("'meshPart' must be of type MeshPart")
        
        self._parts.append(meshPart)
        meshPart.parentMesh = self
        
    def __repr__(self):
        value = "VERTICES:\n%r\n\nPARTS:\n%r\n\n" % (self._vertices, self._parts)
        return value