from lib.PipeUtil import cfe, load_json_file, save_json_file, get_file_info
from pushAWS import make_obs_data
import glob
from datetime import datetime

"""
 Reconcile -- Class for reconciling meteor data with latest detection, redis storage, calib, media, cloud, backup/archive and AWS. 



"""

class Reconcile():
   def __init__(self, meteor_file=None, min_file=None,detect_obj=None):
      self.rec_file = "../conf/reconcile.json"
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      if cfe(self.rec_file) == 1:
         self.rec_data = load_json_file(self.rec_file)
      else:
         self.rec_data = {}
         self.mfiles = []
         self.get_all_meteor_files()

         self.rec_data['mfiles'] = self.mfiles
         save_json_file(self.rec_file, self.rec_data)
      if "meteor_index" not in self.rec_data:
         self.rec_data['meteor_index'] = {}   
      if "day_data" not in self.rec_data:
         self.rec_data['day_data'] = {}   
      c = 0


      for root_file in self.rec_data['mfiles']:
         print(c, root_file)   
         date = root_file[0:10]
         meteor_file = "/mnt/ams2/meteors/" + date + "/" + root_file + ".json"
         if root_file not in self.rec_data['meteor_index']:
            print("GET OBS:", root_file)
            self.rec_data['meteor_index'][root_file] = {}
            self.rec_data['meteor_index'][root_file]['last_update'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file) 
         else:
            print("OBS GET DONE.")

         c += 1

      save_json_file(self.rec_file, self.rec_data)


   def reconcile_scans(self):
      print("REC SCANS")
      """
        LOOP OVER ALL METEORS IN THE REC PERIOD
        CHECK IF THE 3 SCANS WERE DONE YET, meteor_scan, meteor_crop_scan, hd_crop_scan
        RE-RUN THE ONES THAT AREN'T DONE YET. 

      """

   def reconcile_media(self):
      print("REC MEDIA")
      """ 
          FOR MEDIA WE WANT TO DO THIS IN 3 PHASES
          1) Push the AWS data and prev thumbnail and that is it
          2) For successful meteor scan meteors upload the SD video, ROI video, ROI thumb, SD STACK IMAGE (here we wil have 5 total files: prev.jpg, SD.jpg, ROI.jpg SD.mp4 ROI.mp4
          3) For MSM or HC confirmed meteors, push the HD files too -- we will add HD.mp4 HDROI.mp4 HD.jpg and ROIHD.jpg (4 more files)
          If the meteor is confirmed and all media is sync'd there should be a total of 9 files for the meteor inside the METEOR_SCAN DIR
          If these don't exist yet, then the scan was not run, but should be. 

          * CAP THIS / ONLY DO OPTION 1 if there are more than 100 meteors for the day. 
          * IF THERE ARE MORE THAN 200 meteors, abort unless it is Aug 8-16 or Dec 10-16
      """
      for key in self.rec_data['meteor_index']:
         print(key)


   def get_all_meteor_files(self):
      mdirs = glob.glob("/mnt/ams2/meteors/*")
      mds = []
      for md in mdirs:
         if cfe(md,1) == 1:
            mds.append(md + "/")

      for md in sorted(mds,reverse=True):
         print(md)
         self.get_mfiles(md)

   def get_mfiles(self, mdir):
      temp = glob.glob(mdir + "/*.json")
      for json_file in temp:
          if "frame" not in json_file and "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            root = json_file.split("/")[-1].replace(".json", "")

            self.mfiles.append(root)
