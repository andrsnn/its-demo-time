from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import shutil
import os
import subprocess
import hashlib
import aiofiles
import json
import time
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from helpers import create_slide_clip, concat_clips, generate_and_combine_slide_clip, do_the_thing, combine

app = FastAPI()

UPLOAD_DIRECTORY = "./upload"
TEMPLATES_DIRECTORY = "./templates"

if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

if not os.path.exists(TEMPLATES_DIRECTORY):
    os.makedirs(TEMPLATES_DIRECTORY)

app.mount("/templates", StaticFiles(directory="templates"), name="templates")

def calculate_sha256(file_contents):
    readable_hash = hashlib.sha256(file_contents).hexdigest()
    return readable_hash

class FileData(BaseModel):
    start: float
    end: float
    title: str | None
    description: str | None

@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_contents = await file.read()
        file_hash = calculate_sha256(file_contents)
        file_location = f"{UPLOAD_DIRECTORY}/{file_hash}"
        
        if not os.path.exists(file_location):
            with open(file_location, "wb+") as file_object:
                file_object.write(file_contents)
        
        return {"status_code": 200, "sha256": file_hash}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")

def create_directory(path):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass

@app.get("/download/{file_path:path}")
async def download_file(file_path: str):
    if not file_path.startswith("workspaces"):
        raise HTTPException(status_code=403, detail="Unauthorized file access")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type='application/octet-stream', filename=os.path.basename(file_path))

class RedactData(BaseModel):
    startX: int | float
    startY: int | float
    w: int | float
    h: int | float

@app.post("/redact/{file_hash}",)
async def redact_file(file_hash: str, redact_data: RedactData):
    try:
        file_location = f"{UPLOAD_DIRECTORY}/{file_hash}"

        print('here')
        
        if os.path.exists(file_location) and file_hash == calculate_sha256(open(file_location, 'rb').read()):

            workspace_dir = './workspaces/' + file_hash + '-' + str(int(time.time()))
            create_directory(workspace_dir)

            x = redact_data.startX
            y = redact_data.startY
            w = redact_data.w
            h = redact_data.h

            output_file = workspace_dir + '/output.mp4'

            # command = [
            #     "ffmpeg", "-i", input_file, "-vf", 
            #     f"drawbox=enable='between(t,1*60,2*60)':x={x}:y={y}:w={w}:h={h}:color=black@1.0:t=fill", 
            #     output_file
            # ]


            # Ensure you have ffmpeg installed in your system
            command = ["ffmpeg", "-i", file_location, "-vf", f"drawbox=x={x}:y={y}:w={w}:h={h}:color=black@1.0:t=fill", output_file]


            print(command)

            # Using the subprocess.run() method to call FFmpeg as a new process and then continue with your own processing.
            # shell=True, capture_output=True, text=True
            result = subprocess.run(command, check=True)
        else:
            raise HTTPException(status_code=400, detail="File not found")

        return {"status_code": 200, "message": ""}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")
    
@app.post("/combine_files")
async def combine_files(file_shas: List[str]):
    try:
        for file_sha in file_shas:
            file_location = f"{UPLOAD_DIRECTORY}/{file_sha}"

            if os.path.exists(file_location) and file_sha == calculate_sha256(open(file_location, 'rb').read()):
                pass
            else:
                raise HTTPException(status_code=400, detail=f"Error: {file_sha} does not match")

        first_sha = file_shas[0]
        workspace_dir = './workspaces/combine_' + first_sha + '-' + str(int(time.time()))
        create_directory(workspace_dir)

        running_output_path = None

        for file_sha in file_shas:
            file_location = f"{UPLOAD_DIRECTORY}/{file_sha}"
            new_loc = workspace_dir + '/' + file_sha + '.mp4'

            shutil.copy(file_location, new_loc)

            running_output_path = combine(workspace_dir, new_loc, running_output_path)

        return {"status_code": 200, "message": running_output_path}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")
    pass

@app.post("/edit_file/{file_hash}",)
async def edit_file(file_hash: str, trim_data: List[FileData]):
    try:
        file_location = f"{UPLOAD_DIRECTORY}/{file_hash}"
        
        if os.path.exists(file_location) and file_hash == calculate_sha256(open(file_location, 'rb').read()):

            workspace_dir = './workspaces/' + file_hash + '-' + str(int(time.time()))
            create_directory(workspace_dir)
            i = 0
            running_output_path = None

            for trim in trim_data:
                start = trim.start
                end = trim.end
                title = trim.title
                description = trim.description

                # if title:
                #     create_slide_clip(workspace_dir, title, description, str(i))

                #     i += 1

                clip_name = str(i) + '.mp4'

                clip_output_path = workspace_dir + '/' + clip_name

                ffmpeg_extract_subclip(file_location, start, end, targetname=clip_output_path)

                running_output_path = do_the_thing(workspace_dir, clip_output_path, title, description, running_output_path, i)

                # if title:
                #     output = workspace_dir + '/' + str(i) + 'temp.mp4'
                #     # will have no audio because of some bug that eludes me, will resolve this in the concat step...
                #     generate_and_combine_slide_clip(workspace_dir, clip_output_path, title, description, output)

                i += 1

            # output_file_path = concat_clips(workspace_dir)

            # Assuming that the file is a JSON file
            # with open(file_location, 'r+') as file:
            #     data = json.load(file)
            #     data.update(file_data.dict())
            #     file.seek(0)
            #     json.dump(data, file)
                
            return {"status_code": 200, "message": running_output_path}
        
        raise HTTPException(status_code=400, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    async with aiofiles.open(f"{TEMPLATES_DIRECTORY}/index.html", mode='r') as f:
        content = await f.read()
    return HTMLResponse(content=content)
