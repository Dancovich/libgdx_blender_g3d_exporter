from io_scene_g3d.mesh import Mesh

class G3DModel(object):
    """ Our model class that will later be exported to G3D """
    
    _meshes = []
    
    def __init__(self):
        self._meshes = []
    
    def addMesh(self, mesh):
        if mesh == None or not isinstance(mesh, Mesh):
            raise TypeError("'mesh' must be of type Mesh")
        
        self._meshes.append(mesh)
        
    def hasMesh(self, meshId):
        for mesh in self._meshes:
            if mesh.id() == meshId:
                return True
            
        return False