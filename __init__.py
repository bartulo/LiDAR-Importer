import bpy
import bmesh
import binascii
import struct
from laspy.file import File
import numpy as np
import multiprocessing
import time
import bgl

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, CollectionProperty
from bpy.types import Operator

# Blender Addon Information
# Used by User Preferences > Addons
bl_info = {
  "name" : "LiDAR Importer",
  "author" : "Brian C. Hynds, Bernardo Fontana", 
  "version" : (0, 1),
  "blender" : (2, 6, 0),
  "description" : "LiDAR File Importer with 3D Object Recognition",
  "category" : "Import-Export",
  "location" : "File > Import"
}

# Not In Use Yet: For implementing Multiprocessing Module
def worker(ImportLiDARData):
  print("")

# Not In Use Yet: For implementing Multiprocessing Module
def worker_complete(result):
  print("")

class ImportLiDARData(Operator, ImportHelper):
  """Load a LiDAR .las file"""
  bl_idname = "import_mesh.lidar"  # important since its how bpy.ops.import_mesh.lidar is constructed
  bl_label = "Import LiDAR File"

  # ImportHelper mixin class uses this
  filename_ext = ".las"
  files = CollectionProperty(name='File paths', type=bpy.types.OperatorFileListElement)

  filter_glob = StringProperty(
    default="*.las",
    options={'HIDDEN'}
    )

  # List of operator properties, the attributes will be assigned to the class instance from the operator settings before calling.
  pointCloudResolution = IntProperty(
    name="Point Resolution",
    min=1,
    max=100,
    description="This is a percentage resolution of the total point cloud to import.",
    default=100
    )

  cleanScene = BoolProperty(
    name="Empty Scene",
    description="Enable to remove all objects from current scene",
    default=True
    )
    
  classification = EnumProperty( items = (('2', 'ground', 'tierra'), ('3', 'low vegetation', 'verg'), ('4', 'medium vegetation', 'verg'), ('5', 'high vegetation', 'verg')))
    
  def execute(self, context):
    return read_lidar_data(context, self.filepath, self.pointCloudResolution, self.cleanScene, self.classification)

# Addon GUI Panel
class LiDARPanel(bpy.types.Panel):
  """LiDAR Addon Panel"""
  bl_label = "LiDAR Addon"
  bl_space_type = "VIEW_3D"
  bl_region_type = "TOOLS"
  bl_category = "LiDAR Tools"

  def draw(self, context):
    layout = self.layout
    row = layout.row()
    row.operator("import_mesh.lidar")

def read_lidar_data(context, filepath, pointCloudResolution, cleanScene, classification):

  print("running read_lidar_data")

  # importer start time
  start_time = time.time()

  # empty list for coordinates
  coords = []

  # reference to scene
  scn = bpy.context.scene

  # clear the scene if specified during file selection:
  if (cleanScene):
    for obj in scn.objects:
      obj.select = True
    bpy.ops.object.delete()

  # create a new mesh
  me = bpy.data.meshes.new("LidarMesh")

  # create a new object with the mesh
  obj = bpy.data.objects.new("LidarObject", me)
  bm = bmesh.new()
  bm.verts.new((0, 0, 0))
  bm.to_mesh(me)
  bm.free()

  # link the mesh to the scene
  scn.objects.link(obj)
  scn.objects.active = obj

  # Use this array for face construction if we decide to calculate them during import
  # faces = []

  # open the file
  f = File(filepath,mode='r')
  I = f.Classification == int(classification)
  num = len(f.points[I])
  p = len(bin(num)) - 3

  # lets get some header information from the file
  fileCount = f.header.count
  Xmed = (f.header.max[0] + f.header.min[0])/2
  Ymed = (f.header.max[1] + f.header.min[1])/2
  Zmed = (f.header.max[2] + f.header.min[2])/2
  
  #~ Xmax = f.header.max[0]
  #~ Ymax = f.header.max[1]
  #~ Zmax = f.header.max[2]

  #~ Xmin = f.header.min[0]
  #~ Ymin = f.header.min[1]
  #~ Zmin = f.header.min[2]
  
  a = f.x[I] - Xmed
  b = f.y[I] - Ymed
  c = f.z[I] - Zmed

  co = np.ravel(np.column_stack((a, b, c)))

  def potencia(p):
    bpy.ops.object.mode_set( mode = 'EDIT' )
    for i in range(p):
      bpy.ops.mesh.select_all(action='SELECT')
      bpy.ops.mesh.duplicate()
      bpy.ops.object.vertex_group_remove_from(use_all_groups=True)
      bpy.ops.object.vertex_group_assign_new()
    
  potencia(p)

  for ind, val in enumerate(bin(num)[:2:-1]):
    if val == '1':
      bpy.ops.mesh.select_all(action='DESELECT')
      # bpy.context.object.active_index = ind
      bpy.ops.object.vertex_group_set_active(group=bpy.context.object.vertex_groups[ind].name)
      bpy.ops.object.vertex_group_select()
      bpy.ops.mesh.duplicate()
        
  bpy.ops.object.mode_set( mode = 'OBJECT' )
        
  bpy.context.object.data.vertices.foreach_set('co', co)

  # use this value for limiting the maximum number of points.  Set to f.header.count for maximum.
  maxNumPoints = f.header.count
  currentPoint = 0
  wm = bpy.context.window_manager
  wm.progress_begin(0, maxNumPoints/10)

  # iterate through the point cloud and import the X Y Z coords into the array
  #~ for p in f.points[I]:
    #~ if maxNumPoints > 0:
      #~ coords.append((p[0][0]/100-Xmin-((Xmax-Xmin)/2), p[0][1]/100-Ymin-((Ymax-Ymin)/2), p[0][2]/100-Zmin))

      #~ if (((currentPoint/maxNumPoints)*100)%10 == 0):
        #~ wm.progress_update(currentPoint)

      #~ currentPoint +=1
      #~ maxNumPoints -= 1

    # Uncomment the following line for debugging purposes:
    # print("XYZ:", p.x, ",", p.y, ",", p.z)

  #~ me.from_pydata(coords,[],[])
  #~ me.update()

  # bpy.ops.object.mode_set(mode='EDIT', toggle=False)
  # bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

  print(str(fileCount), " verticies in file")
  print(str(currentPoint), " verticies imported")

  print("Total time to process (seconds): ", time.time() - start_time)
  print("File: ", filepath)

  print("completed read_lidar_data...")
  print("Percentage of points imported: ", pointCloudResolution)

  context.area.header_text_set()
  wm.progress_end()

  return {'FINISHED'}

# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
  self.layout.operator(ImportLiDARData.bl_idname, text="LiDAR Format (.las)")


def register():
  bpy.utils.register_class(ImportLiDARData)
  bpy.utils.register_class(LiDARPanel)
  bpy.types.INFO_MT_file_import.append(menu_func_import)

def unregister():
  bpy.utils.unregister_class(ImportLiDARData)
  bpy.utils.unregister_class(LiDARPanel)
  bpy.types.INFO_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
  register()

  # test call
  bpy.ops.import_mesh.lidar('INVOKE_DEFAULT')
