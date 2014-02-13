#################################################################################
# Copyright 2014 See AUTHORS file.
#
# Licensed under the GNU General Public License Version 3.0 (the "LICENSE");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.gnu.org/licenses/gpl-3.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#################################################################################

from mathutils import Vector

class NormalMapHelper():

    def generate_tangent_binormal(self, mesh , face_vectors_out, vextex_vectors_out, uv_layer_name = ""):
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
            
        if (len(face_vectors_out) < len(mesh.polygons)):
            raise Exception("\"face_vectors_out\" must be an array of at least %d positions" % len(mesh.polygons))

        if (len(vextex_vectors_out) < len(mesh.vertices)):
            raise Exception("\"vextex_vectors_out\" must be an array of at least %d positions" % len(mesh.vertices))

        for pol_idx in range(len(mesh.polygons)):
            #    (v2 - v0).(p1 - p0) - (v1 - v0).(p2 - p0)
            #T = ---------------------------------------
            #    (u1 - u0).(v2 - v0) - (v1 - v0).(u2 - u0)
            
            #    (u2 - u0).(p1 - p0) - (u1 - u0).(p2 - p0)
            #B = ---------------------------------------
            #    (v1 - v0).(u2 - u0) - (u1 - u0).(v2 - v0)

            polygon = mesh.polygons[pol_idx]

            p0 = mesh.vertices[ polygon.vertices[0] ].co
            p1 = mesh.vertices[ polygon.vertices[1] ].co
            p2 = mesh.vertices[ polygon.vertices[2] ].co
            
            u0 = uv_layer.data[ polygon.loop_indices[0] ].uv[0]
            u1 = uv_layer.data[ polygon.loop_indices[1] ].uv[0]
            u2 = uv_layer.data[ polygon.loop_indices[2] ].uv[0]
            
            v0 = uv_layer.data[ polygon.loop_indices[0] ].uv[1]
            v1 = uv_layer.data[ polygon.loop_indices[1] ].uv[1]
            v2 = uv_layer.data[ polygon.loop_indices[2] ].uv[1]
            
            tangent = None
            binormal = None
            
            try:
                tangent = ((v2 - v0) * (p1 - p0) - (v1 - v0) * (p2 - p0)) / ((u1 - u0) * (v2 - v0) - (v1 - v0) * (u2 - u0))
            except Exception:
                tangent = None
            
            try:
                binormal = ((u2 - u0) * (p1 - p0) - (u1 - u0) * (p2 - p0)) / ((v1 - v0) * (u2 - u0) - (u1 - u0) * (v2 - v0))
            except Exception:
                binormal = None
                
            # Store tangent and binormal per vertex
            if vextex_vectors_out[ polygon.vertices[0] ] == None:
                vextex_vectors_out[ polygon.vertices[0] ] = [ Vector((0,0,0)) , Vector((0,0,0)) ]
                
            if vextex_vectors_out[ polygon.vertices[1] ] == None:
                vextex_vectors_out[ polygon.vertices[1] ] = [ Vector((0,0,0)) , Vector((0,0,0)) ]
                
            if vextex_vectors_out[ polygon.vertices[2] ] == None:
                vextex_vectors_out[ polygon.vertices[2] ] = [ Vector((0,0,0)) , Vector((0,0,0)) ]
            
            if tangent != None:
                vextex_vectors_out[ polygon.vertices[0] ][0] += tangent
                vextex_vectors_out[ polygon.vertices[1] ][0] += tangent
                vextex_vectors_out[ polygon.vertices[2] ][0] += tangent
            
            if binormal != None:
                vextex_vectors_out[ polygon.vertices[0] ][1] += binormal
                vextex_vectors_out[ polygon.vertices[1] ][1] += binormal
                vextex_vectors_out[ polygon.vertices[2] ][1] += binormal
            
            # Store tangent and binormal per face
            if tangent != None and binormal != None:
                face_vectors_out[pol_idx] = [tangent.normalized() , binormal.normalized()]
    
        # Normalize vertex vectors
        for vectors in vextex_vectors_out:
            vectors[0].normalize()
            vectors[1].normalize()

