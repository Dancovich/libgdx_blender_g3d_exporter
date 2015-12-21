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

# <pep8-80 compliant>

bl_info = {
    "name": "LibGDX G3D Exporter",
    "author": "Danilo Costa Viana",
    "version": (0, 2, 0),
    "blender": (2, 76, 0),
    "location": "File > Import-Export",
    "description": "Export scene to G3D (LibGDX) format",
    "category": "Import-Export"}

import bpy
from io_scene_g3d.model_generator import G3DExporter

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
