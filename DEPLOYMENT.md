# Running and deploying the web app

The web app (`app.py`) is a thin Streamlit UI over the existing redaction pipeline.
It lets a reviewer upload a `.docx`, pick which PII categories to redact, see a summary,
and download the redacted file and audit log. It does not modify the uploaded file — it
works on a copy.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## Deploy (Streamlit Community Cloud — free, simplest)

Streamlit Community Cloud deploys straight from a GitHub repo, so there is no Dockerfile
or server config to manage.

1. Push this project to a public GitHub repository.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app**, pick the repo/branch, and set **Main file path** to `app.py`.
4. Deploy. It installs `requirements.txt` automatically and gives you a public URL like
   `https://<your-app>.streamlit.app` — that is the link for the submission form.

Notes:
- `requirements.txt` is all that is needed; there are no system dependencies.
- spaCy is intentionally **not** in `requirements.txt`, so the deploy stays light. The
  "Use spaCy NER" toggle in the app degrades to a no-op unless spaCy and the model are
  installed, so the deployed app runs the rule-based detectors (the primary system).
- The app accepts any `.docx`; the provided prospectus is only the test/evaluation
  document, not hard-coded into the UI.

## Enable the optional spaCy detector (local only)

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

Then tick "Use spaCy NER (experimental)" in the app, or set `ner.use_spacy: true` in
`config/default.yaml`. With the model missing it is simply ignored.
