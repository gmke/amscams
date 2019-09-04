import re
import cgitb
import sys
import os.path
import cv2
import glob
import numpy as np
import subprocess 

from pathlib import Path 
from PIL import Image
from lib.VideoLib import load_video_frames
from lib.FileIO import load_json_file
from lib.ImageLib import stack_stack
from lib.ReducerLib import stack_frames
from lib.VIDEO_VARS import *
from lib.FileIO import load_config

# CURRENT CONFIG
JSON_CONFIG = "/home/ams/amscams/conf/as6.json"

# PATH WHERE ALL THE FILES GO 
MAIN_FILE_PATH = "/mnt/ams2/"
CACHE_PATH = MAIN_FILE_PATH + "CACHE/"

# Cache subfolders
FRAMES_SUBPATH= "/FRAMES/"          # For the HD Frames
CROPPED_FRAMES_SUBPATH = "/THUMBS/" # For the Cropped Frames (thumbs)
STACKS_SUBPATH   = "/STACKS/"       # For the Stacks

# PATTERN FOR THE FILE NAMES
# YYYY_MM_DD_HH_MM_SS_MSS_CAM_STATION[_HD].EXT
FILE_NAMES_REGEX = r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{3})_(\w{6})_([^_^.]+)(_HD)?(\.)?(\.[0-9a-z]+$)"
FILE_NAMES_REGEX_GROUP = ["name","year","month","day","hour","min","sec","ms","cam_id","station_id","HD","ext"]

# EXTENSION FOR THE FRAMES
EXT_HD_FRAMES = "_HDfr"
EXT_CROPPED_FRAMES = "_frm"
 

 
# Parses a regexp (FILE_NAMES_REGEX) a file name
# and returns all the info defined in FILE_NAMES_REGEX_GROUP
def name_analyser(file_names):
   matches = re.finditer(FILE_NAMES_REGEX, file_names, re.MULTILINE)
   res = {}
  
   for matchNum, match in enumerate(matches, start=1):
      for groupNum in range(0, len(match.groups())):
         if(match.group(groupNum) is not None):
            res[FILE_NAMES_REGEX_GROUP[groupNum]] = match.group(groupNum)
         groupNum = groupNum + 1

   # Get Name without extension if possible
   if(res is not None and "name" in res):
      res['name_w_ext'] = res['name'].split('.')[0]

   return res



# Return Cache folder name based on an analysed_file (parsed video file name)
# and cache_type = stacks | frames | cropped
def get_cache_path(analysed_file_name, cache_type):
    # Build the path to the proper cache folder
   cache_path = CACHE_PATH + analysed_file_name['station_id'] +  "/" + analysed_file_name['year'] + "/" + analysed_file_name['month'] + "/" + analysed_file_name['day'] + "/" + os.path.splitext(analysed_file_name['name'])[0]

   if(cache_type == "frames"):
      cache_path += FRAMES_SUBPATH
   elif(cache_type == "stacks"):
      cache_path += STACKS_SUBPATH
   elif(cache_type == "cropped"):
      cache_path += CROPPED_FRAMES_SUBPATH
   
   return cache_path


# Get the path to the cache of a given detection 
# create the folder if it doesn't exists 
def does_cache_exist(analysed_file_name,cache_type):

   # Debug
   cgitb.enable()

   # Get Cache Path
   cache_path = get_cache_path(analysed_file_name,cache_type)

   if(os.path.isdir(cache_path)):
      # We return the glob of the folder with all the images
      # print(cache_path + " exist")
      return glob.glob(cache_path+"*.png")
   else:
      # We Create the Folder and return null
      os.makedirs(cache_path)
      # print(cache_path + " created")
      return []



# Get the thumbs (cropped frames) for a meteor detection
# Generate them if necessary
def get_thumbs(video_full_path,analysed_name,meteor_json_file,HD,clear_cache):

   # Do we have them already?
   thumbs = does_cache_exist(analysed_name,"cropped")

   if(len(thumbs)==0 or clear_cache is True):
      # We need to generate the thumbs 
      generate_cropped_frames(video_full_path,analysed_name,meteor_json_file,HD)
   else:
      # We return them
      thumbs = glob.glob(get_cache_path(analysed_name,"cropped")+"*"+EXT_CROPPED_FRAMES+"*.png") 

   return thumbs


# Create the cropped frames (thumbs) for a meteor detection
def generate_cropped_frames(video_full_path,analysed_name,meteor_json_file,HD):

   # Get all the frames as defined in the JSON file

   # We parse the JSON
   meteor_json_file = load_config(meteor_json_file)

   # We get the data
   meteor_frame_data = meteor_json_file['meteor_frame_data']
   print(meteor_frame_data)

   if(HD is True):
      print('WE CROP FROM THE HD VERSION')

   else:
      print('WE CROP FROM THE SD VERSION')


# Get the stacks for a meteor detection
# Generate it if necessary
def get_stacks(video_full_path,analysed_name,clear_cache):
   
   # Do we have the Stack for this detection 
   stacks = does_cache_exist(analysed_name,"stacks")

   if(len(stacks)==0 or clear_cache is True):
      # We need to generate the Stacks 
      # Destination = 
      # get_cache_path(analysed_name,"stacks") + analysed_name['name_w_ext'] + ".png"
      stack_file = generate_stacks(video_full_path,get_cache_path(analysed_name,"stacks")+analysed_name['name_w_ext']+".png")
   else:
      # We hope this is the first one in the folder (it should!!)
      stack_file = stacks[0]

   return stack_file



# Generate the Stacks for a meteor detection
def generate_stacks(video_full_path, destination):

   # Debug
   cgitb.enable() 
   
   # Get All Frames
   frames = load_video_frames(video_full_path, load_json_file(JSON_CONFIG), 0, 1)
 
   stacked_image = None

   # Create Stack 
   for frame in frames:
      frame_pil = Image.fromarray(frame)
      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)

   # Save to destination 
   if stacked_image is not None:
      stacked_image.save(destination)
 
   return destination


# Get All HD Frames for a meteor detection
# Generate them if they don't exist
def get_HD_frames(video_full_path,analysed_name,clear_cache,):
   # Test if folder exists / Create it if not
   HD_frames = does_cache_exist(analysed_name,"frames")

   if(len(HD_frames)==0 or clear_cache is True):
      # We need to generate the HD Frame
      HD_frames = generate_HD_frames(video_full_path,get_cache_path(analysed_name,"frames")+analysed_name['name_w_ext'])
   else:
      # We get the frames from the cache 
      HD_frames = glob.glob(get_cache_path(analysed_name,"frames")+"*"+EXT_HD_FRAMES+"*.png") 
   
   return HD_frames


# Generate HD frames for a meteor detection
def generate_HD_frames(video_full_path, destination):

   # Frames
   frames  = []

   # Debug
   cgitb.enable() 
   
   # Get All Frames
   cmd = 'ffmpeg -y  -hide_banner -loglevel panic  -i ' + video_full_path + ' -s ' + HD_DIM + ' ' +  destination + EXT_HD_FRAMES + '_%04d' + '.png' 
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")

   return glob.glob(destination+"*"+EXT_HD_FRAMES+"*.png")


# Display an error message on the page
def print_error(msg):
   print("<div id='main_container' class='container mt-4 lg-l'><div class='alert alert-danger'>"+msg+"</div></div>")
   sys.exit(0)
   


# GENERATES THE REDUCE PAGE METEOR
# from a URL 
# cmd=reduce2
# &video_file=[PATH]/[VIDEO_FILE].mp4
def reduce_meteor2(json_conf,form):
   
   # Debug
   cgitb.enable()

   # Here we have the possibility to "empty" the cache, ie regenerate the files even if they already exists
   # we just need to add "clear_cache=1" to the URL
   if(form.getvalue("clear_cache") is not None):
      clear_cache = True
   else:
      clear_cache = False

   # Get Video File & Analyse the Name to get quick access to all info
   video_full_path   = form.getvalue("video_file")
   analysed_name = name_analyser(video_full_path)
 
   # Test if the name is ok
   if(len(analysed_name)==0):
      print_error(video_full_path + " <b>is not valid video file name.</b>")
   elif(os.path.isfile(video_full_path) is False):
      print_error(video_full_path + " <b>not found.</b>")
  
   # Is it HD? & retrieve the related JSON file that contains the reduced data
   if("HD" in analysed_name):
      HD = True
      meteor_json_file = video_full_path.replace("_HD.mp4", ".json") 
   else:
      HD = False
      meteor_json_file = video_full_path.replace(".mp4", ".json")

   # Does the JSON file exists?
   if(os.path.isfile(meteor_json_file) is False):
      print_error(meteor_json_file + " <b>not found.</b><br>This detection may had not been reduced yet or the reduction failed.")
   
   # Get the HD frames
   HD_frames = get_HD_frames(video_full_path,analysed_name,clear_cache)

   # Get the stacks
   stack = get_stacks(video_full_path,analysed_name,clear_cache)
    
   # Get the thumbs (cropped frames)
   thumbs = get_thumbs(video_full_path,analysed_name,meteor_json_file,HD,clear_cache)

   print('THUMBS<br>')
   print(thumbs)

   #print('FRAMES<br>')
   #print(HD_frames)

   #print('STACKS<br>')
   #print(stack)