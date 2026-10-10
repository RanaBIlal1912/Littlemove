#!/usr/bin/env bash
# Regenerate .po files from source and compile
set -e
python manage.py makemessages -l en -l ur -l ur_Latn -l ar --ignore=venv --ignore=staticfiles
python manage.py compilemessages
echo "Translation files updated."
