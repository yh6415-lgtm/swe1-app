# swe1-app

Individual Software Engineering I assignment: the Django 5.2 polls application,
covering [tutorial parts 1-4](https://docs.djangoproject.com/en/5.2/intro/tutorial01/).

Live application: [Open polls](http://swe1-app-287872994760.us-east-1.elasticbeanstalk.com/polls/).

Repository: [yuelihe2-svg/swe1-app](https://github.com/yuelihe2-svg/swe1-app).

## Features

- Latest published questions at `/polls/`.
- Question details, radio choices, CSRF-protected POST voting and error messages.
- Atomic vote increments and a redirect to the results page after voting.
- Results with vote counts and a link to vote again.
- `Question` and `Choice` models, migrations and Django admin at `/admin/`.
- Generic list/detail views and namespaced URLs from tutorial part 4.
- Three sample polls, seeded without resetting existing votes.
- Elastic Beanstalk WSGI configuration, Gunicorn and static files via WhiteNoise.

The root URL redirects to `/polls/`. Public voting requires no account.

## Run locally (PowerShell, Python 3.12)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_polls
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/polls/`. Create your own admin password with
`createsuperuser`; no admin credentials are included in the repository.

## Verify

```powershell
.\.venv\Scripts\python.exe manage.py test polls
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

The tests cover voting, malformed and cross-question choices, missing polls,
CSRF, admin access, future publication dates and repeatable sample-data setup.

## Deploy and submit

Follow [DEPLOYMENT.md](DEPLOYMENT.md) for personal AWS registration, EB CLI setup,
deployment and the Brightspace checklist. Build a source ZIP with:

```powershell
.\.venv\Scripts\python.exe scripts\package.py
```

The ZIP is `dist/swe1-app.zip`, with `manage.py` at its root. It excludes virtual
environments, local databases, credentials, Git history and deployment tools.

The deployment uses one EC2 instance and SQLite. Its database and random Django
secret are stored outside the deployed source directory in `/var/app/data`, so
normal code deployments on the same instance preserve them. Replacing or
terminating the EC2 instance loses this local data; this is a coursework setup,
not a durable multi-instance production architecture.

The minimal EB endpoint uses HTTP. Adding HTTPS requires a separate configuration;
after HTTPS is working, set `DJANGO_HTTPS=True` to enable secure cookies, redirects
and HSTS. Do not submit an `https://` URL unless you have verified it works.

AWS credentials and deployed secret keys must never be committed.
