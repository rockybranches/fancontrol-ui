# AUR publication

User installation instructions and the complete maintainer workflow are in the
[AUR packaging guide](../../docs/aur-packaging.md). This file documents the
repository-specific publication setup.

Tagged releases publish `fancontrol-ui` to the Arch User Repository after the
GitHub release succeeds. The workflow downloads the immutable GitHub tag
archive, calculates its SHA-256 checksum, renders `PKGBUILD`, generates
`.SRCINFO` with Arch's `makepkg`, verifies the AUR SSH host fingerprint, and
pushes both files to the package's AUR Git repository.

## One-time setup

1. Create a dedicated SSH key for AUR publication and add its public key to the
   maintainer's AUR account.
2. Add the private key as the `AUR_SSH_PRIVATE_KEY` GitHub Actions repository
   secret. Keep the key dedicated to this repository so it can be revoked
   independently.
3. Publish a normal `v<version>` tag. The tag must match the versions in
   `pyproject.toml` and `src/fancontrol_ui/__init__.py`.

The first publication creates the `fancontrol-ui` AUR repository if the package
name is still available. The **Publish to AUR** workflow can be run manually
with an existing release tag to retry a failed publication without recreating
the GitHub release.

## Local validation

Render the template with the intended version and archive checksum, then run
these commands on Arch Linux:

```bash
makepkg --verifysource
makepkg --printsrcinfo > .SRCINFO
makepkg --cleanbuild
```

Review dependency and license changes before every release. AUR automation
does not replace the maintainer's responsibility to keep the package accurate.
