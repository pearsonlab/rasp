FROM continuumio/miniconda3

RUN apt-get update && apt-get install -y gcc g++ libgl1 libgl1-mesa-glx libqt5x11extras5 xvfb x11-apps imagemagick && conda config --set always_yes yes && conda update --yes conda

# Hold until submodule is fixed.
# # Create conda environment and setup zsh
# RUN ["/bin/bash", "-c", "cd opt && git clone https://github.com/pearsonlab/improv && cd improv && git checkout docker && conda env create -f docker_environment.yml && conda init zsh && echo 'conda activate improv' >> ~/.zshrc"]

# Create conda environment
RUN ["/bin/bash", "-c", "cd opt && git clone https://github.com/pearsonlab/CaImAn/ && cd CaImAn && git checkout lite && conda env create -n caiman -f environment.yml && echo 'conda activate caiman' >> ~/.bashrc"]

# Install caimanmanager
RUN ["/bin/bash", "-c", "source activate caiman && cd opt/CaImAn/ && pip install . && cp caimanmanager.py ../ && cd ../ && python caimanmanager.py install"]
#
# improv
RUN ["/bin/bash", "-c", "source activate caiman && cd opt && git clone https://github.com/pearsonlab/improv && cd improv && git checkout docker && conda install pyqtgraph seaborn && pip install lmdb pyarrow==0.13"]
#
# Download test data
RUN cd ~/caiman_data/example_movies && mkdir Mesoscope && cd Mesoscope && wget https://caiman.flatironinstitute.org/~neuro/caiman_downloadables/Tolias_mesoscope_2.hdf5
#
# RUN ["/bin/bash", "-c", "apt-get  install -y cabextract && wget http://ftp.uk.debian.org/debian/pool/contrib/m/msttcorefonts/ttf-mscorefonts-installer_3.7_all.deb && dpkg -i ttf-mscorefonts-installer_3.7_all.deb"]

# RUN chmod +x /opt/improv/docker/docker_entrypoint.sh
# ENTRYPOINT /opt/improv/docker/docker_entrypoint.sh

# https://github.com/microsoft/WSL/issues/4166
# docker build . -t caiman
# docker run -it --rm --shm-size=8g -e DISPLAY=10.197.4.247:0 -p 6000:6000 -v ~/Documents/GitHub:/mnt improv
