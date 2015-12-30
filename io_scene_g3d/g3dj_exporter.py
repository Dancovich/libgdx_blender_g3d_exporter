from io_scene_g3d.g3d_model import G3DModel

class G3DJExporter(object):
    
    def export(self, g3dModel=G3DModel()):
        if g3dModel == None or not isinstance(g3dModel, G3DModel):
            raise TypeError("'g3dModel' must be of type G3DModel")
        
        g3dJsonDictionary = {}
        
        g3dJsonDictionary["version"] = [0,1]
        
        g3dJsonDictionary["meshes"] = []
        for mesh in g3dModel.meshes:
            meshSection = {}
            
            meshSection["attributes"] = mesh.getAttributes()