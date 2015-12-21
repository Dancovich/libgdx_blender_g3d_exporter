
class Node(object):
    
    _id = ""
    
    _rotation = []
    
    _translation = []
    
    _scale = []
    
    _children = []
    
    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, boneId):
        self._id = boneId
        
    @property
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, x, y, z, w):
        self._rotation[0] = x
        self._rotation[1] = y
        self._rotation[2] = z
        self._rotation[3] = w
        
    @property
    def translation(self):
        return self._translation
    
    @translation.setter
    def translation(self, x, y, z):
        self._translation[0] = x
        self._translation[1] = y
        self._translation[2] = z
        
    @property
    def scale(self):
        return self._scale
    
    @scale.setter
    def scale(self, x, y, z):
        self._scale[0] = x
        self._scale[1] = y
        self._scale[2] = z
        
    def addChild(self, childNode):
        if childNode == None or not isinstance(childNode, Node):
            raise TypeError("'childNode' must be of type Node")
        
        self._children.append(childNode)
        
    @property
    def children(self):
        return self._children