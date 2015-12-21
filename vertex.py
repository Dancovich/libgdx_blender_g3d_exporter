from io_scene_g3d.vertex_attribute import VertexAttribute

class Vertex(object):
    """Define a mesh vertex"""
    
    _index = 0
    
    _attributes = []
    
    @property
    def index(self):
        return self._index
    
    @index.setter
    def index(self, index):
        self._index = index
    
    def add(self, attribute):
        if attribute == None or not isinstance(attribute, VertexAttribute):
            raise TypeError("'attribute' must be a VertexAttribute")
        
        alreadyAdded = False
        for attr in self._attributes:
            if attr.compare(attribute):
                alreadyAdded = True
                break
            
        if not alreadyAdded:
            self._attributes.append(attribute)
        
    @property
    def attributes(self):
        return self._attributes
    
    def compare(self, another):
        if another == None or not isinstance(another, Vertex):
            raise TypeError("'another' must be a Vertex")
        
        totalAttributes = self._attributes.__len__()
        comparison = totalAttributes == another._attributes.__len__()
        if (comparison):
            equalAttributes = 0
            for attr in self._attributes:
                for attr2 in another._attributes:
                    if attr.compare(attr2):
                        equalAttributes = equalAttributes + 1
        
        return comparison and equalAttributes == totalAttributes
    
    def __repr__(self):
        reprStr = "{\nid = %d\n" % self._index
        for attr in self._attributes:
            reprStr = reprStr + ("    %s [%r]\n" % (attr.name(), attr.value()))
        
        reprStr = reprStr + "}"
        
        return reprStr
        