import cgitb
import os
import glob
import sys
import subprocess

from lib.CGI_Tools import print_error
from lib.FileIO import cfe
from lib.Minutes_Tools import minute_name_analyser, MINUTE_STACK_EXT, MINUTE_HD_VID_FOLDER, MINUTE_SD_FOLDER
from lib.Minutes_Details import HD_TMP_STACK_EXT

MANUAL_RED_MINUTE_PAGE_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/minute_manual_reduction_template_step0.html"

# FIRST STEP: WE DEFINE THE ROI
def define_ROI(form):

   # Get stack
   stack = form.getvalue('stack')

   # Build the page based on template  
   with open(MANUAL_RED_MINUTE_PAGE_TEMPLATE_STEP1, 'r') as file:
      template = file.read()

   # We dont have any other info for the page
   template = template.replace("{STACK}",stack) 
    
   # Display Template
   print(template) 


# SECOND STEP: GET HD 
def automatic_detect(form):
   
   # In form we should have
   stack = form.getvalue('stack')
   # ROI
   x = form.getvalue('x_start')
   y = form.getvalue('y_start')
   w = form.getvalue('w')
   h = form.getvalue('h')
 
   # Do we have a HD version on the video of this stack?
   # Ex: 
   # stack    = /mnt/ams2/SD/proc2/2020_02_17/images/2020_02_17_11_12_20_000_010039_HD_tmp_stack.png
   # SD video => /mnt/ams2/SD/proc2/2020_02_17/2020_02_17_11_12_20_000_010039.mp4
   # HD video => /mnt/ams2/HD/2020_02_17_11_12_XX_XXX_010039.mp4
   analysed_minute = minute_name_analyser(stack.replace(HD_TMP_STACK_EXT, MINUTE_STACK_EXT+'.png').replace("-stacked-stacked","-stacked"))
  
   # Search for HD
   HD_path = MINUTE_HD_VID_FOLDER + os.sep + analysed_minute['full'].replace( MINUTE_STACK_EXT+'.png','.mp4')
   HD_found = False
   SD_found = False

   # Search same path:
   if(cfe(HD_path)==1):
      HD_found = True 

   # Search for almost the same path (same hour, same minute)
   if(HD_found is False):
      tmp_almost_path = MINUTE_HD_VID_FOLDER + os.sep + analysed_minute['year'] + '_' + analysed_minute['month'] + '_' + analysed_minute['day'] + '_' + analysed_minute['hour'] + '_' + analysed_minute['min'] + '_' + '*' +  analysed_minute['cam_id'] + '*' + '.mp4'
      filelist = glob.glob(tmp_almost_path)
      if(len(filelist)==1):
         HD_found = True 
         HD_path = filelist[0]

   # HD hasn't been found, we search for SD vid and we resize it
   if(HD_found is False):
      tmp_almost_path = MINUTE_SD_FOLDER + os.sep + analysed_minute['year'] + '_' + analysed_minute['month'] + '_' + analysed_minute['day']  + os.sep + analysed_minute['year'] + '_' + analysed_minute['month'] + '_' + analysed_minute['day'] + '_' + analysed_minute['hour'] + '_' + analysed_minute['min'] + '_' + '*' +  analysed_minute['cam_id'] + '*' + '.mp4'
      filelist = glob.glob(tmp_almost_path)
      if(len(filelist)==1):
         SD_found = True 
         SD_path = filelist[0]

         # But we need to resize it!

   if(HD_found is False and SD_found is False):
      print_error('Impossible to find the related SD or HD video.') 

   # Now we need to crop the frames 
   if(HD_found is True):
      input_path = HD_path
   elif(SD_found is True):
      input_path = SD_path

      output_path = input_path.replace('.mp4','-cropped.mp4')
         
      # Create cropped video
      cmd = 'ffmpeg -i -y '+HD_path+' -filter:v "crop='+w+':'+h+':'+x+':'+y+'" '+ HD_path.replace('.mp4','-cropped.mp4')
      
      # Test if it's doable
      try:
         output = subprocess.check_output(cmd, shell=True).decode("utf-8")   
      except subprocess.CalledProcessError as e:
          print_error("Command " + cmd + "  return on-zero exist status: " + str(e.returncode))

      printoutput_path()
      
   sys.exit(0)
 
 
  

         


