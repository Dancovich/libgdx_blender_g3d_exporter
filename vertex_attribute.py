from mathutils import Vector

class VertexAttribute(object):
    """A vertex attribute"""
    
    _name = None
    
    _value = Vector()
    
    """Attribute Types"""
    POSITION = "POSITION"
    NORMAL = "NORMAL"
    COLOR = "COLOR"
    COLORPACKED = "COLORPACKED"
    TANGENT = "TANGENT"
    BINORMAL = "BINORMAL"
    
    TEXCOORD0 = "TEXCOORD0"
    TEXCOORD1 = "TEXCOORD1"
    TEXCOORD2 = "TEXCOORD2"
    TEXCOORD3 = "TEXCOORD3"
    TEXCOORD4 = "TEXCOORD4"
    TEXCOORD5 = "TEXCOORD5"
    TEXCOORD6 = "TEXCOORD6"
    TEXCOORD7 = "TEXCOORD7"
    TEXCOORD8 = "TEXCOORD8"
    TEXCOORD9 = "TEXCOORD9"
    
    BLENDWEIGHT0 = "BLENDWEIGHT0"
    BLENDWEIGHT1 = "BLENDWEIGHT1"
    BLENDWEIGHT2 = "BLENDWEIGHT2"
    BLENDWEIGHT3 = "BLENDWEIGHT3"
    BLENDWEIGHT4 = "BLENDWEIGHT4"
    BLENDWEIGHT5 = "BLENDWEIGHT5"
    BLENDWEIGHT6 = "BLENDWEIGHT6"
    BLENDWEIGHT7 = "BLENDWEIGHT7"
    BLENDWEIGHT8 = "BLENDWEIGHT8"
    BLENDWEIGHT9 = "BLENDWEIGHT9"
    """"""
    
    def __init__(self, name="POSITION", value = [0.0, 0.0, 0.0]):
        self._name = name
        self._value = value
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, name):
        self._name = name
        
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, value):
        self._value = value
        
    def compare(self, another):
        """Compare this attribute with another for value"""
        if another == None or not isinstance(another, VertexAttribute):
            return False
        
        return self._name == another._name and self._value == another._value