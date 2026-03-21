# xiVIEW Full-Stack Deployment

This repository contains the deployment configurations and orchestration submodules required to host your own full-stack instance of **xiVIEW**—a platform for the downstream analysis of cross-linking mass spectrometry data.

## Architecture

This stack runs entirely natively inside Kubernetes, orchestrated via standard `.yaml` manifests utilizing Docker containers. It sets up 6 distinct microservices to cleanly map and digest crosslinking data securely:

1. **`xiview-frontend`**: The modern React-based UI allowing users to aggregate `mzIdentML` (.mzid) formats alongside mass spectra files (.mzML).
2. **`xiview-server`**: The legacy JavaScript rendering visualization engine bridging complex node networks and 3D Structure mapping.
3. **`xiview-upload-api`**: Manages file caching and routes `.mzIdentML` schemas into DB structures utilizing Pyteomics readers.
4. **`crosslinking-api`**: Exposes read access mapping `spectrum`, `peptides`, and `crosslinks` from PostgreSQL natively to the visualization engine without polling EBI.
5. **`mzidentml-reader`**: Python processor tasked with ripping heavy `.mzIdentML` trees gracefully into normalized DB rows.
6. **`postgresql-service`**: Highly available data-layer housing your crosslinking datasets cleanly.

## Prerequisites

- A running Kubernetes cluster (e.g. k3s, minikube, or EKS).
- `kubectl` configured with cluster access.
- Local Docker environment to build standard configurations (`docker buildx`).

## Quickstart Deployment via Helm

We utilize a Helm Chart to rapidly deploy and parameterize all components dynamically without needing to alter source `.yaml` files.

**1. Clone the repository and initialize submodules:**
```bash
git clone https://github.com/Rappsilber-Laboratory/xiview-stack.git
cd xiview-stack
git submodule update --init --recursive
```

**2. Configure your Deployment Values:**
Open `helm-chart/values.yaml` and adjust the variables specifying your Docker Hub repository names, preferred tags, and custom Ingress host URLs.

**3. Install the Deployment Stack:**
Assuming your Kubernetes cluster (`kubectl`) is currently active, install the generic release name natively:
```bash
helm install my-xiview ./helm-chart
```
*Note: This command provisions the complete Postgres layer, installs the crosslinking indexing services, and binds the generic frontend to your chosen Traefik Ingress routes automatically.*

**Upgrading or Rolling Actions:**
If you change `values.yaml` or rebuild container components, seamlessly push the upgrade logic via Helm:
```bash
helm upgrade my-xiview ./helm-chart
```

**Why is the Ingress setup so complex?**
The xiVIEW architecture uses submodules that were originally built to interface directly with EBI PRIDE's public `.org` HTTP endpoint structures. Instead of modifying each submodule's source code to utilize new internal DNS paths, our cluster safely emulates the exact EBI namespace dynamically. 
The Ingress rules ensure that broad requests pointing to `/pride` correctly hit the database querying service (`crosslinking-api`), while highly-specific exact matches like `/pride/ws/.../upload_local` safely bypass the database and perfectly filter into your file processing service (`xiview-upload-api`). The remaining visualization static assets scale backwards seamlessly from the legacy `.html` engines.

## Creating Custom Docker Containers
The deployment YAML files currently pull from `rappsilberlab` docker-hub repositories. If you would like to edit the Python/React codebase uniquely or compile fresh artifacts locally natively:
```bash
docker build -t rappsilberlab/xiview-frontend:2026-03-20 -f Dockerfile.xiview-frontend .
```
*(Repeat for `Dockerfile.crosslinking-api`, `Dockerfile.xiview-server`, `Dockerfile.xiview-upload-api`, and `Dockerfile.mzidentml-reader`).*

## Security
The `/pride` backend namespace utilizes simulated endpoints to fulfill exact EBI API requirements dynamically. All crosslinking uploads will live privately inside your isolated local Postgres volume storage unshared.
