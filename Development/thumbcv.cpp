//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%                                  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%   HCAMS Meteor Thumbnails 1.00   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%                                  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//
//  Version 1.00 reads H.264 MP4 files and creates thumbnails. Output is a PNG formatted thumbnail for 
//  each camera and each MP4 spanning the entire night's collection in the user specified folder.
//
//  MP4 assumed naming convention is a 34 character string:   YYYY_MM_DD_HH_MM_SS_MSC_CAMERA.mp4
//                                                     e.g.   2018_11_18_04_23_16_000_010005.mp4
//
//  The app is launched from a CAMS/RunFolder with an argument list containing:
//      Folder pathname containing the H.264 video MP4 files to be processed
//      If the argument is not there, a dialog box will let the user navigate to the folder
//      
//  Note that the pathname of the configuration parameter file is assumed to be located
//      in the .../CAMS/RunFolder and named:  HCAMS_Config_Parameters.txt
//      Only the FFMPEG and FFPROBE paths are used from the config file.
//
//  Thumbnail output files are placed in the same folder as the input MP4s 
//
//
//  Date         Description
//  ----------   ----------------------------------------------------------------------------------------
//  2018-11-30   Initial implementation based HCAMS_Detection_Driver.c
//
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#pragma warning(disable: 4996)  // disable warning on strcpy, fopen, ...


//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#ifdef _WIN32 /************* WINDOWS ******************************/

    #include <windows.h>    // string fncts, malloc/free, system
    #include <WinBase.h>

    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    #include <math.h>
    #include <time.h>

    #include "TimeFunctions.h"
    #include "SystemFileFunctions.h"
    #include "UtilityFunctions.h"
    #include "FFMPEG_IOFunctions.h"
    #include "HCAMS_IOFunctions.h"
    #include "CAMS_IOFunctions.h"
    #include "lodepng.h"

    //void   BmpFileWriteBytes(char *filename, long nrows, long ncols, unsigned char *fimage_ptr);

#else  /********************  LINUX  ******************************/


#include <opencv2/opencv.hpp>
#include <opencv2/tracking.hpp>
#include <opencv2/core/ocl.hpp>
#include <unistd.h>
using namespace cv;
using namespace std;


    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    #include <math.h>
    #include <time.h>
    #include <unistd.h>

    #include "../common/TimeFunctions.h"
    #include "../common/SystemFileFunctions.h"
    #include "../common/UtilityFunctions.h"
    #include "../common/FFMPEG_IOFunctions.h"
    #include "../common/HCAMS_IOFunctions.h"
    #include "../common/CAMS_IOFunctions.h"
    #include "lodepng.h"

#endif /***********************************************************/



//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

int main( int argc, char *argv[] )
{
int              nrows, ncols, npixels, status, nframes_file;
long             cameranumber, kpixel;

float            framerateHz;
double           version;

FILE            *FileDirListing;

char                listing_pathname[256];
char         parametersfile_pathname[256];
char                imagery_filename[256];
char          imageryfolder_pathname[256];
char            imageryfile_pathname[256];
char                    png_filename[256];
char                    motion_filename[256];


unsigned short   *dummyframe = NULL;
unsigned char    *imagefrm   = NULL;
unsigned char    *maxpixel   = NULL;


struct DateAndTime         ut;

struct HCAMSparameters     params;

// opencv vars
Mat frame, gray, frameDelta, thresh, firstFrame;
vector<vector<Point> > cnts;




    //################ Software version number

    version = 1.00;


    //################ Get the location of the mp4 video files

    if( argc < 2 )  GetMP4_Folder(imageryfolder_pathname);

	else            strcpy(imageryfolder_pathname, argv[1]);

	EndsInSlash(imageryfolder_pathname);


	//################  Read the configuration parameters for FFMPEG and FFPROBE paths

	strcpy(parametersfile_pathname, "HCAMS_Config_Parameters.txt");

	ReadConfigFile_HCAMSparameters(parametersfile_pathname, &params);


	//################  Get the listing of all the MP4 files in the imagery folder and open the listing file

    strcpy( listing_pathname, "MP4FileListing.txt"  );

	GenerateExtensionBasedFileListing(imageryfolder_pathname, "mp4", listing_pathname );

    if( ( FileDirListing = fopen( listing_pathname, "rt" ) ) == NULL )  {
        fprintf( stdout, " File directory listing %s not found (or not generated)\n\n", listing_pathname );
        fprintf( stderr, " File directory listing %s not found (or not generated)\n\n", listing_pathname );
        Delay_msec(15000);
        exit(1);
    }


	//##########################################################################################################
	//    Loop over all the MP4 files and generate the maxpixel thumbnail image
	//##########################################################################################################

		while (fgets(imagery_filename, 256, FileDirListing) != NULL) {

			imagery_filename[34] = '\0';

			sscanf(imagery_filename, "%4d_%2d_%2d_%2d_%2d_%2d_%3d_%6ld.",
				&ut.year, &ut.month, &ut.day, &ut.hour, &ut.minute, &ut.second, &ut.msec, &cameranumber);

			printf("Thumbnailing  %s\n", imagery_filename);


			//-------- Open the mp4 file for reading

			strcpy(imageryfile_pathname, imageryfolder_pathname);

			strcat(imageryfile_pathname, imagery_filename);

			Read_FFMPEG_Pipe_Open(params.FFMPEGpath, params.FFPROBEpath, 2, imageryfile_pathname, &nrows, &ncols, &nframes_file, &framerateHz);

			npixels = (long)nrows * (long)ncols;


			//################  Allocate memory for the image frame and maxpixel arrays

			imagefrm = (unsigned char*)malloc(npixels * sizeof(unsigned char));
			maxpixel = (unsigned char*)malloc(npixels * sizeof(unsigned char));

			if (imagefrm == NULL || maxpixel == NULL) {
				fprintf(stdout, " ERROR ===> imagefrm and maxpixel memory not allocated\n");
				fprintf(stderr, " ERROR ===> imagefrm and maxpixel memory not allocated\n");
				Delay_msec(15000);
				exit(1);
			}


			//-------- Read through the image sequence filling out the maxpixel product

			memset(maxpixel, 0, npixels);
// main video loop here
Mat firstFrame = Mat(480,640, CV_8UC1);
Mat new_frame = Mat(480,640, CV_8UC1);
int frame_count;
int ffset;
ffset = 0;
frame_count = 0;
int motion;
motion = 0;
int frame_motion;
frame_motion = 0;
int motion_frames[2000]; 
int px_frames[2000]; 
int cons_frames[2000]; 
int max_cons_px;

int bp_total;
int this_bp_total;
int bp_avg;
int this_bp_factor;

max_cons_px = 0;
this_bp_factor = 0;
this_bp_total = 0;
bp_total = 0;
bp_avg = 0;

status = Read_FFMPEG_Pipe_Image(imagefrm, dummyframe);

/*
memcpy(firstFrame.data, imagefrm, sizeof(unsigned char)*long(nrows)*long(ncols)) ;

Rect r=Rect(0,440,305,40);
rectangle(firstFrame, r, Scalar(20,0,00), -1,8,0);
blur(firstFrame, firstFrame, Size(5, 5));

double area;
*/

			while (1) {

                                
				status = Read_FFMPEG_Pipe_Image(imagefrm, dummyframe);
/*
                                if (frame_count == 0) {
                                   memcpy(firstFrame.data, imagefrm, sizeof(unsigned char)*long(nrows)*long(ncols)) ;
                                   Rect r=Rect(0,440,305,40);
                                   rectangle(firstFrame, r, Scalar(20,0,00), -1,8,0);
                                   //GaussianBlur(firstFrame, firstFrame, Size(21, 21), 0);
                                   blur(firstFrame, firstFrame, Size(5, 5));
                                }

                                //Mat frameDelta = Mat(480, 640, CV_8UC1);
                                //new_frame.data = imagefrm;
                                memcpy(new_frame.data, imagefrm, sizeof(unsigned char)*long(nrows)*long(ncols)) ;
                                //mask out time

                                if (frame_count % 3 == 1) {
                                rectangle(new_frame, r, Scalar(20,0,00), -1,8,0);
                                //GaussianBlur(new_frame, new_frame, Size(5, 5), 0);
                                blur(new_frame, new_frame, Size(5, 5));
                                //compute difference between first frame and current frame
                                absdiff(firstFrame, new_frame, frameDelta);
                                threshold(frameDelta, thresh, 10, 255, THRESH_BINARY);
                                findContours(thresh, cnts, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE);
                                if (cnts.size() > 1) {
                                   //printf("Motion:%s : %d\n", imagery_filename,frame_count);
                                   cout << cnts.size() <<endl;
                                   motion = 1;
                                   frame_motion = 1;
                                }
                                else {
                                   frame_motion = 0;
                                }
*/
                                motion_frames[frame_count] = frame_motion;
/*
                                //cout << "Thresh Width: " << thresh.cols <<endl;
*/
/*
                                for(int i = 0; i< cnts.size(); i++) {
                                   area = contourArea(cnts[i]);
                                   if(contourArea(cnts[i]) < 4) {
                                      //cout << "area = " << area << endl; 
                                      continue;
                                   }
                                   //else {
                                   //   printf("Motion:%s : %d\n", imagery_filename,frame_count);
                                   //   cout << "area = " << area << endl; 
                                   //}
                                   //putText(frame, "Motion Detected", Point(10, 20), FONT_HERSHEY_SIMPLEX, 0.75, Scalar(0,0,255),2);
 
                                }
                                } //end % 2
*/
                                /*
                                */
/*
                                imshow("Camera", new_frame);

                                if(waitKey(1) == 27){
                                   //exit if ESC is pressed
                                   break;
                                }
                                imshow("Camera2", frameDelta);
                                if(waitKey(1) == 27){
                                   //exit if ESC is pressed
                                   break;
                                }
*/

/*
*/



                                //cout << "Width: " << new_frame.cols <<endl;
/*


*/


                                frame_count = frame_count + 1;


				if (status > 0)  break;    //... EOF reached or file error (pipe was closed for status > 0)

				for (kpixel = 0; kpixel < npixels; kpixel++) {
                                        

					if (maxpixel[kpixel] < imagefrm[kpixel])  {
                                           maxpixel[kpixel] = imagefrm[kpixel];
                                             if (frame_count > 60 ) {
                                                if (imagefrm[kpixel] >= 60) {
                                                   bp_total = bp_total + 1;
                                                   this_bp_total = this_bp_total + 1;
                                                }
                                             }
                                        }

	 			}
                                if (frame_count > 50) {
                                   bp_avg = bp_total / (frame_count -50);
                                }
                                if (bp_avg > 0) {
                                   this_bp_factor = (int)(this_bp_total / bp_avg);
                                } 
                                else {
                                   this_bp_factor = 0;
                                }
                                if (this_bp_factor >= 1) {
                                   max_cons_px = max_cons_px + 1; 
                                   printf("PX:%d,%d,%d,%d,X%d,%d\n", frame_count, bp_total, bp_avg, this_bp_total,this_bp_factor, max_cons_px);
                                }
                                else {
                                   max_cons_px = 0; 
                                }
                                
                                px_frames[frame_count] = this_bp_factor;
                                cons_frames[frame_count] = max_cons_px;
                                   this_bp_total = 0;
                               

			}  //... end of loop reading all frames from the mp4 file


		    //======== Write out the full thumbnail image

		    sprintf(png_filename, "%sThumb_%04i_%02i_%02i_%02i_%02i_%02i_%03i_%06li.png", imageryfolder_pathname, 
			        ut.year, ut.month, ut.day, ut.hour, ut.minute, ut.second, ut.msec, cameranumber);
		    sprintf(motion_filename, "%sThumb_%04i_%02i_%02i_%02i_%02i_%02i_%03i_%06li-motion.txt", imageryfolder_pathname, 
			        ut.year, ut.month, ut.day, ut.hour, ut.minute, ut.second, ut.msec, cameranumber);

                    //write motion file
                    if (motion == 1) {
                       FILE * mfp;
                       mfp = fopen(motion_filename, "w");
                       //fprintf(mfp, "motion detected");
                       for (int i = 0; i <= frame_count -1; i++) {
                          fprintf(mfp, "%d,%d,%d,%d\n",i,motion_frames[i],px_frames[i],cons_frames[i]);
                          if (motion_frames[i] == 1) {
                          }
              
                       }
                       fclose(mfp);
                    } 

		    //BmpFileWriteBytes(png_filename, nrows, ncols, maxpixel);

			lodepng_encode_file(png_filename, maxpixel, ncols, nrows, LCT_GREY, 8);

			free(imagefrm);
			free(maxpixel);
                        frame_count = 0;
                        motion = 0;

		}  //... end of mp4 file loop



    //######################################################################################################################

	//................

    fprintf( stdout, "\nProcessing Complete\n");
    fprintf( stderr, "\nProcessing Complete\n");

    //Delay_msec(2000);

}


//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


//=========================================================================
//                           BmpFileWriteBytes
//-------------------------------------------------------------------------
//
// Purpose:  Function to write a gray scale bmp file from a image array.
//           The output image is truncated to byte data and file is only
//           a single 8-bit depth plane.
//           
//
// Inputs:  *filename        full file and pathname of image data file
//          *fimage          pointer to imagery structure containing:
//             .nrows           number of rows
//             .ncols           number of columns
//             .data_ptr        pointer to short array
//
//
// Revision History:
//    1.00  01/12/2014  P. Gural   Creation
//
//=========================================================================
/*
void   BmpFileWriteBytes(char *filename, long nrows, long ncols, unsigned char *fimage_ptr)
{

	long           krow, kcol;
	unsigned char *in_ptr, *out_ptr, *flipped_ptr, kquad[4];
	BITMAPFILEHEADER    bmfh;     //stores information about the file format
	BITMAPINFOHEADER    bmih;     //stores information about the bitmap
	FILE                *bmpfile; //stores file pointer


								  //------- first copy the flipped up-down image into a temporary array

	flipped_ptr = (unsigned char *)malloc(nrows * ncols * sizeof(unsigned char));

	if (flipped_ptr == NULL) {
		printf(" ====> ERROR: Memory for flipped image not allocated in BmpFileWriteBytes \n");
		Delay_msec(5000);
		exit(1);
	}

	in_ptr = fimage_ptr + (nrows - 1) * ncols;
	out_ptr = flipped_ptr;

	for (krow = 0; krow<nrows; krow++) {

		for (kcol = 0; kcol<ncols; kcol++)  *out_ptr++ = (unsigned char)*in_ptr++;

		in_ptr -= 2 * ncols;
	}


	//-------- create bitmap file header

	((unsigned char *)&bmfh.bfType)[0] = 'B';
	((unsigned char *)&bmfh.bfType)[1] = 'M';

	bmfh.bfSize = 54 + 1024 + nrows * ncols;
	bmfh.bfReserved1 = 0;
	bmfh.bfReserved2 = 0;
	bmfh.bfOffBits = 54 + 1024;

	//-------- create bitmap information header

	bmih.biSize = 40;
	bmih.biWidth = ncols;
	bmih.biHeight = nrows;
	bmih.biPlanes = 1;
	bmih.biBitCount = 8;
	bmih.biCompression = 0;
	bmih.biSizeImage = nrows * ncols;
	bmih.biXPelsPerMeter = 0;
	bmih.biYPelsPerMeter = 0;
	bmih.biClrUsed = 256;
	bmih.biClrImportant = 0;

	//-------- save all header and image data to a bit mapped file

	bmpfile = fopen(filename, "wb");

	fwrite(&bmfh, sizeof(BITMAPFILEHEADER), 1, bmpfile);
	fwrite(&bmih, sizeof(BITMAPINFOHEADER), 1, bmpfile);
	for (krow = 0; krow<256; krow++) {
		kquad[0] = (unsigned char)krow;  //...gray scale color palette
		kquad[1] = (unsigned char)krow;
		kquad[2] = (unsigned char)krow;
		kquad[3] = (unsigned char)0;
		fwrite(&kquad[0], sizeof(unsigned char), 4, bmpfile);
	}

	fwrite(flipped_ptr, sizeof(unsigned char), nrows * ncols, bmpfile);

	fclose(bmpfile);

	//-------- free memory

	free(flipped_ptr);

}
*/
