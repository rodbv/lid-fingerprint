# Contributing

## Setup

```
uv sync
uv run pre-commit install
```

## Checks

```
uv run pre-commit run --all-files   # ruff, ruff format, shellcheck, file hygiene
uv run pytest
```

The tests do not need root or PyQt6. They patch a copy of the Fedora `local` authselect profile in `tests/fixtures/local` and feed fake lid and PAM files to the tray state logic.

## Run the tray icon from the checkout

```
python3 src/fingerprint_tray.py
```

Use the system `python3`, which has PyQt6 from `python3-pyqt6`. The icons must be installed in `~/.local/share/icons/hicolor/scalable/status` (`install.sh` does that). If you change an icon name, pick one whose dash-separated prefixes match no icon in Breeze or Papirus: Qt and KDE remove the last dash part of a missing name and use the first match they find before they reach `hicolor`.

## Regenerate the README preview

```
python3 scripts/render-icon-preview.py
```

The script writes `docs/icons.png` with the three tray states on a dark and a light panel. Open the image and compare it with the icons in your panel before you commit it.
