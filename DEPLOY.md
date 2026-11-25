# Deploying PlaceIQ

PlaceIQ deploys as **one Docker container**: the Python engine stays internal, and only the web app is public.
The model is trained on the bundled public placement datasets while the image builds.

## Render (free), recommended

**What the free plan gives you:**
- a public `https://…onrender.com` URL;
- 512 MB of memory (PlaceIQ uses about 360 MB);
- sleeps after 15 minutes without visitors, and the next visit wakes it in about a minute;
- no persistent disk, so profiles students *shared* with the placement cell are lost when it restarts or redeploys. Students' own profiles are safe either way, because they live in each student's browser;
- online retraining is switched off (the server is too small). Retrain on your own computer and redeploy (see Updating).

### 1. Put the code on GitHub (you do this)
1. Create a GitHub account if you don't have one, then **New repository**, e.g. `placeiq`. Private is fine.
2. Push this folder. It's already a git repository with a first commit:
   ```powershell
   git remote add origin https://github.com/YOUR-USERNAME/placeiq.git
   git push -u origin main
   ```

### 2. Create the service on Render (you do this)
1. Sign up at https://render.com with your GitHub account (no card needed for the free web service).
2. **New → Blueprint**, then pick the `placeiq` repository. Render reads `render.yaml`.
3. When asked for `PLACEIQ_ADMIN_PASSWORD`, type the placement-cell password. `PLACEIQ_SALT` is generated for you.
4. **Apply**. The first build takes about 10–15 minutes. Then open the URL Render shows.

### Updating
- **Code changes:** commit and `git push`. Render rebuilds automatically.
- **New model:** on your own computer, run `start.bat` and train on the Model page, or run `.venv\Scripts\python -m placeiq public`. Then copy the training data into the image build:
  - put your processed CSV in `placeiq-data/processed/`;
  - change the training line in the Dockerfile (`RUN ... python -m placeiq public`) to train on it, e.g. `python -m placeiq.model.train --data placeiq-data/processed/historical.csv`;
  - make sure `.gitignore` doesn't exclude that file. Only commit **anonymised** data (hashed ids, no names).

## Hugging Face Spaces (paid)
Docker Spaces need a PRO subscription (about $9/month). With PRO: run `deploy\hf_upload.py YOUR-USERNAME/placeiq` (after
`hf auth login`), then add the secrets `PLACEIQ_ADMIN_PASSWORD` and `PLACEIQ_SALT` in the Space settings. Retraining works
there, so don't set `PLACEIQ_DISABLE_TRAINING`.

## Settings reference
| Variable | Purpose |
|---|---|
| `PLACEIQ_ADMIN_PASSWORD` | Placement-cell password. If unset, those pages are open to anyone with the link. |
| `PLACEIQ_SALT` | Long random secret for hashing roll numbers. Keep it the same forever. |
| `PLACEIQ_DISABLE_TRAINING` | `1` turns off online retraining (small servers). |
| `DATABASE_URL` | Optional external database (e.g. PostgreSQL), so shared profiles survive restarts. |

## Test the container locally
```powershell
docker build -t placeiq .
docker run --rm -p 7860:7860 -e PLACEIQ_ADMIN_PASSWORD=change-me -e PLACEIQ_SALT=some-long-random-string -e PLACEIQ_DISABLE_TRAINING=1 placeiq
```
Then open http://localhost:7860.
