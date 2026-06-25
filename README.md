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
pytest
```

## Docker

Build the image:

```powershell
docker build -t who-is-your-bff:latest .
```

Run the app:

```powershell
docker run --rm -p 8501:8501 who-is-your-bff:latest
```

## Kubernetes

The manifests in `k8s/` deploy the Streamlit app as a single replica service.

For a local cluster such as kind or Docker Desktop Kubernetes, build/load the image and
apply the manifests:

```powershell
docker build -t who-is-your-bff:latest .
kubectl apply -f k8s/
kubectl port-forward service/who-is-your-bff 8501:8501
```

Then open `http://localhost:8501`.

If you publish the image to a registry, update `image` in
`k8s/deployment.yaml` before applying the manifests.
