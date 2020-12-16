import glob
from lib.FFFuncs import best_crop_size
from lib.PipeUtil import load_json_file, save_json_file, cfe, day_or_night, convert_filename_to_date_cam, bound_cnt
from lib.PipeMeteorTests import gap_test
from lib.PipeDetect import get_contours_in_image, find_object, analyze_object, get_trim_num
import datetime as dt
from datetime import datetime 
from suntime import Sun, SunTimeException

from lib.PipeVideo import load_frames_fast
from lib.PipeAutoCal import fn_dir , get_image_stars
import cv2
import os
import numpy as np
import pytz
utc = pytz.UTC

def time_lapse_frames(date, cams_id, json_conf, sunset, sunrise):

   date_dt = datetime.strptime(date, "%Y_%m_%d")
   fy, mf, md = date.split("_")
   yest = (date_dt - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
   print(date)
   print(yest)

   all_files = []
   yest_files = glob.glob("/mnt/ams2/SD/proc2/" + yest + "/*" + cams_id + "*.mp4")
   today_files = glob.glob("/mnt/ams2/SD/proc2/" + date + "/*" + cams_id + "*.mp4")
   for file in yest_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      f_datetime= utc.localize(f_datetime) 
      if sunset <= f_datetime <= sunrise:
         all_files.append(file)
   for file in today_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      f_datetime= utc.localize(f_datetime) 
      if int(fh) < 20:
         all_files.append(file)
   yest_snap_dir = "/mnt/ams2/SD/proc2/" + yest + "/snaps/"
   if cfe(yest_snap_dir,1) == 0:
      os.makedirs(yest_snap_dir)   
   snap_dir = "/mnt/ams2/SD/proc2/" + date + "/snaps/"
   if cfe(snap_dir,1) == 0:
      os.makedirs(snap_dir)   
   tl_files = []
   for file in sorted(all_files):
      if "trim" not in file and "crop" not in file:
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)

         outfile = "/mnt/ams2/SD/proc2/" + fy + "_" + fmin + "_" + fd + "/snaps/" + fy + "_" + fmin + "_" + fd + "_" + fh + "_" + fm + "_" + fs + "_000_" + cams_id + ".jpg"
 
         if cfe(outfile) == 0:
            print("NOT FOUND:", outfile)
            cmd = """ /usr/bin/ffmpeg -i """ + file + """ -vf select="between(n\,""" + str(0) + """\,""" + str(1) + """),setpts=PTS-STARTPTS" -y -update 1 """ + outfile + " >/dev/null 2>&1"
            print(cmd)
            os.system(cmd)
            img = cv2.imread(outfile)
            img_big = cv2.resize(img,(1280,720))
            cv2.imwrite(outfile, img_big)
         tl_files.append(outfile)

         #os.system(cmd)
   return(tl_files)


def meteors_last_night_detect_data(date, cams_id, json_conf, hd_meteors):
    mdir = "/mnt/ams2/meteors/" + date + "/" 
    meteor_data = []
    for mf, hdf in hd_meteors:
       mdata = {}
       mdata['jsf'] = mf
       mdata['hdf'] = hdf
       #mj = load_json_file(mf)
       hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hdf, json_conf, 0, 0, 1, 1,[])
       file_fn, file_dir = fn_dir(hdf)
       frame_prefix = file_fn.replace(".mp4", "")
       avg_val = np.mean(sum_vals)
       med_val = np.median(sum_vals)
       fn = 0
       cm = 0
       nm = 0
       ff = 0
       lf = 0
       last_frame = None

       # get_stars in image
       stars = get_image_stars(hdf, hd_frames[0].copy(), json_conf, 0)
       objects,hd_crop = detect_meteor_in_frames(mf , hd_color_frames,subframes,sum_vals,stars)
       mdata['objects'] = objects
       (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
       trim_num = get_trim_num(mf)
       extra_sec = int(trim_num) / 25
       start_trim_frame_time = f_datetime + dt.timedelta(0,extra_sec)
       print("TRIM ", trim_num)
       print(start_trim_frame_time)
       mdata['start_trim_frame_time'] = start_trim_frame_time.strftime("%Y_%m_%d_%H_%M_%S")
       meteor_data.append(mdata)
    mdata_file = mdir + json_conf['site']['ams_id'] + "_" + date + "_" + cams_id + "_meteor_data.info"
    save_json_file(mdata_file, meteor_data)
    print("SAVED:", mdata_file)
    exit()

def meteors_last_night_for_cam(date, cams_id, json_conf):
    meteors = []


    date_dt = datetime.strptime(date, "%Y_%m_%d")
    ffy, fmm, fdd = date.split("_")
    yest = (date_dt - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
    yest_dt = (date_dt - dt.timedelta(days = 1))

    mdir = "/mnt/ams2/meteors/" + date + "/" 
    jfiles = glob.glob(mdir + "*" + cams_id + "*.json")


    ymdir = "/mnt/ams2/meteors/" + yest + "/" 
    yfiles = glob.glob(ymdir + "*" + cams_id + "*.json")

    sun = Sun(float(json_conf['site']['device_lat']), float(json_conf['site']['device_lng']))
    sunrise =sun.get_sunrise_time(date_dt)
    sunset =sun.get_sunset_time(yest_dt)

    print("SS:", sunset, sunrise)


    tl_files = time_lapse_frames(date, cams_id, json_conf, sunset, sunrise)
    #tl_files = []
    #exit()

    # we only want meteors between dusk and dawn from the active date passed in. 
    for mf in yfiles:
       if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf:
          (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
          # only add meteors that happened after the sunset yesterday
          f_datetime= utc.localize(f_datetime) 
          if sunset <= f_datetime <= sunrise:
             meteors.append(mf)

    hd_meteors = []
    for mf in jfiles:
       # only add meteors BEFORE dawn,
       if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf:
          (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
          f_datetime= utc.localize(f_datetime) 
          if sunset <= f_datetime <= sunrise:
             meteors.append(mf)

    for meteor_file in meteors:

       mj = load_json_file(meteor_file)
       if "hd_trim" in mj:
          hd_meteors.append((meteor_file, mj['hd_trim']))
    hd_meteors = sorted(hd_meteors, key=lambda x: x[0], reverse=True)


    meteors_last_night_detect_data(date, cams_id, json_conf, hd_meteors)
    exit()

    if cfe("./CACHE/", 1) == 0:
       os.makedirs("./CACHE/")
    #else:
    #   os.system("rm ./CACHE/*.jpg")

    for tl in tl_files:
       (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(tl)
       fn, dir = fn_dir(tl)
       cache_file = "./CACHE/" + fn
       if cfe(cache_file) == 0:
          print("cp "+ tl + " ./CACHE/")
          os.system("cp "+ tl + " ./CACHE/")
          cimg = cv2.imread(cache_file)
          cv2.putText(cimg, str(f_date_str),  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          op_desc = json_conf['site']['operator_name'] + " " + json_conf['site']['obs_name'] + " " + json_conf['site']['location']
          cv2.putText(cimg, str(op_desc),  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          cv2.imshow('pepe', cimg)
          cv2.waitKey(30)
          cv2.imwrite(cache_file, cimg)

    meteor_data = []
    hd_meteors = sorted(hd_meteors, key=lambda x: x[0], reverse=False)
   

    for mf, hdf in hd_meteors:
       mdata = {}
       mdata['jsf'] = mf
       mdata['hdf'] = hdf
       #mj = load_json_file(mf)
       hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hdf, json_conf, 0, 0, 1, 1,[])
       file_fn, file_dir = fn_dir(hdf)
       frame_prefix = file_fn.replace(".mp4", "") 
       avg_val = np.mean(sum_vals)
       med_val = np.median(sum_vals)
       fn = 0
       cm = 0
       nm = 0
       ff = 0
       lf = 0
       last_frame = None

       # get_stars in image
       stars = get_image_stars(hdf, hd_frames[0].copy(), json_conf, 0)
       objects,hd_crop = detect_meteor_in_frames(mf , hd_color_frames,subframes,sum_vals,stars)
       mdata['objects'] = objects
       (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
       trim_num = get_trim_num(mf)
       extra_sec = int(trim_num) / 25
       start_trim_frame_time = f_datetime + dt.timedelta(0,extra_sec)
       print("TRIM ", trim_num)
       print(start_trim_frame_time)
       mdata['start_trim_frame_time'] = start_trim_frame_time
       meteor_data.append(mdata)

       fns = []
       xs = []
       ys = []
       if len(objects) == 1:
          for obj in objects:
             ff = objects[obj]['ofns'][0] - 15
             lf = objects[obj]['ofns'][-1] + 15
             min_x = objects[obj]['oxs'][0] - 25
             min_y = objects[obj]['oys'][0] - 25
             max_x = objects[obj]['oxs'][-1] + 25
             max_y = objects[obj]['oys'][-1] + 25
       elif len(objects) == 0:
          print("NO METEOR FOUND!?")
          continue
       else:
          print("MORE THAN ONE OBJECT!")
          ff = 0
          lf = len(hd_color_frames)
          min_x = 0
          min_y = 0
          max_x = 0
          max_y = 0

       if ff < 0:
          ff = 0
       if lf > len(hd_color_frames):
          lf = len(hd_color_frames)
       if min_x < 0:
          min_x = 0
       if min_y < 0:
          min_y = 0
       if min_x > 1920:
          min_x = 1919 
       if min_y > 1080:
          min_y = 1079 

       rcc = 0
       cx1, cy1,cx2,cy2 = hd_crop
       for fn in range(ff, lf):

          frame = hd_color_frames[fn]
          counter = "{:04d}".format(fn)
          frame_file = frame_prefix + "-" + counter + ".jpg"
          print(min_x,min_y,max_x,max_y)
          extra_sec = fn / 25
          frame_time = start_trim_frame_time + dt.timedelta(0,extra_sec)
          frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


          if rcc <= 15:
             if rcc <= 7 :
                rc_val = 130 + (rcc * 5)
             else:
                rc_val = rc_val - 5
          #cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (rc_val,rc_val,rc_val), 2, cv2.LINE_AA)

          show_frame = cv2.resize(frame,(1280,720))
          cv2.putText(show_frame, str(frame_time_str),  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          op_desc = json_conf['site']['operator_name'] + " " + json_conf['site']['obs_name'] + " " + json_conf['site']['location']
          cv2.putText(show_frame, str(op_desc),  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

          #cv2.putText(show_frame, str("DETECT"),  (20,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          #cv2.putText(show_frame, str(fn),  (20,70), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

          cv2.imshow('pepe', show_frame)
          cv2.waitKey(30)
          cv2.imwrite("./CACHE/" + frame_file, show_frame)
          rcc += 1
    cmd = "./FFF.py imgs_to_vid ./CACHE/ " + cams_id + " /mnt/ams2/CUSTOM_VIDEOS/" + date + "_" + cams_id + ".mp4 25 28"
    print(cmd)
    os.system(cmd)

def detect_meteor_in_frames(file, hd_color_frames, subframes,sum_vals, stars):

   objects = {}
   last_frame = None
   fn = 0
   cm = 0
   nm = 0
   ff = 0
   lf = 0

   if True:
      for c in range(0, len(hd_color_frames)):

         cframe = hd_color_frames[c]
         frame = subframes[c]
         frame = blackout_stars(frame, stars)
         if last_frame is not None:
            subsub = cv2.subtract(frame, last_frame)
         else:
            subsub = frame
         thresh = 25
         _, threshold = cv2.threshold(subsub.copy(), thresh, 255, cv2.THRESH_BINARY)
         sum_val = int(np.sum(threshold))
         show_frame = cv2.resize(threshold,(1280,720))
         #cv2.imshow('pepe', show_frame)
         if sum_val > 80:
            cm += 1
            nm = 0
         #   cv2.waitKey(0)
         else:
            nm += 1
         #   cv2.waitKey(30)

         if cm >= 2 and ff == 0:
            ff = fn - 10

         if lf == 0 and cm >= 2 and nm >= 10:
            lf = fn
         if sum_val > 80:
            cnts = get_contours_in_image(threshold)
            for cnt in cnts:
               cx,cy,cw,ch = cnt
               cnt_img = subsub[cy:cy+ch,cx:cx+cw]
               max_val = int(np.sum(cnt_img))
               object, objects = find_object(objects, c,cx, cy, cw, ch, max_val, 1, 0, None)

   bad = []
   for obj in objects:
      if len(objects[obj]['ofns']) < 2:
         bad.append(obj)
         continue
      objects[obj] = analyze_object(objects[obj])
      gap_test_res , gap_test_info = gap_test(objects[obj]['ofns'])

      if objects[obj]['report']['meteor'] == 1 and gap_test_res != 0:
         meteor_obj = obj
         print("METEOR!")
      else:
         bad.append(obj)
   hd_crop = [0,0,0,0]
   for bb in bad:
      del objects[bb]

   if objects is None:
      print("NO OBJECTS FOUND!?")
      return([], hd_crop)
   elif len(objects) == 0:
      print("NO OBJECTS FOUND!?")
      return([], hd_crop)
   elif len(objects) == 1:
      oxs = objects[meteor_obj]['oxs']
      oys = objects[meteor_obj]['oys']
      cw, ch = best_crop = best_crop_size(oxs, oys, 1920,1080)
      cx = int(np.mean(oxs))
      cy = int(np.mean(oys))
      cx1 = int(cx - (cw/2))
      cy1 = int(cy - (ch/2))
      cx2 = int(cx1 + cw)
      cy2 = int(cy1 + ch)

      #cv2.rectangle(cframe, (cx1, cy1), (cx2, cy2), (255,255,255), 2, cv2.LINE_AA)
      #cv2.imshow('pepe', cframe)
      #cv2.waitKey(0)
      #print("BEST CROP:", best_crop)
      hd_crop = [cx1,cy1,cx2,cy2] 
      return(objects, hd_crop)
   else:
      print("MANY OBJECTS.")
      for obj in objects:
         return(objects[obj], hd_crop)


def blackout_stars(frame, stars):
   for star in stars:
      print(star)
      x,y,ii = star
      rx1,ry1,rx2,ry2 = bound_cnt(x, y,1920,1080, 10)
      frame[ry1:ry2,rx1:rx2] = 0
   #cv2.imshow('pepe', frame)
   #cv2.waitKey(0)
   return(frame)


def find_start_end(sum_vals):
   avg_val = np.mean(sum_vals)
   for c in range(0, len(sum_vals)):
      if sum_vals[c] > avg_val:
         print("*** VAL:", sum_vals[c])
      else:
         print("VAL:", sum_vals[c])
   exit()
