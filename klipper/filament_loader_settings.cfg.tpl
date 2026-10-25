#@schema 1
# =====================================================================
# voronv0-filament-loader - Einstellungen (vom Installer erzeugt)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Diese Datei gehoert dir: der Installer ueberschreibt sie nie ohne Rueckfrage,
# Updates ueber den Update-Manager fassen sie nicht an. Bearbeiten in der
# Web-Oberflaeche (Mainsail -> Loader -> Einstellungen) oder von Hand.
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
velocity: ${velocity}
accel: ${accel}

[tmc2209 manual_stepper loader]
uart_pin: ${uart_pin}                # gemeinsamer UART-Bus des Pico
tx_pin: ${tx_pin}
uart_address: ${uart_address}              # E0-Treiber
run_current: ${run_current}
stealthchop_threshold: 999999

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
variable_speed: ${speed}               # mm/s Normalfoerderung
variable_slow_speed: ${slow_speed}          # mm/s Feinanfahrt / Uebergabe
variable_step_mm: ${step_mm}              # mm pro Schritt bei der Sensor-Abfrage (Rekursion!)
variable_coarse_len: ${coarse_len}         # mm ohne Sensorabfrage (muss kleiner als tube_len sein)
variable_tube_len: ${tube_len}           # mm Loader-Zahnraeder -> Toolhead-Sensor
variable_overrun: ${overrun}             # mm Reserve bis Timeout
# --- Toolhead ---
variable_gear_offset: ${gear_offset}          # mm Toolhead-Sensor -> Extruder-Zahnraeder
variable_gear_push: ${gear_push}            # mm Loader schiebt ueber die Zahnraeder hinaus
variable_ext_to_nozzle: ${ext_to_nozzle}       # mm Extruder-Zahnraeder -> Duese (inkl. Cold-End)
variable_ext_speed: ${ext_speed}            # mm/s Extruder beim Laden
variable_purge_len: ${purge_len}          # mm Ausspuelen nach dem Laden
variable_purge_speed: ${purge_speed}          # mm/s
variable_default_temp: ${default_temp}      # Standard-Duesentemperatur
# --- Entladen ---
variable_unload_ext_len: ${unload_ext_len}      # mm Extruder zieht zurueck (Spitze bleibt in den Zahnraedern)
variable_unload_hold: ${unload_hold}         # mm Spitze bleibt im Loader-Griff
# --- Auto-Trigger ---
variable_auto_delay: ${auto_delay}         # s Zeit zum Nachschieben, bevor der Loader klemmt
variable_bench_mode: ${bench_mode}          # 1 = Auto-Trigger macht nur den Bench-Test (klemmen, bench_dist fahren, loesen)
variable_bench_dist: ${bench_dist}          # mm im Bench-Test
gcode:
