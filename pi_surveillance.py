#import necessary packages
#from pi-gan-security.tempimage import TempImage
#from dropbox.client import Dropbox0Auth2FlowNoRedirect
from dropbox.client import DropboxClient
from picamera.array import PiRGBArray
from picamera import PiCamera
#import sys
#sys.path.append('/usr/local/lib/python2.7/site-packages/')
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2

#construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="Path to JSON config file")
args = vars(ap.parse_args())

#filter warnings, load conf file and dropbox client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None

if conf["use_dropbox"]:
	#if true, connect to dropbox and start session authorization process
	flow = Dropbox0Auth2FlowNoRedirect(conf["dropbox_key"], conf["dropbox_secret"])
	print"[INFO] Authorize this application: {}".format(flow.start())
	authCode = raw_input("Enter authorization code here: ").strip()

	#finsh authorization and grab the dropbox client
	(accessToken, userID) = flow.finish(authCode)
	client = DropboxClient(accessToken)
	print "[SUCCESS] dropbox account linked"

#initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.rotation = 180
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

#allow camera to warm up, initialize average frame, last uploaded timestamp, and frame motion counter
print "[INFO] camera warming up...."
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

#capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
	#grab the raw NumPy array representing the image and initialize timestamp and occupied/unoccupied text
	frame = f.array
	timestamp = datetime.datetime.now()
	text = "Unoccupied"
	
	#resize the frame, convert to grayscale and blur it
	frame = imutils.resize(frame, width=500)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (21,21), 0)
	
	#if avg frame is None, then initialize it
	if avg is None:	
		print "[INFO] starting background model...."
		avg = gray.copy().astype("float")
		rawCapture.truncate(0)
		continue
		
	#accumulate the weighted average between current and previous frames, then compute the difference between
	#current frame and running average
	cv2.accumulateWeighted(gray, avg, 0.5)
	frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
	
	#threshold the delta image, dilate the threshold image to fill holes, then find contours on threshold
	thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
	thresh = cv2.dilate(thresh, None, iterations = 2)
	(cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	
	#loop over the contours
	for c in cnts:
		#if contour is too small, ignore it
		if cv2.contourArea(c) < conf["min_area"]:
			continue
		
		#compute the bounding box for the contour, draw it on frame, and update text
		(x, y, w, h) = cv2.boundingRect(c)
		cv2.rectangle(frame, (x,y), (x + w, y + h), (0, 255, 0), 2)
		text = "Occupied"

	#draw the timestamp and text on the frame
	ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
	cv2.putText(frame, "Room Status: {}".format(text), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
	cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)


	#check to see if room is occupied
	if text == "Occupied":
			
		#check to see if enough time has passed between uploads
		if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
			motionCounter += 1

			#check to see if frames with consistent motion is high enough
			if motionCounter >= conf["min_motion_frames"]:
					
				#check to see if dropbox should be used
				if conf["use_dropbox"]:
						
					#write the image to temporary file
					t = TempImage()
					cv2.imwrite(t.path, frame)

					#upload image to Dropbox and cleanup temporary image
					print "[UPLOAD] {}".format(ts)
					path = "{base_path}/{timestamp}.jpg".format(base_path=conf["dropbox_base_path"], timestamp=ts)
					client.put_file(path, open(t.path, "rb"))
					t.cleanup()
					
				#update last uploaded timestamp and reset motion counter
				lastUploaded = timestamp
				motionCounter = 0

	#otherwise room is not occupied
	else:
		motionCounter = 0
			
	#check to see if frames should be displayed on the screen
	if conf["show_video"]:
				
		#display the security feed
		cv2.namedWindow("Security Feed", cv2.WINDOW_AUTOSIZE)
		cv2.imshow("Security Feed", frame)	
		key = cv2.waitKey(1) & 0xFF

		#if q is pressed, break from the loop
		if key == ord("q"):
			break
	
	#clear the stream in preparation for the next frame
	rawCapture.truncate(0)


						
	


	

