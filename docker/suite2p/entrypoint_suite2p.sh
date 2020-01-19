#!/bin/bash

source activate improv-suite
cd /opt
git clone --single-branch --branch suite2p https://github.com/pearsonlab/improv
cd improv
plasma_store -s /tmp/store -m 3000000000 &>/dev/null &
python -m nexus.nexus
