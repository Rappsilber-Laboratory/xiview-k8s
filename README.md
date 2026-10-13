# xiVIEW Full-Stack Deployment

This repository contains the deployment configurations and orchestration submodules required to host your own full-stack instance of **xiVIEW**—a platform for the downstream analysis of cross-linking mass spectrometry data.

## Prerequisites

- A running Kubernetes cluster (e.g. k3s, minikube, or EKS).
- `kubectl` configured with cluster access.
- [Helm v3+](https://helm.sh/) installed.

## Quickstart Deployment via Helm

### Option A: From Helm Repository (Remote)

**1. Add the xiVIEW Helm Repository:**
```bash
helm repo add xiview-repo https://rappsilber-laboratory.github.io/xiview-k8s
helm repo update
```

**2. Create your Configuration Override (e.g. `k3s-values.yaml`):**
If you are deploying on a local K3s cluster, you can define a minimal values file like this for the local-path StorageClass and the Traefik IngressController:
```yaml
# k3s-values.yaml
auth:
  api_key: "change_me"
  db_password: "change_me"
  redis_password: "change_me"

ingress:
  enabled: true
  host: "xiview.local"
  className: "traefik"

postgres:
  persistence:
    enabled: true
    size: 5Gi
    storageClass: "local-path"

redis:
  persistence:
    enabled: false
```

**3. Install or Upgrade the Stack:**
```bash
helm upgrade --install my-xiview xiview-repo/xiview-stack -f k3s-values.yaml
```

### Option B: From Cloned Repository (Local Chart)

If you have cloned this repository, you can deploy directly using the local chart:
```bash
helm upgrade --install my-xiview ./helm-chart -f k3s-values.yaml
```

> **Local Development Mode:** You can enable live hot-reloading with hostPath mounts by setting `localDev: true` and `localDevPath: "/absolute/path/to/xiview-k8s"` in `k3s-values.yaml`. This mounts code from your local workspace directly into the running pods without rebuilding Docker images.

## Architecture

This stack runs entirely inside Kubernetes. It orchestrates 7 distinct application services and supporting caching infrastructure:

1. **`xiview-frontend`**: Modern React-based UI allowing users to upload `mzIdentML` (.mzid) formats alongside mass spectra files (.mzML).
2. **`xiview-server`**: Core JavaScript visualization rendering engine for node networks, 3D structures, and pride data feeds.
3. **`xiview-upload-api`**: Ingests uploads and persists custom user layouts (protein coordinates, rotations, groupings) across sessions.
4. **`xiview-exporter`**: Dedicated standalone microservice generating self-contained static HTML network packages as ZIP archives with bundled 3D models and saved layouts.
5. **`crosslinking-api`**: Exposes read access mapping `spectrum`, `peptides`, and `crosslinks` from PostgreSQL to the visualization engine without polling EBI.
6. **`mzidentml-reader`**: Python processor tasked with reading `.mzIdentML` trees into normalized DB rows.
7. **`postgresql-service`**: Relational data-layer housing crosslinking datasets and user projects.
8. **Supporting Infrastructure**: `redis` and `cache-proxy` for high-throughput response caching.

## Standalone Static xiVIEW Network Export (ZIP / Serverless)

You can convert any `mzIdentML` (`.mzid` or `.mzid.gz`) file into a self-contained, serverless static HTML package bundled into a ZIP archive. The extracted page can be opened directly from disk in any web browser (`file:///path/to/index.html`) without running any database, server, or container!

### CLI Usage

1. Set up dependencies:
```bash
pip install -r xiview-exporter/requirements.txt
# Or if using Pipenv in this workspace:
pipenv install
```

2. Generate the static ZIP archive (with optional 3D structure and layout bundling):
```bash
python xiview-exporter/exporter.py \
    -i hRpn1_pepSCX_FDR_2-5_proteinpairs_boost_xiFDR2.3.2.mzid \
    -s AF-P35998-F1-model_v6.cif \
    -l upload_temp/LOC_3264AB/layout.json \
    -o xiview_network_hRpn1.zip
```

3. Share or inspect:
- Unzip `xiview_network_hRpn1.zip`
- Double-click `index.html` to open directly in your web browser (`file:///...`)
- All crosslink network visualizers, filters, domain layouts, and peptide tables function offline seamlessly.
- Open **LOAD 3D MODEL** to load bundled structures with 1 click or choose any local CIF/PDB structure file.
- Bundled layouts (protein coordinates and groupings) are automatically applied on load.
- Use **Load Layout ▼** in the button bar to reload the default layout, import layout JSON files, or restore saved configurations.
- Use **Save Layout** to store the layout in browser localStorage and download a portable `.layout.json` file.

### Dataset Overview Download Button

In the Dataset Overview table (`My Data` in `xiview-frontend`):
- Each dataset row includes a **Download** action button (`<Download />` icon).
- Clicking this triggers `GET /pride/ws/archive/crosslinking/v3/export_static_project?project_id=...`, which automatically packages the project's mzIdentML file, saved layout (including custom groupings and positions), and 3D structures into a downloadable `.zip`.

### 3D Viewer & RDP / Remote Desktop Note

When running over Linux RDP / Remote Desktop (e.g. xrdp, Chrome Remote Desktop), hardware GPU WebGL acceleration is typically disabled by the display server. To enable Google's CPU-based SwiftShader WebGL rasterizer in Chrome:

```bash
google-chrome --enable-unsafe-swiftshader --ignore-gpu-blocklist &
```
or navigate to `chrome://flags` and set **Override software rendering list** to **Enabled**.

### API Endpoints

- **Upload & Layout API (`xiview-upload-api` : 8090)**:
  - **POST** `/pride/ws/archive/crosslinking/v3/upload_local`: Ingests mzIdentML data.
  - **POST** `/pride/ws/archive/crosslinking/v3/layout/{project_id}`: Persists layout JSON (protein positions, groupings, colors) for a project.
  - **GET** `/pride/ws/archive/crosslinking/v3/layout/{project_id}`: Retrieves stored layout JSON.

- **Static Exporter Service (`xiview-exporter` : 8092)**:
  - **GET** `/health`: Exporter health check.
  - **GET** `/pride/ws/archive/crosslinking/v3/export_static_project?project_id={id}`: Generates a standalone static ZIP for a stored project, bundling its saved layout (groupings/coordinates) and 3D structures.
  - **POST** `/pride/ws/archive/crosslinking/v3/export_static`: Ad-hoc file upload static ZIP generator.



