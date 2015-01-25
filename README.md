![logo](http://libgdx.badlogicgames.com/img/logo.png)
![logo](http://download.blender.org/institute/logos/blender-plain.png)

Blender G3D Exporter
====================

This is an addon for the Blender 3D modeling tool (http://www.blender.org). The purpose of this addon is to allow Blender to export 3D models as G3DJ files (G3D models written as JSON objects).

G3D is a custom 3D model file format compatible with the LibGDX framework (http://http://libgdx.badlogicgames.com/). The format is easy enough to allow use for other frameworks and is powerfull enough to support most features for game development, like multiple materials, multiple textures, different kinds of textures (diffuse maps, normal maps, etc.) and even armature based animations. The specification for this format can be found at [the project's wiki page](https://github.com/libgdx/fbx-conv/wiki) (work in progress).

This addon is currently compatible with Blender v2.69. I can't garantee compatibility with previous or future versions, but I'll try to update it if future Blender updates break compatibility.

This software is licensed under the [GNU General Public License Version 3.0](http://www.gnu.org/licenses/gpl-3.0.txt) (see LICENSE).

### Installation

You have to install this script as a Blender add-on. To do this copy the *io_scene_g3d* folder into the Blender *../scripts/addons* folder. These are the most common locations for this folder:

* **Windows 7 / 8** - C:\\Users\\%username%\\AppData\\Roaming\\Blender Foundation\\Blender\\_$version_\\scripts\\addons 
* **Windows XP** - C:\\Documents and Settings\\%username%\\Application Data\\Blender Foundation\\Blender\\_$version_\\scripts\\addons 
* **Linux** - /home/_$user_/.config/blender/_$version_/scripts/addons
* **All** (when addons are inside the Blender folder) - *$blender_folder*/*$version*/scripts/addons

After copying the folder to the correct place, open Blender and go to the *File -> User Preferences* menu under the Addons tab. Select the *Import-Export* category and enable the *LibGDX G3D Exporter* addon.

Usually you have to activate the addon for each new file. To have it already enabled for all new files first go to *File -> New* to reset your workspace (remember to save your work), enable the addon and then go to *File -> Save Startup File* to make this your default new file.

### Usage

To export a model simply load it into Blender and go to *File -> Export -> LibGDX G3D text format*. These are the current options you can use to configure the exporting process.

* **Selection Only** - Only export selected objects and armatures. The exporter is only able to export mesh objects and armatures; lights, cameras and other kind of objects are ignored. Default is *unchecked*.
* **Normals To** - Define which normals you want to export to your vertices. Options are *Face Normals* (each 3 vertices sharing a face will receive the face's normals), *Vertex Normals* (each vertex will receive the average normals of all faces sharing that vertex) and *Blender Normals* (respect the Smooth Vertex option in Blender, allow to have face normals for some vertices and vertex normals for others). Default is *Blender Normals*.
* **Export Armatures** - Uncheck to ignore armatures even if *Selection Only* is unchecked. Default is *checked*.
* **Export Actions as Animations** - Check to export actions as bone animations. Only used actions are exported, if you have several actions for a single armature use the *FAKE USER* option in Blender to make all actions *used* (have at least one user). Default is *checked*.
* **Export Tangent and Binormal Vectors** - Calculate tangent and binormal vectors for each vertex (used for Normal Mapping). You need to create an UV map for your model. The tangent and binormal will be exported as the *TANGENT* and *BINORMAL* vertex attributes. Default is *unchecked*.

### Features

These are some of the things that get exported by this script:

* Multiple materials for the same mesh (will create multiple mesh parts)
* Diffuse, specular, opacity and shininess material attributes
* Multiple UV coordinates for texture mapping
* Various kinds of texture mappings (diffuse, normal, transparency, specular)
* Armatures
* Multiple bone animations

### Limitations

These are the things to keep in mind when exporting to ensure your model gets exported correctly:

* **Blender uses Z-Up coordinates, LibGDX uses Y-Up** - When modeling remember that Blender uses Z-Up, that means if your game uses Y-Up (the camera UP vector is (0 , 1 , 0) ) by default you'll see your model from top-down perspective. The exporter will not try to change this. If you want to see your model  from the front by default you can rotate it -90º on the X axis in Blender or you can make your game Z-Up (make the camera's up vector be (0, 0, 1) ). Careful if you want to apply the rotation in Blender because that usually messes up animations.
* **Texture paths are exported as they are in Blender** - If your texture points to an absolute file path that's how it will get exported. As LibGDX only supports relative file paths please use the *File -> External Data -> Make All Paths Relative* option in Blender prior to exporting your model.
* **Some options are supported by the G3D file format but are not used on the default shader in LibGDX** - Normal maps are an example, you can export them but the default shader program in LibGDX will not read them. These limitations can change with future updates of LibGDX.
* **All bone weights must be normalized** - If you export armatures make sure all vertices have a bone weight to at least one bone. When exporting the BLENDWEIGHT vertex attribute LibGDX will always render vertices with no weight associated to them at the origin of the scene (location \[0, 0, 0\]), this is because the default shader in LibGDX expects bone weights to be normalized (total sum is 1.0) and the exporter can't normalize weights if they sum to zero. This problem doesn't happen if the mesh has no armature (no BLENDWEIGHT vertex attribute).
* **If your Blender mesh object has too many bones consider splitting it into different objects** - The default shader in LibGDX supports 12 bones per node part. This limit can be increased in code (setting the `DefaultShader.Config.numBones` property) but if your object is parented to an armature with more than 12 bones consider splitting it into multiple objects where each object has at most 12 bones. In fact try to keep each vertex weighted to at most 4 bones. The reason for this is that a bone is nothing more than a 4x4 matrix, meaning that each bone is composed of 16 floating point values giving a total of 192 floats for 12 bones. On a GPU there is a limited number of floats that can be stored per render pass - it varies depending of the GPU but to give an example the PowerVR SGX supports 512 floats on the vertex shader. Bottom line, try to keep the number of bones per object low. More info on the matter [can be found here](http://www.badlogicgames.com/forum/viewtopic.php?f=11&t=12910).
* **The JSON output file will have attributes in a different order than the files produced by _fbx-conv_** - Python saves dictionaries (associative arrays) in an arbitrary order. That means if you store an index *"meshes"* and then an index *"nodes"* it may store them in the reverse order. This doesn't affect the functionality so I chose to leave it as it is.

### About the license

The intention was to make this script licensed under the Apache License v2 (same as LibGDX) until I found out any Python scripts that use the Blender API need to be licensed under the GNU General Public License. The site says they're looking into a way to allow other licenses but until that this software will be licensed under GNU General Public License v3.

Any *.g3dj* files exported by this script are considered program output and as such are copyrighted to the user. You are free to use them as you see fit.
