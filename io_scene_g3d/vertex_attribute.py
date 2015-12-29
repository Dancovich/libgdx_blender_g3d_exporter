import math

from io_scene_g3d.util import ROUND_STRING

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
                isEqual = True
                for pos in range(0, len(self.value)):
                    thisValue = ROUND_STRING % self.value[pos]
                    otherValue = ROUND_STRING % another.value[pos]
                    
                    if thisValue != otherValue:
                        # handles cases where 0 and -0 are different when compared as strings
                        if math.fabs(self.value[pos]) - math.fabs(another.value[pos]) == math.fabs(self.value[pos]):
                            compareThisForZero = ROUND_STRING % math.fabs(self.value[pos])
                            compareOtherForZero = ROUND_STRING % math.fabs(another.value[pos])
                            
                            if compareThisForZero != compareOtherForZero:
                                isEqual = False
                                break
                        else:
                            isEqual = False
                            break
                        
                return isEqual
            else:
                return False
        else:
            return self.value == another.value
    
    def __repr__(self):
        value = "%s {%r}" % (self.name, self.value)
        return value