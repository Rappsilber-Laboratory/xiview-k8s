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
If you have a Traefik Ingress Controller and Let's Encrypt cluster-issuers already configured on your cluster, you can securely route internet traffic using a standard Ingress manifest. Create a file named `k8s-ingress.yaml` routing internal services outwards. For example:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: xiview-ingress
spec:
  rules:
    - host: xiview.your-domain.com
      http:
        paths:
          # Frontend React UI for Overviews/Uploads
          - path: /
            pathType: Prefix
            backend:
              service:
                name: xiview-frontend-service
                port:
                  number: 80
          # Legacy xiVIEW server reserved for visualization scripts and rendering HTML
          - path: /network.html
            pathType: Exact
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          - path: /spectra.html
            pathType: Exact
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          - path: /xiview.js
            pathType: Exact
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          - path: /vendors.js
            pathType: Exact
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          - path: /xiview-pride.css
            pathType: Exact
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          # Asset prefixes for the legacy server visualization engine
          - path: /images
            pathType: Prefix
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          - path: /Lato
            pathType: Prefix
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          - path: /fontawesome
            pathType: Prefix
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          - path: /R
            pathType: Prefix
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          - path: /docs
            pathType: Prefix
            backend:
              service:
                name: xiview-server-service
                port:
                  number: 80
          # Explicit hook bypassing regular /pride routing to the fastAPI uploader
          - path: /pride/ws/archive/crosslinking/v3/upload_local
            pathType: Exact
            backend:
              service:
                name: xiview-upload-api-service
                port:
                  number: 8090
          # Default EBI REST mapping towards your local backend
          - path: /pride
            pathType: Prefix
            backend:
              service:
                name: crosslinking-api-service
                port:
                  number: 8080
```

## Creating Custom Docker Containers
The deployment YAML files currently pull from `rappsilberlab` docker-hub repositories. If you would like to edit the Python/React codebase uniquely or compile fresh artifacts locally natively:
```bash
docker build -t rappsilberlab/xiview-frontend:latest -f Dockerfile.xiview-frontend .
```
*(Repeat for `Dockerfile.crosslinking-api`, `Dockerfile.xiview-server`, `Dockerfile.xiview-upload-api`, and `Dockerfile.mzidentml-reader`).*

## Security
The `/pride` backend namespace utilizes simulated endpoints to fulfill exact EBI API requirements dynamically. All crosslinking uploads will live privately inside your isolated local Postgres volume storage unshared.
