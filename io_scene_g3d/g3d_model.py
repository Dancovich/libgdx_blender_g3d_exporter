from io_scene_g3d.mesh import Mesh

class G3DModel(object):
    """ Our model class that will later be exported to G3D """
    
    _meshes = []
    
    _materials = []
    
    _nodes = []
    
    def __init__(self):
        self._meshes = []
        
    @property
    def meshes(self):
        return self._meshes
    
    @meshes.setter
    def meshes(self, meshes):
        if meshes == None or not isinstance(meshes, list) or len(meshes)==0 or not isinstance(meshes[0], Mesh):
            raise TypeError("'meshes' must be a list of Mesh")
        
        self._meshes = meshes
    
    def addMesh(self, mesh):
        if mesh == None or not isinstance(mesh, Mesh):
            raise TypeError("'mesh' must be of type Mesh")
        
        self._meshes.append(mesh)
        
    def hasMesh(self, meshId):
        for mesh in self._meshes:
            if mesh.id() == meshId:
                return True
            
        return False
    
    @property
    def materials(self):
        return self._materials
    
    @materials.setter
    def materials(self, materials):
        if materials == None or not isinstance(materials, list):
            raise TypeError("'materials' must be of type list")
        
        self._materials = materials
        
    @property
    def nodes(self):
        return self._nodes
    
    @nodes.setter
    def nodes(self, nodes):
        if nodes == None or not isinstance(nodes, list):
            raise TypeError("'nodes' must be of type list")
        
        self._nodes = nodes