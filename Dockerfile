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
  && rm -f /app/requirements.txt



# Install application
RUN mkdir /app
COPY ./requirements.txt /app/requirements.txt
RUN \
  # Install Python dependencies
  python3 -m pip install -r /app/requirements.txt

# Install application
COPY ./src/app/* /app/

RUN \
  chmod +x /app/*


# Set the working directory
WORKDIR /app
ENV PATH="/app:${PATH}"

VOLUME [ "/backups" ]

CMD [ "python3",  "/app/backup.py" ]

COPY ./metadata.json /metadata.json
