
class Material(object):
    """Material associated with a geometry"""
    
    _id = ""
    
    _ambient = []
    
    _diffuse = []
    
    _emissive = []
    
    _opacity = 1.0
    
    _specular = []
    
    _shininess = 1.0
    
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
    def ambient(self, r, g, b, a):
        self._ambient[0] = r
        self._ambient[1] = g
        self._ambient[2] = b
        self._ambient[3] = a
        
    @property
    def diffuse(self):
        return self._diffuse
    
    @diffuse.setter
    def diffuse(self, r, g, b, a):
        self._diffuse[0] = r
        self._diffuse[1] = g
        self._diffuse[2] = b
        self._diffuse[3] = a
        
    @property
    def emissive(self):
        return self._emissive
    
    @emissive.setter
    def emissive(self, r, g, b, a):
        self._emissive[0] = r
        self._emissive[1] = g
        self._emissive[2] = b
        self._emissive[3] = a
        
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
    def specular(self, r, g, b, a):
        self._specular[0] = r
        self._specular[1] = g
        self._specular[2] = b
        self._specular[3] = a
        
    @property
    def shininess(self):
        return self._shininess
    
    @shininess.setter
    def shininess(self, shininess):
        self._shininess = shininess