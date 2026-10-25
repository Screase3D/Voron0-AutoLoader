# Third-party notices

voron0-autoloader is licensed under the GNU General Public License v3.0 or later
(see [LICENSE](LICENSE)). It is derived in structure from, and contains approaches and code from,
[VoronV0-Zeroclick-Mainsail-UI](https://github.com/Screase3D/voronv0-zeroclick-mainsail-ui)
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

## Ideas and inspiration – nothing copied

| Project | What was taken | License |
|---|---|---|
| [fila_feeder](https://github.com/DarkK9Design/fila_feeder) by DarkK9Design | the idea for the loader hardware: NEMA17 with BMG gears, an MG90S servo pressing the idler arm, a micro switch at the entrance. The STEP/STL files of this project's own loader design will be added separately. | GPL-3.0 |
| [Happy Hare](https://github.com/moggieuk/Happy-Hare) by moggieuk | the tip-forming sequence (break-off, cooling moves with rising speed) and its default values; the macros here are written from scratch | GPL-3.0 |

## Used at runtime, not included

| Project | Use | License |
|---|---|---|
| [Klipper](https://github.com/Klipper3d/klipper) | firmware the macros run on | GPL-3.0 |
| [Moonraker](https://github.com/Arksine/moonraker) | API used by the web UI and installer, update manager | GPL-3.0 |
| [Mainsail](https://github.com/mainsail-crew/mainsail) | web interface; its stylesheets (including Vuetify, MIT) are loaded from the printer's own installation at runtime | GPL-3.0 |
| [nginx](https://nginx.org) | serves the web UI next to Mainsail | BSD-2-Clause |
