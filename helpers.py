import cv2
import numpy as np
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont
import ffmpeg
from typing import Tuple
import os
import textwrap
from moviepy.editor import concatenate_videoclips, concatenate_audioclips, VideoFileClip, AudioFileClip
from moviepy.audio.AudioClip import AudioArrayClip
import moviepy.editor as mpy


# from PIL import Image, ImageFont, ImageDraw, ImageColor

from PIL import Image, ImageDraw, ImageFont

def gen_image(workspace_path, main_text, sub_text=''):
    # Define the image size
    img_size = (2560, 1440)

    # Create a new image with black background
    image = Image.new('RGB', img_size, 'black')

    # Initialize ImageDraw
    draw = ImageDraw.Draw(image)

    # Load a font (this should be a path to a .ttf or .otf file on your system)
    font_main = ImageFont.truetype("./Montserrat-Black.ttf", size=70)
    font_sub = ImageFont.truetype("./Montserrat-Black.ttf", size=50)  # Smaller size for subtext

    # Calculate position and draw main text
    text_width, text_height = draw.textsize(main_text, font=font_main)
    x = (img_size[0] - text_width) / 2
    y = (img_size[1] - text_height) / 2
    draw.text((x, y), main_text, font=font_main, fill='white')

    # Calculate position and draw subtext with word wrapping
    padding = 50  # Distance from the main text
    subtext_width = img_size[0] - 2*padding  # Subtext width is the image width minus padding on both sides
    lines = textwrap.wrap(sub_text, width=subtext_width)
    y_text = y + text_height + padding
    for line in lines:
        line_width, line_height = draw.textsize(line, font=font_sub)
        x_line = (img_size[0] - line_width) / 2
        draw.text((x_line, y_text), line, font=font_sub, fill='white')
        y_text += line_height

    img_path = workspace_path + "/image.png"
    image.save(img_path)

    return img_path

def combine(workspace_path, video_path, running_concat_file_path):

# ,setsar=1
    command1 = ['ffmpeg', '-y', '-i', video_path, '-vf', 'scale=2560:1440,setsar=1', '-r', '30', '-c:a', 'copy', workspace_path + '/step.mp4']
    subprocess.run(command1, check=True)

    if running_concat_file_path:
        command = [
            'ffmpeg', 
            '-i', running_concat_file_path,
            '-i', workspace_path + "/step.mp4",
            '-filter_complex', '[0:v:0] [0:a:0] [1:v:0] [1:a:0] concat=n=2:v=1:a=1 [v] [a]',
            '-map', '[v]',
            '-map', '[a]',
            '-vsync', 'vfr', # variable frame rate mode
            workspace_path + '/output2.mp4'
        ]

        subprocess.run(command, check=True)

        shutil.move(workspace_path + '/output2.mp4', workspace_path + '/output.mp4')
    else:
        shutil.move(workspace_path + '/step.mp4', workspace_path + '/output.mp4')

    return workspace_path + '/output.mp4'

def do_the_thing(workspace_path, video_path, text, sub_text, running_concat_file_path, i):
    
    command1 = ['ffmpeg', '-y', '-i', video_path, '-vf', 'scale=2560:1440', '-c:a', 'copy', workspace_path + '/encoded.mp4']
    subprocess.run(command1, check=True)

    if text:

        # Command 2
        command2 = ['ffmpeg', '-y', '-i', workspace_path + '/encoded.mp4', '-t', '5', '-c', 'copy', workspace_path + '/first5.mp4']
        subprocess.run(command2, check=True)

        # subprocess.call([
        #     "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "5", "./silence.mp3"
        # ])

        img_path = gen_image(workspace_path, text, sub_text)

        # Second command
        subprocess.run([
            "ffmpeg", "-y", "-i", workspace_path + "/first5.mp4", "-i", img_path, "-f", "lavfi", "-t", "5", "-i", "anullsrc=r=44100:cl=stereo",
            "-filter_complex", "[0:v][1:v] overlay=0:0,format=yuv420p[v];[2:a]anull[a]", "-map", "[v]", "-map", "[a]", workspace_path + "/first5_overlay.mp4"
        ], check=True)

        # Third command
        subprocess.run([
            "ffmpeg", "-y", "-i", workspace_path + "/first5_overlay.mp4", "-i", workspace_path + '/encoded.mp4',
            "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-c:a", "aac", 
            workspace_path + "/step.mp4"
        ], check=True)

    else:
        shutil.move(workspace_path + '/encoded.mp4', workspace_path + '/step.mp4')

    shutil.copy(workspace_path + '/step.mp4', workspace_path + f'/step-{i}.mp4')

    if running_concat_file_path:
        command = [
            'ffmpeg', 
            '-i', running_concat_file_path,
            '-i', workspace_path + "/step.mp4",
            '-filter_complex', '[0:v:0] [0:a:0] [1:v:0] [1:a:0] concat=n=2:v=1:a=1 [v] [a]',
            '-map', '[v]',
            '-map', '[a]',
            workspace_path + '/output2.mp4'
        ]

        subprocess.run(command, check=True)

        shutil.move(workspace_path + '/output2.mp4', workspace_path + '/output.mp4')
    else:
        shutil.move(workspace_path + '/step.mp4', workspace_path + '/output.mp4')

    return workspace_path + '/output.mp4'

def generate_and_combine_slide_clip(workspace_path, video_path, text, sub_text, output_path):

    img_path = gen_image(workspace_path, text, sub_text)

    # Load video and audio
    video = mpy.VideoFileClip(video_path)
    audio = video.audio 

    # Transcode 
    video = video.resize(width=2560, height=1440)

    # Take first 5 seconds
    clip = video.subclip(0, 5)

    # Add image overlay
    overlay = mpy.ImageClip(img_path).set_position(('center','center')).set_duration(5)
    clip = mpy.CompositeVideoClip([clip, overlay]) 

    # Concatenate full video with overlay clip
    final = mpy.concatenate_videoclips([clip, video])

    # Set final clip audio to original audio  
    final = final.set_audio(audio)

    # Write final result
    final.write_videofile(output_path, fps=video.fps)

def create_slide_clip(workspace_path, text, sub_text, output_name):
    img_path = gen_image(workspace_path, text, sub_text)

    # Set the duration of the video
    duration = 2  # seconds

    img = cv2.imread(img_path)

    height, width, layers = img.shape

    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 

    # Create VideoWriter with fps = 1/duration to have each image during "duration" seconds
    video = cv2.VideoWriter(workspace_path + '/video.mp4', fourcc, 1/duration, (width,height))

    # Write the image to the video file
    video.write(img)

    # Close the video file
    video.release()

    # Use FFmpeg to loop the video for the desired duration
    command = [
        'ffmpeg',
        '-i', workspace_path + '/video.mp4', 
        '-stream_loop', str(duration), 
        '-i', './silence.mp3', 
        '-c:v', 'copy', 
        '-c:a', 'aac', 
        '-shortest', 
        workspace_path + '/' + output_name + '.mp4'
    ]
    subprocess.run(command, check=True)

    os.remove(workspace_path + '/video.mp4')
    # os.remove(img_path)



def concat_clips(workspace_dir):
    # get all files in the directory
    files = [workspace_dir + '/' + f for f in os.listdir(workspace_dir) if os.path.isfile(workspace_dir + '/' + f)]

    # filter out the .mp4 files and sort them
    mp4_files = sorted([f for f in files if f.endswith('.mp4')])

    for file in mp4_files:
        print(file)

    # Transcode each file to ensure that they all have the same codec and parameters
    # transcoded_files = []
    # for i, file in enumerate(mp4_files):
    #     # output_file = f"{workspace_dir}/{file}"
    #     # transcoded_files.append(file)
    #     output_file = f"{workspace_dir}/transcoded_{i}.mp4"
    #     transcoded_files.append(output_file)
    #     (
    #         ffmpeg
    #         .input(file)
    #         .output(
    #             output_file,
    #             vcodec='libx264',
    #             acodec='aac', # audio codec is AAC
    #             map='0',  # map all streams (not only default) from input to output
    #             vf='scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',  # resize each video to 1920x1080
    #             crf=23,  # set the Constant Rate Factor to 23
    #             preset='slow',  # use a slow preset for better quality
    #             format='mp4',
    #             ab='192k',  # set audio bitrate
    #             strict='experimental' # needed for some versions of ffmpeg to support AAC
    #         )
    #         .run()
    #     )
    # clips = []

    # for file in transcoded_files:
    #     # p = f"{workspace_dir}/{file}"
    #     clip = VideoFileClip(file)
    #     # if clip.audio is None:
    #     #     clip = clip.set_audio(AudioFileClip("silence.mp3"))
    #     clips.append(clip)

    # audio_clips = []

    # for clip in clips:
    #     if clip.audio is None:  # if clip doesn't have audio, we create a silent one
    #         fps = 44100  # assuming the sample rate of your silent audio is 44100
    #         silent_audio = AudioArrayClip(np.zeros((int(clip.duration*fps), 2)), fps=fps)  # creating silent audio with clip's duration
    #         audio_clips.append(silent_audio)
    #     else:
    #         audio_clips.append(clip.audio)

    # Concatenate video clips and audio clips separately
    # final_audio = concatenate_audioclips(audio_clips)
    # final_video = concatenate_videoclips(clips)

    # Set final audio to final video
    # final_clip = final_video.set_audio(final_audio)

    # final_clip = concatenate_videoclips(clips)

    # final_clip.write_videofile(workspace_dir + '/output.mp4')

    # return workspace_dir + '/output.mp4'



    # # Create a text file listing the files to concatenate
    # with open(workspace_dir + '/files.txt', 'w') as f:
    #     for file in transcoded_files:
    #         # Write only the file name, not the full path
    #         f.write(f"file '{os.path.basename(file)}'\n")

    # # Use the "concat demuxer" method to concatenate the files
    # subprocess.run([
    #     'ffmpeg',
    #     '-f', 'concat',
    #     '-safe', '0',
    #     '-i', workspace_dir + '/files.txt',
    #     '-c:v', 'copy',  # copy the video codec directly
    #     '-c:a', 'aac',  # encode audio in AAC
    #     '-b:a', '192k',
    #     workspace_dir + '/output.mp4',
    # ])

    # ffmpeg -f concat -safe 0 -i files.txt -c:v libx264 -preset slow -crf 23 -s 1920x1080 -c:a aac -b:a 192k output.mp4

    # Clean up the temporary transcoded files
    # for file in transcoded_files:
    #     os.remove(file)

    # return workspace_dir + '/output.mp4'