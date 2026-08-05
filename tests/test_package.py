from importlib.metadata import version

from fancontrol_ui import __version__


def test_runtime_version_matches_package_metadata() -> None:
    assert __version__ == version("fancontrol-ui")
