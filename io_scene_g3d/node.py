class Node(object):
    
    _id = ""
    
    _rotation = None
    
    _translation = None
    
    _scale = None

    _parts = None
    
    _children = None
    
    def __init__(self):
        self._id = ""
        self._rotation = None
        self._translation = None
        self._scale = None
        self._children = None
    
    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, nodeId):
        self._id = nodeId
        
    @property
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, rotation):
        self._rotation = rotation
        
    @property
    def translation(self):
        return self._translation
    
    @translation.setter
    def translation(self, translation):
        self._translation = translation
        
    @property
    def scale(self):
        return self._scale
    
    @scale.setter
    def scale(self, scale):
        self._scale = scale
        
    def addChild(self, childNode):
        if childNode == None or not isinstance(childNode, Node):
            raise TypeError("'childNode' must be of type Node")
        
        if self._children == None:
            self._children = []
        
        self._children.append(childNode)
        
    @property
    def children(self):
        return self._children
    
    @children.setter
    def children(self, children):
        if children == None or not isinstance(children, list):
            raise TypeError("'children' must be of type list")
        
        self._children = children
    
    def addPart(self,part):
        if part == None or not isinstance(part, NodePart):
            raise TypeError("'part' must be of type NodePart")
        
        if self._parts == None:
            self._parts = []
            
        self._parts.append(part)
        
    @property
    def parts(self):
        return self._parts
    
class NodePart(object):
    
    _meshPartId = ""
    
    _materialId = ""
    
    _bones = None
    
    _uvLayers = None
    
    def __init__(self):
        self._meshPartId = ""
        self._materialId = ""
        
    @property
    def meshPartId(self):
        return self._meshPartId
    
    @meshPartId.setter
    def meshPartId(self, meshPartId):
        self._meshPartId = meshPartId
        
    @property
    def materialId(self):
        return self._materialId
    
    @materialId.setter
    def materialId(self, materialId):
        self._materialId = materialId
        
    def addUVLayer(self, uvLayerMapping):
        if uvLayerMapping == None or not isinstance(uvLayerMapping, list):
            raise TypeError("'uvLayerMapping' must be of type list")
        
        if self._uvLayers == None:
            self._uvLayers = []
            
        self._uvLayers.append(uvLayerMapping)
        
    @property
    def uvLayers(self):
        return self._uvLayers
    
    def addBone(self, bone):
        if bone == None or not isinstance(bone, Bone):
            raise TypeError("'bone' must be of type Bone")
        
        if self._bones == None:
            self._bones = []
            
        self._bones.append(bone)
    
    @property
    def bones(self):
        return self._bones
    
class Bone(object):
    
    _node = ""
    
    _rotation = None
    
    _translation = None
    
    _scale = None
    
    def __init__(self):
        self._node = ""
        self._rotation = None
        self._translation = None
        self._scale = None
    
    @property
    def node(self):
        return self._node
    
    @node.setter
    def node(self, node):
        self._node = node
        
    @property
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, rotation):
        self._rotation = rotation
        
    @property
    def translation(self):
        return self._translation
    
    @translation.setter
    def translation(self, translation):
        self._translation = translation
        
    @property
    def scale(self):
        return self._scale
    
    @scale.setter
    def scale(self, scale):
        self._scale = scale 