import cgitb
import sys
import os
import random
import json

from lib.FileIO import cfe, load_json_file, save_json_file
from lib.VIDEO_VARS import HD_W, HD_H, SD_W, SD_H
from lib.CGI_Tools import redirect_to
from lib.MeteorReduce_Tools import name_analyser
from lib.Archive_Listing import *


# Replace SD video by the resized HD video
def replace_SD(form):
   # Debug
   cgitb.enable()

   json_file = form.getvalue('json_file')

   # Test if JSON exists
   if(cfe(json_file)==0):
      print("{'error':'JSON File not readable,'status':0}")
      sys.exit(0)

   # Get Paths to SD & HD Video
   video_hd_full_path = json_file.replace('.json','-HD.mp4')
   video_sd_full_path = json_file.replace('.json','-SD.mp4')

   # Test if HD exists
   if(cfe(video_hd_full_path)==0):
      print("{'error':'HD file not found,'status':0}")
      sys.exit(0)

   # Test if SD exists
   if(cfe(video_sd_full_path)==0):
      print("{'error':'SD file not found,'status':0}")
      sys.exit(0)

   # Are the SD & HD videos sync'd 
   json_data = load_json_file(json_file)

   hd_ind = -1
   sd_ind = -1
   if('sync' in json_data):
      if('hd_ind' in json_data['sync']):
         hd_ind = json_data['sync']['hd_ind']
      if('sd_ind' in json_data['sync']):
         sd_ind = json_data['sync']['sd_ind']
      
   if(hd_ind != -1 and sd_ind != -1):
      # The video has been sync' 
      # Resize SD and replace HD 
      cmd = "ffmpeg -y -i " + video_hd_full_path + " -vf scale="+str(SD_W)+":"+str(SD_H)+" " + video_sd_full_path
      os.system(cmd)
   
      # We DONT update the JSON!!!
      # if('info' not in json_data):
      #    json_data['info'] = []

      json_data['info']['SD_fix'] = 1
      save_json_file(json_file,json_data)

      # We update the monthly & yearly index accordingly (not optimized but this function will be rarely called)
      a = name_analyser(json_file)
      write_month_index(int(a['month']),int(a['year']))
      write_year_index(int(a['year']))

      # We assume everything went fine
      print(json.dumps("{'status':1}"))


   else:
      # We need to sync the video first.
      print(json.dumps("{'status':0,'msg':'You need to synchronized the SD & HD videos first.}"))

# Replace HD video by the resized SD video
def replace_HD(form):
   
   # Debug
   cgitb.enable()

   json_file = form.getvalue('json_file')

   # Test if JSON exists
   if(cfe(json_file)==0):
      print("{'error':'JSON File not readable,'status':0}")
      sys.exit(0)

   # Get Paths to SD & HD Video
   video_hd_full_path = json_file.replace('.json','-HD.mp4')
   video_sd_full_path = json_file.replace('.json','-SD.mp4')

   # Test if HD exists
   if(cfe(video_hd_full_path)==0):
      print("{'error':'HD file not found,'status':0}")
      sys.exit(0)

   # Test if SD exists
   if(cfe(video_sd_full_path)==0):
      print("{'error':'SD file not found,'status':0}")
      sys.exit(0)
 
   # Are the SD & HD videos sync'd 
   json_data = load_json_file(json_file)
   # We artificially sync the videos
   json_data['sync'] = {'hd_ind':1,'sd_ind':1}
     
  
   # The video has been sync' 
   # Resize SD and replace HD 
   cmd = "ffmpeg -y -i " + video_sd_full_path + " -vf scale="+str(HD_W)+":"+str(HD_H)+" " + video_hd_full_path
   os.system(cmd)

   
   json_data['info']['HD_fix'] = 1
   save_json_file(json_file,json_data)

   # We update the monthly & yearly index accordingly (not optimized but this function will be rarely called)
   a = name_analyser(json_file)
   write_month_index(int(a['month']),int(a['year']))
   write_year_index(int(a['year']))

   # We assume everything went fine
   print(json.dumps("{'status':1}"))
 