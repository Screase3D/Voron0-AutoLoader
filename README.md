# Voron0-AutoLoader

Automatic filament loader for the **Voron V0.2** – Klipper macros, a one-command installer and a
Mainsail page that shows where the filament is.

A small loader with BMG gears and a NEMA17 sits next to the printer and pushes the filament through a
PTFE tube into the toolhead. An MG90S servo presses the idler gear onto the filament while the loader
is feeding and lets go afterwards, so the loader never fights the extruder. Two normally closed micro
switches tell Klipper where the filament is: one at the loader entrance, one directly in front of the
extruder gears in the toolhead.

![Overview](docs/images/overview.png)

## Features

- **Load cold** – feeds the filament from the loader through the tube into the extruder gears.
  The hotend can stay cold.
- **Load hot** – heats the hotend, loads (if needed), extrudes to the nozzle and purges.
- **Unload** – heats, retracts with the extruder, then the loader pulls the filament back out of the toolhead.
- **Auto trigger** – push filament into the loader entrance and it gets loaded on its own.
- **Bench mode** – the auto trigger only clamps, runs a test distance and releases. Safe for testing
  the loader on the table before it is mounted.
- **Mainsail page** with a live drawing of the filament path, status, setup checklist, manual tests,
  servo-angle and `rotation_distance` calibration, history and a settings editor.
- **KlipperScreen menu** (More → AutoLoader).
- German and English – UI, installer and Klipper messages.
- Updates through Moonraker's update manager.

## Screenshots

| Feeding through the tube | Loaded to the nozzle |
|---|---|
| ![Loading](docs/images/filament-path-loading.png) | ![Loaded](docs/images/filament-path-loaded.png) |

| Manual & test | Stepper calibration | Settings |
|---|---|---|
| ![Manual](docs/images/manual.png) | ![Calibration](docs/images/calibration.png) | ![Settings](docs/images/settings.png) |

## Hardware

| Part | Notes |
|---|---|
| Printer | Voron V0.2 with BTT SKR Pico V1.0, Nitehawk-SB toolhead board, BTT Pi / CB1 |
| Loader | BMG-style dual gear drive (drive gear on the stepper, idler gear on a swing arm) |
| Stepper | NEMA17 on the free **E0** driver of the SKR Pico (TMC2209, UART) |
| Servo | MG90S, presses the idler arm |
| Sensor 1 | micro switch at the loader entrance, normally closed (NC) |
| Sensor 2 | micro switch at the toolhead entrance, a few mm above the extruder gears, NC |
| PTFE tube | loader → toolhead, about 300 mm |

### Default wiring

| Function | Board | Header | Pin |
|---|---|---|---|
| Stepper step / dir / enable | SKR Pico | E0 driver | `gpio14` / `!gpio13` / `!gpio15` |
| TMC2209 UART | SKR Pico | shared UART | `gpio9` / `gpio8`, address 3 |
| Servo signal | SKR Pico | SERVOS | `gpio29` (not `gpio21` – that is the bed heater) |
| Sensor 1 | SKR Pico | E0-STOP | `^gpio16` |
| Sensor 2 | Nitehawk-SB | IO | `^nhk:gpio12` – the MCU name must match `[mcu …]` in your `nitehawk-sb.cfg` |

Both switches are **normally closed**: no filament = contact closed = pin low. They use the pull-up
(`^`) and are **not** inverted. A broken wire therefore reads as "filament present".
All pins can be changed in the installer or later in the web UI.

## Installation

Requirements: Klipper, Moonraker, Mainsail (nginx), Python 3, and `[respond]` / `[pause_resume]`
(both come with `mainsail.cfg`).

```bash
cd ~
git clone https://github.com/Screase3D/Voron0-AutoLoader.git
cd Voron0-AutoLoader
./install.sh --analyze     # look only, changes nothing
./install.sh --dry-run     # show what would happen
./install.sh               # install
```

Do not run it with `sudo` – it asks for sudo itself where needed (nginx).

The installer

1. backs up your config folder to `~/autoloader-backups/`,
2. links `filament_loader.cfg` (the macros) into your config folder as a symlink to the repo,
3. creates `filament_loader_settings.cfg` with your pins and parameters,
4. takes over the values of an existing single-file `filament_loader.cfg` (renamed to `.old`),
5. comments out clashing sections, e.g. an old filament sensor on the same pin
   (marked with `#loader# `, restored on uninstall),
6. adds both includes to `printer.cfg`,
7. adds the web UI to nginx and a menu entry **AutoLoader** to Mainsail,
8. registers the update manager in `moonraker.conf`,
9. optionally adds the KlipperScreen menu,
10. restarts Klipper.

`filament_loader_settings.cfg` belongs to you. Updates never touch it, and the installer only
regenerates it when you confirm (or with `--reconfigure`).

### Options

| Option | Effect |
|---|---|
| `--analyze` | analyse only |
| `--dry-run` | show all changes without writing anything |
| `--reconfigure` | ask for the settings again and regenerate the settings file |
| `--yes` | accept all suggestions (non-interactive) |
| `--lang de\|en` | language of the installer and of the Klipper messages |
| `--no-web` | skip nginx and the Mainsail menu entry |
| `--no-restart` | do not restart Klipper |
| `--klipperscreen` / `--no-klipperscreen` | add / skip the KlipperScreen menu |
| `--config-dir`, `--nginx-site` | non-standard paths |

### Update and uninstall

Updates appear in Mainsail under *Machine → Update Manager* (`voron0-autoloader`) and as a notice on the
AutoLoader page.

```bash
cd ~/Voron0-AutoLoader
./uninstall.sh
```

Removes includes, symlink, nginx entry, menu entries and update manager entry, and restores the
sections the installer commented out. The settings file is kept unless you choose to delete it.

## First setup

The page has a setup checklist that ticks itself off where it can. The order:

1. **Sensor 1** – insert and remove filament, the status changes (`LOADER_STATUS`).
2. **Servo angles** – *Manual & test → Servo*: move to an angle until the idler arm presses the
   filament, then *Use as clamp angle*. Same for the release angle. Save in the settings.
3. **Stepper** – *Calibrate stepper*: mark the filament, run 100 mm, measure, enter the measured length,
   *Apply to settings*, save. If it runs backwards, invert `dir_pin` (`!`).
4. **Bench test** – with bench mode on (default), inserting filament clamps, feeds `bench_dist` and releases.
5. **Mount on the printer**, wire sensor 2 and enable it under *Settings → Hardware*.
6. **Measure** `tube_len`, `gear_offset` and `ext_to_nozzle` (see below).
7. **Turn bench mode off** – the auto trigger now loads into the extruder.
8. **Cold load → hot load → unload** – watch the first runs with a hand on the emergency stop.

## How it works

### Load cold – `FILAMENT_LOAD_COLD`

1. Servo clamps.
2. The loader feeds `coarse_len` without checking the sensor.
3. It continues in steps of `step_mm` until sensor 2 triggers (timeout after `tube_len + overrun`).
4. It pushes `gear_offset + gear_push` further, so the tip ends up between the extruder gears.
5. Servo releases, the stepper is switched off.

### Load hot – `FILAMENT_LOAD TEMP=… PURGE=…`

Starts heating first, does a cold load if sensor 2 is still empty, waits for temperature, then the
extruder pushes `ext_to_nozzle` and purges `purge_len`.

### Unload – `FILAMENT_UNLOAD TEMP=…`

Heats, the extruder retracts `unload_ext_len` (the tip stays in the extruder gears), the loader
clamps, the extruder motor is switched off, the loader pulls until sensor 2 is free and then the rest
of the tube, leaving `unload_hold` mm in the loader. The servo releases and the filament can be taken out.

### Auto trigger

`[filament_switch_sensor loader_in]` calls `FILAMENT_LOADER_AUTO` when filament is inserted. After
`auto_delay` it runs the bench test (bench mode) or a cold load. Klipper only fires `insert_gcode`
when no print is running. During a print, sensor 1 acts as runout sensor and pauses the print.
*Auto load* and *bench mode* can be toggled on the page; that lasts until the next restart. To make
it permanent, change it in the settings.

### Where is the filament?

There is no encoder, so the page combines the two sensors, the macro state and the elapsed time:

| Sensor 1 | Sensor 2 | Last operation | Shown as |
|---|---|---|---|
| – | – | – | no filament at the loader entrance |
| ✔ | – | – | in the loader gears (estimated progress through the tube while loading) |
| ✔/– | ✔ | load ok | in the extruder gears, or at the nozzle after a hot load |
| ✔/– | ✔ | error | stuck at sensor 2, in front of the extruder gears |
| ✔/– | ✔ | unknown (e.g. after restart) | at sensor 2, grip unknown |

Positions between the sensors are estimates based on the configured speeds and lengths.

## Macros

| Macro | Purpose |
|---|---|
| `FILAMENT_LOAD_COLD` | load into the extruder gears |
| `FILAMENT_LOAD TEMP= PURGE=` | load to the nozzle |
| `FILAMENT_UNLOAD TEMP=` | unload |
| `LOADER_STATUS` | print the sensor state |
| `LOADER_CLAMP ANGLE=` / `LOADER_RELEASE ANGLE=` | servo, optional angle for testing |
| `LOADER_MOVE DIST= SPEED= CLAMP=1/0` | move the loader (negative = back) |
| `LOADER_BENCHTEST DIST=` | clamp, move, release |
| `LOADER_STOP` | release and switch the stepper off |
| `LOADER_AUTO ENABLE=1/0` | auto trigger on/off until restart |
| `LOADER_BENCH VALUE=1/0` | bench mode on/off until restart |

The macros refuse to run while printing. Your own `LOAD_FILAMENT` / `UNLOAD_FILAMENT` macros are not touched.

## Settings

All values live in `filament_loader_settings.cfg` and can be edited on the page (diff preview,
previous version kept as `.bak`, Klipper restarts after saving).

| Variable | Default | Meaning |
|---|---|---|
| `servo_clamp` / `servo_release` | 45 / 170 | servo angles in degrees |
| `servo_settle` | 0.5 | s to wait after a servo move |
| `servo_off_released` | 1 | switch the servo signal off after releasing |
| `speed` / `slow_speed` | 25 / 10 | mm/s loader speed / fine speed |
| `step_mm` | 2 | mm per sensor check |
| `coarse_len` | 240 | mm fed without checking (must be shorter than `tube_len`) |
| `tube_len` | 300 | mm from the loader gears to sensor 2 |
| `overrun` | 60 | mm reserve before the timeout |
| `gear_offset` | 8 | mm from sensor 2 to the extruder gears |
| `gear_push` | 3 | mm the loader pushes beyond the gears |
| `ext_to_nozzle` | 70 | mm from the extruder gears to the nozzle |
| `ext_speed` | 5 | mm/s extruder speed while loading |
| `purge_len` / `purge_speed` | 30 / 3 | purge after loading |
| `default_temp` | 220 | °C when no `TEMP=` is given |
| `unload_ext_len` | 65 | mm the extruder retracts when unloading |
| `unload_hold` | 15 | mm of filament left in the loader after unloading |
| `auto_delay` | 2.0 | s before the auto trigger clamps |
| `bench_mode` / `bench_dist` | 1 / 50 | bench mode and its test distance |
| `lang` | de | language of the Klipper messages (`de` / `en`) |

Keep `(tube_len + overrun − coarse_len) / step_mm` below about 100. The sensor check is a chain of
macro calls, and the page warns you when you get close.

## Files

```
klipper/filament_loader.cfg               macros (symlinked, updated by the update manager)
klipper/filament_loader_settings.cfg.tpl  template for your settings file
klipperscreen/autoloader_{de,en}.conf     KlipperScreen menu
scripts/installer.py, scripts/i18n.py     installer (Python standard library only)
web/index.html                            the Mainsail page (single file)
```

The page is served at `/server/autoloader/` (and `/autoloader/`). It loads Mainsail's own
stylesheets and theme, talks to Moonraker over the websocket and keeps its history in Moonraker's
database. *Fast switching* in the sidebar keeps Mainsail loaded in the background, so moving between
pages does not reload anything.

## Troubleshooting

- **"macros not found"** on the page – run `./install.sh --analyze` and check the includes in `printer.cfg`.
- **Sensor shows filament with nothing inserted** – check the wiring; with NC switches a broken wire
  reads as "filament present". The pin must be `^pin` without `!`.
- **Unknown pin / MCU** for sensor 2 – the prefix (`nhk:`) must match the MCU name of the toolhead board.
- **Loader runs backwards** – invert `dir_pin` in the settings.
- **Timeout before sensor 2** – increase `tube_len` / `overrun`, check for friction in the tube.
- **Filament stays in front of the extruder gears** – increase `gear_push` a little, check `gear_offset`.
- **Page not reachable** – `sudo nginx -t`. The home directory must be accessible to nginx (`chmod o+x ~`).

## Safety

Hot loading and unloading heat the hotend and move the extruder. Watch the first runs and keep the
emergency stop at hand. During a print, all loader operations and the settings editor are locked.

## License

GPL-3.0-or-later – see [LICENSE](LICENSE). Installer, web UI shell and theme handling are based on
[VoronV0-Zeroclick-Mainsail-UI](https://github.com/Screase3D/VoronV0-Zeroclick-Mainsail-UI).
Icons: Material Design Icons (Apache-2.0). Details in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
