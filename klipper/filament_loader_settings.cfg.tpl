#@schema 8
# =====================================================================
# voron0-autoloader - Einstellungen (vom Installer erzeugt)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Diese Datei gehoert dir: der Installer ueberschreibt sie nie ohne Rueckfrage,
# Updates ueber den Update-Manager fassen sie nicht an. Bearbeiten in der
# Web-Oberflaeche (Mainsail -> AutoLoader -> Einstellungen) oder von Hand.
# Neu erzeugen: ./install.sh --reconfigure
#
# Zeilen mit "#off# " am Anfang gehoeren zu einer deaktivierten Section
# (Sensor 2 noch nicht verdrahtet) - die Web-Oberflaeche schaltet sie um.
# =====================================================================


# ---------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------
[manual_stepper loader]
step_pin: ${step_pin}               # SKR Pico V1.0: E0-Treiber
dir_pin: ${dir_pin}                # "!" invertiert die Drehrichtung
enable_pin: ${enable_pin}
microsteps: ${microsteps}
rotation_distance: ${rotation_distance}    # mm Filament pro Motorumdrehung - mit LOADER_MOVE DIST=100 nachmessen
velocity: ${velocity}                  # Standardtempo, die Makros geben das Tempo immer selbst vor
accel: ${accel}                     # mm/s^2 - mit voller 1-kg-Rolle 500 oder weniger

[tmc2209 manual_stepper loader]
uart_pin: ${uart_pin}                # gemeinsamer UART-Bus des Pico
tx_pin: ${tx_pin}
uart_address: ${uart_address}              # E0-Treiber
run_current: ${run_current}
stealthchop_threshold: ${stealth_speed}      # mm/s: darunter leise (StealthChop), darueber kraeftig (SpreadCycle). 0 = immer SpreadCycle

[servo loader_clamp]
pin: ${servo_pin}                    # SKR Pico: SERVOS-Header. gpio21 waere der Bed-Heater!
maximum_servo_angle: 180
minimum_pulse_width: 0.001
maximum_pulse_width: 0.002
# initial_angle bewusst NICHT gesetzt -> beim Start kein Servo-Signal

# Sensor 1: Loader-Eingang. Oeffner (NC): kein Filament = Kontakt geschlossen = Pin LOW.
# Loest den Auto-Load aus.
[filament_switch_sensor loader_in]
switch_pin: ${loader_in_pin}            # "^" Pull-up, kein "!"
pause_on_runout: True               # nur waehrend eines Drucks aktiv
event_delay: 3.0
pause_delay: 0.5
insert_gcode:
    FILAMENT_LOADER_AUTO
runout_gcode:
    _LOADER_RUNOUT

# Sensor 2: Eingang des Toolhead-Extruders (am Nitehawk). Oeffner (NC) wie Sensor 1.
# Ohne Sensor 2 sind nur Servo-/Stepper-Tests und der Bench-Test moeglich.
${tool}[filament_switch_sensor toolhead_in]
${tool}switch_pin: ${toolhead_in_pin}         # MCU-Name gegen [mcu ...] in nitehawk-sb.cfg pruefen
${tool}pause_on_runout: False
${tool}event_delay: 3.0


# ---------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------
[gcode_macro _LOADER_VARS]
description: Zentrale Parameter des Filament Loaders
variable_lang: "${lang}"             # Sprache der Meldungen: "de" oder "en"
# --- Servo ---
variable_servo_clamp: ${servo_clamp}         # Winkel: Hebel gedrueckt (BMG greift)
variable_servo_release: ${servo_release}       # Winkel: Hebel frei
variable_servo_settle: ${servo_settle}       # s Wartezeit nach Servo-Bewegung
variable_servo_off_released: ${servo_off_released}   # 1 = nach Loesen Servo-Signal abschalten
# --- Loader-Stepper ---
variable_speed: ${speed}               # mm/s volle Fahrt durch den Schlauch
variable_slow_speed: ${slow_speed}          # mm/s Sensorsuche, Uebergabe an den Extruder
variable_step_mm: ${step_mm}              # mm pro Schritt bei der Sensorsuche (Genauigkeit)
variable_approach: ${approach}            # mm vor Sensor 2: ab hier Sensorsuche statt voller Fahrt
variable_tube_len: ${tube_len}           # mm Loader-Zahnraeder -> Toolhead-Sensor
variable_overrun: ${overrun}             # mm Reserve bis Timeout
variable_slip_warn: ${slip_warn}           # mm: Warnung, wenn Sensor 2 so viel spaeter kommt als erwartet (Schlupf, z. B. volle Rolle)
# --- Toolhead ---
variable_gear_offset: ${gear_offset}          # mm Toolhead-Sensor -> Extruder-Zahnraeder
variable_gear_push: ${gear_push}            # mm Loader schiebt ueber die Zahnraeder hinaus
variable_ext_to_nozzle: ${ext_to_nozzle}       # mm Extruder-Zahnraeder -> Duese (inkl. Cold-End)
variable_ext_speed: ${ext_speed}            # mm/s Extruder beim Laden
variable_grip_len: ${grip_len}            # mm: Loader und Extruder schieben gemeinsam, damit der Extruder auch kalt sicher greift (0 = aus)
variable_grip_speed: ${grip_speed}          # mm/s beim Greifen
variable_purge_len: ${purge_len}          # mm Ausspuelen nach dem Laden
variable_purge_speed: ${purge_speed}          # mm/s
variable_default_temp: ${default_temp}      # Standard-Duesentemperatur
# --- Entladen ---
variable_unload_ext_len: ${unload_ext_len}      # mm Extruder zieht insgesamt ab Duese zurueck (inkl. Tip-Forming)
variable_unload_hold: ${unload_hold}         # mm Spitze bleibt im Loader-Griff
variable_park_dist: ${park_dist}          # mm hinter Sensor 2 beim Parken (Filament bleibt im Schlauch)
# --- Auto-Trigger ---
variable_auto_enable: ${auto_enable}         # 1 = Filament am Loader-Eingang wird automatisch geladen
variable_auto_target: "${auto_target}"       # "prepare" = bis Sensor 2, "cold" = in den Extruder (greift kalt), "hot" = bis zur Duese (heizt auf)
variable_heater_off: ${heater_off}          # 1 = Duese nach Laden/Entladen ausschalten (nicht im Druck / in der Pause)
variable_auto_delay: ${auto_delay}         # s Zeit zum Nachschieben, bevor der Loader klemmt
variable_bench_mode: ${bench_mode}          # 1 = Auto-Trigger macht nur den Bench-Test (klemmen, bench_dist fahren, loesen)
variable_bench_dist: ${bench_dist}          # mm im Bench-Test
# --- Tip-Forming beim Entladen (Startwerte fuer Sherpa Mini + Dragon, nach Happy Hare) ---
variable_tip_enable: ${tip_enable}          # 1 = Spitze formen vor dem Entladen
variable_tip_ram_len: ${tip_ram_len}         # mm rammen (extrudieren) vor dem Abreissen, 0 = aus
variable_tip_temp: ${tip_temp}            # Temperatur fuer die Kuehlbewegungen (wird abgewartet), 0 = nicht aendern
variable_tip_speed_start: ${tip_speed_start}     # mm/s erstes schnelles Zurueckziehen (15 mm)
variable_tip_speed: ${tip_speed}          # mm/s weiter bis in die Kuehlzone
variable_tip_cool_pos: ${tip_cool_pos}        # mm Duese -> Mitte der Kuehlzone (Heatbreak), Dragon HF: 35
variable_tip_cool_len: ${tip_cool_len}        # mm Hoehe der Kuehlzone = Weg einer Kuehlbewegung
variable_tip_cool_moves: ${tip_cool_moves}       # Anzahl Kuehlbewegungen
variable_tip_cool_start: ${tip_cool_start}      # mm/s erste Kuehlbewegung
variable_tip_cool_end: ${tip_cool_end}        # mm/s letzte Kuehlbewegung
variable_tip_cool_pause: ${tip_cool_pause}      # s warten, bis die Spitze fest ist, 0 = aus
variable_tip_dip_pos: ${tip_dip_pos}         # Skinnydip: mm ueber der Duese kurz eintauchen (feine Haerchen), 0 = aus
variable_tip_dip_in: ${tip_dip_in}          # mm/s Skinnydip rein
variable_tip_dip_out: ${tip_dip_out}         # mm/s Skinnydip raus
variable_tip_eject_speed: ${tip_eject_speed}     # mm/s restliches Zurueckziehen bis unload_ext_len
# --- Druck-Hooks ---
variable_print_start_mode: ${print_start_mode}    # 0 = aus, 1 = nur fertig laden, was an Sensor 2 / im Extruder steht (sonst Abbruch), 2 = immer automatisch laden
variable_print_end_action: ${print_end_action}    # nach dem Druck (PRINT_END): 0 = nichts, 1 = parken, 2 = ganz entladen
gcode:

${save_vars}

${sync_module}
