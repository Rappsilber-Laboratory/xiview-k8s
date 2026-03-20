import os
import shutil
import uuid
import logging
from typing import List

from fastapi import FastAPI, UploadFile, File
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
