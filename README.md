# Voron0-AutoLoader

> [!NOTE]
> **This repository was written by Claude Opus 5.5**, Anthropic's AI model – Klipper macros, installer, web UI and
> documentation. Review the macros before using them on your printer and watch the first runs with a hand on the
> emergency stop.

**Automatic filament loader for the Voron V0.2** – Klipper macros, a one-command installer and a Mainsail page that
shows where the filament is.

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
![Printer: Voron V0.2](https://img.shields.io/badge/printer-Voron%20V0.2-red)
![Klipper](https://img.shields.io/badge/firmware-Klipper-b12f35)
![Mainsail](https://img.shields.io/badge/UI-Mainsail-2196f3)
![Languages](https://img.shields.io/badge/languages-English%20%7C%20Deutsch-lightgrey)

A NEMA17 with BMG gears pushes the filament through a PTFE tube into the toolhead. An MG90S servo clamps the idler
gear only while the loader feeds, so it never fights the extruder. Two NC micro switches – at the loader entrance and
right above the extruder gears – tell Klipper where the filament is.

![The AutoLoader page inside Mainsail](docs/images/overview.png)

## Features

- **Three ways to load:**
  - *Prepare* – up to the toolhead sensor and stop. The filament is not in the extruder yet and can be pulled out by
    hand, even with the printer off.
  - *Load* – into the extruder; the extruder already turns before the tip arrives and pulls it in a few mm, even with
    a cold nozzle. Ready for the next print.
  - *Load hot* – heats up and loads to the nozzle with purge.
- **Park / unload where the filament is** – the nozzle only heats if the filament can be molten in it; prepared or
  cold-gripped filament is pulled back cold. With heat: tip forming (ERCF / Happy Hare approach).
- **Remembers the filament position** across restarts and power-off; at start-up it is checked against the sensors.
- **Fast** – 150 mm/s by default, only the last centimetres are searched slowly.
- **Slip check** – every load compares where sensor 2 triggers with where it should; slip or lost steps (e.g. with a
  heavy spool) are shown on the page and in the history.
- **Auto load** when filament is inserted (prepare, load or load hot), **print hooks** that finish loading from
  wherever the filament is, Mainsail and KlipperScreen buttons `LOAD_FILAMENT` / `UNLOAD_FILAMENT`.
- **Mainsail page** with an *Operate* mode for daily use and a separate *Setup & calibration* mode.
- **Bench mode**, English / German, updates through Moonraker's update manager.

## Screenshots

| Control | Setup & calibration | Settings |
|---|---|---|
| ![Control](docs/images/control.png) | ![Setup](docs/images/setup.png) | ![Settings](docs/images/settings.png) |

| Manual & test | Measuring | Lengths |
|---|---|---|
| ![Manual](docs/images/manual.png) | ![Measure](docs/images/measure.png) | ![Lengths](docs/images/settings-lengths.png) |

## Hardware

The loader is inspired by **[fila_feeder](https://github.com/DarkK9Design/fila_feeder)** by DarkK9Design.

> [!NOTE]
> STEP/STL files and a build guide for this loader will be added later.

| Function | Part | Default pin |
|---|---|---|
| Stepper | NEMA17 + BMG dual gear drive on the **E0** driver of the SKR Pico (TMC2209) | `gpio14` / `!gpio13` / `!gpio15`, UART addr. 3 |
| Servo | MG90S on the idler arm | `gpio29` (SERVOS header) |
| Sensor 1 | micro switch at the loader entrance, NC | `^gpio16` (E0-STOP) |
| Sensor 2 | micro switch at the toolhead entrance, NC | `^nhk:gpio12` (Nitehawk-SB) |

Tested setup: Voron V0.2, SKR Pico, Nitehawk-SB, BTT Pi, Dragon Burner V0 with Sherpa Mini and Dragon HF.
The switches use the pull-up and are not inverted (no filament = closed = low). All pins can be changed in the
installer or on the page.

## Installation

Requires Klipper, Moonraker, Mainsail and `[respond]` / `[pause_resume]` (part of `mainsail.cfg`).

```bash
cd ~ && git clone https://github.com/Screase3D/Voron0-AutoLoader.git
cd Voron0-AutoLoader
./install.sh --dry-run     # show what would happen
./install.sh               # install (no sudo – it asks itself where needed)
```

The installer backs up your config, links the macros, creates `filament_loader_settings.cfg` (yours – updates never
overwrite it), `[save_variables]` and `[force_move]`, comments out clashing sections, adds the includes and – on request – the
print hooks, the Mainsail page, the update manager entry and the KlipperScreen menu.
Options: `--analyze`, `--reconfigure`, `--yes`, `--lang de|en`, `--no-web`, `--no-hooks`, `--no-restart`,
`--no-klipperscreen`.

**Update:** Mainsail → *Update Manager* → `voron0-autoloader`, then run `./install.sh` once if the page reports new
settings. **Uninstall:** `./uninstall.sh` – restores everything the installer changed, the settings file is kept.

## First setup

Switch the page to **Setup & calibration** and follow the checklist:

1. Check sensor 1, find the servo clamp/release angles, calibrate `rotation_distance`.
2. Bench test with bench mode on (default).
3. Mount on the printer, enable sensor 2.
4. *Measure lengths*: `tube_len` (*To sensor 2*), `gear_offset` (nudge until the tip touches the gears),
   `ext_to_nozzle` (extrude until filament appears).
5. Test the tip (*Form tip*), turn bench mode off, then prepare → load → load hot → park → unload.

## How it works

**Position.** Klipper adds up every clamped loader move; sensor 2 resets it to the exact value. After every operation
the position is saved (`none`, `loader`, `tube`, `sensor2`, `gears`, `nozzle` + tip in mm). At start-up it is
compared with the sensors: filament removed or pulled back while the printer was off is detected and reported. If the
place in the tube is unknown, the next load searches sensor 2 step by step instead of the fast move.

**Prepare / load / load hot.** Clamp → full speed to `approach` mm before sensor 2 (50 mm earlier for freshly inserted
filament, in case it was pushed in by hand) → search in 5 mm steps → back a little and search again in `step_mm`
steps, so the tip is never more than `step_mm` past the sensor. *Prepare* stops a few mm past sensor 2 and releases
(`sensor2`). *Load* hands the filament over to the extruder (below) (`gears`). *Load hot* heats, does the same and
extrudes the rest of `ext_to_nozzle` plus the purge (`nozzle`). Each one continues from wherever the filament is –
from parked or prepared it only feeds the remaining distance.

**Hand-over to the extruder.** From sensor 2 on, loader and extruder move together at `grip_speed` – the extruder
gears are already turning long before the tip arrives, so it is pulled in instead of being pushed against standing
gears, however exact `gear_offset` is. They move through `gear_offset + gear_push` and another `grip_len` mm. Klipper
refuses extruder moves below `min_extrude_temp`; `FORCE_MOVE` drives the extruder stepper directly and is not limited
by that, so this works with a cold nozzle. It needs `[force_move]` with `enable_force_move: True` (the installer adds
it, and the page can add it with one click; it also enables `SET_KINEMATIC_POSITION`). The filament only moves a few mm
into the cold heatsink, nothing is extruded. The loader never pushes into stationary gears: without `[force_move]`
*Load* (cold) is refused, *Load hot* waits at sensor 2 until the nozzle is hot and then turns the extruder with `G1 E`.

**Tolerances.** In a PTFE tube with 3 mm bore the filament snakes a little, so pushing and pulling the same distance
can differ by a few mm. The macros never rely on the exact length: every load and unload is referenced at sensor 2,
after the coarse search the loader backs off until sensor 2 is really free before the fine search, the search windows
have tens of mm of reserve, and prepared filament stops only a couple of mm past sensor 2, well before the gears.

**Unload / park.** First the macros decide whether the filament can be molten in the nozzle: yes if it was loaded
hot, or if the extruder has extruded since it was prepared or gripped (`toolhead.position.e` is compared with the
value at the last position change); unknown filament at sensor 2 counts as yes.
- *In the nozzle:* heat → form the tip → extruder retracts `unload_ext_len` → loader pulls until sensor 2 is free.
  The nozzle is switched off afterwards (not during a print or pause).
- *Prepared or gripped cold:* no heating – loader and extruder pull the tip out of the extruder gears together
  (`FORCE_MOVE`), the loader pulls until sensor 2 is free.
- *In the tube:* the loader just pulls back; if the place is unknown, it first feeds to sensor 2 as a reference.

Then *park* stops `park_dist` behind sensor 2, *unload* goes back to `unload_hold` inside the loader. *Prepare* on
loaded filament also works: it pulls the filament out (hot or cold) and stops at sensor 2.

**When something goes wrong.** Every operation remembers its command and the step it is in. If it fails, the page
shows what happened, in which step (e.g. *search for sensor 2*), the likely causes, where the filament and the servo
are now, and offers *Retry*, *Retry carefully* (searches sensor 2 step by step along the whole tube) or *Retry hot*
(unload with heating), plus *OK*, which releases the servo, switches the loader motor off and checks the position
against the sensors. If Klipper itself aborts an operation (e.g. a heater error), its error message is shown.
*Reset …* (in the error, on the control panel and under *Manual & test*) is for when the filament has to come out by
hand, e.g. after a clog: it releases the servo, switches loader and extruder motor off and forgets the stored position.

![Error with retry](docs/images/error.png)

**Filament change in a pause.** Unload, insert new filament – during a pause the auto trigger always loads to the
nozzle with purge. The buttons on the page that make sense in a pause stay usable.

**Print hooks.** `LOADER_PRINT_START` (after `M109`) looks where the filament is: loaded → nothing; prepared or
gripped → loads it on to the nozzle (no purge – your purge line follows); toolhead empty → loads from the loader or
the tube (`print_start_mode` 2) or aborts the print (1). `LOADER_PRINT_END` (before `TURN_OFF_HEATERS`) does
nothing, parks or unloads (`print_end_action` 0/1/2).

**Full spools.** The loader has to accelerate the spool, and the spool keeps turning when the loader stops. A gentle
acceleration (`accel` 500 mm/s², default) avoids both and costs only a fraction of a second. Every load reports the
deviation at sensor 2 (*Deviation on the last load*): a few mm are normal, more than `slip_warn` triggers a warning.
If it grows with the speed, lower `accel` or `speed`, or check the clamp angle; if it is the same at every speed,
measure `tube_len` again. A spool holder with bearings and a light brake helps, and a straight path from the spool
into the loader. A full unload pushes about `tube_len` of filament back towards the spool – parking avoids that.

**Tip tuning.** Thin string → more cooling moves or higher `tip_cool_pos`. Blob or fat tip → lower `tip_cool_pos`
or a lower `tip_temp`. The defaults are Happy Hare's starting values.

## Macros

| Macro | Purpose |
|---|---|
| `FILAMENT_PREPARE` | prepare: up to sensor 2 (`TEMP=` only used if it has to come out of the nozzle first) |
| `FILAMENT_LOAD_COLD` / `FILAMENT_LOAD TEMP= PURGE=` | load into the extruder (cold grip) / load hot to the nozzle |
| `FILAMENT_PARK TEMP=` / `FILAMENT_UNLOAD TEMP=` | park in the tube / unload into the loader – heat only if needed |
| `LOAD_FILAMENT` / `UNLOAD_FILAMENT` | Mainsail / KlipperScreen buttons |
| `LOADER_PRINT_START` / `LOADER_PRINT_END` | print hooks |
| `LOADER_STATUS`, `LOADER_SYNC`, `LOADER_SET_POS POS=` | show / check / correct the stored position |
| `LOADER_ACK`, `LOADER_CAREFUL` | acknowledge an error / make the next sensor search careful; `HOT=1` on unload or park always heats |
| `LOADER_RESET CONFIRM=1` | when everything goes wrong (e.g. a clog): servo released, loader and extruder motor off, errors cleared, position forgotten – the filament can be pulled out by hand, the next load searches carefully |
| `LOADER_CLAMP`, `LOADER_RELEASE`, `LOADER_STOP` | servo and stepper |
| `LOADER_MOVE DIST= SPEED= CLAMP=`, `LOADER_BENCHTEST`, `LOADER_FORM_TIP TEMP=` | tests |
| `LOADER_TO_SENSOR`, `LOADER_NUDGE`, `LOADER_EXTRUDE` | measuring |

The macros refuse to run while printing, except when called by the print hooks.

**No accidental runs.** Mainsail and KlipperScreen list every macro without a leading `_`, and both have Load/Unload
buttons. Those buttons call `LOAD_FILAMENT` / `UNLOAD_FILAMENT` (Mainsail also `FILAMENT_LOAD` / `FILAMENT_UNLOAD`),
which all lead to the loader; the installer comments out older macros with these names, and the page warns if another
`LOAD_FILAMENT` / `UNLOAD_FILAMENT` further down in the config overrides them. Test and measuring macros refuse to run
without their parameters (`LOADER_MOVE DIST=`, `LOADER_TO_SENSOR COARSE=`, `LOADER_NUDGE`, `LOADER_EXTRUDE DIST=`,
`LOADER_BENCH VALUE=`, `LOADER_RESET CONFIRM=1`), `LOADER_MOVE` and the bench test refuse moves that could reach
sensor 2 or the extruder (`FORCE=1` overrides), and `LOADER_FORM_TIP` only runs with filament in the nozzle.

## Settings

Edited on the page under *Setup → Settings* (grouped, with units, explanations, presets and a lengths sketch) or
directly in `filament_loader_settings.cfg`, where every value is commented. The most important ones:

| Variable | Default | Meaning |
|---|---|---|
| `speed` / `slow_speed` | 150 / 30 | mm/s fast feed / sensor search |
| `accel` | 500 | mm/s² start and stop of the loader (gentle on full spools) |
| `tube_len` | 300 | mm loader gears → sensor 2 (measure it) |
| `gear_offset` / `gear_push` | 8 / 3 | mm sensor 2 → extruder gears / extra push |
| `grip_len` / `grip_speed` | 5 / 5 | mm the extruder pulls in after the hand-over / mm/s of the hand-over |
| `ext_to_nozzle` | 70 | mm extruder gears → nozzle |
| `approach` / `overrun` | 30 / 40 | mm where the slow search starts / timeout margin |
| `park_dist` / `unload_hold` | 20 / 15 | mm behind sensor 2 when parking / left in the loader |
| `auto_enable` / `auto_target` | 1 / "cold" | auto load and its target (`prepare` / `cold` / `hot`) |
| `print_start_mode` / `print_end_action` | 2 / 0 | print hooks (see above) |
| `slip_warn` | 10 | mm deviation at sensor 2 before a warning |

For high speeds the stepper needs SpreadCycle (`stealthchop_threshold` below the feed speed) and 0.6–0.8 A. If it
skips: lower `speed` or `accel` first, then raise `run_current`.

## Troubleshooting

- **Sensor shows filament with nothing inserted** – wiring; with NC switches a broken wire reads as "filament".
- **Loader runs backwards** – invert `dir_pin`.
- **Timeout before sensor 2** – measure `tube_len`, check friction in the tube.
- **Deviation warning** – see *Full spools* above.
- **"Sensor 2 reached during the full-speed move"** – `tube_len` too large or wrong stored position.
- **Position notice after power-on** – filament was moved while off; check it or correct it under *Manual & test*.
- **Filament stuck after unloading** – tune the tip forming.
- **"The extruder cannot turn while cold"** – `[force_move]` with `enable_force_move: True` is missing (e.g. after an
  update via the Update Manager, which doesn't run the installer). Click *Enable now* on the page, or run `./install.sh`.
- **Page not reachable** – `sudo nginx -t`, and `chmod o+x ~`.

## Credits

| Project | Author | Relation |
|---|---|---|
| [Claude](https://www.anthropic.com/claude) (Opus 5.5) | Anthropic | wrote the code and documentation |
| [fila_feeder](https://github.com/DarkK9Design/fila_feeder) | DarkK9Design | inspiration for the loader hardware |
| [VoronV0-Zeroclick-Mainsail-UI](https://github.com/Screase3D/voronv0-zeroclick-mainsail-ui) | Screase3D | installer and page shell are based on it |
| [Happy Hare](https://github.com/moggieuk/Happy-Hare) / [ERCF](https://github.com/Enraged-Rabbit-Community/ERCF_v2) | moggieuk / Enraged Rabbit Community | tip-forming sequence and defaults |
| [Voron V0](https://github.com/VoronDesign/Voron-0) | Voron Design | the printer |
| [Klipper](https://github.com/Klipper3d/klipper), [Moonraker](https://github.com/Arksine/moonraker), [Mainsail](https://github.com/mainsail-crew/mainsail) | their authors and contributors | firmware, API, web interface |
| [Material Design Icons](https://pictogrammers.com/library/mdi/) | Pictogrammers | icons |

This project is not affiliated with or endorsed by any of the projects above.

## License

GPL-3.0-or-later – see [LICENSE](LICENSE). Details in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
