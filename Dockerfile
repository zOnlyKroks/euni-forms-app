FROM python:3.9-bullseye

ARG AA_GIT="https://gitlab.com/allianceauth/allianceauth.git"
ARG AA_GIT_BRANCH="v3.x"
ARG PIP_INDEX_URL="https://pypi.eveuniversity.org"

# These should be set to the UID/GID of the host user.
# Otherwise the apps:dev mount will not be writable by the container
ARG DOCKER_HOST_UID=1000
ARG DOCKER_HOST_GID=1000 

# Things done as root
COPY ./scripts/auth_startup.sh /startup.sh
RUN chmod 755 /startup.sh

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y build-essential
RUN apt-get install -y gettext git
RUN apt-get install -y mariadb-client libmariadb-dev
RUN groupadd -g ${DOCKER_HOST_GID} euni-aa-dev && useradd -u ${DOCKER_HOST_UID} -g euni-aa-dev -m -d /app euni-aa-dev

RUN mkdir -p /var/www

# Things done as euni-aa-dev
USER euni-aa-dev

WORKDIR /app

RUN mkdir dev

ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install wheel tox
RUN git clone -b "${AA_GIT_BRANCH}" -- "${AA_GIT}"

# Install each pip package you need here that you aren't actively developing
RUN pip install allianceauth

RUN pip install aa-euni-core

# Copy any local dev projects into the container
COPY --chown=euni-aa-dev:euni-aa-dev apps /app/dev

# Install any local development or editable things here
# For example:
# RUN pip install -e dev/aa-euni-core
# You may need to use compat mode to make allianceauth editable:
# RUN pip install -e dev/allianceauth --config-settings editable_mode=compat

RUN allianceauth start myauth

EXPOSE 8000

CMD ["/startup.sh"]
