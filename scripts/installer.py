#!/usr/bin/env python3
"""voron0-autoloader - analysis, installation and removal.

Called via ./install.sh. Needs only the Python standard library.
Structure and approach follow the voron0-dockprobe installer
(https://github.com/Screase3D/VoronV0-Zeroclick-Mainsail-UI).

SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from string import Template

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n  # noqa: E402
from i18n import tr  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
LOGIC_SRC = REPO_DIR / "klipper" / "filament_loader.cfg"
SETTINGS_TPL = REPO_DIR / "klipper" / "filament_loader_settings.cfg.tpl"
WEB_DIR = REPO_DIR / "web"
KS_DIR = REPO_DIR / "klipperscreen"

LOGIC_NAME = "filament_loader.cfg"
SETTINGS_NAME = "filament_loader_settings.cfg"
MARK = "#loader# "          # prefix for lines the installer commented out
OFF = "#off# "              # prefix for lines of a deactivated section (Sensor 2)
NGINX_SNIPPET = os.environ.get("AUTOLOADER_NGINX_SNIPPET", "/etc/nginx/snippets/autoloader.conf")
NGINX_TAG = "# autoloader"
NAVI_HREF = "/server/autoloader/"
OLD_HREFS = ("/autoloader/", "/autoloader", "/server/autoloader/", "/server/autoloader")
UM_SECTION = "update_manager voron0-autoloader"
MOONRAKER = os.environ.get("AUTOLOADER_MOONRAKER", "http://127.0.0.1:7125")
BACKUP_DIR = "autoloader-backups"

KS_NAME = "autoloader_klipperscreen.conf"
KS_INCLUDE = f"[include {KS_NAME}]"
KS_CREATED = "# created by voron0-autoloader"

SETTINGS_SCHEMA = 6  # matches "#@schema" in filament_loader_settings.cfg.tpl
TOOL_SECTION = "filament_switch_sensor toolhead_in"

# icon: Material Design Icons "printer-3d-nozzle" (Pictogrammers, Apache-2.0)
NAVI_ICON = "M7,2H17V8H19V13H16.5L13,17H11L7.5,13H5V8H7V2M10,22H2V20H10A1,1 0 0,0 11,19V18H13V19A3,3 0 0,1 10,22Z"

# our config sections: (section name, option(s) that carry a pin)
OWN_SECTIONS = [
    "manual_stepper loader", "tmc2209 manual_stepper loader", "servo loader_clamp",
    "filament_switch_sensor loader_in", TOOL_SECTION,
]
PIN_KEYS = ("step_pin", "dir_pin", "enable_pin", "pin", "switch_pin", "endstop_pin")

# (key, section, option) - the settings file fields; defaults for the BTT SKR Pico V1.0 + Nitehawk-SB
FIELDS = [
    ("step_pin", "manual_stepper loader", "step_pin"),
    ("dir_pin", "manual_stepper loader", "dir_pin"),
    ("enable_pin", "manual_stepper loader", "enable_pin"),
    ("microsteps", "manual_stepper loader", "microsteps"),
    ("rotation_distance", "manual_stepper loader", "rotation_distance"),
    ("velocity", "manual_stepper loader", "velocity"),
    ("accel", "manual_stepper loader", "accel"),
    ("uart_pin", "tmc2209 manual_stepper loader", "uart_pin"),
    ("tx_pin", "tmc2209 manual_stepper loader", "tx_pin"),
    ("uart_address", "tmc2209 manual_stepper loader", "uart_address"),
    ("run_current", "tmc2209 manual_stepper loader", "run_current"),
    ("stealth_speed", "tmc2209 manual_stepper loader", "stealthchop_threshold"),
    ("servo_pin", "servo loader_clamp", "pin"),
    ("loader_in_pin", "filament_switch_sensor loader_in", "switch_pin"),
    ("toolhead_in_pin", TOOL_SECTION, "switch_pin"),
] + [(k, "gcode_macro _loader_vars", "variable_" + k) for k in (
    "lang", "servo_clamp", "servo_release", "servo_settle", "servo_off_released", "speed", "slow_speed",
    "step_mm", "approach", "tube_len", "overrun", "gear_offset", "gear_push", "ext_to_nozzle", "ext_speed",
    "purge_len", "purge_speed", "default_temp", "unload_ext_len", "unload_hold", "auto_delay", "bench_mode",
    "bench_dist", "tip_enable", "tip_ram_len", "tip_temp", "tip_speed_start", "tip_speed", "tip_cool_pos",
    "tip_cool_len", "tip_cool_moves", "tip_cool_start", "tip_cool_end", "tip_eject_speed", "print_start_mode",
    "print_end_action", "park_dist", "auto_enable", "auto_target", "heater_off", "slip_warn")]
NEW_VARS_V2 = ["slip_warn", "park_dist", "print_end_action", "auto_enable", "auto_target", "heater_off", "approach", "tip_enable", "tip_ram_len", "tip_temp", "tip_speed_start", "tip_speed", "tip_cool_pos", "tip_cool_len",
               "tip_cool_moves", "tip_cool_start", "tip_cool_end", "tip_eject_speed", "print_start_mode"]

HOOK_TAG = "# autoloader"
HOOK_START = "LOADER_PRINT_START  # autoloader: load filament if the toolhead is empty"
HOOK_END = "LOADER_PRINT_END  # autoloader: optional unload after the print"
HOOK_RE = re.compile(r"^\s*LOADER_PRINT_(START|END)\b.*#\s*autoloader")
HEAT_RE = re.compile(r"^\s*(M109\b|TEMPERATURE_WAIT\s+SENSOR=extruder\b)", re.I)
OFF_RE = re.compile(r"^\s*TURN_OFF_HEATERS\b", re.I)

DEFAULTS = {
    "step_pin": "gpio14", "dir_pin": "!gpio13", "enable_pin": "!gpio15", "microsteps": "16",
    "rotation_distance": "22.99646", "velocity": "150", "accel": "500",
    "uart_pin": "gpio9", "tx_pin": "gpio8", "uart_address": "3", "run_current": "0.6", "stealth_speed": "60",
    "servo_pin": "gpio29", "loader_in_pin": "^gpio16", "toolhead_in_pin": "^nhk:gpio12",
    "lang": "de", "servo_clamp": "45", "servo_release": "170", "servo_settle": "0.5", "servo_off_released": "1",
    "speed": "150", "slow_speed": "30", "step_mm": "2", "approach": "30", "tube_len": "300", "overrun": "40",
    "gear_offset": "8", "gear_push": "3", "ext_to_nozzle": "70", "ext_speed": "5", "purge_len": "30",
    "purge_speed": "3", "default_temp": "220", "unload_ext_len": "65", "unload_hold": "15", "auto_delay": "2.0",
    "bench_mode": "1", "bench_dist": "50",
    "tip_enable": "1", "tip_ram_len": "0", "tip_temp": "0", "tip_speed_start": "80", "tip_speed": "18",
    "tip_cool_pos": "35", "tip_cool_len": "10", "tip_cool_moves": "4", "tip_cool_start": "10", "tip_cool_end": "50",
    "tip_eject_speed": "25", "print_start_mode": "2", "print_end_action": "0", "park_dist": "20",
    "auto_enable": "1", "auto_target": "cold", "heater_off": "1", "slip_warn": "10",
}

QUOTED = {"lang", "auto_target"}   # string variables, written with quotes
LEGACY_KEYS = {"step_pin", "dir_pin", "enable_pin", "microsteps", "rotation_distance", "uart_pin", "tx_pin", "uart_address",
               "servo_pin", "loader_in_pin", "toolhead_in_pin", "servo_clamp", "servo_release", "tube_len", "gear_offset",
               "gear_push", "ext_to_nozzle", "unload_ext_len", "unload_hold", "default_temp"}

SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*(?:[#;].*)?$")
OPTION_RE = re.compile(r"^([A-Za-z0-9_]+)\s*[:=]\s*(.*?)\s*$")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
USE_COLOR = sys.stdout.isatty()


def c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def head(text):
    print("\n" + c("1;36", f"== {tr(text)} =="))


def ok(text):
    print("  " + c("32", "✔ ") + tr(text))


def warn(text):
    print("  " + c("33", "! ") + tr(text))


def err(text):
    print("  " + c("31", "✘ ") + tr(text))


def info(text):
    print("  " + tr(text))


def strip_comment(v):
    return re.split(r"\s[#;]", v, maxsplit=1)[0].strip()


def norm_pin(p):
    return re.sub(r"^[\^~!]+", "", str(p).strip()).replace("!", "").lower()


# ---------------------------------------------------------------------------
# Reading Klipper config
# ---------------------------------------------------------------------------
class Section:
    def __init__(self, name, file, start):
        self.name, self.file, self.start, self.end = name, file, start, None
        self.options = {}

    @property
    def lname(self):
        return self.name.lower()


def parse_config(printer_cfg):
    ctx = {"sections": [], "missing": [], "unreadable": []}
    _parse_file(Path(printer_cfg), ctx, 0)
    return ctx


def _parse_file(path, ctx, depth):
    if depth > 8:
        return
    try:
        lines = path.read_text(errors="replace").split("\n")
    except OSError:
        ctx["unreadable"].append(str(path))
        return
    cur = None
    for i, raw in enumerate(lines):
        if raw.startswith("#*#"):
            break
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith(("#", ";")):
            continue
        m = SECTION_RE.match(line)
        if m:
            if cur is not None:
                cur.end = i
            name = m.group(1).strip()
            if name.lower().startswith("include "):
                pat = name[8:].strip()
                pat = pat if os.path.isabs(pat) else str(path.parent / pat)
                hits = sorted(glob.glob(pat))
                if not hits:
                    ctx["missing"].append(name[8:].strip())
                for h in hits:
                    _parse_file(Path(h), ctx, depth + 1)
                if cur is not None:
                    cur.end = i
                cur = None
                continue
            cur = Section(name, str(path), i)
            ctx["sections"].append(cur)
            continue
        o = OPTION_RE.match(line) if not line[0].isspace() else None
        if o and cur is not None:
            cur.options[o.group(1).lower()] = strip_comment(o.group(2))
    if cur is not None and cur.end is None:
        cur.end = len(lines)


def has_section(ctx, name):
    return any(s.lname == name.lower() for s in ctx["sections"])


def read_values(path):
    """{section(lower): {option: value}} + set of deactivated sections from a loader cfg."""
    vals, off, cur = {}, set(), None
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return vals, off
    for raw in text.split("\n"):
        if raw.startswith("#*#"):
            break
        is_off = raw.startswith(OFF)
        line = raw[len(OFF):] if is_off else raw
        m = SECTION_RE.match(line)
        if m:
            cur = m.group(1).strip().lower()
            vals.setdefault(cur, {})
            if is_off:
                off.add(cur)
            continue
        o = OPTION_RE.match(line) if line and not line[0].isspace() and not line.startswith("#") else None
        if o and cur:
            vals[cur][o.group(1).lower()] = strip_comment(o.group(2))
    return vals, off


def own_logic_sections():
    try:
        return {m.group(1).strip().lower() for l in LOGIC_SRC.read_text().split("\n") if (m := SECTION_RE.match(l))}
    except OSError:
        return set()


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
def detect(args):
    home = Path.home()
    env = {"home": home}
    if args.config_dir:
        cfg = Path(args.config_dir).expanduser().resolve()
    else:
        cfg = next((p for p in (home / "printer_data/config", home / "klipper_config")
                    if (p / "printer.cfg").exists()), None)
    env["cfg"] = cfg
    env["printer_cfg"] = cfg / "printer.cfg" if cfg else None
    env["moonraker_conf"] = cfg / "moonraker.conf" if cfg and (cfg / "moonraker.conf").exists() else None
    if args.nginx_site:
        env["nginx_site"] = Path(args.nginx_site)
    else:
        env["nginx_site"] = next((Path(os.path.realpath(p)) for p in
                                  ("/etc/nginx/sites-available/mainsail", "/etc/nginx/sites-enabled/mainsail")
                                  if os.path.exists(p)), None)
    env["nginx_bin"] = shutil.which("nginx") or ("/usr/sbin/nginx" if os.path.exists("/usr/sbin/nginx") else None)
    env["systemctl"] = shutil.which("systemctl")
    return env


def service_state(env, name):
    if not env["systemctl"]:
        return "?"
    r = subprocess.run([env["systemctl"], "is-active", name], capture_output=True, text=True)
    return r.stdout.strip() or "?"


def git_origin():
    r = subprocess.run(["git", "-C", str(REPO_DIR), "remote", "get-url", "origin"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def git_branch():
    r = subprocess.run(["git", "-C", str(REPO_DIR), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    b = r.stdout.strip()
    return b if r.returncode == 0 and b and b != "HEAD" else "main"


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def analyze(env):
    cfg = env["cfg"]
    ctx = parse_config(env["printer_cfg"])
    A = {"ctx": ctx}
    logic, settings = cfg / LOGIC_NAME, cfg / SETTINGS_NAME
    A["logic_linked"] = logic.is_symlink() and os.path.realpath(logic) == str(LOGIC_SRC)
    A["legacy_logic"] = logic.exists() and not logic.is_symlink()
    A["settings_exists"] = settings.exists()
    printer_text = env["printer_cfg"].read_text(errors="replace")
    A["has_inc_logic"] = bool(re.search(rf"^\[include\s+{re.escape(LOGIC_NAME)}\s*\]", printer_text, re.M))
    A["has_inc_settings"] = bool(re.search(rf"^\[include\s+{re.escape(SETTINGS_NAME)}\s*\]", printer_text, re.M))

    # sections of ours that live in other files (not the settings file / the old single file)
    ours = {s.lower() for s in OWN_SECTIONS} | own_logic_sections()
    skip = {os.path.realpath(settings), os.path.realpath(logic)}
    A["conflicts"] = [s for s in ctx["sections"] if s.lname in ours and os.path.realpath(s.file) not in skip]

    # other sensors on the pins we are going to use (e.g. the old filament sensor)
    A["mcus"] = [s.name.split(None, 1)[1] for s in ctx["sections"] if s.lname.startswith("mcu ")]
    A["has_respond"] = has_section(ctx, "respond")
    A["has_pause"] = has_section(ctx, "pause_resume")
    A["ks_conf"] = cfg / "KlipperScreen.conf"
    A["ks_present"] = A["ks_conf"].exists() or (env["home"] / "KlipperScreen").is_dir()
    A["ks_menu"] = (cfg / KS_NAME).exists() or (A["ks_conf"].exists() and KS_INCLUDE in A["ks_conf"].read_text(errors="replace"))
    A["web_nginx"] = bool(env["nginx_site"] and env["nginx_site"].exists() and NGINX_SNIPPET in env["nginx_site"].read_text(errors="replace"))
    navi = cfg / ".theme" / "navi.json"
    A["navi"] = navi.exists() and any(h in navi.read_text(errors="replace") for h in OLD_HREFS)
    A["save_vars_elsewhere"] = any(sec.lname == "save_variables" and os.path.realpath(sec.file) != os.path.realpath(settings)
                                   for sec in ctx["sections"])
    A["um"] = bool(env["moonraker_conf"] and f"[{UM_SECTION}]" in env["moonraker_conf"].read_text(errors="replace"))
    return A


def pin_users(A, pins):
    """Other sections that use one of the pins: [(section, option, pin)]"""
    wanted = {norm_pin(p): p for p in pins if p}
    own = {s.lower() for s in OWN_SECTIONS}
    out = []
    for s in A["ctx"]["sections"]:
        if s.lname in own:
            continue
        for k, v in s.options.items():
            if k in PIN_KEYS and norm_pin(v) in wanted:
                out.append((s, k, v))
    return out


def report(env, A):
    head("Umgebung")
    info(f"Config-Ordner:  {env['cfg']}")
    for svc in ("klipper", "moonraker", "nginx"):
        info(f"Dienst {svc}: {service_state(env, svc)}")
    head("Installationsstand")
    info(f"{LOGIC_NAME}: " + ("Symlink aufs Repo" if A["logic_linked"] else
                              "alte Einzeldatei (wird ersetzt, Werte werden übernommen)" if A["legacy_logic"] else "nicht gefunden"))
    info(f"{SETTINGS_NAME}: " + ("vorhanden" if A["settings_exists"] else "nicht gefunden"))
    info("Includes in printer.cfg: " + ("vollständig" if A["has_inc_logic"] and A["has_inc_settings"] else "unvollständig"))
    info("Web-Oberfläche in nginx: " + ("eingebunden" if A["web_nginx"] else "nicht gefunden"))
    info("Menüeintrag in Mainsail: " + ("eingetragen" if A["navi"] else "nicht gefunden"))
    info("Update-Manager: " + ("eingetragen" if A["um"] else "nicht gefunden"))
    if A["ks_present"]:
        info("KlipperScreen-Menü: " + ("eingebunden" if A["ks_menu"] else "nicht gefunden"))
    if A["ctx"]["missing"]:
        for m in A["ctx"]["missing"]:
            warn(f"Include nicht gefunden: {m}")
    for m in A["ctx"]["unreadable"]:
        warn(f"Datei nicht lesbar: {m}")
    head("Voraussetzungen")
    for name, present in (("respond", A["has_respond"]), ("pause_resume", A["has_pause"])):
        (ok if present else warn)(f"[{name}] " + ("vorhanden" if present else "fehlt (kommt normalerweise aus mainsail.cfg)"))
    if A["mcus"]:
        info("MCUs: " + ", ".join(["mcu"] + A["mcus"]))
    if A["conflicts"]:
        head("Konflikte")
        for s in A["conflicts"]:
            warn(f"[{s.name}] in {os.path.basename(s.file)} (Zeile {s.start + 1}) – wird auskommentiert")


# ---------------------------------------------------------------------------
# PRINT_START / PRINT_END hooks
# ---------------------------------------------------------------------------
def macro_body(ctx, cfg, name):
    """(file, [line indices of the gcode body]) of a gcode_macro inside the config folder"""
    sec = next((s for s in ctx["sections"] if s.lname == f"gcode_macro {name}"), None)
    if not sec:
        return None, None, None
    inside = os.path.realpath(sec.file).startswith(str(cfg) + os.sep)
    lines = Path(sec.file).read_text(errors="replace").split("\n")
    return sec, inside, lines


def hook_plan(ctx, cfg):
    plan = {}
    for kind, names, rx, before in (("start", ("print_start", "start_print"), HEAT_RE, False),
                                    ("end", ("print_end", "end_print"), OFF_RE, True)):
        sec = inside = lines = None
        for n in names:
            sec, inside, lines = macro_body(ctx, cfg, n)
            if sec:
                break
        p = {"found": bool(sec), "name": sec.name.split()[1].upper() if sec else names[0].upper(), "inside": inside}
        if sec:
            body = range(sec.start + 1, sec.end)
            p["file"] = sec.file
            p["present"] = any(HOOK_RE.match(lines[i]) for i in body if i < len(lines))
            idx = next((i for i in body if i < len(lines) and rx.match(lines[i])), None)
            p["line"] = idx
            if idx is not None:
                p["indent"] = re.match(r"^(\s*)", lines[idx]).group(1) or "  "
                p["ref"] = lines[idx].strip()
                p["before"] = before
        plan[kind] = p
    return plan


def hooks_install(env, ops):
    plan = hook_plan(parse_config(env["printer_cfg"]), env["cfg"])
    for kind, text in (("start", HOOK_START), ("end", HOOK_END)):
        p = plan[kind]
        if not p["found"] or p.get("present") or not p["inside"] or p.get("line") is None:
            continue
        lines = Path(p["file"]).read_text(errors="replace").split("\n")
        at = p["line"] if p["before"] else p["line"] + 1
        lines.insert(at, p["indent"] + text)
        ops.write(p["file"], "\n".join(lines))
        ok(f"{text.split()[0]} in {p['name']} eingefügt ({os.path.basename(p['file'])}:{at + 1})")


def hooks_remove(cfg, ops):
    for f in sorted(set(glob.glob(str(cfg / "**/*.cfg"), recursive=True))):
        if os.path.islink(f):
            continue
        text = Path(f).read_text(errors="replace")
        if "LOADER_PRINT_" not in text:
            continue
        lines = text.split("\n")
        kept = [l for l in lines if not HOOK_RE.match(l)]
        if len(kept) != len(lines):
            ops.write(f, "\n".join(kept))
            ok(f"Druck-Hooks aus {os.path.basename(f)} entfernt")


def save_vars_block(env, A):
    """[save_variables] for the persistent filament position – only if the printer has none yet"""
    if A["save_vars_elsewhere"]:
        return "# [save_variables] ist bereits in deiner Konfiguration vorhanden – die Position wird dort mitgespeichert"
    return ("# Filament-Position ueber Neustarts und Ausschalten merken\n"
            f"[save_variables]\nfilename: {env['cfg']}/autoloader_variables.cfg")


def upgrade_settings(env, A, ops):
    """add variables introduced by newer versions to an existing settings file (values stay untouched)"""
    path = env["cfg"] / SETTINGS_NAME
    if not path.exists():
        return
    lines = path.read_text(errors="replace").split("\n")
    vals, _ = read_values(path)
    have = vals.get("gcode_macro _loader_vars", {})
    missing = [k for k in NEW_VARS_V2 if "variable_" + k not in have]
    add_sv = not A["save_vars_elsewhere"] and "save_variables" not in vals
    if not missing and not add_sv:
        return
    if add_sv:
        lines += ["", save_vars_block(env, A)]
        ok("[save_variables] ergänzt – die Filament-Position wird jetzt dauerhaft gespeichert")
    if not missing:
        ops.write(path, "\n".join(lines))
        return
    defaults = dict(DEFAULTS)
    if str(have.get("variable_unload_after_print", "0")).strip() == "1":
        defaults["print_end_action"] = "2"      # old option "unload after the print"
    idx = next((i for i, l in enumerate(lines) if SECTION_RE.match(l) and SECTION_RE.match(l).group(1).strip().lower() == "gcode_macro _loader_vars"), None)
    if idx is None:
        warn(f"[gcode_macro _LOADER_VARS] fehlt in {SETTINGS_NAME} – neue Einstellungen übersprungen")
        return
    end = next((i for i in range(idx + 1, len(lines)) if lines[i].startswith("gcode:") or SECTION_RE.match(lines[i])), len(lines))
    lines[end:end] = [f"variable_{k}: " + (f'"{defaults[k]}"' if k in QUOTED else defaults[k]) for k in missing]
    lines = [re.sub(r"^#@schema\s+\d+", f"#@schema {SETTINGS_SCHEMA}", l) for l in lines]
    ops.write(path, "\n".join(lines))
    ok(f"{len(missing)} neue Einstellungen in {SETTINGS_NAME} ergänzt (neue Funktionen)")


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------
class Asker:
    def __init__(self, yes):
        self.interactive = not yes and sys.stdin.isatty()

    def ask(self, prompt, default, kind="str"):
        prompt = tr(prompt)
        if kind == "bool":
            yes, no = ("j", "n") if i18n.LANG == "de" else ("y", "n")
            shown = yes if default else no
        else:
            shown = "" if default is None else str(default)
        if not self.interactive:
            info(f"{prompt}: {shown}")
            return default
        while True:
            raw = input(f"  {prompt} [{shown}]: ").strip()
            if not raw:
                return default
            if kind == "bool":
                return raw.lower() in ("j", "ja", "y", "yes", "1", "true")
            if kind == "lang" and raw.lower() not in ("de", "en"):
                print("    " + tr("Bitte de oder en eingeben."))
                continue
            return raw

    def confirm(self, prompt, default=True):
        if not self.interactive:
            return default
        yes = "J" if i18n.LANG == "de" else "Y"
        d = f"{yes}/n" if default else f"{yes.lower()}/N"
        raw = input(f"  {tr(prompt)} [{d}]: ").strip().lower()
        return default if not raw else raw in ("j", "ja", "y", "yes")


def existing_values(env, A):
    """Defaults: previous settings file > old single file > built-in defaults. Returns (values, tool_on)."""
    cfg = env["cfg"]
    values, tool_on = dict(DEFAULTS), False
    if A["mcus"]:
        values["toolhead_in_pin"] = f"^{A['mcus'][0]}:gpio12"
    for src in (cfg / f"{LOGIC_NAME}.old", cfg / LOGIC_NAME if A["legacy_logic"] else None, cfg / SETTINGS_NAME):
        if not src or not Path(src).exists():
            continue
        vals, off = read_values(src)
        legacy = src.name != SETTINGS_NAME
        for key, sec, opt in FIELDS:
            if legacy and key not in LEGACY_KEYS:
                continue      # old single file: take over calibrated values only, new defaults for speeds
            v = vals.get(sec, {}).get(opt)
            if v not in (None, ""):
                values[key] = v.strip("\"'") if key in QUOTED else v
        if TOOL_SECTION in vals:
            tool_on = TOOL_SECTION not in off
    return values, tool_on


def gather(env, A, asker):
    V, tool_on = existing_values(env, A)
    head("Einstellungen")
    info("Enter übernimmt den Vorschlag in [Klammern]. Alles weitere stellst du später in der Web-Oberfläche ein.")
    V["lang"] = asker.ask("Sprache der Klipper-Meldungen (de/en)", V["lang"] if A["settings_exists"] else i18n.LANG, "lang")
    for key, prompt in (("step_pin", "Stepper step_pin"), ("dir_pin", "Stepper dir_pin (! = invertiert)"),
                        ("enable_pin", "Stepper enable_pin"), ("servo_pin", "Servo-Pin"),
                        ("loader_in_pin", "Sensor 1 (Loader-Eingang), Öffner")):
        V[key] = asker.ask(prompt, V[key])
    tool_on = asker.ask("Sensor 2 (Toolhead-Eingang) ist verdrahtet und soll aktiv sein?", tool_on, "bool")
    if tool_on:
        V["toolhead_in_pin"] = asker.ask("Sensor 2 Pin (MCU-Name:gpioX), Öffner", V["toolhead_in_pin"])
    V["tool"] = "" if tool_on else OFF
    V["save_vars"] = save_vars_block(env, A)
    return V


def render_settings(V):
    text = Template(SETTINGS_TPL.read_text()).safe_substitute(V)
    return text if text.endswith("\n") else text + "\n"


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------
class Ops:
    def __init__(self, dry, use_sudo=True):
        self.dry, self.use_sudo = dry, use_sudo

    def write(self, path, content, root=False):
        path = Path(path)
        if self.dry:
            info(c("2", f"[dry-run] schreibe {path}"))
            return
        if root and not self._writable(path):
            subprocess.run(["sudo", "tee", str(path)], input=content, text=True, stdout=subprocess.DEVNULL, check=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def remove(self, path, root=False):
        path = Path(path)
        if not (path.exists() or path.is_symlink()):
            return
        if self.dry:
            info(c("2", f"[dry-run] entferne {path}"))
            return
        if root and not os.access(path.parent, os.W_OK):
            subprocess.run(["sudo", "rm", "-f", str(path)], check=True)
        else:
            path.unlink()

    def run_root(self, cmd):
        if self.dry:
            info(c("2", "[dry-run] " + " ".join(cmd)))
            return subprocess.CompletedProcess(cmd, 0, "", "")
        full = cmd if os.geteuid() == 0 or not self.use_sudo else ["sudo"] + cmd
        return subprocess.run(full, capture_output=True, text=True)

    @staticmethod
    def _writable(path):
        if path.exists():
            return os.access(path, os.W_OK)
        return os.access(path.parent, os.W_OK) if path.parent.exists() else False


def backup(env, ops):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = env["home"] / BACKUP_DIR
    target = bdir / f"config-{ts}.tar.gz"
    if ops.dry:
        info(c("2", f"[dry-run] Backup nach {target}"))
        return target
    bdir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, "w:gz") as tar:
        tar.add(env["cfg"], arcname="config", filter=lambda ti: None if ti.name.endswith((".gcode", ".zip")) else ti)
    site = env["nginx_site"]
    if site and site.exists():
        try:
            shutil.copy2(site, bdir / f"nginx-{site.name}-{ts}")
        except OSError:
            pass
    return target


def comment_sections(sections, ops):
    by_file = {}
    for s in sections:
        by_file.setdefault(s.file, []).append(s)
    for f, secs in by_file.items():
        lines = Path(f).read_text(errors="replace").split("\n")
        for s in secs:
            for i in range(s.start, s.end):
                if not lines[i].startswith(MARK) and not lines[i].startswith("#*#"):
                    lines[i] = MARK + lines[i]
        ops.write(f, "\n".join(lines))
        for s in secs:
            ok(f"[{s.name}] in {os.path.basename(f)} auskommentiert")


def uncomment_all(cfg, ops):
    n = 0
    for f in sorted(set(glob.glob(str(cfg / "**/*.cfg"), recursive=True))):
        if os.path.islink(f):
            continue
        text = Path(f).read_text(errors="replace")
        if MARK not in text:
            continue
        ops.write(f, "\n".join(l[len(MARK):] if l.startswith(MARK) else l for l in text.split("\n")))
        n += 1
        ok(f"Auskommentierte Zeilen in {os.path.basename(f)} wiederhergestellt")
    return n


def add_includes(printer_cfg, A, ops):
    new = []
    if not A["has_inc_settings"]:
        new.append(f"[include {SETTINGS_NAME}]")
    if not A["has_inc_logic"]:
        new.append(f"[include {LOGIC_NAME}]")
    if not new:
        return
    lines = printer_cfg.read_text(errors="replace").split("\n")
    idx = next((i for i, l in enumerate(lines) if l.startswith("[")), len(lines))
    lines[idx:idx] = new + [""]
    ops.write(printer_cfg, "\n".join(lines))
    ok("Includes in printer.cfg eingetragen")


def remove_includes(printer_cfg, ops, names=(LOGIC_NAME, SETTINGS_NAME)):
    lines = printer_cfg.read_text(errors="replace").split("\n")
    pat = re.compile(r"^\[include\s+(" + "|".join(re.escape(n) for n in names) + r")\s*\]")
    kept, dropped = [], False
    for l in lines:
        if pat.match(l):
            dropped = True
            continue
        if dropped and l.strip() == "":  # blank line add_includes put after the include block
            dropped = False
            continue
        dropped = False
        kept.append(l)
    if len(kept) != len(lines):
        ops.write(printer_cfg, "\n".join(kept))
        ok("Includes aus printer.cfg entfernt")


# ---- nginx ----------------------------------------------------------------
def nginx_snippet():
    return (f"# voron0-autoloader - web UI (generated automatically)\n"
            f"location = /autoloader {{ return 301 /autoloader/; }}\n"
            f"location ^~ /autoloader/ {{\n"
            f"    alias {WEB_DIR}/;\n"
            f"    index index.html;\n"
            f"    add_header Cache-Control \"no-cache\";\n"
            f"}}\n"
            f"# Mainsail's service worker does not intercept /server/ (matters for https)\n"
            f"location = /server/autoloader {{ return 301 /server/autoloader/; }}\n"
            f"location ^~ /server/autoloader/ {{\n"
            f"    alias {WEB_DIR}/;\n"
            f"    index index.html;\n"
            f"    add_header Cache-Control \"no-cache\";\n"
            f"}}\n")


def nginx_install(env, ops):
    site = env["nginx_site"]
    if not site or not site.exists():
        warn("nginx-Site von Mainsail nicht gefunden – Web-Oberfläche übersprungen")
        return False
    snip_dir = os.path.dirname(NGINX_SNIPPET)
    if not os.path.isdir(snip_dir):
        ops.run_root(["mkdir", "-p", snip_dir])
    ops.write(NGINX_SNIPPET, nginx_snippet(), root=True)
    text = site.read_text(errors="replace")
    if NGINX_SNIPPET not in text:
        lines = text.split("\n")
        idx = next((i for i, l in enumerate(lines) if re.match(r"^\s*server\s*\{", l)), None)
        if idx is None:
            warn(f"Kein server-Block in {site} – bitte 'include {NGINX_SNIPPET};' manuell eintragen")
            return False
        lines.insert(idx + 1, f"    include {NGINX_SNIPPET};  {NGINX_TAG}")
        ops.write(site, "\n".join(lines), root=True)
    if not env["nginx_bin"]:
        warn("nginx-Binary nicht gefunden – Test und Reload übersprungen")
        return True
    r = ops.run_root([env["nginx_bin"], "-t"])
    if r.returncode != 0:
        err("nginx-Test fehlgeschlagen, Änderung wird zurückgenommen:\n" + (r.stderr or r.stdout))
        ops.write(site, text, root=True)
        ops.remove(NGINX_SNIPPET, root=True)
        return False
    ops.run_root(["systemctl", "reload", "nginx"])
    ok("Web-Oberfläche in nginx eingebunden (/server/autoloader/ und /autoloader/)")
    if not env["home"].stat().st_mode & 0o001:
        warn(f"{env['home']} ist für nginx nicht betretbar – ggf. 'chmod o+x {env['home']}'")
    return True


def nginx_remove(env, ops):
    site = env["nginx_site"]
    if not (site and site.exists() and NGINX_SNIPPET in site.read_text(errors="replace")) and not os.path.exists(NGINX_SNIPPET):
        return
    if site and site.exists():
        text = site.read_text(errors="replace")
        if NGINX_SNIPPET in text:
            ops.write(site, "\n".join(l for l in text.split("\n") if NGINX_SNIPPET not in l), root=True)
    ops.remove(NGINX_SNIPPET, root=True)
    if env["nginx_bin"]:
        if ops.run_root([env["nginx_bin"], "-t"]).returncode == 0:
            ops.run_root(["systemctl", "reload", "nginx"])
    ok("nginx-Eintrag entfernt")


# ---- Mainsail menu ------------------------------------------------------------
def navi_install(env, ops):
    navi = env["cfg"] / ".theme" / "navi.json"
    entries = []
    if navi.exists():
        try:
            entries = json.loads(navi.read_text())
            if not isinstance(entries, list):
                raise ValueError
        except ValueError:
            warn(f"{navi} ist kein gültiges JSON-Array – Menüeintrag übersprungen")
            return
    entries = [e for e in entries if e.get("href") not in OLD_HREFS]
    entries.append({"title": "AutoLoader", "href": NAVI_HREF, "target": "_self", "position": 46, "icon": NAVI_ICON})
    ops.write(navi, json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    ok("Menüeintrag 'AutoLoader' in Mainsail angelegt (Browser neu laden)")


def navi_remove(env, ops):
    navi = env["cfg"] / ".theme" / "navi.json"
    if not navi.exists():
        return
    try:
        entries = json.loads(navi.read_text())
    except ValueError:
        return
    rest = [e for e in entries if e.get("href") not in OLD_HREFS]
    if len(rest) == len(entries):
        return
    if rest:
        ops.write(navi, json.dumps(rest, indent=2, ensure_ascii=False) + "\n")
    else:
        ops.remove(navi)
    ok("Menüeintrag entfernt")


# ---- Moonraker update_manager ------------------------------------------------
def um_install(env, ops):
    mc, origin = env["moonraker_conf"], git_origin()
    if not mc:
        warn("moonraker.conf nicht gefunden – Update-Manager übersprungen")
        return False
    if not origin:
        warn("Repo hat keinen git-origin (nicht per git clone installiert) – Update-Manager übersprungen")
        return False
    text = mc.read_text(errors="replace")
    if f"[{UM_SECTION}]" in text:
        return False
    block = (f"\n[{UM_SECTION}]\ntype: git_repo\nchannel: dev\npath: {REPO_DIR}\norigin: {origin}\n"
             f"primary_branch: {git_branch()}\nmanaged_services: klipper\ninfo_tags:\n"
             f"    desc=Voron0-AutoLoader - automatic filament loader (Voron V0.2)\n")
    ops.write(mc, text.rstrip("\n") + "\n" + block)
    ok("Update-Manager in moonraker.conf eingetragen")
    return True


def um_remove(env, ops):
    mc = env["moonraker_conf"]
    if not mc:
        return False
    out, skip, changed = [], False, False
    for l in mc.read_text(errors="replace").split("\n"):
        m = SECTION_RE.match(l)
        if m:
            skip = m.group(1).strip() == UM_SECTION
            changed |= skip
        if not skip:
            out.append(l)
    if changed:
        ops.write(mc, "\n".join(out))
        ok("Update-Manager-Eintrag entfernt")
    return changed


# ---- KlipperScreen ------------------------------------------------------------------
def ks_restart(env, ops):
    if service_state(env, "KlipperScreen") == "active":
        ops.run_root(["systemctl", "restart", "KlipperScreen"])
        ok("KlipperScreen neu gestartet")
    else:
        info("KlipperScreen bitte neu starten, damit die Änderung wirkt")


def ks_link(env, ops, lang):
    link, src = env["cfg"] / KS_NAME, KS_DIR / f"autoloader_{lang}.conf"
    if ops.dry:
        info(c("2", f"[dry-run] Symlink {link} -> {src}"))
        return
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(src)


def ks_install(env, A, ops, lang):
    conf = A["ks_conf"]
    ks_link(env, ops, lang)
    if conf.exists():
        text = conf.read_text(errors="replace")
        if KS_INCLUDE not in text:
            ops.write(conf, KS_INCLUDE + "\n" + text)
    else:
        ops.write(conf, f"{KS_CREATED}\n{KS_INCLUDE}\n")
    ok("KlipperScreen-Menü eingebunden (Mehr → AutoLoader)")
    ks_restart(env, ops)


def ks_remove(env, A, ops):
    conf, changed = A["ks_conf"], False
    if conf.exists():
        lines = conf.read_text(errors="replace").split("\n")
        kept = [l for l in lines if l.strip() != KS_INCLUDE]
        if len(kept) != len(lines):
            changed = True
            if all(l.strip() in ("", KS_CREATED) for l in kept):
                ops.remove(conf)
            else:
                ops.write(conf, "\n".join(kept))
    link = env["cfg"] / KS_NAME
    if link.is_symlink() or link.exists():
        ops.remove(link)
        changed = True
    if changed:
        ok("KlipperScreen-Menü entfernt")
        ks_restart(env, ops)


# ---- Moonraker-API ----------------------------------------------------------------
def api(method, path, timeout=5):
    req = urllib.request.Request(MOONRAKER + path, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def printer_busy():
    try:
        st = api("GET", "/printer/objects/query?print_stats")["result"]["status"]["print_stats"]["state"]
        return st in ("printing", "paused")
    except (urllib.error.URLError, KeyError, ValueError, OSError):
        return None


def restart_services(restart_moonraker, ops):
    if ops.dry:
        info(c("2", "[dry-run] Klipper-Neustart"))
        return
    busy = printer_busy()
    if busy:
        warn("Es läuft ein Druck – Neustart übersprungen. Danach RESTART ausführen.")
        return
    if busy is None:
        warn("Moonraker nicht erreichbar – bitte Klipper manuell neu starten (RESTART)")
        return
    if restart_moonraker:
        try:
            api("POST", "/machine/services/restart?service=moonraker")
            ok("Moonraker wird neu gestartet")
            time.sleep(8)
        except (urllib.error.URLError, OSError):
            warn("Moonraker-Neustart fehlgeschlagen – bitte manuell neu starten")
    try:
        api("POST", "/printer/restart")
    except (urllib.error.URLError, OSError):
        warn("Klipper-Neustart über Moonraker fehlgeschlagen – bitte RESTART ausführen")
        return
    info("Warte auf Klipper ...")
    for _ in range(30):
        time.sleep(1)
        try:
            res = api("GET", "/printer/info")["result"]
        except (urllib.error.URLError, KeyError, ValueError, OSError):
            continue
        if res.get("state") == "ready":
            ok("Klipper ist bereit")
            return
        if res.get("state") == "error":
            err("Klipper meldet einen Fehler:\n" + res.get("state_message", ""))
            return
    warn("Klipper ist nach 30 s noch nicht bereit – Status in Mainsail prüfen")


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------
def do_install(env, A, args, ops, asker):
    cfg = env["cfg"]
    write_settings = True
    if A["settings_exists"] and not args.reconfigure and not A["legacy_logic"]:
        write_settings = asker.confirm(f"{SETTINGS_NAME} existiert – Werte neu abfragen und Datei neu erzeugen?", False)

    V = None
    if write_settings:
        V = gather(env, A, asker)
        for s, k, v in pin_users(A, [V["step_pin"], V["dir_pin"], V["enable_pin"], V["servo_pin"], V["loader_in_pin"]]):
            if s.lname.startswith("filament_switch_sensor") and k == "switch_pin":
                if s not in A["conflicts"]:
                    A["conflicts"].append(s)       # old filament sensor on the pin: comment out
            else:
                warn(f"Pin {v} wird auch von [{s.name}] ({os.path.basename(s.file)}) benutzt – bitte prüfen")

    hooks = []
    plan = hook_plan(A["ctx"], cfg)
    if not args.no_hooks:
        for kind, desc in (("start", "LOADER_PRINT_START nach dem Aufheizen der Düse einfügen (lädt Filament, wenn der Toolhead leer ist)?"),
                           ("end", "LOADER_PRINT_END vor TURN_OFF_HEATERS einfügen (parkt oder entlädt nur, wenn in den Einstellungen gewählt)?")):
            p = plan[kind]
            if not p["found"] or p.get("present"):
                continue
            if not p["inside"]:
                warn(f"{p['name']} liegt außerhalb des Config-Ordners – Hook bitte manuell einfügen")
            elif p.get("line") is None:
                warn(f"{p['name']}: keine passende Stelle gefunden (M109 / TURN_OFF_HEATERS) – Hook bitte manuell einfügen")
            else:
                info(f"{p['name']}: {'vor' if p['before'] else 'nach'} „{p['ref']}“ ({os.path.basename(p['file'])}:{p['line'] + 1})")
                if asker.confirm(desc, True):
                    hooks.append(kind)
    ks = False
    if A["ks_present"] and not A["ks_menu"] and not args.no_klipperscreen:
        ks = args.klipperscreen or asker.confirm("AutoLoader-Menü in KlipperScreen einbinden (Mehr → AutoLoader)?", False)
    web = not args.no_web

    head("Geplante Änderungen")
    info(f"Backup des Config-Ordners nach ~/{BACKUP_DIR}/")
    if A["legacy_logic"]:
        info(f"alte {LOGIC_NAME} umbenennen in {LOGIC_NAME}.old")
    info(f"{LOGIC_NAME} als Symlink aufs Repo anlegen")
    if write_settings:
        info(f"{SETTINGS_NAME} " + ("neu erzeugen" if A["settings_exists"] else "anlegen"))
    for s in A["conflicts"]:
        inside = os.path.realpath(s.file).startswith(str(cfg) + os.sep)
        info(f"[{s.name}] in {os.path.basename(s.file)} auskommentieren" if inside
             else f"[{s.name}] in {s.file} – liegt außerhalb des Config-Ordners, bitte manuell entfernen")
    info("Includes in printer.cfg ergänzen")
    if hooks:
        info("Druck-Hooks in PRINT_START / PRINT_END einfügen")
    if web:
        info("Web-Oberfläche in nginx einbinden und Menüeintrag in Mainsail anlegen")
    info("Update-Manager in moonraker.conf eintragen (falls per git clone installiert)")
    if ks:
        info("KlipperScreen-Menü einbinden und KlipperScreen neu starten")
    if not args.no_restart:
        info("Klipper neu starten")
    if not asker.confirm("Fortfahren?", True):
        raise SystemExit(tr("Abgebrochen."))

    head("Installation")
    b = backup(env, ops)
    ok(f"Backup: {b}")

    if A["legacy_logic"]:
        target = cfg / f"{LOGIC_NAME}.old"
        if ops.dry:
            info(c("2", f"[dry-run] {LOGIC_NAME} -> {target.name}"))
        else:
            os.replace(cfg / LOGIC_NAME, target)
        ok(f"alte {LOGIC_NAME} gesichert als {target.name}")

    link = cfg / LOGIC_NAME
    if ops.dry:
        info(c("2", f"[dry-run] Symlink {link} -> {LOGIC_SRC}"))
    else:
        if link.is_symlink():
            link.unlink()
        link.symlink_to(LOGIC_SRC)
    ok(f"{LOGIC_NAME} verlinkt")

    if write_settings:
        if A["settings_exists"]:
            ops.write(cfg / f"{SETTINGS_NAME}.bak", (cfg / SETTINGS_NAME).read_text(errors="replace"))
        ops.write(cfg / SETTINGS_NAME, render_settings(V))
        ok(f"{SETTINGS_NAME} geschrieben")
    else:
        upgrade_settings(env, A, ops)

    inside = [s for s in A["conflicts"] if os.path.realpath(s.file).startswith(str(cfg) + os.sep)]
    if inside:
        comment_sections(inside, ops)
    for s in A["conflicts"]:
        if s not in inside:
            warn(f"[{s.name}] in {s.file} bitte manuell entfernen")

    add_includes(env["printer_cfg"], A, ops)
    if hooks:
        hooks_install(env, ops)
    if web and nginx_install(env, ops):
        navi_install(env, ops)
    um_changed = um_install(env, ops)
    lang = (V or {}).get("lang") or settings_lang(cfg) or i18n.LANG
    if ks:
        ks_install(env, A, ops, lang)
    elif A["ks_menu"]:
        link = env["cfg"] / KS_NAME
        if link.is_symlink() and os.readlink(link) != str(KS_DIR / f"autoloader_{lang}.conf"):
            ks_link(env, ops, lang)
            ok("KlipperScreen-Menü auf die Sprache der Klipper-Meldungen umgestellt (wirkt nach Neustart von KlipperScreen)")

    if not args.no_restart:
        restart_services(um_changed, ops)

    head("Fertig")
    info("Nächste Schritte (Mainsail → AutoLoader, oder in der Konsole):")
    info("  1. LOADER_STATUS            – Sensor 1 prüfen (Filament einlegen/entfernen)")
    info("  2. LOADER_MOVE DIST=100     – Drehrichtung und rotation_distance prüfen")
    info("  3. Servo-Winkel klemmen/frei am Aufbau ermitteln und in den Einstellungen speichern")
    info("  4. Am Voron: tube_len, gear_offset, ext_to_nozzle messen, Sensor 2 aktivieren, Bench-Modus aus")
    info("  5. FILAMENT_LOAD_COLD → FILAMENT_LOAD TEMP=… → FILAMENT_UNLOAD TEMP=… (mit Tip-Forming)")
    info(f"Bei Problemen: Backup liegt in {b}, Deinstallation mit ./uninstall.sh")


def settings_lang(cfg):
    try:
        m = re.search(r"^variable_lang\s*[:=]\s*[\"']?(de|en)\b", (cfg / SETTINGS_NAME).read_text(errors="replace"), re.M)
    except OSError:
        return None
    return m.group(1) if m else None


def do_uninstall(env, A, args, ops, asker):
    head("Deinstallation")
    if not asker.confirm("voron0-autoloader entfernen?", True):
        raise SystemExit(tr("Abgebrochen."))
    b = backup(env, ops)
    ok(f"Backup: {b}")
    cfg = env["cfg"]
    link = cfg / LOGIC_NAME
    old = cfg / f"{LOGIC_NAME}.old"
    restore_old = old.exists() and (link.is_symlink() or not link.exists()) and \
        asker.confirm(f"alte {LOGIC_NAME} von vor der Installation wiederherstellen?", True)
    # keep the include of the old single-file loader where it was
    remove_includes(env["printer_cfg"], ops, (SETTINGS_NAME,) if restore_old else (LOGIC_NAME, SETTINGS_NAME))
    if link.is_symlink():
        ops.remove(link)
        ok(f"{LOGIC_NAME}-Symlink entfernt")
    if restore_old:
        if ops.dry:
            info(c("2", f"[dry-run] {old.name} -> {LOGIC_NAME}"))
        else:
            os.replace(old, link)
            pc = env["printer_cfg"]
            lines = pc.read_text(errors="replace").split("\n")
            if not any(re.match(rf"^\[include\s+{re.escape(LOGIC_NAME)}\s*\]", l) for l in lines):
                idx = next((i for i, l in enumerate(lines) if l.startswith("[")), len(lines))
                lines[idx:idx] = [f"[include {LOGIC_NAME}]", ""]
                ops.write(pc, "\n".join(lines))
        ok(f"alte {LOGIC_NAME} wiederhergestellt und in printer.cfg eingebunden")
    if (cfg / SETTINGS_NAME).exists():
        if asker.confirm(f"{SETTINGS_NAME} löschen? (Nein = behalten für spätere Neuinstallation)", False):
            ops.remove(cfg / SETTINGS_NAME)
            ok(f"{SETTINGS_NAME} gelöscht")
    if asker.confirm("Vom Installer auskommentierte Sections wiederherstellen?", True):
        uncomment_all(cfg, ops)
    hooks_remove(cfg, ops)
    ks_remove(env, A, ops)
    nginx_remove(env, ops)
    navi_remove(env, ops)
    um_changed = um_remove(env, ops)
    if not args.no_restart:
        restart_services(um_changed, ops)
    head("Fertig")


def main():
    ap = argparse.ArgumentParser(description="voron0-autoloader – Installer (de/en)")
    ap.add_argument("--analyze", action="store_true", help="nur analysieren / analyse only")
    ap.add_argument("--uninstall", action="store_true", help="Paket entfernen / uninstall")
    ap.add_argument("--reconfigure", action="store_true", help="Einstellungen neu abfragen / ask for settings again")
    ap.add_argument("--yes", "-y", action="store_true", help="Vorschläge übernehmen / accept all suggestions")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen / show what would happen")
    ap.add_argument("--no-web", action="store_true", help="ohne Web-Oberfläche / without web UI")
    ap.add_argument("--no-restart", action="store_true", help="Klipper nicht neu starten / do not restart Klipper")
    ap.add_argument("--config-dir", help="Config-Ordner / config folder (~/printer_data/config)")
    ap.add_argument("--nginx-site", help="nginx-Site von Mainsail / Mainsail nginx site file")
    ap.add_argument("--lang", choices=("de", "en"), help="Sprache der Ausgaben / language")
    ap.add_argument("--no-hooks", action="store_true", help="PRINT_START/PRINT_END nicht ändern / don't touch PRINT_START/PRINT_END")
    ap.add_argument("--klipperscreen", action="store_true", help="KlipperScreen-Menü einbinden / add the KlipperScreen menu")
    ap.add_argument("--no-klipperscreen", action="store_true", help="kein KlipperScreen-Menü / no KlipperScreen menu")
    args = ap.parse_args()

    i18n.LANG = args.lang or i18n.default_lang()
    if not args.lang and not args.yes and sys.stdin.isatty():
        raw = input(f"Sprache / Language [de/en] ({i18n.LANG}): ").strip().lower()
        if raw in ("de", "en"):
            i18n.LANG = raw
    print(c("1", tr("Voron0-AutoLoader – automatischer Filament-Loader für Voron V0.2")))
    env = detect(args)
    if not env["cfg"] or not env["printer_cfg"].exists():
        raise SystemExit(tr("printer.cfg nicht gefunden – mit --config-dir angeben."))

    A = analyze(env)
    report(env, A)
    if args.analyze:
        return

    ops, asker = Ops(args.dry_run), Asker(args.yes)
    if args.uninstall:
        do_uninstall(env, A, args, ops, asker)
    else:
        do_install(env, A, args, ops, asker)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + tr("Abgebrochen."))
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        err(f"Befehl fehlgeschlagen: {e}")
        err(f"Installation unvollständig – Backup liegt in ~/{BACKUP_DIR}/")
        sys.exit(1)
