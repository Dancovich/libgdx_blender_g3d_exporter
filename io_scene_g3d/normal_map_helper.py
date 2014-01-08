import bpy
from mathutils import Vector
from bpy.types import (MeshVertex,MeshPolygon)

def tangent_getter(self):
    """Getter method for tangent property"""
    value = None
    if (self._tangent == None):
        value = Vector()
    else:
        value = self._tangent
    return value

def tangent_setter(self , value):
    """Setter method for tangent property"""
    self._tangent = value

def binormal_getter(self):
    """Getter method for tangent property"""
    return self._binormal

def binormal_setter(self , value):
    """Setter method for tangent property"""
    self._binormal = value

class NormalMapHelper():

    def create_properties(self):
        """Create aditional properties to MeshVertex and MeshPolygon classes to store tangent and binormal vectors"""
        MeshVertex._tangent = None
        MeshVertex._binormal = None
        MeshPolygon._tangent = None
        MeshPolygon._binormal = None
        MeshVertex.tangent = property(tangent_getter , tangent_setter)
        MeshVertex.binormal = property(binormal_getter , binormal_setter)
        MeshPolygon.tangent = property(tangent_getter , tangent_setter)
        MeshPolygon.binormal = property(binormal_getter , binormal_setter)
    
    def generate_tangent_binormal(self, mesh , uv_layer_name = ""):
        """Generate tangent and binormal vectors and add them as new 'tangent' and 'binormal' properties to each vertex and face on the mesh"""
        uv_layer = None
        try:
            if uv_layer_name != "":
                uv_layer = mesh.uv_layers[uv_layer_name]
            elif len(mesh.uv_layers) > 0:
                uv_layer = mesh.uv_layers[0]
        except Exception:
            raise Exception("There must be at least one UV layer to calculate tangent and binormal vectors")
            
        if uv_layer == None:
            raise Exception("There must be at least one UV layer to calculate tangent and binormal vectors")
            
        for polygon in mesh.polygons:
            v0 = mesh.vertices[ polygon.vertices[0] ].co
            v1 = mesh.vertices[ polygon.vertices[1] ].co
            v2 = mesh.vertices[ polygon.vertices[2] ].co
            
            edge1 = v1 - v0
            edge2 = v2 - v0
            
            delta_u1 = uv_layer.data[ polygon.loop_indices[1] ].uv[0] - uv_layer.data[ polygon.loop_indices[0] ].uv[0]
            delta_v1 = uv_layer.data[ polygon.loop_indices[1] ].uv[1] - uv_layer.data[ polygon.loop_indices[0] ].uv[1]
            delta_u2 = uv_layer.data[ polygon.loop_indices[2] ].uv[0] - uv_layer.data[ polygon.loop_indices[0] ].uv[0]
            delta_v2 = uv_layer.data[ polygon.loop_indices[2] ].uv[1] - uv_layer.data[ polygon.loop_indices[0] ].uv[1]
            
            factor = 1.0 / ( delta_u1 * delta_v2 - delta_u2 * delta_v1 )
            
            tangent = Vector()
            tangent[0] = factor * (delta_v2 * edge1[0] - delta_v1 * edge2[0])
            tangent[1] = factor * (delta_v2 * edge1[1] - delta_v1 * edge2[1])
            tangent[2] = factor * (delta_v2 * edge1[2] - delta_v1 * edge2[2])
            
            binormal = Vector()
            binormal[0] = factor * (-delta_u2 * edge1[0] - delta_u1 * edge2[0])
            binormal[1] = factor * (-delta_u2 * edge1[1] - delta_u1 * edge2[1])
            binormal[2] = factor * (-delta_u2 * edge1[2] - delta_u1 * edge2[2])
            
            mesh.vertices[ polygon.vertices[0] ].tangent += tangent
            mesh.vertices[ polygon.vertices[1] ].tangent += tangent
            mesh.vertices[ polygon.vertices[2] ].tangent += tangent
            
            mesh.vertices[ polygon.vertices[0] ].binormal += binormal
            mesh.vertices[ polygon.vertices[1] ].binormal += binormal
            mesh.vertices[ polygon.vertices[2] ].binormal += binormal
            
            polygon.tangent = tangent
            polygon.binormal = binormal
            
            # Normalize face vectors
            polygon.tangent.normalize()
            polygon.binormal.normalize()
            
    
        # Normalize vertex vectors
        for v in mesh.vertices:
            v.tangent.normalize()
            v.binormal.normalize()
