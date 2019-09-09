import sys
import cgitb
import json

from lib.FileIO import cfe, load_json_file 

 

# Return the JSON Files from a given reduction
# with modified info
def get_reduction_info(json_file):

   # Debug
   cgitb.enable()
  
   # Cnters
   total_res_deg = 0 
   total_res_px = 0 
   max_res_deg = 0 
   max_res_px = 0 

   # Output
   rsp = {}

   if cfe(json_file) == 1:

      # We load the JSON
      mr = load_json_file(json_file) 

      if "cal_params" in mr:
         if "cat_image_stars" in mr['cal_params']:

            # Get all the stars and compute max_res_deg & max_res_px
            rsp['cat_image_stars'] = mr['cal_params']['cat_image_stars'] 
            sc = 0
            for star in mr['cal_params']['cat_image_stars']:
               (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) = star
               max_res_deg = float(max_res_deg) + float(match_dist)
               max_res_px = float(max_res_px) + float(cat_dist )
               sc = sc + 1

            if "total_res_px" in mr['cal_params']:
               rsp['total_res_px']  = mr['cal_params']['total_res_px']
               rsp['total_res_deg'] = mr['cal_params']['total_res_deg']

            elif len(mr['cal_params']['cat_image_stars']) > 0:
               rsp['total_res_px']  = max_res_px/ sc
               rsp['total_res_deg'] = (max_res_deg / sc)  

         new_mfd = []
         
         if "meteor_frame_data" in mr: 
            temp = sorted(mr['meteor_frame_data'], key=lambda x: int(x[1]), reverse=False)

            for frame_data in temp:      
               frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data 
               new_mfd.append((frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el)) 

            rsp['meteor_frame_data'] = new_mfd
          
      rsp['status'] = 1
   else: 
      rsp['status'] = 0
         

   print(json.dumps(rsp))
