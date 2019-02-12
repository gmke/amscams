import time
import subprocess
import math
from pathlib import Path
import datetime
import cv2
import numpy as np
import ephem
import glob
import os
from lib.VideoLib import load_video_frames, get_masks
from lib.ImageLib import stack_frames, median_frames, adjustLevels, mask_frame
from lib.UtilLib import convert_filename_to_date_cam, bound_cnt, check_running
from lib.FileIO import cfe, save_json_file
from lib.DetectLib import eval_cnt
from scipy import signal

def Decdeg2DMS( Decin ):
   Decin = float(Decin)
   if(Decin<0):
      sign = -1
      dec  = -Decin
   else:
      sign = 1
      dec  = Decin

   d = int( dec )
   dec -= d
   dec *= 100.
   m = int( dec*3./5. )
   dec -= m*5./3.
   s = dec*180./5.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(d,m,s)
   else: out = '+%02d:%02d:%06.3f'%(d,m,s)

   return out


def RAdeg2HMS( RAin ):
   RAin = float(RAin)
   if(RAin<0):
      sign = -1
      ra   = -RAin
   else:
      sign = 1
      ra   = RAin

   h = int( ra/15. )
   ra -= h*15.
   m = int( ra*4.)
   ra -= m/4.
   s = ra*240.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(h,m,s)
   else: out = '+%02d:%02d:%06.3f'%(h,m,s)

   return out


def radec_to_azel(ra,dec, caldate,json_conf):
   lat = json_conf['site']['device_lat']
   lon = json_conf['site']['device_lng']
   alt = json_conf['site']['device_lng']

   body = ephem.FixedBody()
   #print ("BODY: ", ra, dec)
   #body._epoch=ephem.J2000

   rah = RAdeg2HMS(ra)
   dech= Decdeg2DMS(dec)

   body._ra = rah
   body._dec = dech

   obs = ephem.Observer()
   obs.lat = ephem.degrees(lat)
   obs.lon = ephem.degrees(lon)
   obs.date = caldate
   obs.elevation=float(alt)
   body.compute(obs)
   az = str(body.az)
   el = str(body.alt)
   (d,m,s) = az.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   az = dd

   (d,m,s) = el.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   el = dd
   #az = ephem.degrees(body.az)
   return(az,el)


def xyfits(cal_file, stars):
   xyfile = cal_file.replace(".jpg", "-xy.txt")
   xyf = open(xyfile, "w")
   xyf.write("x,y\n")
   for x,y,mg in stars:
      xyf.write(str(x) + "," + str(y) + "\n")
   xyf.close()

   xyfits = xyfile.replace(".txt", ".fits")

   cmd = "/usr/local/astrometry/bin/text2fits -f \"ff\" -s \",\" " + xyfile + " " + xyfits
   print (cmd)
   os.system(cmd)

   cmd = "/usr/local/astrometry/bin/solve-field " + xyfits + " --overwrite --width=1920 --height=1080 --scale-low 50 --scale-high 95 --no-remove-lines --x-column x --y-column y"
   os.system(cmd)
   print(cmd)


def check_if_solved(cal_file):
   cal_wild = cal_file.replace(".jpg", "*")
   astr_files = []
   solved = 0
   for astr_file in sorted((glob.glob(cal_wild))):
      if 'wcs' in  astr_file:
         print("This image has been solved.")
         solved = 1
      astr_files.append(astr_file)
   return(solved, astr_files)


def save_cal_params(wcs_file):
   wcs_info_file = wcs_file.replace(".wcs", "-wcsinfo.txt")
   cal_params_file = wcs_file.replace(".wcs", "-calparams.json")
   fp =open(wcs_info_file, "r")
   cal_params_json = {}
   for line in fp:
      line = line.replace("\n", "")
      field, value = line.split(" ")
      if field == "imagew":
         cal_params_json['imagew'] = value
      if field == "imageh":
         cal_params_json['imageh'] = value
      if field == "pixscale":
         cal_params_json['pixscale'] = value
      if field == "orientation":
         cal_params_json['position_angle'] = float(value) + 180
      if field == "ra_center":
         cal_params_json['ra_center'] = value
      if field == "dec_center":
         cal_params_json['dec_center'] = value
      if field == "fieldw":
         cal_params_json['fieldw'] = value
      if field == "fieldh":
         cal_params_json['fieldh'] = value
      if field == "ramin":
         cal_params_json['ramin'] = value
      if field == "ramax":
         cal_params_json['ramax'] = value
      if field == "decmin":
         cal_params_json['decmin'] = value
      if field == "decmax":
         cal_params_json['decmax'] = value

   save_json_file(cal_params_file, cal_params_json)


def find_image_stars(cal_img):
   bgavg = np.mean(cal_img)
   thresh = bgavg * 1.5
   if thresh < 1:
      thresh =  10

   print("THREHS:", thresh)
   if cal_img.shape == 3:
      cal_img= cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)
   _, threshold = cv2.threshold(cal_img.copy(), thresh, 255, cv2.THRESH_BINARY)
   #cal_img = cv2.dilate(threshold, None , iterations=4)
   cal_img= cv2.convertScaleAbs(threshold)
   (_, cnts, xx) = cv2.findContours(cal_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         star_pixels.append((x,y,w,h))
         #cv2.rectangle(cal_img, (x, y), (x + w, y + h), (128, 128, 128), 1)
   return(star_pixels,cal_img)

def last_sunrise_set(json_conf, cal_date = None):
   if cal_date == None:
      cal_date =  datetime.date.today().strftime("%Y-%m-%d %H:%M:%S")
   print("CAL DATE:", cal_date)
   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = cal_date

   sun = ephem.Sun()
   sun.compute(obs)
   last_sunrise = obs.previous_rising(ephem.Sun())
   last_sunset = obs.previous_setting(ephem.Sun())
   # if the sun is currently set, use the next sunset as the end time not prev
   timediff = last_sunrise - last_sunset
   print(last_sunrise, last_sunset)
   print(timediff)
   sr_datetime = last_sunrise.datetime().strftime('%Y-%m-%d %H:%M:%S')
   ss_datetime = last_sunset.datetime().strftime('%Y-%m-%d %H:%M:%S')
   print(sr_datetime)
   print(ss_datetime)
   sr_datetime_t = datetime.datetime.strptime(sr_datetime, "%Y-%m-%d %H:%M:%S")
   ss_datetime_t = datetime.datetime.strptime(ss_datetime, "%Y-%m-%d %H:%M:%S")

   time_diff = sr_datetime_t - ss_datetime_t
   hr = time_diff.seconds / (3600)   
   print(sr_datetime,ss_datetime,hr)
   return(sr_datetime_t, ss_datetime_t,hr)

def find_hd_file(cal_glob):
   print(cal_glob)
   files = glob.glob(cal_glob)
   return(files)

def calibrate_pic(cal_image_file, json_conf, show = 1):
   cal_file = cal_image_file
   new_cal_file = cal_file
   orig_cal_file = cal_image_file.replace(".jpg", "-orig.jpg")
   plate_cal_file = cal_image_file.replace(".jpg", "-plate.jpg")
   dark_cal_file = cal_image_file.replace(".jpg", "-dark.jpg")

   cal_image_np = cv2.imread(cal_image_file, 0)
   orig_image = cal_image_np
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_image_file)


   cams_id = hd_cam

   print("cal pic")
   cams_id = cams_id.replace(".jpg", "")
   print("CAMS ID:", cams_id)
   masks = get_masks(cams_id, json_conf, hd = 1)
   print("MASKS:", masks)
   cal_image_np = mask_frame(cal_image_np, [], masks)
   avg_px = np.mean(cal_image_np)
   print("AVG PX",avg_px)
   temp = adjustLevels(cal_image_np, avg_px+10,1,255)
   cal_image_adj  = cv2.convertScaleAbs(temp)

   cv2.imwrite(new_cal_file, cal_image_np)
   cv2.imwrite(dark_cal_file, cal_image_adj)
   cv2.imwrite(orig_cal_file, orig_image)

   cal_star_file = cal_file.replace(".jpg", "-median.jpg")

   show_img = cv2.resize(cal_image_np, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Cal Image NP",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   (stars, nonstars, plate_image) = make_plate_image(cal_image_adj, cal_star_file, cams_id, json_conf)
   cv2.imwrite(plate_cal_file, plate_image)

   if show == 1:
      show_img = cv2.resize(plate_image, (0,0),fx=.4, fy=.4)
      cv2.namedWindow('pepe')
      cv2.putText(show_img, "Plate Image",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(10)
   print("STARS:", len(stars))

   rect_file = orig_cal_file.replace("-orig", "-rect")
   for x,y,mg in sorted(stars, key=lambda x: x[2], reverse=True) :
      print(x,y,mg)
      cv2.rectangle(orig_image, (x-5, y-5), (x + 5, y + 5), (255, 0, 0), 1)
   for x,y,mg in sorted(nonstars, key=lambda x: x[2], reverse=True) :
      print(x,y,mg)
      cv2.rectangle(orig_image, (x-7, y-7), (x + 7, y + 7), (120, 0, 0), 1)
   cv2.imwrite(rect_file, orig_image)

   solved = plate_solve(new_cal_file,json_conf)



def calibrate_camera(cams_id, json_conf, cal_date = None, show=1):
   # unless passed in use the last night as the calibration date
   # check 1 frame per hour and if there are enough stars then 
   # attempt to plate solve with astrometry
   # if that succeeds fit the plate and save the calibration file

   # first find the time of the last sun rise and sun set...
   last_sunrise, last_sunset,hr = last_sunrise_set(json_conf, cal_date)
   print("Hours of Dark:", hr)
   for i in range (2,int(hr)-1):
      cal_date = last_sunset + datetime.timedelta(hours=i)
      cal_video = find_hd_file(cal_date.strftime('/mnt/ams2/HD/%Y_%m_%d_%H_%M*' + cams_id + '*.mp4') )
      if len(cal_video) == 0:
         continue 
      cal_file = cal_video[0].replace('.mp4', '.jpg')

      frames = load_video_frames(cal_video[0],json_conf,100)
      el = cal_file.split("/")
      cal_file = "/mnt/ams2/cal/tmp/" + el[-1]
      print(cal_file)
      cal_image, cal_image_np = stack_frames(frames,cal_file) 
      #cal_image_np =  median_frames(frames) 

      orig_img = cal_image_np

      masks = get_masks(cams_id, json_conf, hd = 1)
      cal_image_np = mask_frame(cal_image_np, [], masks)
      cal_star_file = cal_file.replace(".jpg", "-median.jpg")
      cal_orig_file = cal_file.replace(".jpg", "-orig.jpg")

      #MIKE!

      avg_px = np.mean(cal_image_np)
      print("AVG PX",avg_px)
      temp = adjustLevels(cal_image_np, avg_px+10,1,255)
      cal_image_np = cv2.convertScaleAbs(temp)

      show_img = cv2.resize(cal_image_np, (0,0),fx=.4, fy=.4)
      cv2.putText(show_img, "Cal Image NP",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(10)
      (stars, nonstars, plate_image) = make_plate_image(cal_image_np, cal_star_file, cams_id, json_conf)
      if show == 1:
         show_img = cv2.resize(plate_image, (0,0),fx=.4, fy=.4)
         cv2.namedWindow('pepe')
         cv2.putText(show_img, "Plate Image",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.imshow('pepe', show_img)
         cv2.waitKey(10)
     # cv2.imwrite(cal_file, cal_image_np)
      cv2.imwrite(cal_file, plate_image)
      cv2.imwrite(cal_star_file, plate_image)
      cv2.imwrite(cal_orig_file, orig_img)

      print("STARS:", len(stars))
      rect_file = cal_orig_file.replace("-orig", "-rect")
      for x,y,mg in sorted(stars, key=lambda x: x[2], reverse=True) :
         print(x,y,mg)
         cv2.rectangle(orig_img, (x-5, y-5), (x + 5, y + 5), (255, 0, 0), 1)
      for x,y,mg in sorted(nonstars, key=lambda x: x[2], reverse=True) :
         print(x,y,mg)
         cv2.rectangle(orig_img, (x-7, y-7), (x + 7, y + 7), (120, 0, 0), 1)
      cv2.imwrite(rect_file, orig_img)

      print("STARS:", len(stars))
      print("NONSTARS:", len(nonstars))

      if len(stars) >= 12 and len(stars) < 200:

         #xyfits(cal_file, stars)
         #exit()
         solved = plate_solve(cal_file,json_conf)
         print("SOLVED:", solved)
         if solved == 1:
            star_file = cal_file.replace(".jpg", "-mapped-stars.json")
            cmd = "./calFit.py " + star_file
            print(cmd)
            os.system(cmd)

def find_best_cal_file(hd_datetime, hd_cam):
   cal_file = None
   return(cal_file)

def reduce_object(object, sd_video_file, hd_file, hd_trim, hd_crop_file, hd_crop_box, json_conf, cal_file = None):

   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)

   if cal_file is None:
      cal_file = find_best_cal_file(hd_datetime, hd_cam)

   print("HD TRIM REDUCE OBJECT: ", hd_trim)
   el = hd_trim.split("-trim-")
   min_file = el[0] + ".mp4"

   print(el[1])
   ttt = el[1].split("-")
   trim_num = ttt[0]

   print("REDUCE OBJECT", trim_num)

   meteor_frames = []
   extra_sec = int(trim_num) / 25
   start_frame_time = hd_datetime + datetime.timedelta(0,extra_sec)
   start_frame_str = start_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
   start_frame_num = object['history'][0][0]
   for hist in object['history']:
      fc,x,y,w,h,mx,my = hist
      hd_x = x + hd_crop_box[0] 
      hd_y = x + hd_crop_box[1] 

      extra_sec = (start_frame_num + fc) /  25
      frame_time = hd_datetime + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      if cal_file is None:
         ra, dec, rad, decd, az, el = 0,0,0,0,0,0
      meteor_frames.append((fc,frame_time_str,x,y,w,h,hd_x,hd_y,ra,dec,rad,decd,az,el))

   return(meteor_frames) 

def plate_solve(cal_file,json_conf):

   el = cal_file.split("/")

   wcs_file = cal_file.replace(".jpg", ".wcs")
   grid_file = cal_file.replace(".jpg", "-grid.png")

   star_file = cal_file.replace(".jpg", "-stars-out.jpg")
   star_data_file = cal_file.replace(".jpg", "-stars.txt")
   astr_out = cal_file.replace(".jpg", "-astrometry-output.txt")

   wcs_info_file = cal_file.replace(".jpg", "-wcsinfo.txt")

   quarter_file = cal_file.replace(".jpg", "-1.jpg")

   image = cv2.imread(cal_file)

   if len(image.shape) > 2:
      gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   else:
      gray = image
   height = gray.shape[0]
   width = gray.shape[1]
# --crpix-center
   cmd = "/usr/local/astrometry/bin/solve-field " + cal_file + " --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " -d 1-40 --scale-units dw --scale-low 50 --scale-high 90 > " + astr_out + " 2>&1 &"
   print(cmd) 
   os.system(cmd)

   running = check_running("solve-field") 
   start_time = datetime.datetime.now()
   while running > 0:
      running = check_running("solve-field") 
      cur_time = datetime.datetime.now()
      tdiff = cur_time - start_time
      print("running plate solve.", tdiff)
      time.sleep(10)
   
   time.sleep(3)

   os.system("grep Mike " + astr_out + " >" +star_data_file + " 2>&1" )

   cmd = "/usr/bin/jpegtopnm " + cal_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600"
   os.system(cmd)

   cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file
   os.system(cmd)

   #bright_star_data = parse_astr_star_file(star_data_file)
   #plot_bright_stars(cal_file, image, bright_star_data)
   solved = cfe(grid_file)
   if solved == 1:
      save_cal_params(wcs_file)
   return(solved)

def distort_xy_new(sx,sy,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale=1):

   #print("INPUT", sx,sy,ra,dec,RA_center,dec_center,pos_angle_ref,F_scale)
   ra_star = ra
   dec_star = dec

   #F_scale = F_scale/10
   w_pix = 50*F_scale/3600
   #F_scale = 158 * 2
   #F_scale = 155
   #F_scale = 3600/16
   #F_scale = 3600/F_scale
   #F_scale = 1

   #RA_center = RA_center 
   #RA_center = RA_center 

   #dec_center = dec_center + (x_poly[13] * 100)
   #dec_center = dec_center + (y_poly[13] * 100)

   # Gnomonization of star coordinates to image coordinates
   ra1 = math.radians(float(RA_center))
   dec1 = math.radians(float(dec_center))
   ra2 = math.radians(float(ra_star))
   dec2 = math.radians(float(dec_star))
   ad = math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1))
   radius = math.degrees(ad)
   sinA = math.cos(dec2)*math.sin(ra2 - ra1)/math.sin(ad)
   cosA = (math.sin(dec2) - math.sin(dec1)*math.cos(ad))/(math.cos(dec1)*math.sin(ad))
   theta = -math.degrees(math.atan2(sinA, cosA))
   #theta = theta + pos_angle_ref - 90.0
   theta = theta + pos_angle_ref - 90 
   #theta = theta + pos_angle_ref - 90


   dist = np.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra1 - ra2)))

   # Calculate the image coordinates (scale the F_scale from CIF resolution)
   X1 = radius*math.cos(math.radians(theta))*F_scale
   Y1 = radius*math.sin(math.radians(theta))*F_scale
   # Calculate distortion in X direction
   dX = (x_poly[0]
      + x_poly[1]*X1
      + x_poly[2]*Y1
      + x_poly[3]*X1**2
      + x_poly[4]*X1*Y1
      + x_poly[5]*Y1**2
      + x_poly[6]*X1**3
      + x_poly[7]*X1**2*Y1
      + x_poly[8]*X1*Y1**2
      + x_poly[9]*Y1**3
      + x_poly[10]*X1*math.sqrt(X1**2 + Y1**2)
      + x_poly[11]*Y1*math.sqrt(X1**2 + Y1**2))

   # Add the distortion correction and calculate X image coordinates
   #x_array[i] = (X1 - dX)*x_res/384.0 + x_res/2.0
   new_x = X1 - dX + x_res/2.0

   # Calculate distortion in Y direction
   dY = (y_poly[0]
      + y_poly[1]*X1
      + y_poly[2]*Y1
      + y_poly[3]*X1**2
      + y_poly[4]*X1*Y1
      + y_poly[5]*Y1**2
      + y_poly[6]*X1**3
      + y_poly[7]*X1**2*Y1
      + y_poly[8]*X1*Y1**2
      + y_poly[9]*Y1**3
      + y_poly[10]*Y1*math.sqrt(X1**2 + Y1**2)
      + y_poly[11]*X1*math.sqrt(X1**2 + Y1**2))

   # Add the distortion correction and calculate Y image coordinates
   #y_array[i] = (Y1 - dY)*y_res/288.0 + y_res/2.0
   new_y = Y1 - dY + y_res/2.0
   #print("DENIS RA:", X1, Y1, sx, sy, F_scale, w_pix, dist)
   #print("DENIS:", X1, Y1, dX, dY, sx, sy, F_scale, w_pix, dist)
   #print("THETA:",theta)
   #print("DENIS:", sx,sy,new_x,new_y, sx-new_x, sy-new_y)
   return(new_x,new_y)

def make_plate_image(med_stack_all, cam_num, json_conf, show = 1):
   
   nonstars = []
   stars = []
   center_stars = 0
   med_cpy = med_stack_all.copy()
   plate_image = med_stack_all
   if show == 1:
      show_img = cv2.resize(med_stack_all, (0,0),fx=.4, fy=.4)
      cv2.putText(show_img, "Make Plate Image",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(10)
   img_height,img_width = med_stack_all.shape
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   print("AVG PX:", avg_px)
   best_thresh = find_best_thresh(med_stack_all, avg_px)
   print("BEST THRESH:", best_thresh)
   if best_thresh < 0:
      best_thresh = 1
   print("BEST THRESH:", best_thresh)

   _, star_thresh = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_thresh, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   plate_image= np.zeros((img_height,img_width),dtype=np.uint8)
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cnt_img = med_cpy[y:y+h,x:x+h]
      if True and w < 30 and h < 30:
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)
 
         mx,my = max_loc
         cx = x + mx
         cy = y + my
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)

         is_star = star_test(cnt_img)
         #is_star = 1
         cnt_h, cnt_w = cnt_img.shape
         #cv2.putText(cnt_img, str(is_star),  (0,cnt_h-1), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(1)

         if is_star == 1:
            cx = int(mnx + mxx / 2)
            cy = int(mny + mxy / 2)
            cnt_img = med_cpy[mny:mxy,mnx:mxx]
            cnt_h,cnt_w = cnt_img.shape
            (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)

            cx = int(x + (w/2))
            cy = int(y + (h/2))

            stars.append((cx,cy,max_px))
            bp_x,bp_y = max_loc
            #cv2.putText(cnt_img, str(is_star),  (0,cnt_h-1), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
            #cv2.circle(cnt_img, (int(bp_x),int(bp_y)), 5, (255,255,255), 1)
            star_cnt = cnt_img
            ul = cnt_img[0,0] 
            ur = cnt_img[0,cnt_w-1] 
            ll =  cnt_img[cnt_h-1,0] 
            lr = cnt_img[cnt_h-1,cnt_w-1] 
             
            cavg = int((ul + ur + ll + lr) / 4)
            star_cnt = clean_star_bg(cnt_img, cavg+5)
            # limit to center stars only...
            #if abs(mny - (img_height/2)) <= (img_height/2)*.8 and abs(mnx - (img_width/2)) <= (img_width/2)*.8:
            if True:
               print(abs(mny-(img_height/2)))
               print(abs(mnx-(img_width/2)))
               plate_image[mny:mxy,mnx:mxx] = star_cnt  
               center_stars = center_stars + 1
         else:
            nonstars.append((cx,cy,0))

   temp = sorted(stars, key=lambda x: x[2], reverse=True) 
   if len(temp) > 30:
      stars = temp[0:29]
          
   print("STARS:", len(stars))
   print("NON STARS:", len(nonstars))
   print("CENTER STARS:", center_stars)
   cv2.imshow('pepe', plate_image)
   cv2.waitKey(10)

   return(stars,nonstars,plate_image)


def find_bright_pixels(med_stack_all, solved_file, cam_num, json_conf):

   show_img = cv2.resize(med_stack_all, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Find Bright Pixels",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   cams_id = cam_num
   img_height,img_width = med_stack_all.shape
   med_cpy = med_stack_all.copy()
   star_pixels = []
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   pdif = max_px - avg_px
   pdif = int(pdif / 20) + avg_px

   best_thresh = find_best_thresh(med_stack_all, pdif)
   _, star_bg = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   #thresh_obj = star_bg
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   show_img = cv2.resize(thresh_obj, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Thresh OBJ",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   masked_pixels = []
   bg_avg = 0

   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if True and w < 20 and h < 20:
         cnt_img = med_stack_all[y:y+h,x:x+w]
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(10)
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)
         mx,my = max_loc
         cx = x + mx
         cy = y + my
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)

         cnt_img = med_stack_all[mny:mxy,mnx:mxx]
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(10)

         cnt_w,cnt_h = cnt_img.shape
         if cnt_w > 0 and cnt_h > 0:
            is_star = star_test(cnt_img)
            is_star = 1
            if is_star >= 0:
               bg_avg = bg_avg + np.mean(cnt_img)
               star_pixels.append((cx,cy))
               cv2.circle(med_cpy, (int(cx),int(cy)), 5, (255,255,255), 1)
            else:
               cv2.rectangle(med_cpy, (cx-5, cy-5), (cx + 5, cy + 5), (255, 0, 0), 1)
         else:
               cv2.rectangle(med_cpy, (cx-15, cy-15), (cx + 15, cy + 15), (255, 0, 0), 1)


   show_img = cv2.resize(med_cpy, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Initial Stars Found",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)


   if len(star_pixels) > 0:
      bg_avg = bg_avg / len(star_pixels)
   else:
      bg_avg = 35

   file_exists = Path(solved_file)
   if True:
   #if file_exists.is_file() is False:
      plate_image= med_stack_all 
      plate_image= np.zeros((img_height,img_width),dtype=np.uint8)
      star_sz = 10
      for star in star_pixels:
         sx,sy = star
         mnx,mny,mxx,mxy = bound_cnt(sx,sy,img_width,img_height)
         star_cnt = med_stack_all[mny:mxy,mnx:mxx]
         #star_cnt = clean_star_bg(star_cnt, bg_avg+7)
         plate_image[mny:mxy,mnx:mxx] = star_cnt
         cv2.imshow('pepe', star_cnt)
         cv2.waitKey(10)

   else:
      print("PLATE ALREADY SOLVED HERE! FIX", solved_file)
      plate_file = solved_file.replace("-grind.png", ".jpg")
      plate_image = cv2.imread(plate_file, 0)


   masks = get_masks(cams_id, json_conf, hd = 1)
   print("MASKS:",  masks)
   for mask in masks:
      msx,msy,msw,msh = mask.split(",")
      plate_image[int(msy):int(msy)+int(msh),int(msx):int(msx)+int(msw)] = 0

   plate_image[0:1080,0:200] = 0
   plate_image[0:1080,1720:1920] = 0

   #cv2.imshow('pepe', plate_image)
   #cv2.waitKey(10)

   return(star_pixels, plate_image)


def find_best_thresh(image, start_thresh):
   if len(image.shape) > 2:
      image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   show_img = cv2.resize(image, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Find Best Thresh",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)

   go = 1
   tries = 0
   while go == 1:
      _, star_bg = cv2.threshold(image, start_thresh, 255, cv2.THRESH_BINARY)

      #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
      #star_bg = cv2.convertScaleAbs(star_bg)
      (_, cnts, xx) = cv2.findContours(star_bg.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnts) > 70:
         start_thresh = start_thresh + 1
      elif len(cnts) < 3:
         start_thresh = start_thresh - 1
      else:
         go = 0
      if tries > 10:
         go = 0
      tries = tries + 1
      print("THRESH:", start_thresh)
   return(start_thresh)


def star_test(cnt_img):
   PX = []
   PY = []
   ch,cw = cnt_img.shape
   my = int(ch / 2)
   mx = int(cw / 2)
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img[0:])
   px_diff = max_px - avg_px

   for x in range(0,cw-1):
      px_val = cnt_img[my,x]
      PX.append(px_val)
      #cnt_img[my,x] = 255
   for y in range(0,ch-1):
      py_val = cnt_img[y,mx]
      PY.append(py_val)
      #cnt_img[y,mx] = 255

   ys_peaks = signal.find_peaks(PY)
   y_peaks = len(ys_peaks[0])
   xs_peaks = signal.find_peaks(PX)
   x_peaks = len(xs_peaks[0])


   if px_diff > 8 or max_px > 80:
      is_star = 1
      print("STAR PASSED:", px_diff, max_px)
   else:
      print("STAR FAIL:", px_diff, max_px)
      is_star = 0

   return(is_star)


def clean_star_bg(cnt_img, bg_avg):
   max_px = np.max(cnt_img)
   min_px = np.min(cnt_img)
   avg_px = np.mean(cnt_img)
   halfway = int((max_px - min_px) / 2)
   cnt_img.setflags(write=1)
   for x in range(0,cnt_img.shape[1]):
      for y in range(0,cnt_img.shape[0]):
         px_val = cnt_img[y,x]
         if px_val < bg_avg + halfway:
            #cnt_img[y,x] = random.randint(int(bg_avg - 3),int(avg_px))
            pxval = cnt_img[y,x]
            pxval = int(pxval) / 2
            cnt_img[y,x] = 0
   return(cnt_img)

