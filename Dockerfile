FROM continuumio/miniconda3

RUN apt-get update && apt-get install -y gcc g++ libgl1 libgl1-mesa-glx libqt5x11extras5 zsh && conda config --set always_yes yes && conda update --yes conda
RUN wget https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | zsh || true

# Hold until submodule is fixed.
# # Create conda environment and setup zsh
# RUN ["/bin/bash", "-c", "cd opt && git clone https://github.com/pearsonlab/improv && cd improv && git checkout docker && conda env create -f docker_environment.yml && conda init zsh && echo 'conda activate improv' >> ~/.zshrc"]

# Create conda environment and setup zsh
RUN ["/bin/bash", "-c", "cd opt && git clone https://github.com/flatironinstitute/CaImAn && cd CaImAn && conda env create -n caiman -f environment.yml && conda init zsh && echo 'conda activate caiman' >> ~/.zshrc"]

# Install caimanmanager
RUN ["/bin/zsh", "-c", "source ~/.zshrc && cd opt/CaImAn/ && pip install -e . && python caimanmanager.py install --inplace"]

# improv
RUN ["/bin/zsh", "-c", "source ~/.zshrc && cd opt && git clone https://github.com/pearsonlab/improv && cd improv && git checkout docker && conda install pyarrow pyqtgraph && pip install lmdb"]

# Download test data
RUN cd ~/caiman_data/example_movies && mkdir Mesoscope && cd Mesoscope && wget https://caiman.flatironinstitute.org/~neuro/caiman_downloadables/Tolias_mesoscope_2.hdf5

COPY files/online_cnmf.py /opt/CaImAn/caiman/source_extraction/cnmf/online_cnmf.py

RUN chmod +x /opt/improv/docker_entrypoint.sh
ENTRYPOINT /opt/improv/docker_entrypoint.sh

# https://github.com/microsoft/WSL/issues/4166
# docker build . -t caiman
# docker run -it --rm --shm-size=8g -e DISPLAY=10.197.4.247:0 -p 6000:6000 -v ~/Documents/GitHub:/mnt improv
