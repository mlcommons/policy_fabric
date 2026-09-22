ARG PDO_CLIENT_IMAGE
FROM $PDO_CLIENT_IMAGE

USER root
# Install guardian core and FL client dependencies
COPY requirements.txt /project/requirements.txt
RUN ${PDO_INSTALL_ROOT}/bin/pip install -r /project/requirements.txt

# Install the guardian core operation and the FL client as modules
COPY . /project/inference_guardian
RUN ${PDO_INSTALL_ROOT}/bin/pip install -e /project/inference_guardian

# Configure guardian service to use the new operation
RUN chgrp -R 0 /project && \
    chmod -R g=u /project
USER 1000:0


ENTRYPOINT [ "bash", "/project/inference_guardian/start_services.sh" ]
