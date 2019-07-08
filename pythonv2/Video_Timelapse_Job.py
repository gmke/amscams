import glob, os, os.path, sys
import subprocess 
import json
from pathlib import Path 
from os.path import isfile, join, exists
from lib.Video_Timelapse import generate_timelapse, get_meteor_date_ffmpeg
from lib.VIDEO_VARS import * 


#READ THE waiting_jobs file if it exist 
js_file = Path(WAITING_JOBS)
if js_file.is_file():

    #Open the waiting_job & Load the data
    with open(WAITING_JOBS, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            # in case something went wrong
            data = {} 

    #Do we have any jobs
    alljobs = data['jobs']
    if(alljobs is not None):

        cur_idx = 0
        cur_job = 'X'

        #Get the first "waiting" job
        for idx, cur_jobs in enumerate(alljobs):
            if(cur_jobs['status']=='waiting'):
                cur_job = cur_jobs
                cur_idx = idx
                break;

        #print('CURRENT JOB')
        #print(str(cur_job))

        if(cur_job != 'X'):

            #Change Status of the job in the JSON
            data['jobs'][cur_idx]['status'] = 'processing'
            with open(WAITING_JOBS, 'w') as outfile:
                json.dump(data, outfile)

            #Test if we have the HD files or not
            dirs = os.listdir(HD_VID_SRC_PATH)  #Get All files
            if(isfile(dirs[0]) and get_meteor_date_ffmpeg(dirs[0])==cur_job['date']):
                print("WE HAVE HD")
            
            else:
                # WE NEED TO DO IT FROM THE SDs

                # Generate Video
                #print(str(cur_job))
                video_path = generate_timelapse(cur_job['cam_id'],cur_job['date'],cur_job['fps'],cur_job['dim'],cur_job['text_pos'],cur_job['wat_pos'])

                # Update the JSON so we dont process the same vid twice
                data['jobs'][0]['status'] = 'ready'
                data['jobs'][0]['path']   = video_path
                with open(WAITING_JOBS, 'w') as outfile:
                    json.dump(data, outfile)

        