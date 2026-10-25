"""Translation of the installer output (German is the source text).

tr() replaces known German phrases with English when LANG == "en".
Variable parts (paths, numbers, names) stay unchanged.

SPDX-License-Identifier: GPL-3.0-or-later
"""
import os
import re

LANG = "de"

# (German, English) - applied sorted by length, longest first
PHRASES = [
    # headings
    ("voronv0-filament-loader – Filament Loader für Voron V0.2", "voronv0-filament-loader – filament loader for Voron V0.2"),
    ("Umgebung", "Environment"), ("Installationsstand", "Installation state"), ("Voraussetzungen", "Prerequisites"),
    ("Konflikte", "Conflicts"), ("Einstellungen", "Settings"), ("Geplante Änderungen", "Planned changes"),
    ("Installation", "Installation"), ("Deinstallation", "Uninstall"), ("Fertig", "Done"),
    # analysis
    ("Config-Ordner:  ", "Config folder:  "), ("Dienst ", "Service "), ("nicht gefunden", "not found"),
    ("Symlink aufs Repo", "symlink to the repo"),
    ("alte Einzeldatei (wird ersetzt, Werte werden übernommen)", "old single file (will be replaced, values are kept)"),
    ("Includes in printer.cfg: ", "Includes in printer.cfg: "), ("unvollständig", "incomplete"), ("vollständig", "complete"),
    ("Web-Oberfläche in nginx: ", "Web UI in nginx: "), ("eingebunden", "included"),
    ("Menüeintrag in Mainsail: ", "Menu entry in Mainsail: "), ("eingetragen", "registered"),
    ("Update-Manager: ", "Update manager: "), ("KlipperScreen-Menü: ", "KlipperScreen menu: "),
    ("Include nicht gefunden:", "Include not found:"), ("Datei nicht lesbar:", "File not readable:"),
    ("fehlt (kommt normalerweise aus mainsail.cfg)", "missing (normally comes from mainsail.cfg)"),
    ("vorhanden", "present"),
    (" – wird auskommentiert", " – will be commented out"),
    ("Zeile ", "line "),
    # questions
    ("Sprache / Language", "Language / Sprache"),
    ("Enter übernimmt den Vorschlag in [Klammern]. Alles weitere stellst du später in der Web-Oberfläche ein.",
     "Enter accepts the suggestion in [brackets]. Everything else can be set later in the web UI."),
    ("Sprache der Klipper-Meldungen (de/en)", "Language of the Klipper messages (de/en)"),
    ("Bitte de oder en eingeben.", "Please enter de or en."),
    ("Stepper step_pin", "Stepper step_pin"), ("Stepper dir_pin (! = invertiert)", "Stepper dir_pin (! = inverted)"),
    ("Stepper enable_pin", "Stepper enable_pin"), ("Servo-Pin", "Servo pin"),
    ("Sensor 1 (Loader-Eingang), Öffner", "Sensor 1 (loader entrance), normally closed"),
    ("Sensor 2 (Toolhead-Eingang) ist verdrahtet und soll aktiv sein?", "Is sensor 2 (toolhead entrance) wired and should it be active?"),
    ("Sensor 2 Pin (MCU-Name:gpioX), Öffner", "Sensor 2 pin (MCU name:gpioX), normally closed"),
    ("Loader-Menü in KlipperScreen einbinden (Mehr → Loader)?", "Add the Loader menu to KlipperScreen (More → Loader)?"),
    ("existiert – Werte neu abfragen und Datei neu erzeugen?", "exists – ask for the values again and regenerate the file?"),
    ("Fortfahren?", "Continue?"), ("Abgebrochen.", "Aborted."),
    ("printer.cfg nicht gefunden – mit --config-dir angeben.", "printer.cfg not found – specify it with --config-dir."),
    ("Wert erforderlich.", "Value required."),
    # planned / actions
    ("Backup des Config-Ordners nach", "Backup of the config folder to"),
    ("Includes in printer.cfg ergänzen", "Add includes to printer.cfg"),
    ("Web-Oberfläche in nginx einbinden und Menüeintrag in Mainsail anlegen", "Include the web UI in nginx and add a menu entry to Mainsail"),
    ("Update-Manager in moonraker.conf eintragen (falls per git clone installiert)", "Register the update manager in moonraker.conf (if installed via git clone)"),
    ("KlipperScreen-Menü einbinden und KlipperScreen neu starten", "Add the KlipperScreen menu and restart KlipperScreen"),
    ("Klipper neu starten", "Restart Klipper"),
    ("neu erzeugen", "regenerate"),
    ("Backup: ", "Backup: "), ("gesichert als", "saved as"), ("verlinkt", "linked"), ("geschrieben", "written"),
    ("auskommentiert", "commented out"), ("wiederhergestellt", "restored"),
    ("bitte manuell entfernen", "please remove manually"),
    ("liegt außerhalb des Config-Ordners", "is outside the config folder"),
    ("wird auch von", "is also used by"), ("benutzt – bitte prüfen", "– please check"),
    ("Includes in printer.cfg eingetragen", "Includes added to printer.cfg"),
    ("Includes aus printer.cfg entfernt", "Includes removed from printer.cfg"),
    ("nginx-Site von Mainsail nicht gefunden – Web-Oberfläche übersprungen", "Mainsail's nginx site not found – web UI skipped"),
    ("Kein server-Block in", "No server block in"), ("bitte 'include", "please add 'include"), ("manuell eintragen", "manually"),
    ("nginx-Binary nicht gefunden – Test und Reload übersprungen", "nginx binary not found – test and reload skipped"),
    ("nginx-Test fehlgeschlagen, Änderung wird zurückgenommen:", "nginx test failed, reverting the change:"),
    ("Web-Oberfläche in nginx eingebunden", "Web UI included in nginx"), (" und ", " and "),
    ("ist für nginx nicht betretbar – ggf.", "is not accessible for nginx – maybe run"),
    ("nginx-Eintrag entfernt", "nginx entry removed"),
    ("ist kein gültiges JSON-Array – Menüeintrag übersprungen", "is not a valid JSON array – menu entry skipped"),
    ("Menüeintrag 'Loader' in Mainsail angelegt (Browser neu laden)", "Menu entry 'Loader' added to Mainsail (reload the browser)"),
    ("Menüeintrag entfernt", "Menu entry removed"),
    ("moonraker.conf nicht gefunden – Update-Manager übersprungen", "moonraker.conf not found – update manager skipped"),
    ("Repo hat keinen git-origin (nicht per git clone installiert) – Update-Manager übersprungen",
     "Repo has no git origin (not installed via git clone) – update manager skipped"),
    ("Update-Manager in moonraker.conf eingetragen", "Update manager registered in moonraker.conf"),
    ("Update-Manager-Eintrag entfernt", "Update manager entry removed"),
    ("KlipperScreen neu gestartet", "KlipperScreen restarted"),
    ("KlipperScreen bitte neu starten, damit die Änderung wirkt", "Please restart KlipperScreen for the change to take effect"),
    ("KlipperScreen-Menü eingebunden (Mehr → Loader)", "KlipperScreen menu added (More → Loader)"),
    ("KlipperScreen-Menü auf die Sprache der Klipper-Meldungen umgestellt (wirkt nach Neustart von KlipperScreen)",
     "KlipperScreen menu switched to the language of the Klipper messages (takes effect after restarting KlipperScreen)"),
    ("KlipperScreen-Menü entfernt", "KlipperScreen menu removed"),
    ("Es läuft ein Druck – Neustart übersprungen. Danach RESTART ausführen.", "A print is running – restart skipped. Run RESTART afterwards."),
    ("Moonraker nicht erreichbar – bitte Klipper manuell neu starten (RESTART)", "Moonraker not reachable – please restart Klipper manually (RESTART)"),
    ("Moonraker wird neu gestartet", "Moonraker is restarting"),
    ("Moonraker-Neustart fehlgeschlagen – bitte manuell neu starten", "Moonraker restart failed – please restart manually"),
    ("Klipper-Neustart über Moonraker fehlgeschlagen – bitte RESTART ausführen", "Klipper restart via Moonraker failed – please run RESTART"),
    ("Warte auf Klipper ...", "Waiting for Klipper ..."), ("Klipper ist bereit", "Klipper is ready"),
    ("Klipper meldet einen Fehler:", "Klipper reports an error:"),
    ("Klipper ist nach 30 s noch nicht bereit – Status in Mainsail prüfen", "Klipper is not ready after 30 s – check the status in Mainsail"),
    ("Befehl fehlgeschlagen:", "Command failed:"),
    ("Installation unvollständig – Backup liegt in", "Installation incomplete – backup is in"),
    # next steps
    ("Nächste Schritte (Mainsail → Loader, oder in der Konsole):", "Next steps (Mainsail → Loader, or in the console):"),
    ("– Sensor 1 prüfen (Filament einlegen/entfernen)", "– check sensor 1 (insert/remove filament)"),
    ("– Drehrichtung und rotation_distance prüfen", "– check direction and rotation_distance"),
    ("Servo-Winkel klemmen/frei am Aufbau ermitteln und in den Einstellungen speichern",
     "Find the servo angles for clamped/free on the rig and save them in the settings"),
    ("Am Voron: tube_len, gear_offset, ext_to_nozzle messen, Sensor 2 aktivieren, Bench-Modus aus",
     "On the Voron: measure tube_len, gear_offset, ext_to_nozzle, enable sensor 2, bench mode off"),
    ("Bei Problemen: Backup liegt in", "In case of problems: the backup is in"), ("Deinstallation mit", "uninstall with"),
    # uninstall
    ("voronv0-filament-loader entfernen?", "Remove voronv0-filament-loader?"),
    ("-Symlink entfernt", " symlink removed"), ("gelöscht", "deleted"), ("löschen?", "delete?"),
    ("(Nein = behalten für spätere Neuinstallation)", "(No = keep for a later reinstall)"),
    ("Vom Installer auskommentierte Sections wiederherstellen?", "Restore sections commented out by the installer?"),
    ("Auskommentierte Zeilen in", "Commented-out lines in"),
    ("schreibe ", "write "), ("entferne ", "remove "), ("Backup nach ", "backup to "),
]
PHRASES.sort(key=lambda p: -len(p[0]))

# sentences with a different word order in English
RULES = [
    (r"^alte (\S+) umbenennen in (\S+)$", r"Rename old \1 to \2"),
    (r"^(\S+) als Symlink aufs Repo anlegen$", r"Create \1 as symlink to the repo"),
    (r"^(\S+) anlegen$", r"Create \1"),
    (r"^(\S+) neu erzeugen$", r"Regenerate \1"),
    (r"^\[(.+)\] in (\S+) auskommentieren$", r"Comment out [\1] in \2"),
    (r"^\[(.+)\] in (\S+) auskommentiert$", r"[\1] in \2 commented out"),
    (r"^alte (\S+) gesichert als (\S+)$", r"old \1 saved as \2"),
    (r"^(\S+) existiert – Werte neu abfragen", r"\1 exists – ask for the values again"),
    (r"^Pin (\S+) wird auch von \[(.+)\] \((.+)\) benutzt – bitte prüfen$", r"Pin \1 is also used by [\2] (\3) – please check"),
]

WORDS = {"fehlt": "missing", "vorhanden": "present", "nein": "no", "keine": "none"}


def tr(text):
    if LANG != "en" or not isinstance(text, str):
        return text
    for rx, rep in RULES:
        text = re.sub(rx, rep, text)
    for de, en in PHRASES:
        if de in text:
            text = text.replace(de, en)
    return text


def default_lang():
    for var in ("LOADER_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v:
            return "de" if v.lower().startswith("de") else "en"
    return "en"
