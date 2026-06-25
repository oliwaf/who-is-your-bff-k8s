# Who is your BFF?

Streamlit app for exploring Facebook Messenger JSON exports. It can load one or many
conversation files, scan local export folders, group split conversation parts, and show
basic stats, sender activity, top words, and a word cloud.

## Features

- Upload multiple Messenger JSON files.
- Scan one or more local folders recursively for `*.json` exports.
- Normalize older and newer Messenger export shapes.
- Repair common Messenger UTF-8 mojibake in exported JSON files.
- Merge split conversation parts such as `Name_26`, `Name_27`.
- Compare all conversations or inspect one selected conversation.
- Show message counts, word counts, activity by hour/day, top words, and word cloud.

## Project Layout

```text
app/
  engine.py          JSON loading, validation, encoding repair, file discovery
  participants.py    participant and sender helpers
  stats.py           conversation summaries and activity statistics
  text_analysis.py   word extraction and frequencies
  streamlit_app.py   Streamlit UI
k8s/                 Kubernetes manifests
tests/               pytest test suite and fixtures
```

## Requirements

- Python 3.13+
- pip

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Run Locally

```powershell
python -m pytest -v
streamlit run app/streamlit_app.py
```

Then open the URL printed by Streamlit, usually `http://localhost:8501`.

## Data Input

The app supports two input modes:

- `Upload JSON files`: choose one or many Messenger `message_*.json` files.
- `Scan local folder`: paste one folder path per line. You can point to a single
  conversation folder or a parent folder such as `messages/inbox`.

Messenger exports can contain private data. Keep local exports out of git; the repo
ignores `data/` for that reason.

## Tests

```powershell
python -m pytest -v
```

## Docker

Build the image:

```powershell
docker build -t who-is-your-bff:local .
```

Run the app:

```powershell
docker run --rm -p 8501:8501 who-is-your-bff:local
```

## Kubernetes

The manifests in `k8s/` are prepared for a manual homelab deployment. They do not
include Ingress yet.

Current Kubernetes settings:

- Namespace: `whoisyourbff`
- Deployment: `whoisyourbff`
- Service: `whoisyourbff`
- Image: `ghcr.io/oliwaf/who-is-your-bff-k8s:0.1.1`
- Image pull secret: `ghcr-secret`
- Service type: `ClusterIP`

Tag and push the image to GHCR:

```powershell
docker tag who-is-your-bff:local ghcr.io/oliwaf/who-is-your-bff-k8s:0.1.1
docker push ghcr.io/oliwaf/who-is-your-bff-k8s:0.1.1
```

Create the namespace manually:

```bash
kubectl create namespace whoisyourbff
```

If the GHCR image is private, create the image pull secret manually:

```bash
read -s GHCR_TOKEN

kubectl create secret docker-registry ghcr-secret \
  --namespace whoisyourbff \
  --docker-server=ghcr.io \
  --docker-username=oliwaf \
  --docker-password="$GHCR_TOKEN"

unset GHCR_TOKEN
```

Deploy manually:

```bash
kubectl apply -f k8s/
```

Verify manually:

```bash
kubectl get pods -n whoisyourbff -o wide
kubectl get svc -n whoisyourbff
kubectl logs -n whoisyourbff deploy/whoisyourbff
kubectl rollout status deployment/whoisyourbff -n whoisyourbff
```

Test through port-forward:

```bash
kubectl port-forward -n whoisyourbff svc/whoisyourbff 8501:8501 --address 0.0.0.0
```

Then open:

```text
http://192.168.88.50:8501
```
