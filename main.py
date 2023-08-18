import cv2
from PIL import Image, ImageDraw, ImageFont
import os

# Load image using PIL
im = Image.open("image.jpg")

# Resize the image
im = im.resize((1920, 1080))

d = ImageDraw.Draw(im)

# Set the font and size
fnt = ImageFont.truetype('/Library/Fonts/Arial.ttf', 50)

# Calculate the width and height of the text to center it
w, h = d.textsize("Title", font=fnt)
W, H = im.size
x = (W - w) / 2
y = (H - h) / 2

# Draw the text on the image
d.text((x, y), "Title", fill="black", font=fnt)

# Save the image with text
im.save("image_with_text.jpg")

# Set the duration of the video
duration = 20  # seconds

# Open the image with OpenCV
img = cv2.imread('image_with_text.jpg')

# Get image dimensions (it assumes all images have the same size)
height, width, layers = img.shape

# Choose the codec according to the format needed (mp4 in your case)
fourcc = cv2.VideoWriter_fourcc(*'mp4v') 

# Create VideoWriter with fps = 1/duration to have each image during "duration" seconds
video = cv2.VideoWriter('video.mp4', fourcc, 1/duration, (width,height))

# Write the image to the video file
video.write(img)

# Close the video file
video.release()

# Use FFmpeg to loop the video for the desired duration
os.system(f'ffmpeg -y -stream_loop {duration} -i video.mp4 -c copy output.mp4')
