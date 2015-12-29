
class Animation(object):
    
    _id = ""
    
    _bones = None
    
    def __init__(self):
        self._id = ""
        self._bones = None
        
    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, animationId):
        self._id = animationId
    
    @property
    def bones(self):
        return self._bones
    
    @bones.setter
    def bones(self, bones):
        if bones == None or not isinstance(bones, list):
            raise TypeError("'bones' must be of type list")
        
        self._bones = bones
        
    def addBone(self, bone):
        if bone == None or not isinstance(bone, NodeAnimation):
            raise TypeError("'bone' must be of type NodeAnimation")
        
        if self._bones == None:
            self._bones = []
            
        self._bones.append(bone)
    
class NodeAnimation(object):
    
    _boneId = ""
    
    _keyframes = None
    
    def __init__(self):
        self._boneId = ""
        self._keyframes = None
        
    @property
    def boneId(self):
        return self._boneId
    
    @boneId.setter
    def boneId(self, boneId):
        self._boneId = boneId
        
    @property
    def keyframes(self):
        return self._keyframes
    
    @keyframes.setter
    def keyframes(self, keyframes):
        if keyframes == None or not isinstance(keyframes, list):
            raise TypeError("'keyframes' must be of type list")
        
        self._keyframes = keyframes
        
    def addKeyframe(self, keyframe):
        if keyframe == None or not isinstance(keyframe, Keyframe):
            raise TypeError("'keyframe' must be of type Keyframe")
        
        if self._keyframes == None:
            self._keyframes = []
            
        self._keyframes.append(keyframe)


class Keyframe(object):
    _keytime = 0.0
    
    _translation = None
    
    _rotation = None
    
    _scale = None
    
    def __init__(self):
        self._keytime = 0.0
        self._rotation = None
        self._translation= None
        self._scale = None
        
    @property
    def keytime(self):
        return self._keytime
    
    @keytime.setter
    def keytime(self, keytime):
        self._keytime = keytime
        
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