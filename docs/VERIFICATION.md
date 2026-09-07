# Release verification

`tools/verify_release.py` is a read-only release verification harness. It
checks that both the target and harness checkouts are clean, runs every
unittest in verbose mode, runs the deterministic
`tools/regenerate_v04.py --check`, and compares the immutable 91-file subset
of `fixtures/v0.3-baseline-hashes.json` before and after those checks. The
remaining baseline entries are mutable documentation or implementation files;
their paths and exclusion reason are recorded in `summary.json`. It does not
run `git clean`, reset files, regenerate checked-in output, or upload a
release.

Run it locally with an explicit temporary evidence directory:

```sh
python3 -m pip install -r requirements-v04.txt
python3 tools/verify_release.py \
  --repo . \
  --output-dir "$(mktemp -d /tmp/ylsb-verification.XXXXXX)"
```

The exit status is `0` only when all checks pass, `1` when a verification
check fails, and `2` when the harness cannot be set up. The output directory
contains:

- `summary.json`: machine-readable result, UTC time, Python/platform and
  dependency versions, target and harness commit identities, dirty status,
  source tool hashes, and all check results;
- `verification.log` (also copied to `test.log`): verbose unittest names and
  stdout/stderr with exit status for each harness check;
- `junit.xml`: one testcase per harness check. The unittest count is reported
  separately as `unit_tests.count` in `summary.json`.

The target can be a separate checkout or a detached release tag. The harness
checkout is identified independently so evidence distinguishes the code that
ran the verification from the code under test:

```sh
python3 tools/verify_release.py \
  --harness-repo /path/to/current/checkout \
  --repo /tmp/ylsb-rc2-evidence \
  --output-dir /tmp/ylsb-rc2-verification
```

The GitHub Actions workflow in `.github/workflows/verify.yml` runs on pushes,
pull requests, and manual dispatch. Manual dispatch accepts an optional
`target_ref`; event commit SHA is the default. It grants only `contents: read`,
uses no secrets, and uploads the evidence directory even when verification
fails. Release upload and publication remain manual operations.

The workflow action majors and commit references were checked against the
official action repositories: [`actions/checkout`](https://github.com/actions/checkout),
[`actions/setup-python`](https://github.com/actions/setup-python), and
[`actions/upload-artifact`](https://github.com/actions/upload-artifact). It
pins `checkout` to
`d23441a48e516b6c34aea4fa41551a30e30af803` (v6), `setup-python` to
`5fda3b95a4ea91299a34e894583c3862153e4b97` (v7), and `upload-artifact` to
`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` (v7).
