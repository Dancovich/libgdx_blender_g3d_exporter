from io_scene_g3d.domain_classes import G3DModel

class G3DJExporter(object):
    
    def export(self, g3dModel=G3DModel()):
        if g3dModel == None or not isinstance(g3dModel, G3DModel):
            raise TypeError("'g3dModel' must be of type G3DModel")
        
        g3dJsonDictionary = {}
        
        g3dJsonDictionary["version"] = [0,1]
        
        # Export the "meshes" section
        g3dJsonDictionary["meshes"] = []
        for mesh in g3dModel.meshes:
            meshSection = {}
            
            meshSection["attributes"] = mesh.getAttributes()
            
            meshSection["vertices"] = []
            for vertex in mesh.vertices:
                for attr in vertex.attributes:
                    meshSection["vertices"].extend(attr.value)
                    
            meshSection["parts"] = []
            for part in mesh.parts:
                partSection = {}
                partSection["id"] = part.id
                partSection["type"] = part.type
                partSection["indices"] = []
                
                for vertex in part.vertices:
                    vertexIndex = mesh.vertices.index(vertex)
                    partSection["indices"].append(vertexIndex)
                    
                meshSection["parts"].append(partSection)
            
            # Finally add this mesh to the model
            g3dJsonDictionary["meshes"].append(meshSection)
            
        
        
        print(" GENERATED MESH \n")
        print(" ============== \n")
        print("%r" % g3dJsonDictionary)