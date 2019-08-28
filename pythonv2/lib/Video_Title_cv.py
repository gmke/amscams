import cv2 
import numpy as numpy
from lib.VIDEO_VARS import * 
from lib.Video_Tools_cv import add_text

TITLE_1280x720 = "/home/ams/amscams/dist/vids/ams_intro/1280x720.mp4"
DEFAULT_TITLE = TITLE_1280x720
 
# This function create a quick video (lenght of DEFAULT_TITLE ~ 3sec )
# with the animated AMS logo and a custom text (ONE LINE TEXT ONLY)
def create_title_video(text,output):

    # Open the blank title video
    cap = cv2.VideoCapture(TITLE_1280x720)

    print('CAP')
    print(cap)

    # Define the codec and create VideoWriter object
    fourcc  = cv2.VideoWriter_fourcc(*'mp4v')
    out     = cv2.VideoWriter(output,fourcc, FPS_HD, (int(cap.get(3)),int(cap.get(4))))
    fc = 0

    while(cap.isOpened()):
        ret, frame = cap.read()

        if ret==True:
 
            # Add Text
            frame = add_text(frame,text,0,0,True)

            # Write the Frame
            out.write(frame)

            # Debug
            cv2.imshow('My Frame', frame)
            ch = cv2.waitKey(1)
            if ch == 27:  # ESC
                break

            fc+=1
        
        else:
            break

    print(str(fc) + " frames")

    cap.release()
    out.release()
     cv2.destroyAllWindows()

    print('OUTPUT ' + output)