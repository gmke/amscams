#!/usr/bin/python3
import ephem
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from lib.flexCal import flex_get_cat_stars
#import datetime
import time
import glob
import os
import math
import cv2
import math
import cgitb
import numpy as np
import scipy.optimize
from fitMulti import minimize_poly_params_fwd
from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames
from lib.UtilLib import check_running, get_sun_info, fix_json_file, find_angle

from lib.ImageLib import mask_frame , stack_frames, thumb
#import matplotlib
#matplotlib.use('Agg')
#import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg, define_crop_box
from lib.UtilLib import calc_dist, find_angle, bound_cnt, cnt_max_px

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt

show = 1
json_conf = load_json_file("../conf/as6.json")

def make_plate_from_points(in_file, out_file, points, json_conf ):
   print("IN:", in_file)
   print("OUT:", out_file)
   print("POINTS:", points)
   if "mp4" in in_file :
      extract_one_frame(in_file,out_file)
   
   hd_stack_file = in_file
   hd_stack_img = cv2.imread(hd_stack_file,0)
   shp = hd_stack_img.shape
   ih,iw = shp[0],shp[1]
   sd = 0
   if iw < 1920:
      sd = 1

   hdm_x = 2.7272
   hdm_y = 1.875

   plate_img = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_file_an = hd_stack_file.replace(".png", "-an.png")

   hd_stack_img = cv2.imread(hd_stack_file,0);
   star_points = []
   for x,y,i in points:
      x,y = int(x),int(y)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      x1,y1,x2,y2= bound_cnt(x,y,iw,ih,15)
      cnt_img = hd_stack_img[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      max_pnt,max_val,min_val = cnt_max_px(cnt_img)
      mx,my = max_pnt
      mx = mx - 15
      my = my - 15
      cy1 = y + my - 15
      cy2 = y + my +15
      cx1 = x + mx -15
      cx2 = x + mx +15
      cx1,cy1,cx2,cy2= bound_cnt(x+mx,y+my,iw,ih)
      print("CX:", cx1,cy1,cx2,cy2)
     
      if ch > 0 and cw > 0:
         cnt_img = hd_stack_img[cy1:cy2,cx1:cx2]
         bgavg = np.mean(cnt_img)
         cnt_img = clean_star_bg(cnt_img, bgavg + 3)

         star_points.append([x+mx,y+my])
         #if abs(cy1- (ih/2)) <= (ih/2)*.8 and abs(cx1- (iw/2)) <= (iw/2)*.8:
         plate_img[cy1:cy2,cx1:cx2] = cnt_img

   points_json = {}
   points_json['user_stars'] = points 


   points_file = hd_stack_file.replace(".png", "-user-stars.json")
   save_json_file(points_file,points_json)


   cv2.imwrite(out_file, plate_img)
   print(out_file)
   cv2.imshow('plate', plate_img)
   cv2.waitKey(0)

def day_or_night(capture_date, json_conf):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"
   return(sun_status)


def blind_solve_night():
   now = datetime.now()
   day = now.strftime("%Y_%m_%d")
   if cfe("/mnt/ams2/temp", 1) == 0:
      os.makedirs("/mnt/ams2/temp")

   pos_solve_imgs = [] 
   for cam in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam]['cams_id']
      hd_glob = "/mnt/ams2/HD/" + day + "*" + cam_id + ".mp4"
      hd_files = glob.glob(hd_glob)
      fc = 0
      for file in hd_files:
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         plate_file = file.replace(".mp4", ".jpg")
         pf = plate_file.split("/")[-1]
         plate_file = "/mnt/ams2/temp/" + pf
         img_file = plate_file.replace(".jpg", ".png")
         sun_status = day_or_night(f_datetime, json_conf)
         if sun_status == 'night':
            if fc % 60 == 0:
               print(file, sun_status)
               if cfe(plate_file) == 0: 
                  extract_one_frame(file, img_file)
                  stars,img,oimg = get_image_stars(img_file, None, 0)
                  if len(stars) > 10:
                     make_plate_from_points(img_file, plate_file, stars, json_conf )
                     print("stars:", len(stars))
                     show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
                     print(stars)
                     pos_solve_imgs.append((file, stars, cam))
         
         fc += 1

   cal_files = {}

   temp = sorted(pos_solve_imgs, key=lambda x: x[1], reverse=True)
   for data in temp:
      file, stars, cam = data

def extract_one_frame(file, out_file):

   cmd = "/usr/bin/ffmpeg -y -i " + file + " -ss 00:00:01 -vframes 1 " + out_file
   os.system(cmd)


def astro_integrity():
    # for each cam, for each day in the meteors dir
    # check to see if stars can be found with good res error
    # if not then a new calibration may be needed. 
    # identify the blocks where calibs fail 
    # and then blind solve around that time until a success is made
    cams = []
    for cam in json_conf['cameras']:
       cam_id = json_conf['cameras'][cam]['cams_id']
       cams.append(cam_id)

    print("CAMS:", cams)

    meteor_dir = "/mnt/ams2/meteors/*" 
    meteor_dirs = glob.glob(meteor_dir)
    meteor_dict = {}
    for dir in meteor_dirs:
       date = dir.split("/")[-1]
       if date not in meteor_dict:
          print("DATE", date)
          meteor_dict[date] = {}
       meteor_dict[date]['files'] = get_meteor_files(dir, cams)
       print("FILES:", date, meteor_dict[date]['files'])

    save_json_file("/mnt/ams2/cal/astro_integrity.json", meteor_dict)
    print("/mnt/ams2/cal/astro_integrity.json")

def get_meteor_files(dir, cams):
   cam_files = []
   for cam in cams:
      print(dir+ "/*" + cam +"*.json")
      files = glob.glob(dir + "/*" + cam +"*.json")
      print("LEN FILES:", len(files))
      for file in files:
         if "reduced" not in file and "import" not in file and "star" not in file and "manual" not in file:
            jd = load_json_file(file)
            if 'hd_trim' in jd:
               print(file, jd['hd_trim'])
               if jd['hd_trim'] is not None and jd['hd_trim'] != 0:
                  img_file = jd['hd_trim'].replace(".mp4", "-stacked.png")
                  if "/mnt/ams2/HD" in img_file:
                     ifn = img_file.split("/")[-1]
                     mdir = ifn[0:10]
                     img_file = "/mnt/ams2/meteors/" + mdir + "/" + ifn
                  if cfe(img_file) == 1:
                     img = cv2.imread(img_file, 0)
                     if img is not None:
                        stars = get_image_stars(img_file, img, 0)
                        if show == 1:
                           show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
                           cv2.imshow('pepe', show_img)
                           cv2.waitKey(30)
                        if len(stars) > 15:
                           data = {}
                           data['file'] = file
                           data['img_stars'] = stars
                           data['img_file'] = img_file
                           print("ADDING FILE:", file, len(stars))
                           cam_files.append(data)
                        else:
                           print("Too few stars:", len(stars))
                           #exit()
                     else:
                        print("Image is none!", img_file, file)
                        #exit()
                  else:
                     print("FAILED TO LOAD HD IMAGE:", img_file, file)
                     #exit()
            else:
               print("NO HD TRIM:", file)
               #exit()
      
   return(cam_files)   

def get_image_stars(file,img=None, show=0):
   print("SHOW IS:", show)
   print("FILEIS:", file)
   stars = []
   if img is None:
      img = cv2.imread(file, 0)
   oimg = img.copy()
   avg = np.mean(img)
   best_thresh = avg + 15
   
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   cv2.imshow('ppp', thresh_obj)
   cv2.waitKey(0)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   cc = 0
   for (i,c) in enumerate(cnts):
      cx,cy,w,h = cv2.boundingRect(cnts[i])
      cnt_img = img[cy:cy+h,cx:cx+w]
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
      max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img.copy())
      
      name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
      #star_test = test_star(cnt_img)
      #x = x + int(w/2)
      #y = y + int(h/2)
      mx,my = max_loc
      x = cx + mx 
      y = cy + my
      print("CNT:", x,y,w,h, px_diff)
      if px_diff > 10 and w > 1 and h > 1 and w < 20 and h < 20:
         if 100 < x < 1820 and 50 < y < 1030:
            stars.append((x,y,int(max_px)))
            cv2.circle(img,(x,y), 5, (128,128,128), 1)

      cc = cc + 1
   if show == 1:
      cv2.imshow('pepe', img)
      cv2.waitKey(0)

   temp = sorted(stars, key=lambda x: x[2], reverse=True)
   stars = temp[0:50]
   print("STARS:", stars)
   return(stars, img, oimg)

def find_best_cat_stars(cat_stars, ix,iy, frame, cp_file):
   cat_image_star = None
   cx1,cy1,cx2,cy2 = bound_cnt(ix,iy,frame.shape[1],frame.shape[0], 5)
   intensity = int(np.sum(frame[cy1:cy2,cx1:cx2]))
   min_dist = 100 
   min_star = None
   for cat_star in cat_stars:
      name,mag,ra,dec,new_cat_x,new_cat_y = cat_star

      dist = calc_dist((new_cat_x, new_cat_y), (ix,iy))
      if dist < min_dist and mag < 4:
         #print("DIST:", dist, cat_star)
         min_dist = dist
         min_star = cat_star
   if min_star is not None:
      name,mag,ra,dec,new_cat_x,new_cat_y = min_star
      px_dist = 0
      cat_image_star = ((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,intensity,min_dist,cp_file))
   return(cat_image_star)


def get_best_cal_file(input_file):

   #print("INPUT FILE", input_file)
   if "png" in input_file:
      input_file = input_file.replace(".png", ".mp4")
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)

   # find all cal files from his cam for the same night
   matches = find_matching_cal_files(json_conf['site']['ams_id'], cam_id, f_datetime)
   #print("MATCHED:", matches)
   if len(matches) > 0:
      return(matches)
   else:
      return(None)

def find_matching_cal_files(station_id, cam_id, capture_date):
   matches = []
   #cal_dir = ARCHIVE_DIR + station_id + "/CAL/*.json"
   cal_dir = "/mnt/ams2/cal/freecal/*"
   all_files = glob.glob(cal_dir)
   for file in all_files:
      if cam_id in file :
         el = file.split("/")
         fn = el[-1]
         cp = file + "/" + fn + "-stacked-calparams.json"
         if cfe(cp) == 1:
            matches.append(cp)
         else:
            cp = file + "/" + fn + "-calparams.json"
            if cfe(cp) == 1:
               matches.append(cp)

   td_sorted_matches = []

   for match in matches:
      (t_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(match)
      tdiff = abs((capture_date-t_datetime).total_seconds())
      td_sorted_matches.append((match,f_date_str,tdiff))

   temp = sorted(td_sorted_matches, key=lambda x: x[2], reverse=False)

   return(temp)



def pair_stars():
   meteor_dict = load_json_file("/mnt/ams2/cal/astro_integrity.json")
   for day in meteor_dict:
      for files in meteor_dict[day]:
         updated_files = []
         for data in meteor_dict[day]['files']:
            #print(data)
            # find best free cal files
            best_cal_files = get_best_cal_file(data['file'])
            if len(best_cal_files) > 0:
               img = cv2.imread(data['img_file'], 0)
               cal_params_file = best_cal_files[0][0]
               data['cal_params_file'] = cal_params_file
               data['cat_image_stars'] = pair_stars_in_image(data, img)
               print("PAIRED STARS:", len(data['cat_image_stars']))
               
            else:
               data['cal_params_file'] = ""
            updated_files.append(data)
      meteor_dict[day]['files'] = updated_files
   save_json_file("/mnt/ams2/cal/astro_integrity.json", meteor_dict)
   print("/mnt/ams2/cal/astro_integrity.json")

def pair_stars_in_image(data , frame):
   cal_params = load_json_file(data['cal_params_file'])
   cat_stars = flex_get_cat_stars(data['file'], data['file'], json_conf, cal_params )
   #cat_image_stars = get_cat_image_stars(cat_stars, frame, cal_params_file)
   archive_file = data['file']
   image_stars = data['img_stars']
   cat_image_stars = []
   used_cat_stars = {}
   used_img_stars = {}
   for star in image_stars:
      best_star = find_best_cat_stars(cat_stars, star[0], star[1], frame, archive_file)
      if best_star is not None:
         istar_key = str(star[0]) + str(star[1])
         cstar_key = str(best_star[4]) + str(best_star[5])
         if istar_key not in used_img_stars and cstar_key not in used_cat_stars:
            cv2.line(frame, (star[0], star[1]), (int(best_star[4]), int(best_star[5])), (128,128,128), 1)
            cat_image_stars.append(best_star)
            used_img_stars[istar_key] = 1
            used_cat_stars[cstar_key] = 1
   print("CAT:", cat_image_stars)
   return(cat_image_stars)

def report():
   meteor_dict = load_json_file("/mnt/ams2/cal/astro_integrity.json")
   for day in sorted(meteor_dict.keys()):
      print("DAY", day, len(meteor_dict[day]['files']))
      for files in meteor_dict[day]:
         updated_files = []
         for data in meteor_dict[day]['files']:
            fn = data['file'].split("/")[-1]
            if "cat_image_stars" in data:
               med_res, avg_res = get_cat_star_res_err(data['cat_image_stars'])
               if len(data['img_stars']) > 0:
                  map_perc = round(len(data['cat_image_stars']) / len(data['img_stars']), 2)
               else :
                  map_perc = 0
               print("FILE: ", fn, len(data['img_stars']), len(data['cat_image_stars']), map_perc, med_res, avg_res)

def get_cat_star_res_err(cat_image_stars):
   res = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,star_int,px_dist,cal_params_file in cat_image_stars:
      res.append(px_dist)
   return(round(np.median(res),2), round(np.mean(res),2))

if sys.argv[1] == 'ai':   
   astro_integrity()    
if sys.argv[1] == 'ps':
   pair_stars()
if sys.argv[1] == 'rpt':
   report()
if sys.argv[1] == 'bsn' or sys.argv[1] == 'blind_solve_night':
   blind_solve_night()

if sys.argv[1] == 'mp' :
   in_file = sys.argv[2] 
   out_file = in_file.replace(".png", ".jpg")
   stars,img,oimg = get_image_stars(in_file, None, 0)
   make_plate_from_points(in_file, out_file, stars, json_conf )
