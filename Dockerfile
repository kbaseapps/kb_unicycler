FROM kbase/kbase:sdkbase.latest
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

# RUN apt-get update


RUN cd /opt \
    && wget http://spades.bioinf.spbau.ru/release3.10.0/SPAdes-3.10.0-Linux.tar.gz \
    && tar -xvzf SPAdes-3.10.0-Linux.tar.gz \
    && rm SPAdes-3.10.0-Linux.tar.gz \
    && pip install psutil \
    && pip install pyyaml

RUN sudo apt-get install python-dev libffi-dev libssl-dev
RUN pip install cffi --upgrade
RUN pip install pyopenssl --upgrade
RUN pip install ndg-httpsclient --upgrade
RUN pip install pyasn1 --upgrade

RUN pip install requests --upgrade \
    && pip install 'requests[security]' --upgrade \
    && pip install ipython \
    && apt-get install nano

ENV PATH $PATH:/opt/SPAdes-3.10.0-Linux/bin

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

RUN make

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
