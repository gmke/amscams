import os
import glob
import subprocess 
import datetime
from lib.VIDEO_VARS import * 
from os import listdir, remove
from os.path import isfile, join, exists
from shutil import copyfile


#Return Video length
def getLength(filename):
    cmd = "ffprobe -i "+filename +"  -show_entries format=duration -v quiet"
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    out = [line for line in output.split('\n') if "duration" in line]
    out = out[0][9:]
    return str(datetime.timedelta(seconds=round(float(out),0)))  


#Return Date & Time based on file name (that ends with a date)
def get_meteor_date_ffmpeg(_file):
	fn = _file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "/" + fn[1] + "/" + fn[2] + " " + fn[3] + "\:" + fn[4] + "\:" + fn[5]



#Input: camID, date
#Ouput: list of sd frames found for this date/cam
#ex:camID:010034, date:2019_06_23 
def get_sd_frames(camID,date,limit_frame=False):
    cur_path = IMG_SD_SRC_PATH + date + "/images"
    #print(cur_path)
    frames = [f for f in listdir(cur_path) if camID in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
    
    #DEBUG ONLY!! 
    if(limit_frame is not False):
        frames = frames[1:50]

    if not frames:
        print('NO INPUT FOR VID CamID:' + camID + ' - DATE ' + date)
        print('FOLDER: ' + cur_path)
        return([] , cur_path)
    else:    
        #Move the frames to a tmp folder so we can delete them once we're done with the video
        tmppath = r''+TMP_IMG_HD_SRC_PATH
        
        #Create directory if necessary
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)  

        for frame in frames:
            copyfile(cur_path+'/'+frame, tmppath+frame)
       
        return(sorted(frames) , tmppath)



#Input! camID, date
#Ouput: list of HD frames found for this date or get_sd_frames if no HD frame has been found
#ex: get_hd_frames('010040','2019_07_08')
def get_hd_frames(camID,date,limit_frame=False):
    cur_path = IMG_HD_SRC_PATH
    #test if we have at least one file name - YYYY_DD_MM_HH_ii_SS[_000_]CAM_ID.mp4
    test = [f for f in listdir(cur_path) if f.startswith(date) and f.endswith(camID+'.mp4') and isfile(join(cur_path, f))]
    if not test:
        print('NO HD Frames found - Searching for SD')
        #If nothing is found we try the SD
        return get_sd_frames(camID,date,limit_frame)
    else:
        frames = [f for f in listdir(cur_path) if camID in f and date in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]

        #DEBUG ONLY!! 
        if(limit_frame is not False):
            frames = frames[1:50]
          
        
        #Check temporary folder to store the frames of all the videos
        tmppath = r''+TMP_IMG_HD_SRC_PATH
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)
        else:
            #Clean the directory (maybe necessary)
            files = glob.glob(tmppath+'/*')
            for f in files:
                os.remove(f)
        #We extract one frame per video and add it to the array to return
        toReturn = []
        for idx,vid in enumerate(sorted(frames)):
            vid_out = vid.replace('.mp4','')
            cmd = 'ffmpeg -y -hide_banner -loglevel panic -i '+IMG_HD_SRC_PATH+'/'+vid+' -vframes 1 -f image2 '+ tmppath + vid_out + '.png' 
            output = subprocess.check_output(cmd, shell=True).decode("utf-8")
            toReturn.append( vid_out + '.png' )
            #print(tmppath + '/'  + vid_out + '.png' )
            #print(output)
        return(sorted(toReturn), tmppath)  
 


#Return ffmpeg code for watermarkposition
def get_watermark_pos(watermark_pos):
    if(watermark_pos=='tr'):
        return "main_w-overlay_w-20:20"
    elif (watermark_pos=='tl'):
        return "20:20"    
    elif (watermark_pos=='bl'):
        return "20:main_h-overlay_h-20"
    else: 
       return "main_w-overlay_w-20:main_h-overlay_h-20"


#Return ffmpeg code for Info position (text only + extra text)
def get_text_pos(text_pos, extra_text_here):

    if(extra_text_here==False):
        if(text_pos=='tr'):
            return ("x=main_w-text_w-20:y=20","")
        elif (text_pos=='tl'):
            return ("x=20:y=20","")    
        elif (text_pos=='bl'):
            return("x=20:y=main_h-text_h-20","")
        else: 
            return ("x=main_w-text_w-20:y=main_h-text_h-20","")
    else:
        line_height_spacing = "8"

        if(text_pos=='tr'):
            return ("x=main_w-text_w-20:y=20+line_h+"+line_height_spacing,"x=main_w-text_w-20:y=20")
        elif (text_pos=='tl'):
            return ("x=20:y=20+line_h+"+line_height_spacing,"x=20:y=20")    
        elif (text_pos=='bl'):
            return("x=20:y=main_h-text_h-20","x=20:y=main_h-text_h-20-line_h-"+line_height_spacing)
        else: 
            return ("x=main_w-text_w-20:y=main_h-text_h-20","x=main_w-text_w-20:y=main_h-text_h-20-line_h-"+line_height_spacing)                


#Add text, logo, etc.. to a frame             
def add_info_to_frame(frame, cam_text, extra_text, text_position, extra_text_position, watermark, watermark_position, logo, logo_pos, newpath, dimensions="1920:1080",  enhancement=0):
     

    # Do we have extra text?
    if(extra_text is None):
        with_extra_text = False
        extra_text=''
    elif(extra_text.strip()==''):
        with_extra_text = False
        extra_text=''
    else:
        with_extra_text = True 
 
  
    #if(enhancement!=1):
    cmd = 'ffmpeg -hide_banner -loglevel panic \
            -y \
            -i ' + frame + '    \
            -i ' + watermark  

    if(logo_pos is not 'X'):
        cmd += ' -i ' +  logo
        with_extra_logo= True
    else:
        with_extra_logo= False
 
    
    cmd +=  ' -filter_complex "[0:v]scale='+dimensions+'[scaled]; \
            [scaled]drawtext=:text=\'' + cam_text + '\':fontcolor=white@'+FONT_TRANSPARENCY+':fontsize='+FONT_SIZE+':'+text_position 
    
    #Extra Text
    if(with_extra_text is True):
        cmd+= '[texted];' 
        cmd+= '[texted]drawtext=:text=\''+ extra_text +'\':fontfile=\'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf\':fontcolor=white@'+FONT_TRANSPARENCY+':fontsize='+FONT_SIZE+':'+extra_text_position+'[texted2];[texted2]'  
    else:
        cmd+= '[texted]; [texted]'

    #Watermark
    cmd += 'overlay='+watermark_position;

    #Extra Logo
    if(with_extra_logo is True):
        cmd+= '[wat];[wat]overlay='+logo_pos+'[out];'
    else:
        cmd+= '[out];'

    cmd += '-map "[out]"  ' + newpath + '.png'      


    print("CMD")
    print(cmd)


    #else:
    #    cmd = 'ffmpeg -hide_banner -loglevel panic \
    #            -y \
    #            -i ' + frame + '    \
    #            -i ' + watermark + ' \
    #            -filter_complex "[0:v]scale='+dimensions+'[scaled]; \
    #            [scaled]eq=contrast=1.3[sat];[sat]drawtext=:text=\'' + cam_text + '\':fontcolor=white@'+FONT_TRANSPARENCY+':fontsize='+FONT_SIZE+':'+text_position 
    #    if(with_extra_text is True):
    #        cmd+= '[texted];' 
    #        cmd+= '[texted]drawtext=:text=\''+ extra_text +'\':fontfile=\'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf\':fontcolor=white@'+FONT_TRANSPARENCY+':fontsize='+FONT_SIZE+':'+extra_text_position+'[texted2];[texted2]'  
    #    else:
    #        cmd+= '[texted]; [texted]'
    #
    #
    #    cmd += 'overlay='+watermark_position+'[out]" \
    #           -map "[out]"  ' + newpath + '.png'  


    #print(cmd)
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")  
    return newpath



#Add AMS Logo, Info and eventual logo (todo)
#Resize the frames 
def add_info_to_frames(frames, path, date, camID, extra_text, logo,logo_pos, dimensions="1920:1080", text_pos='bl', watermark_pos='tr', enhancement=0):
 
    newpath = r''+path 
    
    #Create destination folder if it doesn't exist yet
    if not os.path.exists(VID_FOLDER):
        os.makedirs(VID_FOLDER) 
 

    # Do we have extra text?
    if(extra_text is None):
        with_extra_text = False
        extra_text=''
    elif(extra_text.strip()==''):
        with_extra_text = False
        extra_text=''
    else:
        with_extra_text = True
  
    # Info position based on options
    text_position, extra_text_position = get_text_pos(text_pos, (extra_text!=''))
    # Watermark position based on options
    watermark_position = get_watermark_pos(watermark_pos)


    # Do we have extra logo
    if(logo is None):
        with_extra_logo = False 
        logo_position= 'X'
    elif(extra_text.strip()==''):
        with_extra_logo = False
        logo_position = 'X' 
    else:
        with_extra_logo = True 
        logo_position = get_watermark_pos(logo_pos)    


    #Watermark R or L
    if('r' in watermark_pos):
        watermark = AMS_WATERMARK_R
    else:
        watermark = AMS_WATERMARK

    # Treat All frames
    for idx,f in enumerate(frames): 
        #Resize the frames, add date & watermark in /tmp
        text = 'AMS Cam #'+camID+ ' ' + get_meteor_date_ffmpeg(f) + 'UT'
        org_path = path+'/'+ f  
        t_newpath = newpath + '/' + str(idx)
        add_info_to_frame(org_path,text,extra_text,text_position,extra_text_position,watermark,watermark_position,logo,logo_position,t_newpath,dimensions,enhancement)
 
        #Remove the source 
        os.remove(path+'/'+ f)  

    return(newpath)



#Create a video based on a set of frames
def create_vid_from_frames(frames, path, date, camID, fps="25") :
    
    #Create Video based on all newly create frames
    
    #Destination folder
    def_file_path =  VID_FOLDER +'/'+date +'_'+ camID +'.mp4' 
    
    cmd = 'ffmpeg -hide_banner -loglevel panic -y  -r '+ str(fps) +' -f image2 -s 1920x1080 -i ' + path+ '/%d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p ' + def_file_path
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   
    #Rename and Move the first frame in the dest folder so we'll use it as a thumb
    cmd = 'mv ' + path + '/0.png ' +   VID_FOLDER + '/'+date +'_'+ camID +'.png'        
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")

    #DELETING RESIZE FRAMES
    #filelist = glob.glob(os.path.join(path, "*.png"))
    #for f in filelist:
    #    os.remove(f) 

    return def_file_path 