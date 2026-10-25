# Third-party notices

voronv0-filament-loader is licensed under the GNU General Public License v3.0 or later
(see [LICENSE](LICENSE)). It is derived in structure from, and contains approaches and code from,
[VoronV0-Zeroclick-Mainsail-UI](https://github.com/Screase3D/VoronV0-Zeroclick-Mainsail-UI)
(installer, nginx/Mainsail menu/update-manager integration, web UI shell, theme loading), GPL-3.0-or-later.

## Included in this repository

### Material Design Icons
- **What:** SVG path data of the icons used in `web/index.html` and the Mainsail menu icon in `scripts/installer.py`
  (from the npm package `@mdi/js` 7.4.47)
- **Copyright:** Pictogrammers (https://pictogrammers.com)
- **License:** Apache License 2.0 – full text in [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).
- **Changes:** none – only the path strings of the icons in use are embedded.

### Mainsail component styles
- **What:** a handful of component-scoped layout rules in `web/index.html` mirror Mainsail's components so that
  Mainsail's own stylesheet renders the page correctly. They are marked in the source.
- **Copyright:** mainsail-crew – https://github.com/mainsail-crew/mainsail
- **License:** GNU GPL v3.0

## Used at runtime, not included

| Project | Use | License |
|---|---|---|
| [Klipper](https://github.com/Klipper3d/klipper) | firmware the macros run on | GPL-3.0 |
| [Moonraker](https://github.com/Arksine/moonraker) | API used by the web UI and installer, update manager | GPL-3.0 |
| [Mainsail](https://github.com/mainsail-crew/mainsail) | web interface; its stylesheets (including Vuetify, MIT) are loaded from the printer's own installation at runtime | GPL-3.0 |
| [nginx](https://nginx.org) | serves the web UI next to Mainsail | BSD-2-Clause |
