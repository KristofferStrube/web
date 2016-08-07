#! /bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source $DIR/venv/bin/activate

python $DIR/manage.py updateical --settings=tkweb.settings.prod
