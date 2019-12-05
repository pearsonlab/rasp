FROM continuumio/miniconda3

RUN apt-get update && apt-get install -y gcc g++ libgl1 libgl1-mesa-glx libqt5x11extras5 zsh && conda config --set always_yes yes && conda update --yes conda
RUN wget https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | zsh || true

# Create conda environment and setup zsh
RUN ["/bin/bash", "-c", "cd opt && git clone https://github.com/pearsonlab/improv && cd improv && git checkout docker && conda env create -f docker_environment.yml && conda init zsh && echo 'conda activate improv' >> ~/.zshrc"]

# CaImAn
RUN ["/bin/zsh", "-c", "source ~/.zshrc && cd opt && git clone https://github.com/flatironinstitute/CaImAn && cd CaImAn && pip install -e . && python caimanmanager.py install --inplace"]

# Download test data
RUN cd ~/caiman_data/example_movies && mkdir Mesoscope && cd Mesoscope && wget https://caiman.flatironinstitute.org/~neuro/caiman_downloadables/Tolias_mesoscope_2.hdf5
# #
# # RUN mkdir src && cd src && git clone https://github.com/pearsonlab/improv && cd improv
# #
# # # && git submodule init && git submodule update
# #
# COPY files/test_env.yml /src/improv/test_env.yml
# COPY files/process.py /src/improv/src/process/process.py
# COPY files/store.py /src/improv/src/nexus/store.py
# COPY files/nexus.py /src/improv/src/nexus/nexus.py
# COPY files/basic_demo.yaml /src/improv/basic_demo.yaml
COPY files/online_cnmf.py /opt/CaImAn/caiman/source_extraction/cnmf/online_cnmf.py

RUN chmod +x /opt/improv/docker-entrypoint.sh
#
ENTRYPOINT /opt/improv/docker_entrypoint.sh

# ENTRYPOINT ["/bin/zsh"]

# https://github.com/microsoft/WSL/issues/4166
# docker build . -t caiman
# docker run -it --rm --shm-size=8g -e DISPLAY=10.197.4.247:0 -p 6000:6000 -v ~/Documents/GitHub:/mnt improv
