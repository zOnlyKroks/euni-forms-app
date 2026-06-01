#!/bin/sh

# This script is the command ran by the Auth container
python3 /app/myauth/manage.py collectstatic --no-input
python3 /app/myauth/manage.py migrate

python3 /app/myauth/manage.py runserver 0.0.0.0:8000