import cv2
import pytesseract
from pytesseract import Output

def draw_bounding_boxes(input_img_path, output_path):
   #img = cv2.imread(input_img_path)
   img = input_img_path

   # Extract data
   data = pytesseract.image_to_data(img, output_type=Output.DICT)
   n_boxes = len(data["text"])

   for i in range(n_boxes):
       if data["conf"][i] == -1:
           continue
       # Coordinates
       x, y = data["left"][i], data["top"][i]
       w, h = data["width"][i], data["height"][i]

       # Corners
       top_left = (x, y)
       bottom_right = (x + w, y + h)

       # Box params
       green = (0, 255, 0)
       thickness = 1  # The function-version uses thinner lines

       cv2.rectangle(img, top_left, bottom_right, green, thickness)

   # Save the image with boxes
   cv2.imwrite(output_path, img)

def greyscale(img):
   return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def binarize(img):
    thresh = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
    return thresh