# Release verification (w18.2+)

A release bundle is the repository tree at an immutable `w*` tag:

```
release/MANIFEST.json          # integrity root: tag, commit, files[{path,sha256,bytes}]
release/MANIFEST.json.sigstore # optional Sigstore bundle (attestation job)
release/MANIFEST.sha256        # sha256sum-format line for the manifest
vibeweaver/                    # the installed payload
vibeweaver-mini/               # the mini profile payload
```

Paths in `MANIFEST.json` are relative to the bundle root. `vibeweaver/install.sh`
verifies the manifest **before copying any file**; a release bundle with a
missing/broken manifest is refused (`--no-verify` is development-only).

## Consumer commands

```bash
# 1) Corrupt-detection only (trust boundary: the digest must come from an
#    independent channel — a sha256 shipped in the same bundle proves nothing
#    against replacement).
sha256sum -c release/MANIFEST.sha256

# 2) Full file-by-file verification (canonical, no extra tooling).
python3 scripts/verify_release.py --root . --manifest release/MANIFEST.json
# MANIFEST OK N/N

# 3) Signature / provenance (attestation job output).
cosign verify-blob \
  --bundle release/MANIFEST.json.sigstore \
  --certificate-identity-regexp 'https://github.com/logandoo/vibeweaver/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  release/MANIFEST.json

gh attestation verify release/MANIFEST.json --owner logandoo
```

Only (2)+(3) together bind content to a builder identity. A bare
`sha256sum -c` detects accidental corruption, **not** a substituted bundle.

## Maintainer commands

```bash
python3 scripts/make_release_manifest.py --root . --tag w18.2 \
  --commit "$(git rev-parse HEAD)"
python3 scripts/verify_release.py --root . --tag w18.2
```

The tag must be created on the public release commit and never moved; release
assets are immutable (`w18`, `w18.1` are historical and untouched).
