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

## Quickstart Deployment

**1. Clone the repository and initialize submodules:**
```bash
git clone https://github.com/Rappsilber-Laboratory/xiview-stack.git
cd xiview-stack
git submodule update --init --recursive
```

**2. Provision the Postgres Database Layer:**
Initialize the backing dataset tables by creating the stateful resources, database components, and the automatic initialization job:
```bash
kubectl apply -f k8s-postgresql.yaml
kubectl apply -f k8s-db-init.yaml
```
*Tip: Wait for `db-init-job` to complete before proceeding (`kubectl get jobs`).*

**3. Apply Core API Components:**
```bash
kubectl apply -f k8s-xiview-upload-api.yaml
kubectl apply -f k8s-mzidentml-reader.yaml
kubectl apply -f k8s-crosslinking-api.yaml
```

**4. Deploy Frontend Renders:**
```bash
kubectl apply -f k8s-xiview-server.yaml
kubectl apply -f k8s-xiview-frontend.yaml
```

**5. Handle Incoming Traffic:**
If you have a Traefik Ingress Controller and Let's Encrypt cluster-issuers already configured on your cluster, you can securely route internet traffic using a standard Ingress manifest. 

A fully working routing template is provided in **[`k8s-ingress-example.yaml`](./k8s-ingress-example.yaml)**. Apply it utilizing your domain overrides:
```bash
kubectl apply -f k8s-ingress-example.yaml
```

**Why is the Ingress setup so complex?**
The xiVIEW architecture uses submodules that were originally built to interface directly with EBI PRIDE's public `.org` HTTP endpoint structures. Instead of modifying each submodule's source code to utilize new internal DNS paths, our cluster safely emulates the exact EBI namespace dynamically. 
The Ingress rules ensure that broad requests pointing to `/pride` correctly hit the database querying service (`crosslinking-api`), while highly-specific exact matches like `/pride/ws/.../upload_local` safely bypass the database and perfectly filter into your file processing service (`xiview-upload-api`). The remaining visualization static assets scale backwards seamlessly from the legacy `.html` engines.

## Creating Custom Docker Containers
The deployment YAML files currently pull from `rappsilberlab` docker-hub repositories. If you would like to edit the Python/React codebase uniquely or compile fresh artifacts locally natively:
```bash
docker build -t rappsilberlab/xiview-frontend:latest -f Dockerfile.xiview-frontend .
```
*(Repeat for `Dockerfile.crosslinking-api`, `Dockerfile.xiview-server`, `Dockerfile.xiview-upload-api`, and `Dockerfile.mzidentml-reader`).*

## Security
The `/pride` backend namespace utilizes simulated endpoints to fulfill exact EBI API requirements dynamically. All crosslinking uploads will live privately inside your isolated local Postgres volume storage unshared.
