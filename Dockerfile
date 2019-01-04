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
    && apt-get -y update \
    && apt-get install -y python-dev libffi-dev libssl-dev \
    && pip install cffi --upgrade \
    && pip install pyopenssl --upgrade \
    && pip install ndg-httpsclient --upgrade \
    && pip install pyasn1 --upgrade

RUN cd /opt \
    && wget http://cab.spbu.ru/files/release3.13.0/SPAdes-3.13.0-Linux.tar.gz \
    && tar -xvzf SPAdes-3.13.0-Linux.tar.gz \
    && rm SPAdes-3.13.0-Linux.tar.gz

ENV PATH $PATH:/opt/SPAdes-3.13.0-Linux/bin

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

RUN make

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
