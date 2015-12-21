from io_scene_g3d.mesh import Mesh
from io_scene_g3d.material import Material
from io_scene_g3d.node import Node

class Model(object):
    
    _meshes = []
    
    _materials = []
    
    _nodes = []
    
    _animations = []
    
    @property
    def meshes(self):
        return self._meshes
    
    @property
    def materials(self):
        return self._materials
    
    @property
    def nodes(self):
        return self._nodes
    
    @property
    def animations(self):
        return self._animations
    
    def addMesh(self, mesh):
        if mesh == None or not isinstance(mesh, Mesh):
            raise TypeError("'mesh' must be of type Mesh")
        self._meshes.append(mesh)
        
    def addMaterial(self, material):
        if material == None or not isinstance(material, Material):
            raise TypeError("'material' must be of type Material")
        self._materials.append(material)
        
    def addNode(self, node):
        if node == None or not isinstance(node, Node):
            raise TypeError("'node' must be of type Node")
        self._nodes.append(node)
        
