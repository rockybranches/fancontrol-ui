# AUR packaging

Tagged releases are published to the Arch User Repository after the GitHub
release succeeds. The `Publish to AUR` workflow:

1. Verifies that the `v<version>` tag matches `pyproject.toml`.
2. Downloads the immutable GitHub tag archive and calculates its SHA-256
   checksum.
3. Renders `packaging/aur/PKGBUILD.template`.
4. Verifies the source and generates `.SRCINFO` with `makepkg`.
5. Verifies the AUR SSH host fingerprint and pushes the package metadata.

## Maintainer setup

Create a dedicated SSH key for this package, add its public key to the
maintainer's AUR account, and save the private key as the
`AUR_SSH_PRIVATE_KEY` GitHub Actions repository secret. A dedicated key can be
revoked without affecting unrelated repositories.

The first publication creates the `fancontrol-ui` AUR repository if the package
name is available. To retry publication without recreating a GitHub release,
manually run the **Publish to AUR** workflow with an existing release tag.

## Release checklist

Before tagging a release:

1. Keep the versions in `pyproject.toml` and
   `src/fancontrol_ui/__init__.py` synchronized.
2. Review runtime dependencies, build dependencies, installed assets, and
   license metadata in `packaging/aur/PKGBUILD.template`.
3. Confirm the source archive contains the desktop file, icon, and udev rules.
4. Validate the rendered package on Arch Linux.

Render the template with the intended version and archive checksum, then run:

```bash
makepkg --verifysource
makepkg --printsrcinfo > .SRCINFO
makepkg --cleanbuild
```

Inspect the resulting package contents with:

```bash
tar --list --file fancontrol-ui-*.pkg.tar.zst
```

AUR automation does not replace the maintainer's responsibility to review the
package and test it on Arch Linux before publication.
