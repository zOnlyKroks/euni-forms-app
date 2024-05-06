# EVE Uni Alliance Auth Docker Dev Environment

This is the base Alliance Auth Development Environment for EVE Uni.

## Requirements
* Linux based docker host (WSL2, Docker Desktop, Podman Desktop, etc)
* Host must have python3 available to use the project's host based scripts/tools

This project has been tested with M1+ MacOS, but not every image used supports ARM/M1 and will likely be running in translation mode.

This project has not been tested with Podman desktop, but should work.

## First Setup

```bash
scripts/setup_env.py -i

# Fill in all the fields, paying special attention to the required fields.

# Add any projects you wish to DEVELOP under apps/

# Update Dockerfile adding your projects as editable pip packages

# Update conf/local.py as needed for those projects


docker compose up -d

# After first building, environment should be running in detached mode.

# Feel free to test using the default address http://localhost:8000/

# Use the following command to destroy the project if you're not using it now

docker compose down

```

## Using

Whenever you wish to bring the environment up, just run one of the following based upon preference:

**Start in detached mode:**
`docker compose up -d`

**Start in foreground mode:**
`docker compose up`

### Setting up Super User

1. Login at least once using the character you wish to become a super-user.
2. Run the following command from your host shell replacing `[AA USERNAME HERE]` with your username.

```bash
docker compose exec auth python myauth/manage.py shell -c \
"from django.contrib.auth.models import User; u = User.objects.get(username='[AA USERNAME HERE]'); u.is_superuser = True; u.is_staff=True; u.save()"
```

The above command shouldn't raise an exception and should just exist after printing a few log lines.

3. Refresh your browser and you should now be super-user.

### Development

Packages baked into the images are split into installed but not editable and editable. Make sure you put the project(s) you're actively developing with this env into the editable section of the Dockerfile with their paths under `apps/`.

The default compose config will automatically bind mount the `apps/` directory to `/app/dev/` inside the container. Coupled with a proper editable install for each project in under `apps/` the Django `runserver` command will automatically restart as you save files in your editor.

Check the Dockerfile comments for more info and example usage.

## Notes

General notes and important points

### Database
If you re-generate the env or otherwise modify `mysql/initdb.d/*` the MariaDB container will not re-run the init scripts unless the database volume is deleted.

**Delete MariaDB volume *(default)*:**
`docker volume rm dev-aauth_mysql-data`

### After Adding/Removing Apps/Plugins
Since this image is optimized for faster startup times, it bakes applications/plugins into the image. To add or remove applications from your environment you will have to rebuild the Alliance Auth container image. This can be done with the docker compose command and remember to update your INSTALLED_APPS in `conf/local.py`!

**Detached:**
`docker compose up --build -d`

**Foreground:**
`docker compose up --build`

### Celery
This environment doesn't automatically start Celery to run background tasks. It is possible however to run Celery manually.

**Inside a shell attached to the Auth container:**

```bash
cd /app/myauth

celery -A myauth worker -l info -B
```

This will run Celery in the foreground. Just Ctrl-C or close the terminal whenever you are done running it.

**Note that code changes that run within the Celery process will not take effect until Celery is restarted.**