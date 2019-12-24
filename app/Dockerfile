FROM quay.io/ukhomeofficedigital/centos-base:v0.5.14

ENV USERMAP_UID 1000
ENV PYTHONPATH="$PYTHONPATH:/NATS"

# Setup folder structure and copy files
RUN mkdir -p \
             /tmp/NATS/scripts \
             /tmp/NATS/stage/nats \
             /tmp/NATS/log \
             /tmp/NATS/bin \
             /NATS

COPY packages.txt /tmp/NATS/scripts
COPY docker-entrypoint.sh /
ADD bin /tmp/NATS/bin
ADD scripts /tmp/NATS/scripts

# Add user
RUN groupadd -r runner && \
    useradd --no-log-init -u $USERMAP_UID -r -g runner runner && \
    groupadd docker && \
    usermod -aG docker runner && \
    chown -R runner:runner /NATS

# Install script dependencies
RUN yum update -y
RUN yum install -y wget make gcc openssl-devel zlib-devel pcre-devel bzip2-devel libffi-devel epel-release

# Install Python3.7.2 and pip modules
RUN cd /usr/bin && \
    wget https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tgz && \
    tar xzf Python-3.7.2.tgz && \
    cd Python-3.7.2 && \
    ./configure --enable-optimizations && \
    make altinstall && \
    alternatives --install /usr/bin/python python /usr/local/bin/python3.7 1
RUN python -m pip install --no-cache-dir -r /tmp/NATS/scripts/packages.txt

# Fix yum installer with Python3.7 running as a global default
RUN sed -i '/#!\/usr\/bin\/python/c\#!\/usr\/bin\/python2.7' /usr/bin/yum && \
    sed -i '/#! \/usr\/bin\/python/c\#! \/usr\/bin\/python2.7' /usr/libexec/urlgrabber-ext-down

VOLUME ["/NATS"]
RUN chown -R runner:runner /NATS

RUN chown runner:runner /docker-entrypoint.sh && \
chmod +x /docker-entrypoint.sh

USER ${USERMAP_UID}

WORKDIR /NATS

ENTRYPOINT ["/docker-entrypoint.sh"]

# Execute Shell Script.

CMD /NATS/bin/run_nats.sh
