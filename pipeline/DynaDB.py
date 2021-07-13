#!/usr/bin/python3
import redis
import requests
from lib.PipeManager import dist_between_two_points
import math
import os
from datetime import datetime
import json
from decimal import Decimal
import sys
import glob
from lib.PipeUtil import cfe, load_json_file, save_json_file, check_running
import boto3
import socket
import subprocess
from boto3.dynamodb.conditions import Key, Attr
from lib.PipeUtil import get_file_info, fn_dir
from Classes.SyncAWS import SyncAWS

#r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def back_loader(dynamodb, json_conf):
   mdirs = glob.glob("/mnt/ams2/meteors/*")
   meteor_days = []
   update_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
   for mdir in mdirs:
      if cfe(mdir, 1) == 1:
         meteor_days.append(mdir)
   c = 0
   for day_dir in sorted(meteor_days, reverse=True):
      work_file = day_dir + "/" + "work.info"
      day = day_dir.split("/")[-1]
      if cfe(work_file) == 1:
         print("Work file exists we can skip.", day)
      else:
         print("Work file doesn't exist lets do the work.", day)
         os.system("./DynaDB.py ddd " + day)
         work = {}
         work['dyna-ddd'] = update_time
         save_json_file(work_file, work)
         c += 1
      if c > 10:
         print("That's enough for now!")
         exit()

def save_json_conf(dynamodb, json_conf):
   cams = []
   station_id = json_conf['site']['ams_id']
   for cam in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam]['cams_id']
      cams.append(cam_id)
   conf_mini = {}
   conf_mini['station_id'] = json_conf['site']['ams_id']
   conf_mini['operator_name'] = json_conf['site']['operator_name']
   conf_mini['email'] = json_conf['site']['operator_email']
   if "obs_name" not in json_conf['site']:
      conf_mini['obs_name'] = ""
   conf_mini['city'] = json_conf['site']['operator_city']
   conf_mini['state'] = json_conf['site']['operator_state']
   if "operator_country" not in json_conf['site']:
      json_conf['site']['operator_country'] = "USA"
   conf_mini['country'] = json_conf['site']['operator_country']
   conf_mini['lat'] = float(json_conf['site']['device_lat'])
   conf_mini['lon'] = float(json_conf['site']['device_lng'])
   conf_mini['alt'] = float(json_conf['site']['device_alt'])
   conf_mini['passwd'] = json_conf['site']['pwd']
   conf_mini['cameras'] = cams

   conf_mini = json.loads(json.dumps(conf_mini), parse_float=Decimal)
   table = dynamodb.Table('station')
   table.put_item(Item=conf_mini)

   save_json_file("../conf/" + station_id + "_conf.json", conf_mini)

   local_conf = "../conf/" + station_id + "_conf.json"
   cloud_conf = "/mnt/archive.allsky.tv/" + station_id + "/CAL/" + station_id + "_conf.json"
   cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/" 
   os.system("cp " + local_conf + " " + cloud_conf)
   
   # CP CAL FILES
   os.system("cp /mnt/ams2/cal/multi* " + " " + cloud_dir)
   os.system("cp /mnt/ams2/cal/cal_day* " + " " + cloud_dir)
   os.system("cp /mnt/ams2/cal/cal_hist* " + " " + cloud_dir)
   

def create_tables(dynamodb):

   try:
   # station table
      table = dynamodb.create_table(
         TableName='station',
         BillingMode='PAY_PER_REQUEST',
         KeySchema=[
            {
               'AttributeName': 'station_id',
               'KeyType' : 'HASH'
            }
         ],
         AttributeDefinitions=[
            {
               'AttributeName': 'station_id',
               'AttributeType': 'S'
            }
         ]
      ) 
      table.meta.client.get_waiter('table_exists').wait(TableName='stations')
   except:
      print("Station table exists.")

   # obs table
   #if True:
   try:
      table = dynamodb.create_table(
         TableName='meteor_obs',
         BillingMode='PAY_PER_REQUEST',
         KeySchema=[
            {
               'AttributeName': 'station_id',
               'KeyType' : 'HASH'
            },
            {
               'AttributeName': 'sd_video_file',
               'KeyType' : 'RANGE'
            }
         ],
         AttributeDefinitions=[
            {
               'AttributeName': 'station_id',
               'AttributeType': 'S'
            },
            {
               'AttributeName': 'sd_video_file',
               'AttributeType': 'S'
            }
         ]
      ) 
      table.meta.client.get_waiter('table_exists').wait(TableName='meteor_obs')
   #try:
   except:
      print("meteor obs table exists already.")


   # event table
   try:
      table = dynamodb.create_table(
         TableName='x_meteor_event',
         BillingMode='PAY_PER_REQUEST',
         KeySchema=[
            {
               'AttributeName': 'event_day',
               'KeyType' : 'HASH'
            },
            {
               'AttributeName': 'event_id',
               'KeyType' : 'RANGE'
            }
         ],
         AttributeDefinitions=[
            {
               'AttributeName': 'event_day',
               'AttributeType': 'S',
            },
            {
               'AttributeName': 'event_id',
               'AttributeType': 'S',
            }
         ]
      ) 
      table.meta.client.get_waiter('table_exists').wait(TableName='x_meteor_event')
   except: 
      print("Event table exists.")
   print("Made tables.")

def load_obs_month(dynamodb, station_id, wild):
   files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
   for file in sorted(files):
      if cfe(file, 1) == 1:
         day = file.split("/")[-1]
         load_meteor_obs_day(dynamodb, station_id,day)

def load_meteor_obs_day(dynamodb, station_id, day):
   files = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")
   meteors = []
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf and "frame" not in mf:
         meteors.append(mf)

   for meteor_file in meteors:
      insert_meteor_obs(dynamodb, station_id, meteor_file)

def insert_meteor_event(dynamodb=None, event_id=None, event_data=None):
   if cfe("admin_conf.json") == 0:
      print("feature for admin servers only.")
   else:
      admin_conf = load_json_file("admin_conf.json")
      import redis
      r = redis.Redis(admin_conf['redis_host'], port=6379, decode_responses=True)
      admin = 1

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   if event_id is not None and event_data is not None:
      event_data = json.loads(json.dumps(event_data), parse_float=Decimal)
      table = dynamodb.Table('x_meteor_event')
      table.put_item(Item=event_data)
      rkey = "E:" + event_id

      rval = json.dumps(event_data ,cls=DecimalEncoder)
      r.set(rkey,rval)
   # update all impacted obs
   for i in range(0, len(event_data['stations'])):
      # setup vars/values
      station_id = event_data['stations'][i]
      sd_video_file = event_data['files'][i]
      if "solve_status" in event_data:
         solve_status = event_data['solve_status']
      else:
         solve_status = "UNSOLVED"
      event_id_val = event_id + ":" + solve_status

      # setup redis keys for obs and get vals
      okey = "O:" + station_id + ":" + sd_video_file
      oikey = "OI:" + station_id + ":" + sd_video_file
      ro_val = r.get(okey)
      roi_val = r.get(oikey)
      if ro_val is not None:
         ro_val = json.loads(ro_val)
         ro_val['event_id'] = event_id_val
         ro_val = json.dumps(ro_val, cls=DecimalEncoder)
         r.set(okey, ro_val)
      if roi_val is not None:
         roi_val = json.loads(roi_val)
         roi_val['ei'] = event_id_val
         roi_val = json.dumps(roi_val, cls=DecimalEncoder)
         r.set(oikey, roi_val)

      # update DYNA OBS with EVENT ID

      table = dynamodb.Table('meteor_obs')
      response = table.update_item(
         Key = {
            'station_id': station_id,
            'sd_video_file': sd_video_file
         },
      UpdateExpression="set event_id = :event_id_val",
      ExpressionAttributeValues={
         ':event_id_val': event_id_val,
      },
      ReturnValues="UPDATED_NEW"
   )

def insert_meteor_obs(dynamodb, station_id, meteor_file):
   update_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
   if "/mnt/ams2/meteors" not in meteor_file:
      date = meteor_file[0:10]
      meteor_file = "/mnt/ams2/meteors/" + date + "/" + meteor_file

   if cfe(meteor_file) == 1:
      red_file = meteor_file.replace(".json", "-reduced.json")
      mj = load_json_file(meteor_file)
      if "revision" not in mj:
         mj['revision'] = 1

      if "cp" in mj:
         cp = mj['cp']
         if "total_res_px" not in cp:
            cp['total_res_px'] = 9999
         if "cat_image_stars" not in cp:
            cp['cat_image_stars'] = []
         if math.isnan(cp['total_res_px']):
            cp['total_res_px'] = 9999
         calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
      else:
         calib = []
      if cfe(red_file) == 1:
         mjr = load_json_file(red_file)
      else:
         mjr = {}
      sd_vid,xxx = fn_dir(mj['sd_video_file'])
      hd_vid,xxx = fn_dir(mj['hd_trim'])
      if "meteor_frame_data" in mjr:
         meteor_frame_data = mjr['meteor_frame_data']
         duration = len(mjr['meteor_frame_data']) / 25
         event_start_time = mjr['meteor_frame_data'][0][0]
      else:
         meteor_frame_data = []
         event_start_time = ""
         duration = 99
   else:
      return()

   if "best_meteor" in mj:
      peak_int = max(mj['best_meteor']['oint'])
   else:
      peak_int = 0




   obs_data = {
      "sd_video_file": sd_vid,
      "hd_video_file": hd_vid,
      "station_id": station_id,
      "event_start_time": event_start_time,
      "duration": duration,
      "peak_int": peak_int,
      "calib": calib,
      "revision": mj['revision'],
      "last_update": update_time,
      "meteor_frame_data": meteor_frame_data
   }
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   table = dynamodb.Table('meteor_obs')
   try:
      table.update_item(Item=obs_data)
   except:
      table.put_item(Item=obs_data)
   mj['calib'] = calib
   mj['last_update'] = update_time
   save_json_file(meteor_file, mj)

def insert_station(dynamodb, station_id):

   conf_file = "/mnt/ams2/STATIONS/CONF/" + station_id + "_as6.json"
   jss = load_json_file(conf_file)
   js = jss['site'] 

   table = dynamodb.Table('station')
   if "operator_country" not in js:
      js['operator_country'] = ""
   if "obs_name" not in js:
      js['obs_name'] = ""

   station_data = {
      "station_id" : station_id,
      "name" : js['operator_name'],
      "city" : js['operator_city'],
      "state" : js['operator_state'],
      "country" : js['operator_country'],
      "obs_name" : js['obs_name'],
      "lat" : js['device_lat'],
      "lon" : js['device_lng'],
      "alt" : js['device_alt'],
      "passwd" : js['pwd']
   }
   table.put_item(Item=station_data)
   #   "local_ip" : ip,
   #   "vpn_ip" : js['vpn_ip'],
   #   "mac_addr" : js['mac_addr'],


def load_stations(dynamodb):
   files = glob.glob("/mnt/ams2/STATIONS/CONF/*_as6.json")
   for file in files:
      fn, dir = fn_dir(file)
      fn = fn.replace("_as6.json", "")
      insert_station(dynamodb, fn)


def delete_event(dynamodb=None, event_day=None, event_id=None):

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')

   table = dynamodb.Table('x_meteor_event')
   response = table.delete_item(
      Key= {
         "event_day": event_day,
         "event_id": event_id
     }
   )

def delete_obs(dynamodb, station_id, sd_video_file):
   table = dynamodb.Table('meteor_obs')
   response = table.delete_item(
      Key= {
         "station_id": station_id,
         "sd_video_file": sd_video_file
     }
   )


def cache_day(dynamodb, date, json_conf):
   # LOCAL EVENT DIR
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   if cfe(le_dir, 1) == 0:
      os.makedirs(le_dir)
   stations = json_conf['site']['multi_station_sync']
   if json_conf['site']['ams_id'] not in stations:
      stations.append(json_conf['site']['ams_id'])
   events = search_events(dynamodb, date, stations)
   event_file = le_dir + date + "_events.json"
   save_json_file(event_file, events)
   for station in stations:
      obs = search_obs(dynamodb, station, date)
      obs_file = le_dir + station + "_" + date + ".json"
      save_json_file(obs_file, obs)

def select_obs_files(dynamodb, station_id, event_day):
   table = dynamodb.Table("meteor_obs")
   all_items = []
   response = table.query(
      ProjectionExpression='station_id,sd_video_file,revision,event_id',
      KeyConditionExpression=Key('station_id').eq(station_id) & Key('sd_video_file').begins_with(event_day),
      )
   for it in response['Items']:
      all_items.append(it)
   while 'LastEvaluatedKey' in response:
      response = table.query(
         ProjectionExpression='station_id,sd_video_file,revision,event_id',
         KeyConditionExpression=Key('station_id').eq(station_id) & Key('sd_video_file').begins_with(event_day),
         ExclusiveStartKey=response['LastEvaluatedKey'],
         )
      for it in response['Items']:
         all_items.append(it)
   return(all_items)

def get_all_events(dynamodb):
   table = dynamodb.Table("x_meteor_event")
   response = table.scan()
   items = response['Items']
   while 'LastEvaluatedKey' in response:
      response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
      items.extend(response['Items'])
   outfile = "/mnt/ams2/EVENTS/ALL_EVENTS.json"
   save_json_file(outfile, items)


def update_dyna_cache_for_day(dynamodb, date, stations, utype=None):

   if utype is None:
      do_obs = 1
      do_events = 1
   if utype == "events": 
      do_obs = 0
      do_events = 1
   year, mon, day = date.split("_")
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   obs_file = dyn_cache + date + "_ALL_OBS.json" 
   event_file = dyn_cache + date + "_ALL_EVENTS.json" 
   stations_file = dyn_cache + date + "_ALL_STATIONS.json" 

   # remove current files for the day

   # get station list of stations that could have shared obs
   # don't use the API anymore, it times out. Read direct from redis
   all_stations = glob.glob("/mnt/ams2/STATIONS/CONF/*")
   API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi?cmd=get_stations"
   response = requests.get(API_URL)
   content = response.content.decode()
   content = content.replace("\\", "")
   if content[0] == "\"":
      content = content[1:]
      content = content[0:-1]
   jdata = json.loads(content)
   all_stations = jdata['all_vals']
   clusters = make_station_clusters(all_stations)
   cluster_stations = []
   stations = []
   for data in clusters:
      #('AMS8', 32.654, -99.844, 'Hawley', [])
      station, lat, lon, city, partners = data
      if len(partners) > 1:
         cluster_stations.append(data)
   save_json_file(stations_file, clusters)
   cloud_stations_file = stations_file.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/")
   os.system("cp " + stations_file + " " + cloud_stations_file)

   # get the obs for each station for this day
   if do_obs == 1:
      os.system("rm " + obs_file ) 
      all_obs = []
      unq_stations = {}
      for data in cluster_stations:
         station_id = data[0]
         unq_stations[station_id] = 1
         stations.append(station_id)
         obs = search_obs(dynamodb, station_id, date, 1)
         unq_stations[station_id] = len(obs)
         for data in obs:
            all_obs.append(data)
      save_json_file(obs_file, all_obs)
      cloud_obs_file = obs_file.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/")
      os.system("cp " + obs_file + " " + cloud_obs_file)

   if do_events == 1:
      os.system("rm " + event_file ) 
      # get all of the events for this day 
      events = search_events(dynamodb, date, stations, 1)

      save_json_file(event_file, events)
      cloud_event_file = event_file.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/")
      os.system("cp " + event_file + " " + cloud_event_file)
      print("saved" + cloud_event_file)



def search_events(dynamodb, date, stations, nocache=0):
   year, mon, day = date.split("_")
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   if nocache == 0:
      all_events_file = dyn_cache + date + "_ALL_EVENTS.json"   
      aed = load_json_file(all_events_file)
      return(aed)

   # This area should really only be used by the update dyna cache calls

   if nocache == 1:
      use_cache = 0

   #use_cache = 0
   if use_cache == 0:
      if dynamodb is None:
         dynamodb = boto3.resource('dynamodb')


      table = dynamodb.Table('x_meteor_event')
      response = table.query(
         KeyConditionExpression='event_day= :date',
         ExpressionAttributeValues={
           ':date': date,
         } 
      )
      #save_json_file(dc_file, response['Items'])
      return(response['Items'])

def make_station_clusters(all_stations):
   st_lat_lon = []
   for station_data in all_stations:
      #jc = load_json_file(stc)
      station_id = station_data['station_id']
      if "lat" in station_data:
         lat = float(station_data['lat'])
         lon = float(station_data['lon'])
         if "city" in station_data:
            city = station_data['city']
         else:
            city = ""
         if "alt" in station_data:
            alt = float(station_data['alt'])
            st_lat_lon.append((station_id, lat, lon, alt, city))
         else:
            print("NO ALT FOR THIS STATION?", station_data)
      else:
         print(station_id, "STATION DATA INCOMPLETE!")
   cluster_data = []
   for data in st_lat_lon:
      (station_id, lat, lon, alt, city) = data
      matches = []
      for sdata in st_lat_lon:
         (sid, tlat, tlon, talt, tcity) = sdata
         if sid == station_id :
            continue
         dist = dist_between_two_points(lat, lon, tlat, tlon)
         if dist < 450:
            matches.append((sid, dist))
      cluster_data.append((station_id, lat,lon,city,matches))

   return(cluster_data)

def get_all_obs(dynamodb, date, json_conf):
   all_stations = glob.glob("/mnt/ams2/STATIONS/CONF/*")
   if cfe("/mnt/ams2/STATIONS/CONF/clusters.json") == 0:
      make_station_clusters(all_stations)


def search_obs(dynamodb, station_id, date, no_cache=0):
   year, mon, day = date.split("_")
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   all_obs_file = dyn_cache + date + "_ALL_OBS.json"
   final_data = []
   if cfe(all_obs_file) == 1:
      if no_cache == 0:
         all_obs_data = load_json_file(all_obs_file)
         for data in all_obs_data:
            if len(data) > 0:
               if data['station_id'] == station_id:
                  final_data.append(data)
         use_cache = 1
         return(final_data)

   #use_cache = 0
   if use_cache == 0 or no_cache == 1:
      if dynamodb is None:
         dynamodb = boto3.resource('dynamodb')
      table = dynamodb.Table('meteor_obs')
      response = table.query(
         KeyConditionExpression='station_id = :station_id AND begins_with(sd_video_file, :date)',
         ExpressionAttributeValues={
            ':station_id': station_id,
            ':date': date,
         } 
      )
      #save_json_file(dc_file, response['Items'])
      return(response['Items'])
   else:
      return(load_json_file(dc_file))


def get_event(dynamodb, event_id, nocache=1):
   year = event_id[0:4]
   mon = event_id[4:6]
   dom = event_id[6:8]
   date = year + "_" + mon + "_" + dom


   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + dom + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   y = event_id[0:4]
   m = event_id[4:6]
   d = event_id[6:8]
   date = y + "_" + m + "_" + d

   dc_file = dyn_cache + date + "_events.json"   
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      hours_old = tdiff / 60
      if hours_old < 4:
         use_cache = 1   
   if nocache == 0:
      use_cache = 0 

   if use_cache == 1:
      evs = load_json_file(dc_file)
      for ev in evs:
         if ev['event_id'] == event_id:
            return(ev)

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')


   table = dynamodb.Table('x_meteor_event')
   event_day = event_id[0:8]
   y = event_day[0:4]
   m = event_day[4:6]
   d = event_day[6:8]
   event_day = y + "_" + m + "_" + d
   response = table.query(
      KeyConditionExpression='event_day= :event_day AND event_id= :event_id',
      ExpressionAttributeValues={
         ':event_day': event_day,
         ':event_id': event_id,
      } 
   )

   if len(response['Items']) > 0:
      return(response['Items'][0])
   else:
      return([])

def get_obs(station_id, sd_video_file):
   if True:
      url = API_URL + "?cmd=get_obs&station_id=" + station_id + "&sd_video_file=" + sd_video_file
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      if content[0] == "\"":
         content = content[1:]
         content = content[0:-1]
      if "not found" in content:
         data = {}
         data['aws_status'] = False
      else:
         data = json.loads(content)
         data['aws_status'] = True
      return(data)

def get_obs_old2(dynamodb, station_id, sd_video_file):
   date= sd_video_file[0:10]
   year, mon, day = date.split("_")
   obs_data = None
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/"
   cl_day_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   all_obs_file = dyn_cache + date + "_ALL_OBS.json"   
   all_obs_cloud_file = cl_day_dir + date +"_ALL_OBS.json"   
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   if cfe(all_obs_file) == 0:
      if cfe(all_obs_cloud_file) == 1:
         os.system("cp " + all_obs_cloud_file + " " + all_obs_file) 

   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   if cfe(all_obs_file) == 0:
      print("NO OBS FILE!", all_obs_file)
      print(all_obs_cloud_file)
      exit()

   aod = load_json_file(all_obs_file)
   for row in aod:
      if row['station_id'] == station_id and row['sd_video_file'] == sd_video_file:
         obs_data = row
   return(obs_data)

def get_obs_old():
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      if tdiff / 60 < 4:
         dc_obs = load_json_file(dc_file)
         for obs in dc_obs:
            
            if obs['sd_video_file'] == sd_video_file:
               return(obs)

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table('meteor_obs')
   response = table.query(
      KeyConditionExpression='station_id = :station_id AND sd_video_file = :sd_video_file',
      ExpressionAttributeValues={
         ':station_id': station_id,
         ':sd_video_file': sd_video_file,
      } 
   )
   if len(response['Items']) > 0:
      return(response['Items'][0])
   else:
      return(None)


def sync_db_day_new(dynamodb, station_id, event_day):
   dyn_obs_index = select_obs_files(dynamodb, station_id, event_day)

def sync_db_day(dynamodb, station_id, day):
   # remove the cache 
   #cmd = "rm /mnt/ams2/DYCACHE/*.json"
   #os.system(cmd)
   #cmd = "./DynaDB.py cd " + day 
   #os.system(cmd)

   db_meteors = {}
   items = search_obs(dynamodb, station_id, day, 1)
   for item in items:
      db_meteors[item['sd_video_file']] = {}
      db_meteors[item['sd_video_file']]['dyna'] = 1
      if "meteor_frame_data" not in item:
         db_meteors[item['sd_video_file']]['meteor_frame_data'] = item['meteor_frame_data']
      else:
         db_meteors[item['sd_video_file']]['meteor_frame_data'] = []
      if "revision" not in item:
         db_meteors[item['sd_video_file']]['revision'] = 1
      else:
         db_meteors[item['sd_video_file']]['revision'] = item['revision']
   #   if "meteor_frame_data" in item:

   files = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")   
   meteors = []
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf and "frame" not in mf:
         meteors.append(mf)

   local_meteors = {}
   for mf in meteors:
      fn, xxx = fn_dir(mf)
      sd_video_file = fn.replace(".json", ".mp4")
      mfr = mf.replace(".json", "-reduced.json")
      mj = load_json_file(mf)
      if cfe(mfr) == 1:
         mjr = load_json_file(mfr)
      else:
         mjr = {}
         mjr['meteor_frame_data'] = []
      if "revision" not in mj:
         mj['revision'] = 1
      local_meteors[sd_video_file] = {}
      local_meteors[sd_video_file]['revision'] = mj['revision']
      local_meteors[sd_video_file]['meteor_frame_data'] = mjr['meteor_frame_data']
      if "final_vid" in mj:
         local_meteors[sd_video_file]['final_vid'] = mj['final_vid']

   # Do all of the db meteors still exist locally, if not 
   # they have been deleted and should be removed from the remote db
   for dkey in db_meteors:
      if dkey not in local_meteors:
         meteor_file = dkey.replace(".mp4", ".json")
         video_file = dkey
         delete_obs(dynamodb, station_id, video_file)

   # Do all of the local meteors exist in the remote db?
   # if not add them in
   for lkey in local_meteors:
      if lkey not in db_meteors:
         meteor_file = lkey.replace(".mp4", ".json")
         insert_meteor_obs(dynamodb, station_id, meteor_file)
      else:
         if len(db_meteors[lkey]['meteor_frame_data']) == 0:
            print("MISSING MFD!", lkey)

   # Do all of the revision numbers match between the local and db meteors?
   # If the local revision is higher than the remote, we need to push the updates to the DB
   # BUT if the DB revision is higher than the local, we need to pull the MFD from the db and update the meteor objects (populate reduced file and manual overrides in mj) *** The PULL part is only needed once we have remote editing enabled. *** 
   for lkey in local_meteors:
      if lkey not in db_meteors:
         print(lkey, "IGNORE: is not in the DB yet. But should be added in this run." )
      else:
         force = 0
         if local_meteors[lkey]['revision'] > db_meteors[lkey]['revision'] or force == 1:
          
            print(lkey, "UPDATE REMOTE : The local DB has a newer version of this file. " , local_meteors[lkey]['revision'] ,   db_meteors[lkey]['revision'])
            meteor_file = lkey.replace(".mp4", ".json")
            #insert_meteor_obs(dynamodb, station_id, meteor_file)
            obs_data = {}
            obs_data['revision'] = local_meteors[lkey]['revision']
            obs_data['meteor_frame_data'] = local_meteors[lkey]['meteor_frame_data']
            obs_data['last_update'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            if "final_vid" in local_meteors[lkey]:
               print("ADD FINAL DATA!")
               final_vid = local_meteors[lkey]['final_vid']
               final_vid_fn, xxx = fn_dir(final_vid)
               final_data_file = final_vid.replace(".mp4", ".json")
               final_data = load_json_file(final_data_file)
               obs_data['final_vid'] = final_vid_fn
               obs_data['final_data'] = final_data 
            else:
               print("No final data?")

             
            sd_video_file = meteor_file.replace(".json", ".mp4")
            update_meteor_obs(dynamodb, station_id, sd_video_file, obs_data)

         if local_meteors[lkey]['revision'] == db_meteors[lkey]['revision']:
            print(lkey, "GOOD: The remote and local revisions are the same." )

   print("SEARCH OBS:", station_id, day)
   items = search_obs(dynamodb, station_id, day, 1)
   for item in items:
      print("IN DB:", station_id, item['sd_video_file'], item['revision'])
   print(len(items), "items for", station_id)


def update_meteor_obs(dynamodb, station_id, sd_video_file, obs_data=None):

   if obs_data is None:
      day = sd_video_file[0:10]
      jsf = "/mnt/ams2/meteors/" + day + "/" + sd_video_file
      jsf = jsf.replace(".mp4", ".json")
      jsfr = jsf.replace(".json", "-reduced.json")
      mj = load_json_file(jsf)
      mjr = load_json_file(jsfr)
      obs_data = {}
      obs_data['revision'] = mj['revision']
      obs_data['meteor_frame_data'] = mjr['meteor_frame_data']
      obs_data['last_update'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
      if "final_vid" in mj:
         print("ADD FINAL DATA!")
         final_vid = mj['final_vid']
         final_vid_fn, xxx = fn_dir(final_vid)
         final_data_file = final_vid.replace(".mp4", ".json")
         final_data = load_json_file(final_data_file)
         obs_data['final_vid'] = final_vid_fn
         obs_data['final_data'] = final_data
      else:
         print("No final data?")



   dmfd = []
   for data in obs_data['meteor_frame_data']:
      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = data
      dmfd.append((dt,float(fn),float(x),float(y),float(w),float(h),float(oint),float(ra),float(dec),float(az),float(el)))
   obs_data['meteor_frame_data'] = dmfd
   if "final_vid" not in obs_data:
      obs_data['final_vid'] = "" 
   if "final_data" not in obs_data:
      obs_data['final_data'] = {} 

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table("meteor_obs")
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   print("REV:", obs_data['revision'])
   print("ST:", station_id)
   print("F:", sd_video_file)
   if True:
      if "cp" in mj:
         cp = mj['cp']
         if "total_res_px" not in cp:
            cp['total_res_px'] = 9999
         if "cat_image_stars" not in cp:
            cp['cat_image_stars'] = []
         if math.isnan(cp['total_res_px']):
            cp['total_res_px'] = 9999
         calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
      else:
         calib = []

   response = table.update_item(
      Key = {
         'station_id': station_id,
         'sd_video_file': sd_video_file 
      },
      UpdateExpression="set revision = :revision, last_update= :last_update, meteor_frame_data=:meteor_frame_data, final_vid=:final_vid, final_data=:final_data",
      ExpressionAttributeValues={
         ':meteor_frame_data': obs_data['meteor_frame_data'],
         ':final_vid': obs_data['final_vid'],
         ':final_data': obs_data['final_data'],
         ':revision': obs_data['revision'],
         ':last_update': obs_data['last_update']
      },
      ReturnValues="UPDATED_NEW"
   )
   print(response)

def update_event_sol(dynamodb, event_id, sol_data, obs_data, status):
   sol_data = json.loads(json.dumps(sol_data), parse_float=Decimal)
   #obs_data_save = json.loads(json.dumps(obs_data), parse_float=Decimal)
   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')

   table = dynamodb.Table("x_meteor_event")
   event_day = event_id[0:8]
   y = event_day[0:4]
   m = event_day[4:6]
   d = event_day[6:8]
   event_day = y + "_" + m + "_" + d

   if "obs" in sol_data:
      del sol_data['obs']
   for key in obs_data:
      for fkey in obs_data[key]:
         
         #obs_data[key][fkey]['calib'][6] = float(obs_data[key][fkey]['calib'][6])
         if key in obs_data:
            if fkey in obs_data[key]:
               if 'calib' in obs_data[key][fkey]:
                  del obs_data[key][fkey]['calib']
         
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
      
   #obs_data = {}
   #sol_data = {}

   response = table.update_item(
      Key = {
         'event_day': event_day ,
         'event_id': event_id
      },
      UpdateExpression="set solve_status=:status, solution=:sol_data, obs=:obs_data  ",
      ExpressionAttributeValues={
         ':status': status ,
         ':sol_data': sol_data,
         ':obs_data': obs_data
      },
      ReturnValues="UPDATED_NEW"
   )
         #':obs_data': obs_data,
   print("UPDATED EVENT WITH SOLUTION.")
   url = API_URL + "?recache=1&cmd=get_event&event_id=" + event_id
   response = requests.get(url)
   content = response.content.decode()
   content = content.replace("\\", "")
   #data = json.loads(content)
   #print("RECACHE REDIS!", content)
   #event_data = get_event(dynamodb, event_id, nocache=1)

   #event_data = json.loads(event_data, parse_float=Decimal)
  # rval = json.dumps(event_data, cls=DecimalEncoder)
  # rkey = "E:" + event_id
  # r.set(rkey,rval)
  # print(rkey,rval)
  # print("REDIS:")
   return response



def update_event(dynamodb, event_id, simple_status, wmpl_status, sol_dir):
   table = dynamodb.Table("x_meteor_event")
   event_day = event_id[0:8]
   y = event_day[0:4]
   m = event_day[4:6]
   d = event_day[6:8]
   event_day = y + "_" + m + "_" + d

   response = table.update_item(
      Key = {
         'event_day': event_day ,
         'event_id': event_id
      },
      UpdateExpression="set simple_solve=:simple_status, WMPL_solve=:wmpl_status, sol_dir=:sol_dir",
      ExpressionAttributeValues={
         ':simple_status': simple_status,
         ':wmpl_status': wmpl_status, 
         ':sol_dir': sol_dir 
      },
      ReturnValues="UPDATED_NEW"
   )
   print(response)
   print("UPDATED EVENT WITH SOLUTION.")
   url = API_URL + "?recache=1&cmd=get_event&event_id=" + event_id
   print(url)
   response = requests.get(url)
   content = response.content.decode()
   content = content.replace("\\", "")
   #data = json.loads(content)
   print(content)

   return response

def do_dyna_day(dynamodb, day):
   # do everything to prep and load meteors
   # to get them ready for solving
   # and then also download event data for this site
   # and update the mse info in the json for each site
   # also sync prev imgs for mse events
   cmd = "./Process.py reject_masks " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py reject_planes " + day
   print(cmd)
   os.system(cmd)
   
   cmd = "./Process.py confirm " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py remaster_day " + day
   #print(cmd)
   os.system(cmd)

   #cmd = "./DynaDB.py sync_db_day " + day
   cmd = "/usr/bin/python3 AWS.py sd " + day
   print(cmd)
   os.system(cmd)

   cmd = "./DynaDB.py cd " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py ded " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py sync_prev_all " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py sync_final_day " + day
   print(cmd)
   os.system(cmd)

   cmd = "./DynaDB.py cd " + day
   print(cmd)
   os.system(cmd)


def update_mj_events(dynamodb, date):
   print("UPDATE MJ FOR DYNA EVENTS FOR", date)
   json_conf = load_json_file("../conf/as6.json")
   stations = json_conf['site']['multi_station_sync']
   amsid = json_conf['site']['ams_id']
   if amsid not in stations:
      stations.append(amdid)
   events = search_events(dynamodb, date, stations)
   year, mon, day = date.split("_")
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   save_json_file(dyn_cache + date + "_events.json",events)
   my_files = []
   for event in events:
      mse = {}
      mse['start_datetime'] = []
      mse['stations'] = []
      mse['files'] = []
 
      if "solution" in event:
         mse['solution'] = event['solution']
      if "orb" in event:
         mse['orb'] = event['orb']
      for i in range(0, len(event['stations'])):
         mse['stations'].append(event['stations'][i])
         mse['files'].append(event['files'][i])
         mse['event_id'] = event['event_id']
      
         if event['stations'][i] == amsid:
            my_files.append((event['files'][i], mse))
            print("my files:", event['files'][i])
        
   mse_log = "/mnt/ams2/meteors/" + date + "/" + amsid + "_" + date + "_mse.info" 
   mse_db = {}
   print("SAVED:", dyn_cache + date + "_events.json")
   for file,ev in my_files:
      mse_db[file] = ev
      print("UPDATE LOCAL FILE:", file, ev)

   save_json_file(mse_log, mse_db)
   print("saved:", mse_log)

def orbs_for_day(date,json_conf):
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   event_file = le_dir + date + "_events.json"
   orbs_file = le_dir + date + "_orbs.json"
   events = load_json_file(event_file)

   
   orbs = {}
   for ev in events:
      if "solution" in ev:
         if "orb" in ev['solution']:
            o = ev['solution']['orb']
            print(ev['event_id'],ev)
            event_url = ev['solution']['sol_dir'].replace("/mnt/ams2/meteor_archive/", "http://archive.allsky.tv/")
            print(event_url)
            op = {}
            op['name'] = ev['event_id']
            op['epoch'] = o['jd_ref']
            op['utc_date'] = min(ev['start_datetime'])
            op['T'] = o['jd_ref']
            op['vel'] = 0
            op['a'] = o['a']
            op['e'] = o['e']
            op['I'] = o['i']
            op['Peri'] = o['peri']
            op['Node'] = o['node']
            op['q'] = o['q']
            op['M'] = o['mean_anomaly']
            op['P'] = o['T']
            orbs[ev['event_id']] = op
   save_json_file(orbs_file, orbs)
   print("saved.", orbs_file)
 
if __name__ == "__main__":
   dynamodb = boto3.resource('dynamodb')
   json_conf = load_json_file("../conf/as6.json")
   cmd = sys.argv[1]
   if cmd == "sync_db_day" or cmd == "sdd":
      station_id = json_conf['site']['ams_id']
      sync_db_day(dynamodb, station_id, sys.argv[2])
   if cmd == "sync_db_day_new" or cmd == "sdd":
      station_id = json_conf['site']['ams_id']
      sync_db_day_new(dynamodb, station_id, sys.argv[2])

   if cmd == "ct":
      create_tables(dynamodb)
   if cmd == "ls":
      load_stations(dynamodb)
   if cmd == "del_obs":
      station_id = json_conf['site']['ams_id']
      meteor_file = sys.argv[2]
      delete_obs(dynamodb, station_id, meteor_file)
   if cmd == "add_obs":
      station_id = json_conf['site']['ams_id']
      meteor_file = sys.argv[2]
      insert_meteor_obs(dynamodb, station_id, meteor_file)
   if cmd == "update_obs":
      station_id = json_conf['site']['ams_id']
      meteor_file = sys.argv[2]
      update_meteor_obs(dynamodb, station_id, meteor_file)

   if cmd == "search_obs":
      station_id = json_conf['site']['ams_id']
      search_obs(dynamodb, station_id, sys.argv[2])
   if cmd == "load_day":
      station_id = json_conf['site']['ams_id']
      load_meteor_obs_day(dynamodb, station_id, sys.argv[2])
   if cmd == "load_month":
      station_id = json_conf['site']['ams_id']
      load_obs_month(dynamodb, station_id, sys.argv[2])
   if cmd == "ddd":
      do_dyna_day(dynamodb, sys.argv[2])

   if cmd == "dedm":
      wild = sys.argv[2]
      files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
      for file in sorted(files):
         day = file.split("/")[-1]
         cmd = "./Process.py ded " + day
         os.system(cmd)

   if cmd == "dddm":
      wild = sys.argv[2]
      files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
      for file in sorted(files):
         day = file.split("/")[-1]
         print(file, day)
         do_dyna_day(dynamodb, day)
   if cmd == "umje":
      update_mj_events(dynamodb, sys.argv[2])
   if cmd == "sync_year":
      wild = sys.argv[2]
      station_id = json_conf['site']['ams_id']
      files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
      for file in sorted(files):
         day = file.split("/")[-1]
         print(file, day)
         sync_db_day(dynamodb, station_id, day)
   if cmd == "cache_day" or cmd == "cd":
      day = sys.argv[2]
      cache_day(dynamodb, day, json_conf)
   if cmd == "orbs_for_day" or cmd == "ofd":
      day = sys.argv[2]
      orbs_for_day(day, json_conf)
   if cmd == "save_conf":
      save_json_conf(dynamodb, json_conf)
   if cmd == "back_load":
      back_loader(dynamodb, json_conf)
   if cmd == "get_all_obs":
      get_all_obs(dynamodb, sys.argv[2], json_conf)
   if cmd == "get_all_events":
      get_all_events(dynamodb)
   if cmd == "select_obs_files":
      # station_id and then date please
      select_obs_files(dynamodb, sys.argv[2], sys.argv[3])

   if cmd == "udc":
      if len(sys.argv) > 3:
         utype = sys.argv[3]
      else:
         utype = None
      update_dyna_cache_for_day(dynamodb, sys.argv[2], json_conf, utype)
