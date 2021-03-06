import os
import sys
import time
from lib.VIDEO_VARS import * 

def remove(path):
    if os.path.isdir(path):
        try:
            os.rmdir(path)
        except OSError:
            print("Unable to remove folder: %s" % path)
    else:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            print("Unable to remove file: %s" % path)


def cleanup_video_days(number_of_days, path):
    time_in_secs = time.time() - (number_of_days * 24 * 60 * 60)
    for root, dirs, files in os.walk(path, topdown=False):
        for file_ in files:
           
            full_path = os.path.join(root, file_)
            stat = os.stat(full_path)
            filename, file_extension = os.path.splitext(full_path)

            if stat.st_mtime <= time_in_secs and file_extension!='.json':
                remove(full_path)
 
        #if not os.listdir(root):
        #    #remove(root)
        #    print('REMOVED ROOT ' + root)

        
 
cleanup_video_days(DELETE_VIDS_AFTER_DAYS, VID_FOLDER)