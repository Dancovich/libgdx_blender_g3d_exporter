# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import json

from collections import OrderedDict

from io_scene_g3d import util, simpleubjson
from io_scene_g3d.util import Util
from io_scene_g3d.domain_classes import G3DModel
from io_scene_g3d.g3dj_json_encoder import G3DJsonEncoder
from io_scene_g3d.profile import profile


class G3DBaseWriter(object):

    ordered = True

    @profile('export')
    def mountJsonOutput(self, g3dModel):
        if g3dModel is None or not isinstance(g3dModel, G3DModel):
            raise TypeError("'g3dModel' must be of type G3DModel")

        if self.ordered:
            g3dJsonDictionary = OrderedDict()
        else:
            g3dJsonDictionary = {}

        g3dJsonDictionary["version"] = [0, 1]

        # Export the "meshes" section
        g3dJsonDictionary["meshes"] = []

        if g3dModel.meshes is not None:
            for mesh in g3dModel.meshes:
                if self.ordered:
                    meshSection = OrderedDict()
                else:
                    meshSection = {}

                meshSection["attributes"] = mesh.getAttributes()

                meshSection["vertices"] = []
                for vertex in mesh.vertices:
                    for attr in vertex.attributes:
                        meshSection["vertices"].extend(Util.limitFloatListPrecision(attr.value))

                meshSection["parts"] = []
                for part in mesh.parts:
                    if self.ordered:
                        partSection = OrderedDict()
                    else:
                        partSection = {}

                    partSection["id"] = part.id
                    partSection["type"] = part.type
                    partSection["indices"] = []

                    if part.vertices is not None:
                        for vertex in part.vertices:
                            vertexIndex = mesh.vertices.index(vertex)
                            partSection["indices"].append(vertexIndex)

                    meshSection["parts"].append(partSection)

                # Finally add this mesh to the model
                g3dJsonDictionary["meshes"].append(meshSection)

        # Exporting "materials" section
        g3dJsonDictionary["materials"] = []

        if g3dModel.materials is not None:
            for material in g3dModel.materials:
                if self.ordered:
                    materialSection = OrderedDict()
                else:
                    materialSection = {}

                materialSection["id"] = material.id

                if material.diffuse is not None:
                    materialSection["diffuse"] = material.diffuse

                if material.ambient is not None:
                    materialSection["ambient"] = material.ambient

                if material.emissive is not None:
                    materialSection["emissive"] = material.emissive

                if material.specular is not None:
                    materialSection["specular"] = material.specular

                if material.reflection is not None:
                    materialSection["reflection"] = material.reflection

                if material.shininess is not None:
                    materialSection["shininess"] = material.shininess

                if material.opacity is not None:
                    materialSection["opacity"] = material.opacity

                if material.textures is not None and len(material.textures) > 0:
                    materialSection["textures"] = []
                    for texture in material.textures:
                        if self.ordered:
                            textureSection = OrderedDict()
                        else:
                            textureSection = {}

                        textureSection["id"] = texture.id
                        textureSection["filename"] = texture.filename
                        textureSection["type"] = texture.type

                        materialSection["textures"].append(textureSection)

                g3dJsonDictionary["materials"].append(materialSection)

        # Exporting nodes section
        g3dJsonDictionary["nodes"] = []
        if g3dModel.nodes is not None:
            for node in g3dModel.nodes:
                g3dJsonDictionary["nodes"].append(self._exportChildNodes(node))

        # Exporting animations section
        g3dJsonDictionary["animations"] = []
        if g3dModel.animations is not None:
            for animation in g3dModel.animations:
                if self.ordered:
                    animationSection = OrderedDict()
                else:
                    animationSection = {}

                animationSection["id"] = animation.id
                animationSection["bones"] = []

                if animation.bones is not None:
                    for bone in animation.bones:
                        if self.ordered:
                            boneSection = OrderedDict()
                        else:
                            boneSection = {}

                        boneSection["boneId"] = bone.boneId
                        boneSection["keyframes"] = []

                        if bone.keyframes is not None:
                            for keyframe in bone.keyframes:
                                if self.ordered:
                                    keyframeSection = OrderedDict()
                                else:
                                    keyframeSection = {}

                                keyframeSection["keytime"] = keyframe.keytime

                                if keyframe.translation is not None:
                                    keyframeSection["translation"] = keyframe.translation

                                if keyframe.rotation is not None:
                                    keyframeSection["rotation"] = keyframe.rotation

                                if keyframe.scale is not None:
                                    keyframeSection["scale"] = keyframe.scale

                                boneSection["keyframes"].append(keyframeSection)

                        animationSection["bones"].append(boneSection)

                g3dJsonDictionary["animations"].append(animationSection)

        return g3dJsonDictionary

    def _exportChildNodes(self, parent):
        if self.ordered:
            nodeSection = OrderedDict()
        else:
            nodeSection = {}

        nodeSection["id"] = parent.id

        if parent.translation is not None:
            nodeSection["translation"] = Util.limitFloatListPrecision(parent.translation)

        if parent.rotation is not None:
            nodeSection["rotation"] = Util.limitFloatListPrecision(parent.rotation)

        if parent.scale is not None:
            nodeSection["scale"] = Util.limitFloatListPrecision(parent.scale)

        if parent.parts is not None:
            nodeSection["parts"] = []
            for nodePart in parent.parts:
                if self.ordered:
                    nodePartSection = OrderedDict()
                else:
                    nodePartSection = {}

                nodePartSection["meshpartid"] = nodePart.meshPartId
                nodePartSection["materialid"] = nodePart.materialId

                if nodePart.bones is not None:
                    nodePartSection["bones"] = []

                    for bone in nodePart.bones:
                        if self.ordered:
                            boneSection = OrderedDict()
                        else:
                            boneSection = {}

                        boneSection["node"] = bone.node

                        if bone.rotation is not None:
                            boneSection["rotation"] = Util.limitFloatListPrecision(bone.rotation)

                        if bone.translation is not None:
                            boneSection["translation"] = Util.limitFloatListPrecision(bone.translation)

                        if bone.scale is not None:
                            boneSection["scale"] = Util.limitFloatListPrecision(bone.scale)

                        nodePartSection["bones"].append(boneSection)

                if nodePart.uvLayers is not None:
                    nodePartSection["uvMapping"] = nodePart.uvLayers

                nodeSection["parts"].append(nodePartSection)

        if parent.children is not None:
            childrenSection = []
            for child in parent.children:
                childrenSection.append(self._exportChildNodes(child))

            nodeSection["children"] = childrenSection

        return nodeSection


class G3DJWriter(G3DBaseWriter):

    ordered = True

    def export(self, g3dModel, filepath):
        baseModel = self.mountJsonOutput(g3dModel)

        output_file = open(filepath, 'w')
        json_output = json.dumps(baseModel, indent=2, sort_keys=False, cls=G3DJsonEncoder, float_round=util.FLOAT_ROUND)
        output_file.write(json_output)
        output_file.close()


class G3DBWriter(G3DBaseWriter):

    ordered = True

    def export(self, g3dModel, filepath):
        baseModel = self.mountJsonOutput(g3dModel)

        output_file = open(filepath, 'wb')
        outputdata = simpleubjson.encode(data=baseModel)
        output_file.write(outputdata)
        output_file.close()

        if util.LOG_LEVEL >= util._DEBUG_:
            simpleubjson.pprint(outputdata)
