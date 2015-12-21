from io_scene_g3d.vertex import Vertex

class MeshPart(object):
    """Represents a mesh part"""
    
    _id = ""
    
    _type = "TRIANGLES"
    
    _vertices = []
    
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
        
    def addVertex(self, vertex):
        if vertex == None or not isinstance(vertex, Vertex):
            raise TypeError("'vertex' must be of type Vertex")
        
        self._vertices.append(vertex)