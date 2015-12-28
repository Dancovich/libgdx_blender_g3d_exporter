class Texture(object):
    
    _id = ""
    
    _filename = ""
    
    _type = ""
    
    def __init__(self, textureId="", textureType="", filename=""):
        self._id = textureId
        self._filename = filename
        self._type = textureType
    
    