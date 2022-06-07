FROM kbase/sdkbase2:python
MAINTAINER KBase Developer
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

RUN echo "start building docker image"

# SPAdes needs newer libstdc++, so move from stretch to buster
RUN echo "deb http://deb.debian.org/debian buster main contrib" > /etc/apt/sources.list
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 648ACFD622F3D138 0E98404D386FA1D9 DCC9EFBF77E11517

RUN apt-get update \
    && apt-get -y --allow-unauthenticated install python3-dev \
    && apt-get -y --allow-unauthenticated install wget \
    && apt-get -y --allow-unauthenticated install gcc \
    && apt-get -y --allow-unauthenticated install build-essential \
    && apt-get -y --allow-unauthenticated install zlib1g-dev \
    && apt-get -y --allow-unauthenticated install bowtie \
    && apt-get -y --allow-unauthenticated install bowtie2 \
    && apt-get -y --allow-unauthenticated install ncbi-blast+ \
    && apt-get -y --allow-unauthenticated install samtools

RUN pip install --upgrade pip \
    && pip3 install psutil cmake \
    && python --version

ENV UNICYCLER_VERSION='0.4.8'
ENV SPADES_VERSION='3.15.3'
ENV RACON_VERSION='1.4.21'
ENV PILON_VERSION='1.24'

# use conda version of SPAdes instead of authors' version,
# because spades-hammer from the latter crashes on some linux distros,
# including Debian and Arch
RUN cd /opt \
    && wget https://anaconda.org/bioconda/spades/${SPADES_VERSION}/download/linux-64/spades-${SPADES_VERSION}-h95f258a_0.tar.bz2 \
    && mkdir spades-${SPADES_VERSION} \
    && cd spades-${SPADES_VERSION} \
    && tar -xvjf ../spades-${SPADES_VERSION}-h95f258a_0.tar.bz2 \
    && rm ../spades-${SPADES_VERSION}-h95f258a_0.tar.bz2

RUN cd /opt \
    && wget https://github.com/lbcb-sci/racon/releases/download/${RACON_VERSION}/racon-v${RACON_VERSION}.tar.gz \
    && tar -xvzf racon-v${RACON_VERSION}.tar.gz \
    && rm racon-v${RACON_VERSION}.tar.gz \
    && cd racon-v${RACON_VERSION} \
    && cmake -DCMAKE_BUILD_TYPE=Release \
    && make

RUN cd /opt/ \
    && mkdir pilon \
    && cd pilon \
    && wget https://github.com/broadinstitute/pilon/releases/download/v${PILON_VERSION}/pilon-${PILON_VERSION}.jar \
    && echo '#!/bin/bash' > pilon \
    && echo "/usr/bin/java -Xmx16G -jar /opt/pilon/pilon-${PILON_VERSION}.jar \$@" >> pilon \
    && chmod +x pilon

ENV PATH $PATH:/opt/spades-${SPADES_VERSION}/bin:/opt/racon-v${RACON_VERSION}/bin:/opt/pilon/

# use conda version of unicycler instead of git version
# so it is compatible with conda SPAdes

RUN cd /opt \
    && wget https://anaconda.org/bioconda/unicycler/0.4.8/download/linux-64/unicycler-${UNICYCLER_VERSION}-py36hd181a71_3.tar.bz2 \
    && mkdir Unicycler-${UNICYCLER_VERSION} \
    && cd Unicycler-${UNICYCLER_VERSION} \
    && tar -xvjf ../unicycler-${UNICYCLER_VERSION}-py36hd181a71_3.tar.bz2 \
    && rm ../unicycler-${UNICYCLER_VERSION}-py36hd181a71_3.tar.bz2 \
    && mkdir -p /opt/conda/conda-bld/unicycler_1604335941209/_h_env_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_pla/bin/ \
    && ln -s /miniconda/bin/python /opt/conda/conda-bld/unicycler_1604335941209/_h_env_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_placehold_pla/bin/python 

ENV PATH $PATH:/opt/Unicycler-${UNICYCLER_VERSION}/bin
ENV PYTHONPATH $PYTHONPATH:/opt/Unicycler-${UNICYCLER_VERSION}/lib/python3.6/site-packages/:/opt/Unicycler-${UNICYCLER_VERSION}/lib/python3.6/site-packages/unicycler

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

RUN make

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
