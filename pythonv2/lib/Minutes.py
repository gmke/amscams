import glob
import re
import cgitb

from lib.Get_Cam_ids import get_the_cam_ids

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/browse_minutes.html"


# Build the Cam multi-selector
def get_cam_ids(selected_cam_ids):
   toReturn = ""
   cam_ids = get_the_cam_ids()
   for cam_id in cam_ids:
      toReturn += "<option value='"+cam_id+"'>"+cam_id+"</option>"
   return toReturn


# Generate Browse Minute page
def browse_minute(form):
   # Debug
   cgitb.enable()

   period   = form.getvalue('period')
   cam_ids = form.getvalue('cams_ids')

   print("CAMS IDS")
   print(cam_ids)

   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   # Build the cam ids dd
   template = template.replace('{CAM_IDS}',get_cam_ids(cam_ids))
   
   # Display Template
   print(template)

