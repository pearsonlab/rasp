FROM continuumio/miniconda3

RUN apt-get update && apt-get install -y gcc g++ libgl1 libgl1-mesa-glx libqt5x11extras5

# Conda setup
RUN ["/bin/bash", "-c", "conda config --set always_yes yes && conda update --yes conda && conda config --add channels conda-forge"]

# CaImAn
RUN ["/bin/bash", "-c", "cd opt/ && git clone --single-branch --branch lite https://github.com/pearsonlab/CaImAn/ && cd CaImAn && conda env create -n improv-caiman -f environment.yml && source activate improv-caiman && pip install . && cp caimanmanager.py ../ && cd ../ && python caimanmanager.py install"]

# improv
RUN ["/bin/bash", "-c", "source activate improv-caiman && conda install pyqtgraph seaborn && pip install pyarrow==0.13 lmdb"]

# Download test data
RUN cd ~/caiman_data/example_movies && mkdir Mesoscope && cd Mesoscope && wget https://caiman.flatironinstitute.org/~neuro/caiman_downloadables/Tolias_mesoscope_2.hdf5

ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV PYTHONPATH="${PYTHONPATH}:/opt/improv/src/"

COPY entrypoint_caiman.sh /root/entrypoint_caiman.sh
RUN chmod +x /root/entrypoint_caiman.sh
ENTRYPOINT /root/entrypoint_caiman.sh
