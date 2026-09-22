set -e
# Build and install the PDO client, plus the jupyter tooling.
: "${PDO_INSTALL_ROOT:?Missing environment variable PDO_INSTALL_ROOT}"
: "${PDO_CONTRACTS_ROOT:?Missing environment variable PDO_CONTRACTS_ROOT}"
export PDO_SOURCE_ROOT=${PDO_CONTRACTS_ROOT}/private-data-objects

source ${PDO_SOURCE_ROOT}/build/common-config.sh

# The client/python Makefiles install pdo_client and pdo_common_library with
# `setup.py install`, which names the egg-info directory after the current
# version instead of replacing the previous one. As the private-data-objects
# version advances, stale egg-info dirs from earlier builds pile up alongside
# the fresh one, and pip's dependency resolver picks an older installed
# version, causing spurious version-mismatch failures for anything that
# depends on pdo-client. Clear them out so only the build below remains.

if [ -f ${PDO_INSTALL_ROOT}/bin/python ]; then
    SITE_PACKAGES=$(${PDO_INSTALL_ROOT}/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
    rm -rf ${SITE_PACKAGES}/pdo_client-*-py*.egg-info ${SITE_PACKAGES}/pdo_client-*-py*-nspkg.pth
    rm -rf ${SITE_PACKAGES}/pdo_common_library-*-py*.egg-info ${SITE_PACKAGES}/pdo_common_library-*-py*-nspkg.pth
fi

make -C ${PDO_SOURCE_ROOT}/build client
${PDO_INSTALL_ROOT}/bin/pip install jupyterlab papermill ipywidgets jupytext
# Fix lmdb issue
${PDO_INSTALL_ROOT}/bin/pip install lmdb==1.7.5
