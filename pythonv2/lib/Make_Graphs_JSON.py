import sys
import os
import json
import numpy as np
import cv2
import statistics 
import requests 
import glob

from lib.FileIO import cfe, save_json_file, load_json_file
from lib.VIDEO_VARS import HD_W, HD_H
from lib.MeteorReduce_Tools import get_cache_path, does_cache_exist


DEFAULT_IFRAME = "<div class='load_if'><iframe width='100%' height='517' style='margin:.5rem auto' frameborder='false' data-src='{CONTENT}'></iframe></div>"
DEFAULT_PATH_TO_GRAPH = "/pycgi/graph.html?json_file={JSONPATH}&graph_config={GRAPH_CONFIG}"
PATH_TO_GRAPH_LAYOUTS = "/pycgi/dist/graphics/"

# Predefined GRAPH LAYOUT
TRENDLINE_GRAPHICS = PATH_TO_GRAPH_LAYOUTS + 'trendline.js'


# Return an iframe with a graph or nothing if we don't have enough data
# for this graph type
def make_plot(graph_name,meteor_json_data,analysed_name,clear_cache):

   # Do we have a JSON ready this graph?
   path_to_json = get_graph_file(meteor_json_data,analysed_name,graph_name,clear_cache)
  
   if(path_to_json is None):

      if(graph_name=="xy"):

         # Get the data
         if('frames' in meteor_json_data):
            if len(meteor_json_data['frames']) > 2:
               json_graph_content = create_xy_graph(meteor_json_data['frames'],analysed_name,clear_cache)
               
               if(json_graph_content is not None):
                  
                  # We save it at the right place
                  path_to_json = get_cache_path(analysed_name,"graphs")+graph_name+'.json'

                  # We save it
                  save_json_file(path_to_json,json_graph_content)
 
   else:
      if(graph_name=="xy"):
         return create_iframe_to_graph(analysed_name,graph_name,path_to_json,TRENDLINE_GRAPHICS)


# Build the iFrame 
# Create the corresponding JSON file for the Graph
# and create the iframe with file=this json
def create_iframe_to_graph(analysed_name,name,path_to_json,graph_config):
   # Create iframe src
   src =  DEFAULT_PATH_TO_GRAPH.replace('{JSONPATH}', path_to_json)
   src = src.replace('{GRAPH_CONFIG}',graph_config)

   return DEFAULT_IFRAME.replace('{CONTENT}',src)


# Get a graph.json or create it 
def get_graph_file(meteor_json_file,analysed_name,name,clear_cache):

    # CREATE or RETRIEVE TMP JSON FILE UNDER /GRAPH (see REDUCE_VARS)  
   json_graph = does_cache_exist(analysed_name,'graphs',name+'.json')
 

   print("JSON GRAPH<br>")
   print(json_graph)
   print("<br>len(json_graph)<br>")
   print(str(len(json_graph)))
   print("<br>clear_cache<br>")
   print(str(clear_cache)) 
   
   path_to_json = None
   
   if  len(json_graph)==0  and clear_cache is True :
      print("COND1<br>")

      # We need to create the JSON
      path_to_json = get_cache_path(analysed_name,"graphs")+name+'.json'

      # We delete the file  
      try:
         os.remove(path_to_json) 
      except:
         x=0 # Nothing here as if it fails, it means the file wasn't there anyway (?)
  
   else: 

      # We return them 
      path_to_json = glob.glob(get_cache_path(analysed_name,"graphs")+name+'.json') 

      if(path_to_json is not None and len(path_to_json)>0):
         path_to_json = path_to_json[0]
   

   print("FROM GET GRAPH FILE - PATH TO JSON<br>")
   print(path_to_json)
   sys.exit(0)

   return path_to_json
 


# Clear GRAPH CACHE
def clear_graph_cache(meteor_json_file,analysed_name,graph_type):
   # Clear basic plot
   if(graph_type=='xy'):
      make_basic_plots(meteor_json_file, analysed_name, True)

 
# Create 2 different plots when possible
# 1- X,Y position 
# 2- Light Curves
def make_basic_plots(meteor_json_file, analysed_name, clear_cache):
   plots = ''
   if 'frames' in meteor_json_file:   
      if len(meteor_json_file['frames']) > 0:  
         # Main x,y plot 
         plots = make_xy_point_plot(meteor_json_file['frames'],analysed_name, clear_cache)
         # + Curve Light
         plots += make_light_curve(meteor_json_file['frames'],analysed_name, clear_cache)
   
   return plots




# Basic X,Y Plot with regression (actually a "trending line")
def make_xy_point_plot(frames,analysed_name, clear_cache):

   # Do we have the json ready?

   xs = []
   ys = []
 
   for frame in frames:
      xs.append(frame['x']) 
      ys.append(frame['y']) 
 
   if(len(xs)>2):

      trend_x, trend_y = poly_fit_points(xs,ys)  
    
      tx1 = []
      ty1 = []

      for i in range(0,len(trend_x)):
         tx1.append(int(trend_x[i]))
         ty1.append(int(trend_y[i]))
  
      return   {'title':'XY Points and Trendline',
                'x1_vals':  xs,
                'y1_vals': ys,
                'x2_vals': tx1,
                'y2_vals': ty1,
                'y1_reverse':1,
                'title1': 'Meteor pos.',
                'title2': 'Trend. val.',
                's_ratio1':1} 
   return None


# Curve Light
def make_light_curve(frames, analysed_name, clear_graph_cache):
   lc_cnt = []
   lc_ff = []
   lc_count = []
   
   if(len(frames)>1):
      for frame in frames:
         if "intensity" in frame and "intensity_ff" in frame:
             if frame['intensity']!= '?' and frame['intensity']!= '9999':
               lc_count.append(frame['dt'][14:]) # Get Min & Sec from dt
               lc_cnt.append(frame['intensity']) 
               lc_ff.append(frame['intensity_ff']) 
 
      return create_iframe_to_graph({
           'title':'Light Intensity',
           'title1': 'Intensity',
           'x1_vals':  lc_count,
           'y1_vals':  lc_cnt, 
           'linetype1': 'lines+markers',
           'lineshape1': 'spline'
            })
   return ''






 








# Get "trendingline"
def get_fit_line(poly_x, poly_y):
  return np.unique(poly_x), np.poly1d(np.polyfit(poly_x, poly_y, 1))(np.unique(poly_x))
 
# Compute the fit line of a set of data (MIKE VERSION)
def poly_fit_points(poly_x,poly_y, z = None):
   if z is None:
      if len(poly_x) >= 3:
         try:
            z = np.polyfit(poly_x,poly_y,1)
            f = np.poly1d(z)
         except:
            return 0
      else:
         return 0

      trendpoly = np.poly1d(z)
      new_ys = trendpoly(poly_x)

   return(poly_x, new_ys)
 


# Create 3D Light Curve Graph
def make3D_light_curve(meteor_json_file,hd_stack):
 
   xvals = []
   yvals = []
   zvals = []


   for x in range(0, HD_W):
      xvals.append(x)
   
   for y in range(0, HD_H):
      yvals.append(y)

   for z in range(0, 255):
      zvals.append(0)

   image = cv2.imread(hd_stack)

   for f in meteor_json_file['frames']:   
      try:
         #xvals.append(f['x'])
         #yvals.append(f['y'])
         zvals.append(statistics.mean(image[int(f['y']),int(f['x'])]))  # Average of the 3 VALUES
      except:
         partial = True
   
   if len(xvals)>0 and len(yvals)>0 and len(zvals)>0:
      return create_iframe_to_graph({
         'title':'3D Light Topography',
         'x1_vals': str(xvals),
         'y1_vals':str(yvals),
         'z1_vals':str(zvals) 
      })
   else:
      return ''



   #partial = False 
   #if 'frames' in meteor_json_file:   
   #   if len(meteor_json_file['frames']) > 0:  
#
   #      image = cv2.imread(hd_stack)
#      for f in meteor_json_file['frames']:   
   #         try:
   #            xvals.append(f['x'])
   #            yvals.append(f['y'])
   #            zvals.append(statistics.mean(image[int(f['y']),int(f['x'])]))  # Average of the 3 colors
    #        except:
    #           partial = True
 
