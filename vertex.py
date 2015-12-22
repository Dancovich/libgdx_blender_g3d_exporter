from io_scene_g3d.vertex_attribute import VertexAttribute

class Vertex(object):
    """Define a mesh vertex"""
    
    #_index = 0
    
    _attributes = []
    
    """
    @property
    def index(self):
        return self._index
    
    @index.setter
    def index(self, index):
        self._index = index
    """
    
    def __init__(self):
        self.attributes = []
    
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
        
        return not alreadyAdded
        
    @property
    def attributes(self):
        return self._attributes
    
    @attributes.setter
    def attributes(self, newAttributes):
        self._attributes = newAttributes
    
    def compare(self, another):
        if another == None or not isinstance(another, Vertex):
            raise TypeError("'another' must be a Vertex")
        
        numMyAttributes = len(self.attributes)
        numOtherAttributes = len(another.attributes)
        
        sameAmountOfAttributes = numMyAttributes == numOtherAttributes
        numEqualAttributeValues = 0
        
        if (sameAmountOfAttributes):
            for attr in self._attributes:
                for attr2 in another._attributes:
                    if attr.compare(attr2):
                        numEqualAttributeValues = numEqualAttributeValues + 1
        
        return sameAmountOfAttributes and numEqualAttributeValues == numMyAttributes
    
    def __repr__(self):
        reprStr = "{"
        
        firstTime = True
        for attr in self._attributes:
            if firstTime:
                firstTime = False
                reprStr = reprStr + "    "
            else:
                reprStr = reprStr + ", "
            reprStr = reprStr + ("%s [%r]" % (attr.name, attr.value))

        reprStr = reprStr + ("}\n")
        
        return reprStr
        