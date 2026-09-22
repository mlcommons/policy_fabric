# dev — mock inference guardian

Answers `POST /process_capability` like the real inference guardian: allowed when
the capability's `script_digest` equals the `calculated_script_digest` the caller
reports, `422` otherwise.

    ./build.sh && ./run.sh --port 7900 &
    ./capability_generator.sh sha256:abc                # -> ./capability.b64
    ./redeem.py -f ./capability.b64 -c sha256:abc       # 200; any other -c -> 422
