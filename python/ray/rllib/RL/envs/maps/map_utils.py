"""
Functions / Objects for occupancy grid maps.

!!IMPORTANT!! xy-rc coordinate relation:
2D map. (xmin, ymin) is located at the bottom left corner.
rows are counted from the bottom to top.
columns are counted from left to right. 

Matplotlib.pyplot displays a matrix with (r,c)=(0,0) located at the top left. 
Therefore, in the display_wrapper, the map is flipped.
"""
import numpy as np 
from numba import jit
import pdb
import yaml

def round(x):
  if x >= 0:
    return int(x+0.5)
  else:
    return int(x-0.5)

class GridMap(object):
  def __init__(self, map_path, r_max=1.0, fov=np.pi):
    map_config = yaml.load(open(map_path+".yaml", "r"))
    self.map = np.loadtxt(map_path+".cfg")
    if 'empty' in map_path:
      self.map = None
    else:
      self.map_linear = np.squeeze(self.map.astype(np.int8).reshape(-1, 1))
    self.mapdim = map_config['mapdim']
    self.mapres = np.array(map_config['mapres'])
    self.mapmin = np.array(map_config['mapmin'])
    self.mapmax = np.array(map_config['mapmax'])
    self.origin = map_config['origin']
    self.r_max = r_max
    self.fov = fov

  def se2_to_cell(self, pos):
    pos = pos[:2]
    cell_idx = (pos - self.mapmin)/self.mapres - 0.5
    return round(cell_idx[0]), round(cell_idx[1])

  def cell_to_se2(self, cell_idx):
    return ( np.array(cell_idx) + 0.5 ) * self.mapres + self.mapmin

def bresenham2D(sx, sy, ex, ey):
  """
  Bresenham's ray tracing algorithm in 2D from ESE650 2017 TA resources
  Inputs:
  (sx, sy)  start point of ray
  (ex, ey)  end point of ray
  Outputs:
    Indicies for x-axis and y-axis
  """
  sx = int(round(sx))
  sy = int(round(sy))
  ex = int(round(ex))
  ey = int(round(ey))
  dx = abs(ex-sx)
  dy = abs(ey-sy)
  steep = abs(dy)>abs(dx)
  if steep:
    dx,dy = dy,dx # swap 

  if dy == 0:
    q = np.zeros((dx+1,1))
  else:
    q = np.append(0,np.greater_equal(np.diff(np.mod(np.arange( np.floor(dx/2), -dy*dx+np.floor(dx/2)-1,-dy),dx)),0))
  if steep:
    if sy <= ey:
      y = np.arange(sy,ey+1)
    else:
      y = np.arange(sy,ey-1,-1)
    if sx <= ex:
      x = sx + np.cumsum(q)
    else:
      x = sx - np.cumsum(q)
  else:
    if sx <= ex:
      x = np.arange(sx,ex+1)
    else:
      x = np.arange(sx,ex-1,-1)
    if sy <= ey:
      y = sy + np.cumsum(q)
    else:
      y = sy - np.cumsum(q)
  return np.vstack((x,y)).astype(np.int16)

#@jit
def coord_change2g(vec, ang):
    assert(len(vec) == 2)
    # R * v
    return np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])@vec

#@jit
def is_collision_ray_cell(map_obj, cell):
  """
  cell : cell r, c index from left bottom.
  """
  idx = cell[0] + map_obj.mapdim[0] * cell[1]
  if (cell[0] < 0) or (cell[1] < 0) or (cell[0] >= map_obj.mapdim[0]) or (cell[1] >= map_obj.mapdim[1]):
    return True
  #elif (map_obj.map is not None) and map_obj.map[cell[0], cell[1]] == 1:
  elif (map_obj.map is not None) and map_obj.map_linear[idx] == 1:
    return True
  else:
    return False
#@jit
def is_blocked(map_obj, start_pos, end_pos):
  if map_obj.map is None:
    return False
  start_rc = map_obj.se2_to_cell(start_pos)
  end_rc = map_obj.se2_to_cell(end_pos)
  ray_cells = bresenham2D(start_rc[0], start_rc[1], end_rc[0], end_rc[1])
  i = 0
  while(i < ray_cells.shape[-1]):
    if is_collision_ray_cell(map_obj, ray_cells[:,i]):
        return True
    i += 1
  return False

#@jit
def get_cloest_obstacle(map_obj, odom, ang_res=0.05):
  """
    Return the closest obstacle/boundary cell
  """
  ang_grid = np.arange(-.5*map_obj.fov, .5*map_obj.fov, ang_res)
  closest_obstacle = (map_obj.r_max, 0.0)
  start_rc = map_obj.se2_to_cell(odom[:2])
  for ang in ang_grid:
    end_pt_global_frame = coord_change2g(np.array([map_obj.r_max*np.cos(ang), map_obj.r_max*np.sin(ang)]), odom[-1]) + odom[:2]
    
    if map_obj.map is None:
      if not(in_bound(map_obj, end_pt_global_frame)):
        end_rc = map_obj.se2_to_cell(end_pt_global_frame)
        ray_cells = bresenham2D(start_rc[0], start_rc[1], end_rc[0], end_rc[1])
        i = 0
        while(i < ray_cells.shape[-1]):
          pt = map_obj.cell_to_se2(ray_cells[:,i]) 
          if not(in_bound(map_obj, pt)):
            break
          i += 1
        if i < ray_cells.shape[-1]: # break!
          ro_min_t = np.sqrt(np.sum(np.square(pt - odom[:2])))
          if ro_min_t < closest_obstacle[0]:
            closest_obstacle = (ro_min_t, ang)

    else:
      end_rc = map_obj.se2_to_cell(end_pt_global_frame)
      ray_cells = bresenham2D(start_rc[0], start_rc[1], end_rc[0], end_rc[1])
      i = 0
      while(i < ray_cells.shape[-1]): # break!
        if is_collision_ray_cell(map_obj, ray_cells[:,i]):
            break
        i += 1
      if i < ray_cells.shape[-1]:
        ro_min_t = np.sqrt(np.sum(np.square(map_obj.cell_to_se2(ray_cells[:,i]) - odom[:2])))
        if ro_min_t < closest_obstacle[0]:
          closest_obstacle = (ro_min_t, ang)

  if closest_obstacle[0] == map_obj.r_max:
    return None
  else:
    return closest_obstacle

def is_collision(map_obj, pos, margin=0.5):
  if not(in_bound(map_obj, pos, margin)):
    return True
  else:
    if map_obj.map is not None:
      n = np.ceil(margin/map_obj.mapres).astype(np.int16)
      cell = np.minimum([map_obj.mapdim[0]-1,map_obj.mapdim[1]-1] , map_obj.se2_to_cell(pos))
      for r_add in np.arange(-n[1],n[1],1):
        for c_add in np.arange(-n[0],n[0],1):
          x_c = np.clip(cell[0]+r_add, 0, map_obj.mapdim[0]-1).astype(np.int16)
          y_c = np.clip(cell[1]+c_add,0,map_obj.mapdim[1]-1).astype(np.int16)
          idx = x_c + map_obj.mapdim[0] * y_c 
          if map_obj.map_linear[idx] == 1:
            return True
  return False

#@jit
def in_bound(map_obj, pos,  margin=0.5):
  return not((pos[0] < map_obj.mapmin[0]+margin) or (pos[0] > map_obj.mapmax[0]-margin) or (pos[1] < map_obj.mapmin[1]+margin) or (pos[1] > map_obj.mapmax[1]-margin))

def local_map(map_obj, im_size, odom):
  """
  im_size : the number of rows/columns
  """
  R=np.array([[np.cos(odom[2] - np.pi/2), -np.sin(odom[2] - np.pi/2)],
              [np.sin(odom[2] - np.pi/2), np.cos(odom[2] - np.pi/2)]])
  
  local_map = np.zeros((im_size, im_size))
  local_mapmin = np.array([-im_size/2*map_obj.mapres[0], 0.0])
  for r in range(im_size):
    for c in range(im_size):
      xy_local = cell_to_se2([r,c], local_mapmin, map_obj.mapres)
      xy_global = np.matmul(R, xy_local) + odom[:2]
      local_map[c,r] = int(is_collision_ray_cell(map_obj, map_obj.se2_to_cell(xy_global)))
  # indvec = np.reshape([[[r,c] for r in range(im_size)] for c in range(im_size)], (-1,2))
  # xy_local = cell_to_se2_batch(indvec, local_mapmin, map_obj.mapres)
  # xy_global = np.add(np.matmul(R, xy_local.T).T odom[:2])

  return local_map

def se2_to_cell(pos, mapmin, mapres):
  pos = pos[:2]
  cell_idx = (pos - mapmin)/mapres - 0.5
  return round(cell_idx[0]), round(cell_idx[1])

def cell_to_se2(cell_idx, mapmin, mapres):
  return ( np.array(cell_idx) + 0.5 ) * mapres + mapmin

def se2_to_cell_batch(pos, mapmin, mapres):
  """
  Coversion for Batch input : pos = [batch_size, 2 or 3]

  OUTPUT: [batch_size,], [batch_size,]
  """
  return round((pos[:,0] - mapmin[0])/mapres[0] - 0.5), round((pos[:,1] - mapmin[1])/mapres[1] - 0.5)

def cell_to_se2_batch(cell_idx, mapmin, mapres):
  """
  Coversion for Batch input : cell_idx = [batch_size, 2]

  OUTPUT: [batch_size, 2]  
  """
  return (cell_idx[:,0] + 0.5) * mapres[0] + mapmin[0], (cell_idx[:,1] + 0.5) * mapres[1] + mapmin[1]


def generate_trajectory(map_obj):
  import matplotlib
  matplotlib.use('TkAgg')
  from matplotlib import pyplot as plt
  from scipy.interpolate import interp1d

  ax = plt.gca()
  fig = plt.gcf()
  implot = ax.imshow(map_obj.map, cmap='gray_r', origin='lower', extent=[map_obj.mapmin[0], map_obj.mapmax[0], map_obj.mapmin[1], map_obj.mapmax[1]])

  path_points = []
  def onclick(event):
    if event.xdata != None and event.ydata != None:
      ax.plot(event.xdata, event.ydata, 'ro')
      plt.draw()
      path_points.append([event.xdata, event.ydata])
  cid = fig.canvas.mpl_connect('button_press_event', onclick)

  plt.show()
  print("%d points selected"%len(path_points))
  path_points = np.array(path_points)
  interpol_num = 5
  passed = False
  vel = 0.5
  while(not passed):
    ax = plt.gca()
    fig = plt.gcf()
    implot = ax.imshow(map_obj.map, cmap='gray_r', origin='lower', extent=[map_obj.mapmin[0], map_obj.mapmax[0], map_obj.mapmin[1], map_obj.mapmax[1]])
  
    sorted_paths = []
    newx = []
    newy = []

    t_done = False
    t = 1
    while(not t_done):
      tmp = [path_points[t-1]]
      tmp_x = []
      while((path_points[t-1,0] < path_points[t,0])):
        tmp.append(path_points[t])
        distance = np.sqrt(np.sum(np.square( path_points[t] - path_points[t-1] )))
        num = distance / (0.5 * vel)
        tmp_x.extend(np.linspace(path_points[t-1,0], path_points[t,0], num=num, endpoint=False))
        t += 1
        if t >= len(path_points):
          t_done = True
          break
      if len(tmp) > 1:
        tmp = np.array(tmp)
        f0 = interp1d(tmp[:,0], tmp[:,1], kind='cubic')
        newx.extend(tmp_x)
        newy.extend(f0(np.array(tmp_x)))
        sorted_paths.append(tmp)
        if t_done:
          break

      tmp = [path_points[t-1]]
      tmp_x = []
      while((path_points[t-1,0] >= path_points[t,0])):
        tmp.append(path_points[t])
        distance = np.sqrt(np.sum(np.square( path_points[t] - path_points[t-1] )))
        num = distance / (0.5 * vel)
        tmp_x.extend(np.linspace(path_points[t-1,0], path_points[t,0], num=num, endpoint=False))
        t += 1
        if t >= len(path_points):
          t_done = True
          break
      tmp = np.array(tmp)
      f0 = interp1d(np.flip(tmp[:,0], -1), np.flip(tmp[:,1], -1), kind='cubic')
      newx.extend(tmp_x)
      newy.extend(f0(np.array(tmp_x)))
      sorted_paths.append(tmp)
    
    ax.plot(path_points[:,0], path_points[:,1],'ro')
    ax.plot(newx, newy,'b.')
    print("Total point number: %d"%len(newx))
    plt.show()
    if len(newx) > 150:
      passed = True
    else:
      interpol_num += 1
  newx = np.array(newx)
  newy = np.array(newy)
  x_vel = (newx[1:]-newx[:-1])/0.5
  y_vel = (newy[1:]-newy[:-1])/0.5
  theta = np.arctan2(newy[1:]-newy[:-1], newx[1:]-newx[:-1])

  final = np.concatenate((newx[:-1, np.newaxis], newy[:-1, np.newaxis], theta[:,np.newaxis], x_vel[:,np.newaxis], y_vel[:,np.newaxis]), axis=1)
  np.save(open("path_sh_0.npy", "wb"), final)




