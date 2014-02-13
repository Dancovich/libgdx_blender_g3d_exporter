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

bl_info = {
    "name":      "LibGDX G3D Exporter",
    "author":      "Danilo Costa Viana",
    "blender":    (2,6,9),
    "version":    (0,1,0),
    "location":  "File > Import-Export",
    "description":  "Export scene to G3D (LibGDX) format",
    "category":  "Import-Export"
}
        
import bpy
from io_scene_g3d.export_g3d import G3DExporter

class Mesh(object):
    def __init__(self, s):
        self.s = s
    def __repr__(self):
        return '<Mesh(%s)>' % self.s

def menu_func(self, context):
    self.layout.operator(G3DExporter.bl_idname, text="LibGDX G3D text format (.g3dj)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)
    
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()

