# xiVIEW Full-Stack Deployment

This repository contains the deployment configurations and orchestration submodules required to host your own full-stack instance of **xiVIEW**—a platform for the downstream analysis of cross-linking mass spectrometry data.

## Prerequisites

- A running Kubernetes cluster (e.g. k3s, minikube, or EKS).
- `kubectl` configured with cluster access.

## Quickstart Deployment via Helm

We use Helm to deploy and configure all components. You don't even need to clone this repository!

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

**3. Install the Deployment Stack:**
Assuming your Kubernetes cluster (`kubectl`) is currently active, install the Helm chart natively by passing your overrides:
```bash
helm install my-xiview xiview-repo/xiview-stack -f k3s-values.yaml
```

**Upgrading or Rolling Actions:**
If you rebuild container artifacts or tweak your configuration, seamlessly push the upgrade via Helm across the entire stack:
```bash
helm upgrade my-xiview xiview-repo/xiview-stack -f k3s-values.yaml
```

## Architecture

This stack runs entirely inside Kubernetes. It sets up 6 distinct microservices to map and digest crosslinking data:

1. **`xiview-frontend`**: The React-based UI allowing users to upload `mzIdentML` (.mzid) formats alongside mass spectra files (.mzML).
2. **`xiview-server`**: The legacy JavaScript rendering visualization engine for node networks and 3D Structure mapping.
3. **`xiview-upload-api`**: Manages file caching and routes `.mzIdentML` schemas into DB structures utilizing Pyteomics readers.
4. **`crosslinking-api`**: Exposes read access mapping `spectrum`, `peptides`, and `crosslinks` from PostgreSQL to the visualization engine without polling EBI.
5. **`mzidentml-reader`**: Python processor tasked with reading `.mzIdentML` trees into normalized DB rows.
6. **`postgresql-service`**: Data-layer housing your crosslinking datasets.
