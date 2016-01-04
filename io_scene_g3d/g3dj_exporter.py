import json

from collections import OrderedDict

from io_scene_g3d import util
from io_scene_g3d.domain_classes import G3DModel
from io_scene_g3d.g3dj_json_encoder import G3DJsonEncoder
from io_scene_g3d.profile import profile

class G3DJExporter(object):
    
    @profile('export')
    def export(self, g3dModel):
        if g3dModel == None or not isinstance(g3dModel, G3DModel):
            raise TypeError("'g3dModel' must be of type G3DModel")
        
        g3dJsonDictionary = OrderedDict()
        
        g3dJsonDictionary["version"] = [0,1]
        
        # Export the "meshes" section
        g3dJsonDictionary["meshes"] = []
        
        if g3dModel.meshes != None:
            for mesh in g3dModel.meshes:
                meshSection = OrderedDict()
                
                meshSection["attributes"] = mesh.getAttributes()
                
                meshSection["vertices"] = []
                for vertex in mesh.vertices:
                    for attr in vertex.attributes:
                        meshSection["vertices"].extend(attr.value)
                        
                meshSection["parts"] = []
                for part in mesh.parts:
                    partSection = OrderedDict()
                    partSection["id"] = part.id
                    partSection["type"] = part.type
                    partSection["indices"] = []
                    
                    for vertex in part.vertices:
                        vertexIndex = mesh.vertices.index(vertex)
                        partSection["indices"].append(vertexIndex)
                        
                    meshSection["parts"].append(partSection)
                
                # Finally add this mesh to the model
                g3dJsonDictionary["meshes"].append(meshSection)
            
        # Exporting "materials" section
        g3dJsonDictionary["materials"] = []
        
        if g3dModel.materials != None:
            for material in g3dModel.materials:
                materialSection = OrderedDict()
                materialSection["id"] = material.id
                
                if material.diffuse != None:
                    materialSection["diffuse"] = material.diffuse
                    
                if material.ambient != None:
                    materialSection["ambient"] = material.ambient
                    
                if material.emissive != None:
                    materialSection["emissive"] = material.emissive
                    
                if material.specular != None:
                    materialSection["specular"] = material.specular
                    
                if material.reflection != None:
                    materialSection["reflection"] = material.reflection
                    
                if material.shininess != None:
                    materialSection["shininess"] = material.shininess
                    
                if material.opacity != None:
                    materialSection["opacity"] = material.opacity
                    
                if material.textures != None and len(material.textures) > 0:
                    materialSection["textures"] = []
                    for texture in material.textures:
                        textureSection = OrderedDict()
                        textureSection["id"] = texture.id
                        textureSection["filename"] = texture.filename
                        textureSection["type"] = texture.type
                        
                        materialSection["textures"].append(textureSection)
                        
                g3dJsonDictionary["materials"].append(materialSection)
            
        # Exporting nodes section
        g3dJsonDictionary["nodes"] = []
        if g3dModel.nodes != None:
            for node in g3dModel.nodes:
                g3dJsonDictionary["nodes"].append( self._exportChildNodes(node) )
            
        # Exporting animations section
        g3dJsonDictionary["animations"] = []
        if g3dModel.animations != None:
            for animation in g3dModel.animations:
                animationSection = OrderedDict()
                
                animationSection["id"] = animation.id
                animationSection["bones"] = []
                
                if animation.bones != None:
                    for bone in animation.bones:
                        boneSection = OrderedDict()
                        
                        boneSection["boneId"] = bone.boneId
                        boneSection["keyframes"] = []
                        
                        if bone.keyframes != None:
                            for keyframe in bone.keyframes:
                                keyframeSection = OrderedDict()
                                keyframeSection["keytime"] = keyframe.keytime
                                
                                if keyframe.translation != None:
                                    keyframeSection["translation"] = keyframe.translation
                                    
                                if keyframe.rotation != None:
                                    keyframeSection["rotation"] = keyframe.rotation
                                    
                                if keyframe.scale != None:
                                    keyframeSection["scale"] = keyframe.scale
                                    
                                boneSection["keyframes"].append(keyframeSection)
                                
                        animationSection["bones"].append(boneSection)
                        
                g3dJsonDictionary["animations"].append(animationSection)
        
            
        #output_file = open(self.filepath , 'w')
        json_output = json.dumps(g3dJsonDictionary \
                                 , indent=2 \
                                 , sort_keys=False \
                                 , cls=G3DJsonEncoder \
                                 , float_round = util.FLOAT_ROUND)
        #output_file.write(json_output)
        #output_file.close()
        
        print(" GENERATED MESH \n")
        print(" ============== \n")
        print("%s" % json_output)
        
    def _exportChildNodes(self, parent):
        nodeSection = OrderedDict()
        nodeSection["id"] = parent.id
        
        if parent.translation != None:
            nodeSection["translation"] = parent.translation
            
        if parent.rotation != None:
            nodeSection["rotation"] = parent.rotation
            
        if parent.scale != None:
            nodeSection["scale"] = parent.scale
            
        if parent.parts != None:
            nodeSection["parts"] = []
            for nodePart in parent.parts:
                nodePartSection = OrderedDict()
                nodePartSection["meshpartid"] = nodePart.meshPartId
                nodePartSection["materialid"] = nodePart.materialId
                
                if nodePart.bones != None:
                    nodePartSection["bones"] = []
                    
                    for bone in nodePart.bones:
                        boneSection = OrderedDict()
                        boneSection["node"] = bone.node
                        
                        if bone.rotation != None:
                            boneSection["rotation"] = bone.rotation
                            
                        if bone.translation != None:
                            boneSection["translation"] = bone.translation
                            
                        if bone.scale != None:
                            boneSection["scale"] = bone.scale
                    
                        nodePartSection["bones"].append(boneSection)
                    
                if nodePart.uvLayers != None:
                    nodePartSection["uvMapping"] = nodePart.uvLayers
                    
                nodeSection["parts"].append(nodePartSection)
        
        if parent.children != None:
            childrenSection = []
            for child in parent.children:
                childrenSection.append( self._exportChildNodes(child) )
            
            nodeSection["children"] = childrenSection
            
        return nodeSection