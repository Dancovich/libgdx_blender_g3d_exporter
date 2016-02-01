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

import math

from io_scene_g3d import util
from io_scene_g3d.util import Util, ROUND_STRING
from io_scene_g3d.profile import profile


class Vertex(object):
    """Define a mesh vertex"""

    _attributes = []

    _hashCache = None
    
    _listOfZeros = Util.floatListToString([0.0, 0.0])

    def __init__(self):
        self.attributes = []

    def add(self, attribute):
        if attribute is None or not isinstance(attribute, VertexAttribute):
            raise TypeError("'attribute' must be a VertexAttribute")

        alreadyAdded = attribute in self._attributes
        """
        for attr in self._attributes:
            if attr == attribute:
                alreadyAdded = True
                break
        """

        if not alreadyAdded:
            self._attributes.append(attribute)

        self._hashCache = None
        return not alreadyAdded

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, newAttributes):
        self._attributes = newAttributes
        self._hashCache = None

    def normalizeBlendWeight(self):
        if self.attributes is not None:
            blendWeightSum = 0.0

            for attr in self.attributes:
                if attr.name.startswith(VertexAttribute.BLENDWEIGHT, 0, len(VertexAttribute.BLENDWEIGHT)):
                    blendWeightSum = blendWeightSum + attr.value[1]

            for attr in self.attributes:
                if attr.name.startswith(VertexAttribute.BLENDWEIGHT, 0, len(VertexAttribute.BLENDWEIGHT)):
                    attr.value[1] = attr.value[1] / blendWeightSum

            self._hashCache = None

    def sortAttributes(self):
        if self._attributes is not None:
            self._attributes.sort(key=util.attributeSort)

    @profile('hashVertex')
    def __hash__(self):
        if self._hashCache is None or self._hashCache == 0:
            self._hashCache = 0
            if self._attributes is not None:
                for attr in self._attributes:
                    # If the attribute is of type TEXCOORD or BLENDWEIGHT and it's
                    # value is zero we ignore it.
                    if not ((attr.name.startswith(VertexAttribute.BLENDWEIGHT, 0, len(VertexAttribute.BLENDWEIGHT)) \
                             or attr.name.startswith(VertexAttribute.TEXCOORD, 0, len(VertexAttribute.TEXCOORD))) \
                            and Util.floatListToString(attr.value) == self._listOfZeros):
                        self._hashCache = 31 * self._hashCache + hash(attr)
        return self._hashCache

    @profile('eqVertex')
    def __eq__(self, another):
        if another is None or not isinstance(another, Vertex):
            raise TypeError("'another' must be a Vertex")
        return hash(self) == hash(another)

        """
        if another is None or not isinstance(another, Vertex):
            raise TypeError("'another' must be a Vertex")

        numMyAttributes = len(self.attributes)
        numOtherAttributes = len(another.attributes)

        sameAmountOfAttributes = (numMyAttributes == numOtherAttributes)
        numEqualAttributeValues = 0

        if sameAmountOfAttributes:
            for position in range(0, numMyAttributes):
                myAttr = self._attributes[position]
                otherAttr = another._attributes[position]

                if myAttr == otherAttr:
                    numEqualAttributeValues = numEqualAttributeValues + 1
                else:
                    break

        return sameAmountOfAttributes and (numEqualAttributeValues == numMyAttributes)
        """

    def __ne__(self, another):
        return not self.__eq__(another)

    def __repr__(self):
        reprStr = "{"

        firstTime = True
        for attr in self._attributes:
            if firstTime:
                firstTime = False
                # reprStr = reprStr + "    "
            else:
                reprStr = reprStr + ", "
            reprStr = reprStr + ("{!s} [{!r}]".format(attr.name, attr.value))

        reprStr = reprStr + ("}")

        return reprStr


class VertexAttribute(object):
    """A vertex attribute"""

    _name = None

    _value = None

    """Attribute Types"""
    ###
    POSITION = "POSITION"
    NORMAL = "NORMAL"
    COLOR = "COLOR"
    COLORPACKED = "COLORPACKED"
    TANGENT = "TANGENT"
    BINORMAL = "BINORMAL"

    TEXCOORD = "TEXCOORD"

    BLENDWEIGHT = "BLENDWEIGHT"
    ###

    # Used to calculate attribute hash
    ATTRIBUTE_HASH = "%s||%s"
    _hashCache = None

    def __init__(self, name="POSITION", value=[0.0, 0.0, 0.0]):
        self.name = name
        self.value = value
        self._hashCache = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        self._hashCache = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self._hashCache = None

    @profile('hashVertexAttribute')
    def __hash__(self):
        if self._hashCache is None or self._hashCache == 0:
            self._hashCache = 0
            hashString = None
            if self._value is not None and isinstance(self._value, list):
                hashString = self.ATTRIBUTE_HASH % (self._name, Util.floatListToString(self._value))
            elif self._value is not None:
                hashString = self.ATTRIBUTE_HASH % (self._name, Util.floatToString(self._value))
            else:
                hashString = self.ATTRIBUTE_HASH % (self._name, self._value)
            self._hashCache = hash(hashString)

        return self._hashCache

    @profile('eqVertexAttribute')
    def __eq__(self, another):
        """Compare this attribute with another for value"""
        if another is None or not isinstance(another, VertexAttribute):
            return False

        if self.name != another.name:
            return False

        if isinstance(self.value, list) and isinstance(another.value, list):
            if len(self.value) == len(another.value):
                isEqual = True
                for pos in range(0, len(self.value)):
                    thisValue = ROUND_STRING.format(self.value[pos])
                    otherValue = ROUND_STRING.format(another.value[pos])

                    if thisValue != otherValue:
                        # handles cases where 0 and -0 are different when compared as strings
                        if math.fabs(self.value[pos]) - math.fabs(another.value[pos]) == math.fabs(self.value[pos]):
                            compareThisForZero = ROUND_STRING.format(math.fabs(self.value[pos]))
                            compareOtherForZero = ROUND_STRING.format(math.fabs(another.value[pos]))

                            if compareThisForZero != compareOtherForZero:
                                isEqual = False
                                break
                        else:
                            isEqual = False
                            break

                return isEqual
            else:
                return False
        else:
            return self.value == another.value

    def __ne__(self, another):
        return not self.__eq__(another)

    def __repr__(self):
        value = "{!s} {{{!r}}}".format(self.name, self.value)
        return value


class Texture(object):

    _id = ""

    _filename = ""

    _type = ""

    def __init__(self, textureId="", textureType="", filename=""):
        self._id = textureId
        self._filename = filename
        self._type = textureType


class Node(object):

    _id = ""

    _rotation = None

    _translation = None

    _scale = None

    _parts = None

    _children = None

    def __init__(self):
        self._id = ""
        self._rotation = None
        self._translation = None
        self._scale = None
        self._children = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, nodeId):
        self._id = nodeId

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, rotation):
        self._rotation = rotation

    @property
    def translation(self):
        return self._translation

    @translation.setter
    def translation(self, translation):
        self._translation = translation

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        self._scale = scale

    def addChild(self, childNode):
        if childNode is None or not isinstance(childNode, Node):
            raise TypeError("'childNode' must be of type Node")

        if self._children is None:
            self._children = []

        self._children.append(childNode)

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, children):
        if children is None or not isinstance(children, list):
            raise TypeError("'children' must be of type list")

        self._children = children

    def addPart(self, part):
        if part is None or not isinstance(part, NodePart):
            raise TypeError("'part' must be of type NodePart")

        if self._parts is None:
            self._parts = []

        self._parts.append(part)

    @property
    def parts(self):
        return self._parts


class NodePart(object):

    _meshPartId = ""

    _materialId = ""

    _bones = None

    _uvLayers = None

    def __init__(self):
        self._meshPartId = ""
        self._materialId = ""

    @property
    def meshPartId(self):
        return self._meshPartId

    @meshPartId.setter
    def meshPartId(self, meshPartId):
        self._meshPartId = meshPartId

    @property
    def materialId(self):
        return self._materialId

    @materialId.setter
    def materialId(self, materialId):
        self._materialId = materialId

    def addUVLayer(self, uvLayerMapping):
        if uvLayerMapping is None or not isinstance(uvLayerMapping, list):
            raise TypeError("'uvLayerMapping' must be of type list")

        if self._uvLayers is None:
            self._uvLayers = []

        self._uvLayers.append(uvLayerMapping)

    @property
    def uvLayers(self):
        return self._uvLayers

    def addBone(self, bone):
        if bone is None or not isinstance(bone, Bone):
            raise TypeError("'bone' must be of type Bone")

        if self._bones is None:
            self._bones = []

        self._bones.append(bone)

    @property
    def bones(self):
        return self._bones


class Bone(object):

    _node = ""

    _rotation = None

    _translation = None

    _scale = None

    def __init__(self):
        self._node = ""
        self._rotation = None
        self._translation = None
        self._scale = None

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, node):
        self._node = node

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, rotation):
        self._rotation = rotation

    @property
    def translation(self):
        return self._translation

    @translation.setter
    def translation(self, translation):
        self._translation = translation

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        self._scale = scale


class Mesh(object):

    _id = ""

    _vertices = None

    _parts = None

    # This is a cache so we know all attributes this mesh has.
    # All the real attributes are in the vertices
    _attributes = None

    # This stores positions of each vertex on the _vertices attribute, so searches are faster
    _vertexIndex = None

    def __init__(self):
        self._id = ""
        self._vertices = []
        self._parts = []
        self._attributes = []
        self._vertexIndex = {}

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, meshId):
        self._id = meshId

    @property
    def vertices(self):
        return self._vertices

    def getAttributes(self):
        return self._attributes

    def getVertexIndex(self, vertex):
        if vertex is None or not isinstance(vertex, Vertex):
            raise TypeError("'vertex' must be of type Vertex")

        vertexHash = hash(vertex)
        try:
            existingVertexPos = self._vertexIndex[vertexHash]
            return existingVertexPos
        except KeyError:
            return None

    def addVertex(self, vertex):
        """
        Adds a vertex if it has not been added before.
        A vertex is considered 'already added' if all it's vertex
        attributes have the same value.

        Returns the added vertex if it's new or a pointer
        to the already present vertex if there is one.
        """

        if vertex is None or not isinstance(vertex, Vertex):
            raise TypeError("'vertex' must be of type Vertex")

        vertexHash = hash(vertex)
        try:
            existingVertexPos = self._vertexIndex[vertexHash]
            existingVertex = self._vertices[existingVertexPos]
            return existingVertex
        except KeyError:
            self._vertices.append(vertex)
            vertexIndex = len(self._vertices) - 1
            self._vertexIndex[vertexHash] = vertexIndex

            # Add this vertice's attributes to the attribute name cache
            for attr in vertex.attributes:
                if attr.name not in self._attributes:
                    self._attributes.append(attr.name)

            return vertex
        """

        alreadyAdded = False
        foundVertex = None

        for vtx in self._vertices:
            if vtx == vertex:
                alreadyAdded = True
                foundVertex = vtx
                break

        if not alreadyAdded:
            self._vertices.append(vertex)

            # Add this vertice's attributes to the attribute name cache
            for attr in vertex.attributes:
                if attr.name not in self._attributes:
                    self._attributes.append(attr.name)

            return vertex
        else:
            return foundVertex
        """

    @property
    def parts(self):
        return self._parts

    def addPart(self, meshPart):
        if meshPart is None or not isinstance(meshPart, MeshPart):
            raise TypeError("'meshPart' must be of type MeshPart")

        self._parts.append(meshPart)
        meshPart.parentMesh = self

    def normalizeAttributes(self):
        """
        Makes sure all vertices have the same number of attributes.
        More specifically, individual vertices may not have all BLENDWEIGHT or TEXCOORD
        attributes but if that's the case we need to add blank values for those
        attributes as LibGDX requires all vertices to have the same number of attribute values
        """

        # Naming for our attributes
        blendWeightAttrName = VertexAttribute.BLENDWEIGHT + "%d"
        texCoordAttrName = VertexAttribute.TEXCOORD + "%d"

        # This is how many total attributes we have. We can skip any vertices
        # that have that many attributes
        totalAttributes = len(self._attributes)

        # Figure out how many TEXCOORD and BLENDWEIGHT attributes we have
        numOfTexCoord = 0
        numOfBlendWeight = 0
        for attr in self._attributes:
            if attr.startswith(VertexAttribute.BLENDWEIGHT, 0, len(VertexAttribute.BLENDWEIGHT)):
                numOfBlendWeight = numOfBlendWeight + 1
            elif attr.startswith(VertexAttribute.TEXCOORD, 0, len(VertexAttribute.TEXCOORD)):
                numOfTexCoord = numOfTexCoord + 1

        # Normalize any vertex that has less than these number of attributes
        for vertex in self._vertices:
            if len(vertex.attributes) == totalAttributes:
                continue

            vertexNumOfTexCoord = 0
            vertexNumOfBlendWeight = 0

            for attr in vertex.attributes:
                if attr.name.startswith(VertexAttribute.BLENDWEIGHT, 0, len(VertexAttribute.BLENDWEIGHT)):
                    vertexNumOfBlendWeight = vertexNumOfBlendWeight + 1
                elif attr.name.startswith(VertexAttribute.TEXCOORD, 0, len(VertexAttribute.TEXCOORD)):
                    vertexNumOfTexCoord = vertexNumOfTexCoord + 1

            # Add missing attributes
            for newBlendIndex in range(vertexNumOfBlendWeight, numOfBlendWeight):
                newAttribute = VertexAttribute(name=(blendWeightAttrName % newBlendIndex), value=[0.0, 0.0])
                vertex.add(newAttribute)

            for newTexCoordIndex in range(vertexNumOfTexCoord, numOfTexCoord):
                newAttribute = VertexAttribute(name=(texCoordAttrName % newTexCoordIndex), value=[0.0, 0.0])
                vertex.add(newAttribute)

    def __repr__(self):
        value = "VERTICES:\n{!r}\n\nPARTS:\n{!r}\n\n".format(self._vertices, self._parts)
        return value


class MeshPart(object):
    """Represents a mesh part"""

    _id = ""

    _type = "TRIANGLES"

    _vertices = None

    _parentMesh = None

    def __init__(self, meshPartId="", meshType="TRIANGLES", vertices=None, parentMesh=None):
        self._id = meshPartId
        self._type = meshType
        self._vertices = vertices
        self._parentMesh = parentMesh

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, partId):
        self._id = partId

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, partType):
        self._type = partType

    @property
    def parentMesh(self):
        return self._parentMesh

    @parentMesh.setter
    def parentMesh(self, parentMesh):
        if parentMesh is None or not isinstance(parentMesh, Mesh):
            raise TypeError("'parentMesh' must be of type Mesh")

        self._parentMesh = parentMesh

    def addVertex(self, vertex):
        if vertex is None or not isinstance(vertex, Vertex):
            raise TypeError("'vertex' must be of type Vertex")

        if self._vertices is None:
            self._vertices = []

        self._vertices.append(vertex)

    @property
    def vertices(self):
        return self._vertices

    def __repr__(self):
        reprStr = "{{\n    ID: {!s}\n    TYPE: {!s}\n".format(self.id, self.type)

        if self.parentMesh is not None and self._vertices is not None:
            reprStr = reprStr + ("    TOTAL INDICES: {:d}\n    VERTICES:\n    [".format(len(self._vertices)))
            for ver in self._vertices:
                reprStr = reprStr + ("        {!r}\n".format(ver))
            reprStr = reprStr + "    ]\n"
        reprStr = reprStr + "}}\n"

        return reprStr


class Material(object):
    """Material associated with a geometry"""

    _id = ""

    _ambient = None

    _diffuse = None

    _emissive = None

    _opacity = None

    _specular = None

    _shininess = None

    _reflection = None

    _textures = []

    def __init__(self):
        self._id = ""
        self._ambient = None
        self._diffuse = None
        self._emissive = None
        self._opacity = None
        self._specular = None
        self._shininess = None
        self._reflection = None

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
    def ambient(self, ambient):
        self._ambient = ambient

    @property
    def diffuse(self):
        return self._diffuse

    @diffuse.setter
    def diffuse(self, diffuse):
        self._diffuse = diffuse

    @property
    def emissive(self):
        return self._emissive

    @emissive.setter
    def emissive(self, emissive):
        self._emissive = emissive

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
    def specular(self, specular):
        self._specular = specular

    @property
    def shininess(self):
        return self._shininess

    @shininess.setter
    def shininess(self, shininess):
        self._shininess = shininess

    @property
    def reflection(self):
        return self._reflection

    @reflection.setter
    def reflection(self, reflection):
        self._reflection = reflection

    @property
    def textures(self):
        return self._textures

    @textures.setter
    def textures(self, textures):
        self._textures = textures


class Animation(object):

    _id = ""

    _bones = None

    def __init__(self):
        self._id = ""
        self._bones = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, animationId):
        self._id = animationId

    @property
    def bones(self):
        return self._bones

    @bones.setter
    def bones(self, bones):
        if bones is None or not isinstance(bones, list):
            raise TypeError("'bones' must be of type list")

        self._bones = bones

    def addBone(self, bone):
        if bone is None or not isinstance(bone, NodeAnimation):
            raise TypeError("'bone' must be of type NodeAnimation")

        if self._bones is None:
            self._bones = []

        self._bones.append(bone)


class NodeAnimation(object):

    _boneId = ""

    _keyframes = None

    def __init__(self):
        self._boneId = ""
        self._keyframes = None

    @property
    def boneId(self):
        return self._boneId

    @boneId.setter
    def boneId(self, boneId):
        self._boneId = boneId

    @property
    def keyframes(self):
        return self._keyframes

    @keyframes.setter
    def keyframes(self, keyframes):
        if keyframes is None or not isinstance(keyframes, list):
            raise TypeError("'keyframes' must be of type list")

        self._keyframes = keyframes

    def addKeyframe(self, keyframe):
        if keyframe is None or not isinstance(keyframe, Keyframe):
            raise TypeError("'keyframe' must be of type Keyframe")

        if self._keyframes is None:
            self._keyframes = []

        self._keyframes.append(keyframe)


class Keyframe(object):
    _keytime = 0.0

    _translation = None

    _rotation = None

    _scale = None

    def __init__(self):
        self._keytime = 0.0
        self._rotation = None
        self._translation = None
        self._scale = None

    @property
    def keytime(self):
        return self._keytime

    @keytime.setter
    def keytime(self, keytime):
        self._keytime = keytime

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, rotation):
        self._rotation = rotation

    @property
    def translation(self):
        return self._translation

    @translation.setter
    def translation(self, translation):
        self._translation = translation

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        self._scale = scale


class G3DModel(object):
    """ Our model class that will later be exported to G3D """

    _meshes = None

    _materials = None

    _nodes = None

    _animations = None

    def __init__(self):
        self._meshes = []
        self._materials = []
        self._nodes = []
        self._animations = []

    @property
    def meshes(self):
        return self._meshes

    @meshes.setter
    def meshes(self, meshes):
        if meshes is None or not isinstance(meshes, list):
            raise TypeError("'meshes' must be a list of Mesh")

        self._meshes = meshes

    def addMesh(self, mesh):
        if mesh is None or not isinstance(mesh, Mesh):
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
        if materials is None or not isinstance(materials, list):
            raise TypeError("'materials' must be of type list")

        self._materials = materials

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, nodes):
        if nodes is None or not isinstance(nodes, list):
            raise TypeError("'nodes' must be of type list")

        self._nodes = nodes

    @property
    def animations(self):
        return self._animations

    @animations.setter
    def animations(self, animations):
        if animations is None or not isinstance(animations, list):
            raise TypeError("'animations' must be of type list")

        self._animations = animations
