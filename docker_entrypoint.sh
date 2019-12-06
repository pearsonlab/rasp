#!/bin/zsh

source activate caiman
cd /opt/improv/src
plasma_store -s /tmp/store -m 3000000000 &>/dev/null &
#/bin/zsh
python -m nexus.nexus
