# UHD MCP Deployment

The manifests in this directory are **generic templates**. Before applying, replace the
placeholders for your environment:

| Placeholder | Replace with |
|-------------|--------------|
| `your-namespace` | Your Kubernetes/OpenShift namespace |
| `REPLACE_ME/uhd-mcp:latest` | Your container image reference (registry/repo:tag) |
| `your-sriov-network` / `your-sriov-resource` | Your SR-IOV network name and resource (the dedicated radio network the USRP is reached over) |
| `uhd-mcp.your-domain.example` | Your external route host (optional) |

## 1. Build and push the image

There is no managed image build in this repo — build it yourself from [the Dockerfile](Dockerfile)
and push to your registry:

```bash
docker build -f deploy/Dockerfile --build-arg UHD_VERSION=4.7.0.0 -t REPLACE_ME/uhd-mcp:latest .
docker push REPLACE_ME/uhd-mcp:latest
```

See the repository [README](../README.md) for the full build/run options.

## 2. (Optional) GitHub PAT secret

The image bundles the application via `COPY`, so it runs without any token. The `PAT_TOKEN`
secret is only needed if you opt into the `start.sh` → `update-repo.sh` auto-pull path. If you
use it, create a secret named `github-pat` (key `token`):

```bash
kubectl create secret generic github-pat \
  --from-literal=token=your-actual-github-pat-token \
  --namespace=your-namespace
```

or edit and apply [github-pat-secret.yaml](github-pat-secret.yaml). If you don't use it, remove
the `PAT_TOKEN` env block from [deployment.yaml](deployment.yaml).

## 3. Deploy

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f route.yaml
```

## Environment variables

- `MCP_SHARED_DATA_DIR`: shared data storage directory (captures/downloads). The manifests mount a PVC at `/data/shared`.
- `PAT_TOKEN`: optional GitHub PAT (from the secret above) enabling repo auto-update on start.
