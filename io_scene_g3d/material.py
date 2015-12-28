from io_scene_g3d.texture import Texture

class Material(object):
    """Material associated with a geometry"""
    
    _id = ""
    
    _ambient = None
    
    _diffuse = None
    
    _emissive = None
    
    _opacity = None
    
    _specular = None
    
    _shininess = None
    
    _reflection = None
    
    _textures = []
    
    def __init__(self):
        self._id = ""
        self._ambient = None
        self._diffuse = None
        self._emissive = None
        self._opacity = None
        self._specular = None
        self._shininess = None
        self._reflection = None
    
    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, materialId):
        self._id = materialId
        
    @property
    def ambient(self):
        return self._ambient
    
    @ambient.setter
    def ambient(self, ambient):
        self._ambient = ambient
        
    @property
    def diffuse(self):
        return self._diffuse
    
    @diffuse.setter
    def diffuse(self, diffuse):
        self._diffuse = diffuse
        
    @property
    def emissive(self):
        return self._emissive
    
    @emissive.setter
    def emissive(self, emissive):
        self._emissive = emissive
        
    @property
    def opacity(self):
        return self._opacity
    
    @opacity.setter
    def opacity(self, opacity):
        self._opacity = opacity
        
    @property
    def specular(self):
        return self._specular
    
    @specular.setter
    def specular(self, specular):
        self._specular = specular
        
    @property
    def shininess(self):
        return self._shininess
    
    @shininess.setter
    def shininess(self, shininess):
        self._shininess = shininess
        
    @property
    def reflection(self):
        return self._reflection
    
    @reflection.setter
    def reflection(self, reflection):
        self._reflection = reflection
        
    @property
    def textures(self):
        return self._textures
    
    @textures.setter
    def textures(self, textures):
        self._textures = textures