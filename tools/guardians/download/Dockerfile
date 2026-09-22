ARG PDO_CLIENT_IMAGE
FROM $PDO_CLIENT_IMAGE

USER root
# Install guardian operation dependencies
COPY requirements.txt /project/requirements.txt
RUN ${PDO_INSTALL_ROOT}/bin/pip install -r /project/requirements.txt

# Install guardian operation as a module
COPY . /project/my_guardian
RUN ${PDO_INSTALL_ROOT}/bin/pip install -e /project/my_guardian

# Configure guardian service to use the new operation
RUN chgrp -R 0 /project && \
    chmod -R g=u /project
USER 1000:0


ENTRYPOINT [ "bash", "/project/my_guardian/start_services.sh" ]
