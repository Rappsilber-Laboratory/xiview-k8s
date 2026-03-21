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

We exclusively use Helm to cleanly deploy, configure, and rapidly parameterize all microservice components dynamically natively on any Kubernetes cluster.

**1. Clone the repository and initialize submodules:**
```bash
git clone https://github.com/Rappsilber-Laboratory/xiview-stack.git
cd xiview-stack
git submodule update --init --recursive
```

**2. Create your Configuration Override (e.g. `k3s-values.yaml`):**
If you are deploying on a local K3s cluster, you can define a minimal values file that automatically hooks deeply into natively available ingress controllers (like Traefik) and built-in StorageClasses (like `local-path`).
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

**3. Install the Deployment Stack:**
Assuming your Kubernetes cluster (`kubectl`) is currently active, install the Helm chart by passing your overrides:
```bash
helm install my-xiview ./helm-chart -f k3s-values.yaml
```
*Note: This command provisions the complete Postgres layer, resolves the backend microservices securely, and automatically binds the generic frontend GUI seamlessly to your chosen Ingress routes.*

**Upgrading or Rolling Actions:**
If you rebuild container artifacts or tweak your configuration, seamlessly push the upgrade natively via Helm across the entire stack:
```bash
helm upgrade my-xiview ./helm-chart -f k3s-values.yaml
```

## Architecture Notes
The xiVIEW suite leverages highly specialized ingress mappings to effectively emulate legacy EBI endpoints natively across internal cluster DNS routing. Static frontend nodes scale perfectly without requiring manual HTTP redirects inside source code!

## Creating Custom Docker Containers
The Helm chart defaults to pulling edge-images directly from the `rappsilberlab` docker-hub repositories natively. If you compile fresh custom source-code artifacts locally:
```bash
docker build -t rappsilberlab/xiview-frontend:custom -f Dockerfile.xiview-frontend .
```
*(You can effortlessly point the Helm chart to your custom `:custom` tags dynamically by just modifying the `.Values.xiviewFrontend.image.tag` inside your values file!)*
