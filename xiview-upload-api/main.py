import json
import os
import shutil
import uuid
import logging
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# We can import convert_dir natively since this container is built using mzidentml-reader as the base!
from parser.process_dataset import convert_dir

app = FastAPI()
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/pride/ws/archive/crosslinking/v3/upload_local")
def upload_local(files: List[UploadFile] = File(...)):
    project_identifier = "LOC_" + str(uuid.uuid4())[:6].upper()
    temp_dir = os.path.expanduser('~/mzId_upload_temp')
    local_dir = os.path.join(temp_dir, project_identifier)
    os.makedirs(local_dir, exist_ok=True)
    
    has_peaklist = False
    for file in files:
        filepath = os.path.join(local_dir, file.filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if file.filename.lower().endswith(('.mzml', '.mgf', '.ms2', '.zip')):
            has_peaklist = True
            
    from fastapi import HTTPException
    logger.info(f"Triggering database conversion on native local submission {project_identifier}...")
    try:
        convert_dir(local_dir, project_identifier, writer_method="db", nopeaklist=not has_peaklist)
    except SystemExit as sys_exit:
        logger.error(f"Parser exited with SystemExit code {sys_exit.code}")
        raise HTTPException(status_code=400, detail="Schema validation for the uploaded mzIdentML file failed.")
    except Exception as e:
        import traceback
        logger.error(f"Conversion error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
        
    logger.info("Local upload successfully indexed!")
    
    return {"message": "Success", "project_id": project_identifier}


@app.post("/pride/ws/archive/crosslinking/v3/layout/{project_id}")
async def save_layout(project_id: str, request: Request):
    """
    Saves a layout (protein coordinates and groupings) for a given project.
    """
    temp_dir = os.path.expanduser('~/mzId_upload_temp')
    local_dir = os.path.join(temp_dir, project_id)
    os.makedirs(local_dir, exist_ok=True)
    layout_file = os.path.join(local_dir, "layout.json")

    try:
        body = await request.json()
        with open(layout_file, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=2)
        logger.info("Saved layout for project %s", project_id)
        return {"message": "Layout saved successfully", "project_id": project_id}
    except Exception as e:
        logger.error("Error saving layout: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pride/ws/archive/crosslinking/v3/layout/{project_id}")
def get_layout(project_id: str):
    """
    Retrieves the saved layout for a project.
    """
    temp_dir = os.path.expanduser('~/mzId_upload_temp')
    layout_file = os.path.join(temp_dir, project_id, "layout.json")
    if os.path.isfile(layout_file):
        with open(layout_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)

