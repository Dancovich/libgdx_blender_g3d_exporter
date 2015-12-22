from io_scene_g3d.util import Util

class VertexAttribute(object):
    """A vertex attribute"""
    
    _name = None
    
    _value = None
    
    """Attribute Types"""
    ###
    POSITION = "POSITION"
    NORMAL = "NORMAL"
    COLOR = "COLOR"
    COLORPACKED = "COLORPACKED"
    TANGENT = "TANGENT"
    BINORMAL = "BINORMAL"
    
    TEXCOORD = "TEXCOORD"
    
    BLENDWEIGHT = "BLENDWEIGHT"
    ###
    
    def __init__(self, name="POSITION", value=[0.0, 0.0, 0.0]):
        self.name = name
        self.value = value
    
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
        
        if self.name != another.name:
            return False
        
        if isinstance(self.value, list) and isinstance(another.value, list):
            if len(self.value) == len(another.value):
                if len(self.value) == 3:
                    return Util.compareVector(None, self.value, another.value)
                elif len(self.value) == 4:
                    return Util.compareQuaternion(None, self.value, another.value)
                if len(self.value) == 2:
                    return self.value == another.value
                else:
                    return False
            else:
                return False
        else:
            return self.value == another.value
    
    def __repr__(self):
        value = "%s {%r}" % (self.name, self.value)
        return value