#!/bin/bash

source activate improv-caiman
cd /opt
git clone --single-branch --branch docker https://github.com/pearsonlab/improv
cd improv
plasma_store -s /tmp/store -m 3000000000 &>/dev/null &
python -m nexus.nexus
