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
        
    def normalizeBlendWeight(self):
        if self.attributes != None:
            blendWeightSum = 0.0
            for attr in self.attributes:
                if attr.name.startswith(VertexAttribute.BLENDWEIGHT,0,len(VertexAttribute.BLENDWEIGHT)):
                    blendWeightSum = blendWeightSum + attr.value[1]
            
            for attr in self.attributes:
                if attr.name.startswith(VertexAttribute.BLENDWEIGHT,0,len(VertexAttribute.BLENDWEIGHT)):
                    attr.value[1] = attr.value[1] / blendWeightSum
                    
    
    def compare(self, another):
        if another == None or not isinstance(another, Vertex):
            raise TypeError("'another' must be a Vertex")
        
        numMyAttributes = len(self.attributes)
        numOtherAttributes = len(another.attributes)
        
        sameAmountOfAttributes = (numMyAttributes == numOtherAttributes)
        numEqualAttributeValues = 0
        
        # HACK Blender generates weird tangent and binormal vectors, usually different
        # even when a vertex is shared by two perfectly aligned polygons. For that reason
        # we'll just use the tangent and binormal comparisons if the normals are also different
        normalIsEqual = False
        tangentIsEqual = False
        binormalIsEqual = False
        hasTangent = False
        hasBinormal = False
        
        if sameAmountOfAttributes:
            for attr in self._attributes:
                if attr.name == VertexAttribute.TANGENT:
                    hasTangent = True
                
                if attr.name == VertexAttribute.BINORMAL:
                    hasBinormal = True
                
                for attr2 in another._attributes:
                    if attr.compare(attr2):
                        numEqualAttributeValues = numEqualAttributeValues + 1
                        
                        if attr.name == VertexAttribute.TANGENT:
                            tangentIsEqual = True
                        if attr.name == VertexAttribute.BINORMAL:
                            binormalIsEqual = True
                        if attr.name == VertexAttribute.NORMAL:
                            normalIsEqual = True
                            
            # Applying the above hack here
            if normalIsEqual:
                bonusEqualAttributes = 0
                
                if not tangentIsEqual and hasTangent:
                    bonusEqualAttributes = bonusEqualAttributes + 1
                if not binormalIsEqual and hasBinormal:
                    bonusEqualAttributes = bonusEqualAttributes + 1
                    
                if numEqualAttributeValues + bonusEqualAttributes == numMyAttributes:
                    numEqualAttributeValues = numEqualAttributeValues + bonusEqualAttributes
                        
        
        return sameAmountOfAttributes and (numEqualAttributeValues == numMyAttributes)
    
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
        