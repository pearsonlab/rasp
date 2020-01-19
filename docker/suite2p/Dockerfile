FROM continuumio/miniconda3

RUN apt-get update && apt-get install -y gcc g++ libgl1 libgl1-mesa-glx libqt5x11extras5

# Conda setup
RUN ["/bin/bash", "-c", "conda config --set always_yes yes && conda update --yes conda && conda config --add channels conda-forge"]

COPY environment_suite2p.yml /root/environment_suite2p.yml

# Create conda environment
RUN ["/bin/bash", "-c", "conda env create -n improv-suite -f /root/environment_suite2p.yml"]

# CaImAn
RUN ["/bin/bash", "-c", "cd opt/ && git clone --single-branch --branch lite https://github.com/pearsonlab/CaImAn/ && cd CaImAn && source activate improv-suite && pip install . && cp caimanmanager.py ../ && cd ../ && python caimanmanager.py install"]

# Download test data
RUN cd ~/caiman_data/example_movies && mkdir Mesoscope && cd Mesoscope && wget https://caiman.flatironinstitute.org/~neuro/caiman_downloadables/Tolias_mesoscope_2.hdf5

ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV PYTHONPATH="${PYTHONPATH}:/opt/improv/src"

COPY entrypoint_suite2p.sh /root/entrypoint_suite2p.sh
ENTRYPOINT /root/entrypoint_suite2p.sh
