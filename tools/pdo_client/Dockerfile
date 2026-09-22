FROM ubuntu:22.04

ARG REPOSITORY
ARG BRANCH
ARG CONTRACT_FAMILIES

ENV DEBIAN_FRONTEND=noninteractive
# Only the two roots are env (every other setup input is a script arg).
ENV PDO_CONTRACTS_ROOT=/pdo-contracts
ENV PDO_INSTALL_ROOT=/pdo_install

# Rust toolchain, in a shared location so cargo/rustup are on PATH for every
# later build layer. The rego-contract build shells out to cargo to compile the
# Regorus FFI crate to a wasm32-wasip1 staticlib, which wasm-ld then folds into
# the contract .wasm (linked against wasi-sdk-27 from install_system_deps.sh).
ENV RUSTUP_HOME=/opt/rust
ENV CARGO_HOME=/opt/cargo
ENV PATH=/opt/cargo/bin:${PATH}

WORKDIR /

# Copy the build inputs and do the heavy build first. setup/ holds the install
# steps and activate_env.sh (sourced both at build time and at runtime by the
# runners), so it stays in the image. The runtime scripts are copied last
# (below) so editing them does not invalidate these cached build layers.
COPY setup/install_system_deps.sh /setup/

RUN bash /setup/install_system_deps.sh

# Pinned to the toolchain the Regorus staticlib was validated against (cargo
# 1.95.0). wasm32-wasip1 is Rust's renamed wasm32-wasi target; its objects link
# against the wasi-sdk-27 clang output at the contract link step.
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --default-toolchain 1.95.0 --profile minimal && \
    rustup target add wasm32-wasip1

COPY setup/ /setup/
RUN bash /setup/clone_contracts.sh --repository "${REPOSITORY}" --branch "${BRANCH}"
RUN bash /setup/install_pdo_client.sh
RUN bash /setup/install_contracts.sh --families "${CONTRACT_FAMILIES}"

RUN rm -rf ${PDO_INSTALL_ROOT}/opt/pdo/keys/*

# Webapp dependencies, installed into the PDO client virtualenv. requirements
# are copied alone so editing the webapp source does not bust this pip layer.
COPY webapp/requirements.txt /tmp/webapp-requirements.txt
RUN ${PDO_INSTALL_ROOT}/bin/pip install -r /tmp/webapp-requirements.txt

# Runtime code last: editing it only rebuilds from these layers down.
COPY scripts/ /scripts/
COPY webapp/ /webapp/

# Non-root user + group 0 access on the build outputs and runtime code so any
# host uid can read/write mounted volumes when launched with `--user $(id -u):0`.
# New files written at runtime inherit gid 0 from the process's egid.
RUN useradd -m -u 1000 pdo_user && \
    chgrp -R 0 ${PDO_INSTALL_ROOT}/opt/pdo ${PDO_CONTRACTS_ROOT}/rego-contract/test /scripts /webapp && \
    chmod -R g=u ${PDO_INSTALL_ROOT}/opt/pdo ${PDO_CONTRACTS_ROOT}/rego-contract/test /scripts /webapp

USER 1000:0

# bash is the entrypoint; CMD is the runner (+ args) to execute. The default
# runs the CLI test. run_python.sh overrides the CMD with run_python.sh, and
# the webapp's run_docker.sh overrides it with /webapp/run.sh.
ENTRYPOINT ["bash"]
CMD ["/scripts/run_cli.sh"]
