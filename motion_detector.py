#/bin/bash/python
# import the necessary packages
import argparse
import datetime
import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')
sys.path.append('/home/pi/.virtualenvs/cv/lib/python2.7/site-packages')
import imutils
import time
import cv2

# construct the argument parser and pass the arguments

ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", help="path to the video file")
ap.add_argument("-a", "--min-area", type=int, default=500, help="minimum area size")
args = vars(ap.parse_args())

# if video argument is none, then we are reading from the webcam
if args.get("video", None) is None:
	camera = cv2.VideoCapture(0)
	time.sleep(0.25)
	print("Hi, welcome to Security System")
# otherwise we can read from the video file
else:
	camera = cv2.VideoCapture(args["video"])

# initialize the first frame in the video stream
firstFrame = None


# loop over the first frame of the video
while True:
	# grab the current frame and initialize the occupied/unoccupied text
	(grabbed, frame) = camera.read()
	frame = cv2.flip(frame, 0)
	text = "Unoccupied"
	
	# if frame not grabbed, then we have reached end of video
	if not grabbed:
		break

	# resize the frame, convert it to grayscale and blur it
	frame = imutils.resize(frame, width=430)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (21,21), 0)

	# if first frame is None, then initialize it
	if firstFrame is None:
		firstFrame = gray
		continue
	# compute the absolute difference between the current frame and first frame
	frameDelta = cv2.absdiff(firstFrame, gray)
	thresh = cv2.threshold(frameDelta, 15, 255, cv2.THRESH_BINARY_INV)[1]
	
	# dilate the threshold image to fill in holes, then find contours on threshold image
	thresh = cv2.dilate(thresh, None, iterations=2)
	(cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	
	# loop over the contours
	for c in cnts:	
		# if contour is too small, ignore it
		if cv2.contourArea(c) < args["min_area"]:
			continue

		# compute bounding box for contour, draw it on frame, update text
		(x, y, w, h) = cv2.boundingRect(c)
		cv2.rectangle(frame, (x,y), (x + w, y + h), (0, 255, 0), 2)
		text = "Occupied"
		
		# draw text and time stamp on the frame
		cv2.putText(frame, "Room status: {}".format(text), (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
		cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
		
		# show the frame and record if the user presses a key
		cv2.namedWindow("Security Feed", cv2.WINDOW_AUTOSIZE)
		cv2.imshow("Security Feed", frame)
	        cv2.waitKey(1)
		cv2.namedWindow("Thresh", cv2.WINDOW_AUTOSIZE)
		cv2.imshow("Thresh", thresh)
		cv2.waitKey(1)
		cv2.namedWindow("Frame Delta", cv2.WINDOW_AUTOSIZE)
		cv2.imshow("Frame Delta", frameDelta)
		cv2.waitKey(1)
		key = cv2.waitKey(1) & 0xFF

		# if q is pressed, break from the loop
		if key == ord("q"):
			break
		
# clean up camera and close any open windows
camera.release()
cv2.destroyAllWindows()


