#!/usr/bin/python3 

import os
import cv2
import subprocess
import json
import glob
import sys
from PIL import Image, ImageChops
from pathlib import Path
json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
sd_video_dir = json_conf['site']['sd_video_dir']
proc_dir = json_conf['site']['proc_dir']

def stack_dir(dir, cams_id):
   master_stack = None
      #filename = filename.replace(".txt", "-stacked.png")
   glob_dir = dir + "*" + cams_id +"*.png"
   out_file = dir + cams_id + "-meteors.png"
   files = glob.glob(glob_dir)
   print(len(files), glob_dir)
   for file in files:
      pic1 = Image.open(str(file))
      if master_stack is None:
         master_stack = stack_stack(pic1, pic1)
      else:
         master_stack = stack_stack(master_stack, pic1)
   master_stack.save(out_file)   
   

def load_video_frames(trim_file):
   cap = cv2.VideoCapture(trim_file)

   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 1:
            cap.release()
            print("Bad file.")
            return(frames)
         else:
            go = 0
      else:
         if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         frames.append(frame)
         frame_count = frame_count + 1
   return(frames)

def get_brightness(filename):
   cmd = "convert " + filename + " -colorspace Gray -format \"%[mean]\" info: "
   magic = str(subprocess.check_output(cmd, shell=True))
   magic = magic.replace("b", "")
   magic = magic.replace("'", "")
   magic = float(magic)
   print ("Mean Image Brightness:", magic)
   return(magic)

def stack_stack(pic1, pic2):
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(stacked_image)

def stack_meteors(dir, cams_id):
   master_stack = None
   glob_dir = dir + "/data/*" + str(cams_id) + "*meteor.txt"
   image_dir = dir + "/images/"

   print("GLOB", glob_dir)
   for filename in (glob.glob(glob_dir)):
      filename = filename.replace("data", "images")
      filename = filename.replace(".txt", "-stacked.png")
      print(filename)
      pic1 = Image.open(str(filename))
      if master_stack is None:
         master_stack = stack_stack(pic1, pic1)
      else:
         master_stack = stack_stack(master_stack, pic1)

   stacked_file = dir + "/images/" + cams_id + "-meteor-stacked.png"
   if master_stack is None:
      print("No detections worth stacking :(")
      # make alternative stack here
   else:
      print(stacked_file)
      master_stack.save(stacked_file)   
   

def get_files(dir, cams_id):
   master_stack = None
   cmd = "mv " + dir  + "/*motion* " + dir + "/data/"
   os.system(cmd)
   print(cmd)
   cmd = "mv " + dir + "/*stacked* " + dir + "/images/"
   os.system(cmd)
   print(cmd)

   glob_dir = dir + "/images/*" + str(cams_id) + "-stacked.png"
   print(glob_dir)
   image_dir = dir + "/images/"
   for filename in (glob.glob(glob_dir)):
      motion_file = filename.replace("-stacked.png", "-motion.txt") 
      motion_file = motion_file.replace("images", "data")
      file_exists = Path(motion_file)
      if file_exists.is_file():


         cmd = "convert " + filename + " -colorspace Gray -format \"%[mean]\" info: "
         try:
            magic = str(subprocess.check_output(cmd, shell=True))
            magic = magic.replace("b", "")
            magic = magic.replace("'", "")
            magic = float(magic)
            print ("Mean Image Brightness:", magic)
         except:
            magic = 30000

         if magic > 0 and magic < 24000:
            print(filename,motion_file)
            pic1 = Image.open(str(filename))
            if master_stack is None:
               master_stack = stack_stack(pic1, pic1)
            else:
               master_stack = stack_stack(master_stack, pic1)
   stacked_file = dir + "/images/" + cams_id + "-night-stack.png"
   if master_stack is None:
      print("No detections worth stacking :(")
      # make alternative stack here
   else:
      print(stacked_file)
      master_stack.save(stacked_file)   

def stack_rejects():
   glob_dir = sd_video_dir + "/proc2/rejects/*-trim*.mp4"
   for filename in (sorted(glob.glob(glob_dir), reverse=True)):
      stack_file = filename.replace(".mp4", "-stacked.png") 
      file_exists = Path(stack_file)
      if file_exists.is_file():
         print("Skip already done.")
      else:
         print("do", filename)
         stack_video(filename)
      

def stack_video(video_file):
   stacked_image = None
   stacked_file= video_file.replace(".mp4", "-stacked.png") 
   frames = load_video_frames(video_file)
   for frame in frames:
      frame_pil = Image.fromarray(frame)

      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)
   if stacked_image is not None:
      stacked_image.save(stacked_file)   
      print ("Saved: ", stacked_file)
   else:
      print("bad file:", video_file)

def batch_night():
  
   dirs = glob.glob(proc_dir + "/*")  
   for dir in dirs:
      for cam_num in range(1,7):
         cam_key = 'cam' + str(cam_num)
         cams_id = json_conf['cameras'][cam_key]['cams_id']
         master_stack = dir + "/images/" + cams_id + "-night-stack.png"
         exists = Path(master_stack)
         if exists.is_file():
            print("SKIP:", master_stack)
         else:
            print(dir, cams_id)
            get_files(dir, cams_id)




cmd = sys.argv[1]

if cmd == 'batch_night':
   batch_night()


if cmd == 'stack_meteors':
   dir = sys.argv[2]
   cams_id = sys.argv[3]
   stack_meteors(dir, cams_id)

if cmd == 'stack_night':
   dir = sys.argv[2]
   cams_id = sys.argv[3]
   get_files(dir, cams_id)
if cmd == 'stack_vid':
   file = sys.argv[2]
   stack_video(file)
   if len(sys.argv) > 3:
      if sys.argv[3] == "mv":
         el = file.split("/")
         file_name = el[-1]
         base_dir = file.replace(file_name, "")
         png = file_name.replace(".mp4", "-stacked.png")
         cmd = "mv " + base_dir + png + " " + base_dir + "images/" 
         print(cmd)
         os.system(cmd)
if cmd == 'stack_rejects':
   stack_rejects()
if cmd == 'stack_dir':
   dir = sys.argv[2] 
   cams_id = sys.argv[3] 
   stack_dir(dir, cams_id)
