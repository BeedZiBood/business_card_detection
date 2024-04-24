from imutils.perspective import four_point_transform
from ultralytics import YOLO
import pytesseract
import numpy as np
import argparse
import imutils
import cv2
import re


ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True,
	help="path to input receipt image")
ap.add_argument("-d", "--debug", type=int, default=-1,
	help="whether or not we are visualizing each step of the pipeline")
args = vars(ap.parse_args())

# load the input image from disk, resize it, and compute the ratio
# of the *new* width to the *old* width
orig = cv2.imread(args["image"])
image = orig.copy()
image = imutils.resize(image, height=800)
model = YOLO('nanobest.pt')
names = model.model.names
results = model.predict(image, conf=0.6) # predict contours
contours = results[0].masks.xy
ratio = orig.shape[1] / float(image.shape[1])

# initialize a contour that corresponds to the receipt outlines
receiptCnt = None
# loop over the contours
for c in contours:
	# approximate the contour
	peri = cv2.arcLength(c, True)
	approx = cv2.approxPolyDP(c, 0.02 * peri, True)
	# if our approximated contour has four points, then we can
	# assume we have found the outline of the receipt
	if len(approx) == 4:
		receiptCnt = approx
		break

# if the receipt contour is empty then our script could not find the
# outline and we should be notified
if receiptCnt is None:
	raise Exception(("Could not find receipt outline. "
					 "Try debugging your edge detection and contour steps."))

# convert list to numpy array and reshape it for cv
receiptCnt = np.array(receiptCnt).reshape((-1,1,2)).astype(np.int32)
# check to see if we should draw the contour of the receipt on the
# image and then display it to our screen
if args["debug"] > 0:
	output = image.copy()
	cv2.drawContours(output, [receiptCnt], -1, (0, 255, 0), 2)
	cv2.imshow("Receipt Outline", output)
	cv2.waitKey(0)
# apply a four-point perspective transform to the *original* image to
# obtain a top-down bird's-eye view of the receipt
receipt = four_point_transform(orig, receiptCnt.reshape(4, 2) * ratio)
# show transformed image
cv2.imshow("Receipt Transform", imutils.resize(receipt, width=500))
cv2.waitKey(0)

# apply OCR to the receipt image by assuming column data, ensuring
# the text is *concatenated across the row* (additionally, for your
# own images you may need to apply additional processing to cleanup
# the image, including resizing, thresholding, etc.)
options = "--psm 4"
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\beedz\AppData\Local\Tesseract-OCR\tesseract.exe'
text = pytesseract.image_to_string(
	cv2.cvtColor(receipt, cv2.COLOR_BGR2RGB),
	config=options, lang='rus')
# show the raw output of the OCR process
print("[INFO] raw output:")
print("==================")
print(text)
print("\n")

# define a regular expression that will match line items that include
# a price component
pricePattern = r'([0-9]+\.[0-9]+)'
# show the output of filtering out *only* the line items in the
# receipt
print("[INFO] price line items:")
print("========================")
# loop over each of the line items in the OCR'd receipt
for row in text.split("\n"):
	# check to see if the price regular expression matches the current
	# row
	if re.search(pricePattern, row) is not None:
		print(row)