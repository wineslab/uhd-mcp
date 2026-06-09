# UHD MCP Deployment

## Deployment Setup

### 1. GitHub PAT Token Secret

Before deploying, create a GitHub Personal Access Token (PAT) and configure it as a Kubernetes secret:

#### Option A: Using kubectl (Recommended)

```bash
kubectl create secret generic github-pat-secret \
  --from-literal=token=your-actual-github-pat-token \
  --namespace=your-namespace
```

#### Option B: Using the YAML file

1. Edit `github-pat-secret.yaml`
2. Replace the base64 encoded token with your actual token:

   ```bash
   echo -n 'your-actual-github-pat-token' | base64
   ```

3. Apply the secret:

   ```bash
   kubectl apply -f github-pat-secret.yaml
   ```

### 2. Deploy the Application

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f route.yaml
```

## Repository Auto-Update

The deployment includes automatic repository updates on startup:

- The `PAT_TOKEN` environment variable is injected from the Kubernetes secret
- On container start, `update-repo.sh` is called to:
  - Remove old remote configurations
  - Set new remote with PAT authentication
  - Pull latest changes from the repository
- If the update fails, the service continues to start with existing code

## Environment Variables

- `MCP_SHARED_DATA_DIR`: Shared data storage directory
- `VNC_HOST`: VNC server hostname for screenshots
- `VNC_PORT`: VNC server port
- `VNC_PASSWORD`: VNC server password
- `PAT_TOKEN`: GitHub Personal Access Token (from secret)