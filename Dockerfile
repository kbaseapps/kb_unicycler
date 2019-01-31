FROM kbase/kbase:sdkbase2.latest
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

RUN pip install --upgrade pip \
    && pip install requests --upgrade \
    && pip install 'requests[security]' --upgrade \
    && pip install psutil \
    && pip install pyyaml \
    && pip install regex \
    && apt-get -y update \
    && apt-get install -y python-dev libffi-dev libssl-dev \
    && pip install cffi --upgrade \
    && pip install pyopenssl --upgrade \
    && pip install ndg-httpsclient --upgrade \
    && pip install pyasn1 --upgrade

ENV SPADES_VERSION='3.13.0'

RUN cd /opt \
    && wget http://cab.spbu.ru/files/release${SPADES_VERSION}/SPAdes-${SPADES_VERSION}-Linux.tar.gz \
    && tar -xvzf SPAdes-${SPADES_VERSION}-Linux.tar.gz \
    && rm SPAdes-${SPADES_VERSION}-Linux.tar.gz

ENV PATH $PATH:/opt/SPAdes-${SPADES_VERSION}-Linux/bin

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

RUN make

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
