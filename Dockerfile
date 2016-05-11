FROM kbase/kbase:sdkbase.latest
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

# RUN apt-get update

RUN cd /opt \
    && wget http://spades.bioinf.spbau.ru/release3.7.1/SPAdes-3.7.1-Linux.tar.gz \
    && tar -xvzf SPAdes-3.7.1-Linux.tar.gz \
    && rm SPAdes-3.7.1-Linux.tar.gz \
    && pip install psutil \
    && pip install pyyaml \
    && sudo apt-get install python-dev libffi-dev libssl-dev \
    && pip install pyopenssl ndg-httpsclient pyasn1 \
    && pip install requests --upgrade \
    && pip install 'requests[security]' --upgrade \
    && pip install ipython \
    && apt-get install nano

RUN . /kb/dev_container/user-env.sh \
    && cd /kb/dev_container/modules \
    && rm -rf kb_sdk \
    && git clone https://github.com/mrcreosote/kb_sdk -b dev-ctx_prov \
    && cd /kb/dev_container/modules/kb_sdk \
    && make \
    && make deploy \
    && echo "3"

ENV PATH $PATH:/opt/SPAdes-3.7.1-Linux/bin

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod 777 /kb/module/

WORKDIR /kb/module

RUN make

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
