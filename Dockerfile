FROM mcr.microsoft.com/azure-cli:cbl-mariner2.0

LABEL org.opencontainers.image.description="Azure Backup Container"

USER root

# Install dependencies
RUN \
  # Install and Update Python/pip
  tdnf install -y python3 python3-pip \
  && python3 -m pip install --upgrade pip \
  # Clean up
  && rm -rf /var/lib/apt/lists/* \
  && rm -f /scripts/requirements.txt



# Install application
RUN mkdir /scripts
COPY ./requirements.txt /scripts/requirements.txt
RUN \
  # Install Python dependencies
  python3 -m pip install -r /scripts/requirements.txt

# Install Scripts
COPY ./src/scripts/* /scripts/

RUN \
  chmod +x /scripts/*


# Set the working directory
WORKDIR /scripts
ENV PATH="/scripts:${PATH}"

VOLUME [ "/backups" ]

CMD [ "python3",  "/scripts/backup.py" ]

COPY ./metadata.json /metadata.json
