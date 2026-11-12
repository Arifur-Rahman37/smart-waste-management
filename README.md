# ♻️ Smart Waste Management System (SE331 – Assessment 2)

Full-stack web app built with **Streamlit + SQLite**. Citizens report waste problems; municipal admins manage collection.

## Features
| Required | Where |
|---|---|
| Citizen registration/login (PBKDF2-hashed passwords) | `views/auth_view.py` |
| Report waste problems / select category / enter location | `views/citizen.py → report_problem` |
| View reported complaints (with status history) | `views/citizen.py → my_complaints` |
| Admin dashboard | `views/admin.py → dashboard` |
| Update collection status | `views/admin.py → manage_reports` |
| Search / filter reports (text, status, category, priority, team, dates) + CSV export | `views/admin.py → manage_reports` |

| Advanced | Where |
|---|---|
| Upload waste-site photograph | report form (stored in DB) |
| Priority-based reporting | Low / Medium / High / Critical |
| Assign collection teams | Manage Reports + Teams page |
| Waste collection statistics | Statistics page |
| **Bonus:** interactive map + intelligent priority classification | `views/common.py → report_map`, `classifier.py` |

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Report form has a click-to-pick map (streamlit-folium).

Admin login: `admin@city.gov` / `admin123` (change in `config.py`). Use **Load demo data** in the admin sidebar for sample reports (demo citizen: `citizen@demo.com` / `demo123`).

## Deploy on Streamlit Community Cloud
1. Push this folder to a GitHub repo.
2. Go to https://share.streamlit.io → **New app** → choose repo, branch, main file `app.py`.
3. Deploy.

> Note: Community Cloud storage is ephemeral — SQLite data resets when the app restarts/redeploys. For persistent data use an external DB (e.g. Supabase/Postgres).

## Structure
```
app.py  config.py  database.py  classifier.py
views/ (auth_view, citizen, admin, common)
.streamlit/config.toml  requirements.txt
```
