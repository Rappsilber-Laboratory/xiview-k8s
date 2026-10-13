import logging
import os
import shutil
import sys
import tempfile
from typing import List, Optional

# Ensure /home/appuser (containing parser, models, config) is on Python path
sys.path.insert(0, '/home/appuser')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from exporter import export_static_xiview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xiview-exporter")

app = FastAPI(
    title="xiVIEW Static Exporter Service",
    description="Standalone microservice for generating offline static xiVIEW packages",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "xiview-exporter"}


@app.get("/pride/ws/archive/crosslinking/v3/export_static_project")
def export_static_project(project_id: str):
    """
    Generates and returns a standalone static xiVIEW ZIP package for a stored project,
    automatically bundling its saved layout (groupings/coordinates) and 3D structures if available.
    """
    temp_dir = os.path.expanduser('~/mzId_upload_temp')
    local_dir = os.path.join(temp_dir, project_id)

    # 1. Locate mzIdentML file
    mzid_file = None
    if os.path.isdir(local_dir):
        for f in os.listdir(local_dir):
            if f.lower().endswith(('.mzid', '.mzid.gz')):
                mzid_file = os.path.join(local_dir, f)
                break

    # Fallback to search in mounted workspace directory
    if not mzid_file:
        candidates = [
            "/home/default/workspaces/misc/xiview-k8s",
            "/home/appuser/workspace",
            "/workspace"
        ]
        for cdir in candidates:
            if os.path.isdir(cdir):
                for f in os.listdir(cdir):
                    if f.lower().endswith(('.mzid', '.mzid.gz')):
                        mzid_file = os.path.join(cdir, f)
                        break
            if mzid_file:
                break

    if not mzid_file:
        raise HTTPException(status_code=404, detail=f"No mzIdentML file found for project {project_id}")

    # 2. Locate saved layout
    layout_file = None
    if os.path.isdir(local_dir):
        candidate_layout = os.path.join(local_dir, "layout.json")
        if os.path.isfile(candidate_layout):
            layout_file = candidate_layout

    # 3. Locate optional structure files
    structure_paths = []
    if os.path.isdir(local_dir):
        for f in os.listdir(local_dir):
            if f.lower().endswith(('.cif', '.pdb')):
                structure_paths.append(os.path.join(local_dir, f))

    # Also check workspace for structure files
    for cdir in ["/home/default/workspaces/misc/xiview-k8s", "/home/appuser/workspace"]:
        if os.path.isdir(cdir):
            for f in os.listdir(cdir):
                if f.lower().endswith(('.cif', '.pdb')):
                    candidate = os.path.join(cdir, f)
                    if candidate not in structure_paths:
                        structure_paths.append(candidate)

    # 4. Export static bundle
    export_temp = tempfile.mkdtemp(prefix="xiview_proj_export_")
    base_name = os.path.splitext(os.path.basename(mzid_file))[0]
    if base_name.endswith('.mzid'):
        base_name = os.path.splitext(base_name)[0]
    zip_path = os.path.join(export_temp, f"{base_name}_static_xiview.zip")

    try:
        logger.info(f"Generating static bundle for {project_id} (layout={layout_file}, structures={len(structure_paths)})")
        export_static_xiview(
            mzid_path=mzid_file,
            output_zip=zip_path,
            project_title=f"xiVIEW - {base_name}",
            structure_paths=structure_paths if structure_paths else None,
            layout_path=layout_file
        )
        return FileResponse(
            zip_path,
            filename=f"{base_name}_static_xiview.zip",
            media_type="application/zip"
        )
    except Exception as e:
        import traceback
        logger.error(f"Static project export error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pride/ws/archive/crosslinking/v3/export_static")
async def export_static(
    mzid_file: UploadFile = File(...),
    structure_files: Optional[List[UploadFile]] = File(None),
    project_title: Optional[str] = Form(None),
    layout_file: Optional[UploadFile] = File(None)
):
    """
    Uploads an mzIdentML file and optional structures/layout, and streams back a standalone static ZIP.
    """
    temp_dir = tempfile.mkdtemp(prefix="xiview_export_")
    try:
        mzid_path = os.path.join(temp_dir, mzid_file.filename)
        with open(mzid_path, "wb") as f:
            shutil.copyfileobj(mzid_file.file, f)

        struct_paths = []
        if structure_files:
            for sfile in structure_files:
                if sfile.filename:
                    spath = os.path.join(temp_dir, sfile.filename)
                    with open(spath, "wb") as f:
                        shutil.copyfileobj(sfile.file, f)
                    struct_paths.append(spath)

        layout_path = None
        if layout_file and layout_file.filename:
            layout_path = os.path.join(temp_dir, layout_file.filename)
            with open(layout_path, "wb") as f:
                shutil.copyfileobj(layout_file.file, f)

        base_name = os.path.splitext(mzid_file.filename)[0]
        zip_path = os.path.join(temp_dir, f"{base_name}_static_xiview.zip")

        export_static_xiview(
            mzid_path=mzid_path,
            output_zip=zip_path,
            project_title=project_title or f"xiVIEW - {base_name}",
            structure_paths=struct_paths if struct_paths else None,
            layout_path=layout_path
        )

        return FileResponse(
            zip_path,
            filename=f"{base_name}_static_xiview.zip",
            media_type="application/zip"
        )
    except Exception as e:
        import traceback
        logger.error(f"Static export error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8092)
