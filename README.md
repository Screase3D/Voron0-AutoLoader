# voronv0-filament-loader

Automatic filament loader for a **Voron V0.2** (BTT SKR Pico, Nitehawk-SB toolhead, Klipper / Moonraker / Mainsail):
a NEMA17 with BMG gears pushes the filament through a PTFE tube to the toolhead, an MG90S servo clamps the lever,
two normally-closed micro switches detect the filament. Includes a Mainsail page for status, tests, calibration and settings.

**Deutsch:** Siehe unten – die Oberfläche und der Installer sind zweisprachig (DE/EN).

## What it does

| Function | Macro |
|---|---|
| Load cold: feed until the toolhead sensor, then past the gears, servo releases | `FILAMENT_LOAD_COLD` |
| Load hot: heat, load if needed, extrude to the nozzle, purge | `FILAMENT_LOAD TEMP=… PURGE=…` |
| Unload: heat, retract, loader pulls the filament back out | `FILAMENT_UNLOAD TEMP=…` |
| Auto trigger when filament enters sensor 1 | `FILAMENT_LOADER_AUTO` (bench test or cold load) |
| Test helpers | `LOADER_MOVE`, `LOADER_CLAMP`, `LOADER_RELEASE`, `LOADER_BENCHTEST`, `LOADER_STATUS`, `LOADER_STOP`, `LOADER_AUTO`, `LOADER_BENCH` |

The loader never fights the extruder: the servo releases after every feed, and for unloading the extruder stepper
is switched off while the loader pulls.

## Install

```bash
cd ~
git clone https://github.com/<your-user>/voronv0-filament-loader.git
cd voronv0-filament-loader
./install.sh --analyze     # look only
./install.sh --dry-run     # show what would happen
./install.sh               # install
```

The installer (Python standard library only)

- backs up the config folder to `~/filament-loader-backups/`,
- links `filament_loader.cfg` (macros) into your config as a symlink to the repo,
- creates `filament_loader_settings.cfg` (pins and parameters – **yours**, never overwritten without asking;
  values of an older single `filament_loader.cfg` are taken over),
- comments out clashing sections (e.g. an old filament sensor on the same pin),
- adds the includes, the nginx location, a Mainsail menu entry "Loader" and a Moonraker update-manager entry,
- optionally adds a KlipperScreen menu (More → Loader),
- restarts Klipper.

`./uninstall.sh` reverts everything (settings file is kept on request). Options: `--reconfigure`, `--lang en|de`, `--yes`,
`--no-web`, `--no-restart`, `--config-dir`, `--klipperscreen`.

## Wiring (defaults for BTT SKR Pico V1.0 + Nitehawk-SB)

| Part | Pin |
|---|---|
| Stepper (E0 driver, TMC2209 UART address 3) | step gpio14, dir !gpio13, enable !gpio15 |
| Servo | gpio29 (SERVOS header) |
| Sensor 1, loader entrance, NC | `^gpio16` (E0-STOP header) |
| Sensor 2, toolhead entrance, NC | `^nhk:gpio12` (check the MCU name in `nitehawk-sb.cfg`) |

Switches are **normally closed**: no filament = contact closed = pin low. Everything can be changed in the web UI.

## Commissioning order

1. `LOADER_STATUS`, insert/remove filament: sensor 1 changes.
2. Servo angles: *Manual & test → Servo*, then **Use as clamp / release angle**, save.
3. Stepper: *Calibrate stepper*: clamp, run 100 mm, measure, apply the new `rotation_distance`, save.
4. **Bench mode** (default on): the auto trigger only clamps, runs `bench_dist` and releases – safe on the table.
5. Mount on the Voron, measure `tube_len`, `gear_offset`, `ext_to_nozzle`, wire sensor 2 and enable it in the settings.
6. Turn bench mode off, then `FILAMENT_LOAD_COLD` → `FILAMENT_LOAD TEMP=…` → `FILAMENT_UNLOAD TEMP=…`.

## Web UI

Mainsail → **Loader** (`/server/loader/`). Uses Mainsail's own stylesheets and theme. Panels: status, setup checklist,
manual test (stepper + servo), stepper calibration, history (stored in Moonraker's database), settings editor
(diff dialog, `.bak`, restart) and console. The "fast switching" option keeps Mainsail loaded in the background.

## Notes

- Messages are bilingual (`variable_lang`); the language button in the UI switches them live.
- The macros block while printing; sensor 1 only triggers when no print is running.
- Hot load/unload are the least tested parts – watch the first runs with a hand on the emergency stop.

## License

GPL-3.0-or-later. Based on the structure of [VoronV0-Zeroclick-Mainsail-UI](https://github.com/Screase3D/VoronV0-Zeroclick-Mainsail-UI).
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
