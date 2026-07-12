# OpsCore Deployment Checklist

## Pre-deploy
- Confirm `python manage.py check` passes.
- Confirm `python manage.py test core.tests.OpsCoreSmokeTests -v 2` passes.
- Make sure the demo seed command works locally: `python manage.py seed_demo`.

## PythonAnywhere setup
- Create a new web app and point it at the Django project.
- Set the WSGI module to `opscore/wsgi.py`.
- Use Python 3.13 or the closest supported version available in the account.
- Install dependencies with `pip install -r requirements.txt`.

## Environment variables
- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=yourusername.pythonanywhere.com`

## Database
- Run `python manage.py migrate`.
- Run `python manage.py seed_demo`.

## Static files
- Ensure `collectstatic` is configured if you move to a non-demo static setup.
- For the current demo, the CDN-loaded fonts/icons keep the local static footprint light.

## Verification
- Open `/` and confirm the dashboard loads.
- Open `/purchase-orders/create/` and confirm line items can be added and removed.
- Open `/reports/` and confirm report links work.
- Open `/inventory/` and confirm the branch/product shortcuts work.
