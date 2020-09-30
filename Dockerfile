FROM kbase/sdkbase2:python
MAINTAINER KBase Developer
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

RUN echo "start building docker image"

RUN apt-get update \
    && apt-get -y install python3-dev \
    && apt-get -y install wget \
    && apt-get -y install gcc \
    && apt-get -y install bowtie \
    && apt-get -y install samtools

RUN pip install --upgrade pip \
    && pip3 install psutil \
    && python --version

ENV UNICYCLER_VERSION='0.4.8'
ENV SPADES_VERSION='3.13.0'
ENV RACON_VERSION='1.4.13'
ENV PILON_VERSION='1.23'

RUN cd /opt \
    && wget http://cab.spbu.ru/files/release${SPADES_VERSION}/SPAdes-${SPADES_VERSION}-Linux.tar.gz \
    && tar -xvzf SPAdes-${SPADES_VERSION}-Linux.tar.gz \
    && rm SPAdes-${SPADES_VERSION}-Linux.tar.gz

RUN cd /opt \
    && wget https://github.com/rrwick/Unicycler/archive/v${UNICYCLER_VERSION}.tar.gz \
    && tar -xvzf v${UNICYCLER_VERSION}.tar.gz \
    && rm v${UNICYCLER_VERSION}.tar.gz

RUN cd /opt \
    && wget https://github.com/lbcb-sci/racon/releases/download/${RACON_VERSION}/racon-v${RACON_VERSION}.tar.gz \
    && tar -xvzf racon-v${RACON_VERSION}.tar.gz \
    && rm racon-v${RACON_VERSION}.tar.gz

RUN cd /opt/ \
    && mkdir pilon \
    && cd pilon \
    && wget https://github.com/broadinstitute/pilon/releases/download/v${PILON_VERSION}/pilon-${PILON_VERSION}.jar

ENV PATH $PATH:/opt/SPAdes-${SPADES_VERSION}-Linux/bin:/opt/racon-v${RACON_VERSION}/bin

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

RUN make

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
