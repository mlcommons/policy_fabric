# pdo_client_v2

Merges the old `docker_client` and `pdo_client` folders. Both ran the same
flow (build/install the PDO client + contracts, then run the rego-contract
tests) — one in Docker, one on bare metal. This folder keeps **one** copy of
each step in `scripts/` and has thin wrappers for each environment.

## Layout

```
setup/                       # build/install steps + env activation (args; the
                             # two roots PDO_INSTALL_ROOT + PDO_CONTRACTS_ROOT
                             # are env)
  install_system_deps.sh     # apt deps + wasi-sdk
  clone_contracts.sh         # clone pdo-contracts + checkout branch
  install_pdo_client.sh      # make client + jupyter + lmdb pip deps
  install_contracts.sh       # Local.cmake + make/install contracts
  setup.sh                   # install_pdo_client.sh + install_contracts.sh
  activate_env.sh            # put the PDO client env in scope (source this);
                             # lives here because install_contracts + runners use it

scripts/                     # the runners + their runtime helper (one folder)
                             # (export PDO_INSTALL_ROOT + PDO_CONTRACTS_ROOT first;
                             #  each runner checks them)
  prepare_site.sh            # copy ledger cert + site toml into PDO_HOME (args)
  run_cli.sh                 # rego-contract shell test
  run_python.sh              # rego-contract python test
  run_legacy.sh              # rego system test via `make test`
  cleanup.sh                 # remove the install + build dirs

docker/                      # containerized flow
  Dockerfile                 # COPYs setup/ + builds, then COPYs scripts/ last so
                             # editing them keeps the build cache; CMD = run_cli.sh
  build.sh                   # -i image, -r repo, -b branch (all required)
  run_cli.sh                 # mounts host files, invokes scripts/run_cli.sh in-container
  run_python.sh              # mounts host files, invokes scripts/run_python.sh in-container
  show_eservice_logs.sh      # debug helper for the services_container
```

Each `scripts/run_*.sh` exposes named args, then sources `setup/activate_env.sh`
and runs `prepare_site.sh` to do the work — arg parsing and test logic live in
the one file.

There is **one** runner per task, used by both flows: the image copies `scripts/`,
and `docker/run_*.sh` just mounts the host files and invokes the very same
`scripts/run_*.sh` inside the container (with container-internal paths). So a task
runs identically on host and in Docker.

User keys are a **prerequisite** for the python test (generate them up front
with `../generate_user_keys.sh`); the runners only run tests, never generate
keys (which keeps them runnable inside the container, where there is no docker).

## Docker flow

```bash
docker/build.sh -i mlcommons/pdo_client:latest -r <repo_url> -b <branch> -f "<families>"
# (start ledger + services first)
docker/run_cli.sh -i <image> -c <cert> -s <site.toml> -H <host> -l <ledger_url> -e <eservice_url>
# python test also needs a guardian running and pre-generated user keys:
../generate_user_keys.sh -k <keys_folder>
docker/run_python.sh -i <image> -c <cert> -s <site.toml> -H <host> -l <ledger_url> -k <keys_folder>
```

## Bare-metal flow

```bash
# one time: install system deps (root) + clone the repo
sudo bash setup/install_system_deps.sh
# point at your install + checkout, then build
export PDO_INSTALL_ROOT=/path/to/pdo_install PDO_CONTRACTS_ROOT=/path/to/pdo-contracts
setup/setup.sh -f "exchange-contract identity-contract rego-contract"
# run tests (start ledger + services, and guardian for the python test)
scripts/run_cli.sh    -c <cert> -s <site.toml> -H <host> -l <ledger_url> -e <eservice_url>
../generate_user_keys.sh -k <keys_folder>   # python test prerequisite
scripts/run_python.sh -c <cert> -s <site.toml> -H <host> -l <ledger_url> -k <keys_folder>
scripts/run_legacy.sh -c <cert> -s <site.toml> -H <host>
```

## Reconciled differences from the old folders

- **Python test path**: standardized on `rego-contract/test/python/` (the
  real dir). The old `pdo_client/python_test.sh` used `.../python_test/`, which
  does not exist.
- **Dropped** the `client_app/requirements.txt` pip install from the old
  `pdo_client/setup/install_contracts.sh` — that path does not exist in the repo.
- **Local.cmake / CONTRACT_FAMILIES** is now written in the shared
  `install_contracts.sh` for both flows (previously only the Dockerfile did it).
- `run_python.sh` now also runs `cleanup.py` (the bare-metal flow did; the old
  Docker entrypoint did not).
