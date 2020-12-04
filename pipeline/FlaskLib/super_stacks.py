from flask import Flask, request
from FlaskLib.FlaskUtils import get_template

import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir

def stacks_main(amsid, data) :
   json_file = "/mnt/ams2/SD/proc2/json/" + "main-index.json"
   stats_data = load_json_file(json_file)

   out = """

      <div class='h1_holder d-flex justify-content-between'>
         <h1>Review Stacks by Day<input value='2020/11/28' type='text' data-display-format='YYYY/MM/DD'  data-action='reload' data-url-param='limit_day' data-send-format='YYYY_MM_DD' class='datepicker form-control'></h1>
         <div class='page_h'>Page  1/10</div></div>
         <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
   """


   header = get_template("FlaskTemplates/header.html")
   footer = get_template("FlaskTemplates/footer.html")
   nav = get_template("FlaskTemplates/nav.html")
   template = get_template("FlaskTemplates/super_stacks_main.html")
   json_conf = load_json_file("../conf/as6.json")
   sdirs = glob.glob("/mnt/ams2/meteor_archive/" + amsid + "/STACKS/*")
   for sdir in sorted(sdirs, reverse=True):
      vdir = sdir.replace("/mnt/ams2", "")
      if cfe(sdir,1) == 1:
         stack_day, trash = fn_dir(sdir)
         if stack_day in stats_data:
            data = stats_data[stack_day]
            mets = data['meteor_files']
         date = stack_day
         dsp_date = date.replace("_", "/")
         out += """
         <div class='h2_holder d-flex justify-content-between'>
	       <h2>""" + dsp_date + """ 
               - <a class='btn btn-primary' href=/meteors/""" + amsid + "/?start_day=" + date + ">" + str(mets) + """ Meteors </a>
	      </h2><p><a href=>XX Non-Meteors </a>  </a>
         </div>
         <div class='gallery gal-resize row text-center text-lg-left mb-5'>
         """

         for cam in json_conf['cameras']:
            cams_id = json_conf['cameras'][cam]['cams_id']
            night_stack_file = vdir + "/" + cams_id + "-night-stack.jpg"
            if cams_id in data:
               minutes = data[cams_id]
            else:
               minutes = ""
            out += """
	       <div class='preview'>
	          <a class='mtt' href='/stacks_day/""" + amsid + "/" + date + """/' title='Browse all day'>
                  <img width=320 height=180 alt='""" + date + """' class='img-fluid ns lz' src='""" + night_stack_file + """'>
                  </a><span class='pre-b'>Cam #""" + cams_id + " " + str(minutes) + """ minutes</span>
               </div>
            """
         out += "</div>"
         #all_stacks = glob.glob(sdir + "/*.jpg")
         #for img in all_stacks:
         #   out += img + "<BR>"

   template = template.replace("{HEADER}", header)
   template = template.replace("{MAIN_TABLE}", out)
   template = template.replace("{FOOTER}", footer)
   template = template.replace("{NAV}", nav)
   template = template.replace("{AMSID}", amsid)
   if "obs_name" in json_conf:
      template = template.replace("{OBS_NAME}", json_conf['site']['obs_name'])
   else:
      template = template.replace("{OBS_NAME}", "")
   if "location" in json_conf:
      template = template.replace("{LOCATION}", json_conf['site']['location'])
   else:
      template = template.replace("{LOCATION}", "")
         
   return(template)

def stacks_day_hours(amsid, day, req):
   date = day
   header = get_template("FlaskTemplates/header.html")
   footer = get_template("FlaskTemplates/footer.html")
   nav = get_template("FlaskTemplates/nav.html")
   template = get_template("FlaskTemplates/super_stacks_main.html")
   json_conf = load_json_file("../conf/as6.json")
   sdirs = glob.glob("/mnt/ams2/meteor_archive/" + amsid + "/STACKS/*")

   out = ""
   glob_dir = "/mnt/ams2/meteor_archive/" + amsid + "/STACKS/" + day + "/"
   stack_files = glob.glob(glob_dir + day + "*.jpg")
   last_hour = None 
   
   for sf in sorted(stack_files, reverse=False):
      vsf = sf.replace("/mnt/ams2", "")
      sfn,sd = fn_dir(sf)
     
      el = sfn.split("_")
      hour = el[3]
      cam = el[4].replace(".jpg", "")
      
     
      if last_hour is not None and last_hour != hour:
         out += "</div>"
      if last_hour != hour:
         dsp_date = day.replace("_", "/") + " " + hour + " UTC"
         out += """
         <div class='h2_holder d-flex justify-content-between'>
               <h2>""" + dsp_date + """
              </h2>  </a>
         </div>
         <div class='gallery gal-resize row text-center text-lg-left mb-5'>
         """
      out += """
            <div class='preview'>
               <a class='mtt' href='/stacks_hour/""" + amsid + "/" + date + """/""" + hour + """/' title='Browse hour'>
                  <img width=320 height=180 alt='""" + date + """' class='img-fluid ns lz' src='""" + vsf + """'>
               </a><span class='pre-b'>Cam #""" + cam + """ </span>
            </div>
      """

      last_hour  = hour


   template = template.replace("{MAIN_TABLE}", out)
   template = template.replace("{HEADER}", header)
   template = template.replace("{MAIN_TABLE}", out)
   template = template.replace("{FOOTER}", footer)
   template = template.replace("{NAV}", nav)
   template = template.replace("{AMSID}", amsid)
   if "obs_name" in json_conf:
      template = template.replace("{OBS_NAME}", json_conf['site']['obs_name'])
   else:
      template = template.replace("{OBS_NAME}", "")
   if "location" in json_conf:
      template = template.replace("{LOCATION}", json_conf['site']['location'])
   else:
      template = template.replace("{LOCATION}", "")


   return(template)

def stacks_hour(amsid, day, hour):
   date = day
   out = ""
   json_conf = load_json_file("../conf/as6.json")
   glob_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   stack_files = glob.glob(glob_dir + day + "_" + hour + "*.mp4")
   min_files = {}
   template = make_default_template(amsid, "super_stacks_main.html", json_conf)
   for sf in sorted(stack_files, reverse=False):
      if "trim" in sf or "crop" in sf:
         continue
      fn, dir = fn_dir(sf)
      el = fn.split("_")
      min = el[4]
      cam = el[7].replace(".mp4", "")
      vsf = sf.replace("/mnt/ams2", "")
      sfn = fn.replace(".mp4", "-stacked-tn.jpg") 
      simg = dir + "images/" + sfn
      vsimg = simg.replace("/mnt/ams2", "")
      #out += fn + "<BR>"
      if min not in min_files:
         min_files[min] = {}
         for cam_num in sorted(json_conf['cameras']):
            cams_id = json_conf['cameras'][cam_num]['cams_id']
            min_files[min][cams_id] = ""
      min_files[min][cam] = vsimg 


   for min in sorted(min_files.keys()):

      dsp_date = day.replace("_", "/") + " " + hour + " " + min + " UTC"
      out += """
      <div class='h2_holder d-flex justify-content-between'>
         <h2>""" + dsp_date + """
         </h2>  </a>
      </div>
      <div class='gallery gal-resize row text-center text-lg-left mb-5'>
      """

      for cam in min_files[min]:
         print(cam, min_files[min][cam])
         min_file, min_dir = fn_dir(min_files[min][cam])
         min_link = min_file.replace("-stacked-tn.jpg", "")
         out += """
            <div class='preview'>
                  <a class='mtt' href='/min_detail/""" + amsid + "/" + date + "/" + min_link + """/' title='View Minute'>
                  <img width=320 height=180 alt='""" + date + """' class='img-fluid ns lz' src='""" + min_dir + min_file + """'>
                  </a><span class='pre-b'>Cam #""" + cam + """</span>
            </div>
         """
      out += "</div>"

   template = template.replace("{MAIN_TABLE}", out)

   return(template)

def make_default_template(amsid, main_template, json_conf):
   header = get_template("FlaskTemplates/header.html")
   footer = get_template("FlaskTemplates/footer.html")
   nav = get_template("FlaskTemplates/nav.html")
   template = get_template("FlaskTemplates/" + main_template  )
   template = template.replace("{HEADER}", header)
   template = template.replace("{FOOTER}", footer)
   template = template.replace("{NAV}", nav)
   template = template.replace("{AMSID}", amsid)
   if "obs_name" in json_conf:
      template = template.replace("{OBS_NAME}", json_conf['site']['obs_name'])
   else:
      template = template.replace("{OBS_NAME}", "")
   if "location" in json_conf:
      template = template.replace("{LOCATION}", json_conf['site']['location'])
   else:
      template = template.replace("{LOCATION}", "")
   return template

 
