# voron0-autoloader - move the loader and the extruder at the same time
#
# Copyright (C) 2026 Screase3D
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Klipper has no command that moves a manual_stepper and the extruder
# together while the nozzle is cold: G1 E is blocked below min_extrude_temp,
# and FORCE_MOVE / MANUAL_STEPPER always wait for each other, so the two
# motors would only run one after the other (the filament jams in between).
#
# This module adds
#   LOADER_DUAL_MOVE DIST=<mm> [SPEED=<mm/s>] [ACCEL=<mm/s^2>]
# Both steppers ("manual_stepper loader" and "extruder") get the same
# distance on one shared timeline - they start, accelerate and stop together.
# It is a direct stepper move like FORCE_MOVE (works with a cold nozzle,
# nothing is extruded), but it does not need [force_move] enable_force_move.
#
# Installed by ./install.sh as a symlink in ~/klipper/klippy/extras/ and
# loaded with the config section [autoloader_sync] (in the settings file).
import logging

VERSION = 1


class _StepperGroup:
    """Looks like one stepper to force_move.manual_move() and forwards every
    call to all steppers of the group - they share one trapq and so move in
    lockstep. Every stepper needs its own stepper kinematics object."""
    def __init__(self, steppers, extra_kinematics):
        self.steppers = steppers
        self.extra_kinematics = extra_kinematics

    def get_name(self, short=False):
        return "+".join(s.get_name() for s in self.steppers)

    def units_in_radians(self):
        return False

    def set_stepper_kinematics(self, sk):
        if isinstance(sk, tuple):          # restore the previous ones
            kins = sk
        else:
            kins = (sk,) + tuple(self.extra_kinematics)
        return tuple(s.set_stepper_kinematics(k) for s, k in zip(self.steppers, kins))

    def set_trapq(self, tq):
        if isinstance(tq, tuple):
            return tuple(s.set_trapq(t) for s, t in zip(self.steppers, tq))
        return tuple(s.set_trapq(tq) for s in self.steppers)

    def set_position(self, coord):
        for s in self.steppers:
            s.set_position(coord)

    def generate_steps(self, flush_time):  # only called by older Klipper versions
        for s in self.steppers:
            s.generate_steps(flush_time)


class AutoloaderSync:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.loader_name = config.get("loader_stepper", "manual_stepper loader")
        self.extruder_name = config.get("extruder_stepper", "extruder")
        self.default_accel = config.getfloat("accel", 300., above=0.)
        self.max_speed = config.getfloat("max_speed", 50., above=0.)
        self.max_dist = config.getfloat("max_distance", 200., above=0.)
        self.group = None
        self.printer.register_event_handler("klippy:connect", self._handle_connect)
        gcode = self.printer.lookup_object("gcode")
        gcode.register_command("LOADER_DUAL_MOVE", self.cmd_LOADER_DUAL_MOVE,
                               desc=self.cmd_LOADER_DUAL_MOVE_help)

    def _handle_connect(self):
        fm = self.printer.lookup_object("force_move")
        loader = fm.lookup_stepper(self.loader_name)
        extruder = fm.lookup_stepper(self.extruder_name)
        import chelper
        ffi_main, ffi_lib = chelper.get_ffi()
        sk = ffi_main.gc(ffi_lib.cartesian_stepper_alloc(b"x"), ffi_lib.free)
        self.group = _StepperGroup([loader, extruder], [sk])

    cmd_LOADER_DUAL_MOVE_help = "AutoLoader: move loader and extruder together (DIST=, SPEED=, ACCEL=)"

    def cmd_LOADER_DUAL_MOVE(self, gcmd):
        dist = gcmd.get_float("DIST")
        speed = gcmd.get_float("SPEED", 5., above=0., maxval=self.max_speed)
        accel = gcmd.get_float("ACCEL", self.default_accel, minval=0.)
        if abs(dist) > self.max_dist:
            raise gcmd.error("LOADER_DUAL_MOVE: DIST larger than max_distance (%.0f mm)" % (self.max_dist,))
        if self.group is None or not dist:
            return
        fm = self.printer.lookup_object("force_move")
        logging.info("LOADER_DUAL_MOVE dist=%.3f speed=%.3f accel=%.3f", dist, speed, accel)
        for s in self.group.steppers:
            fm._force_enable(s)
        fm.manual_move(self.group, dist, speed, accel)

    def get_status(self, eventtime):
        return {"version": VERSION}


def load_config(config):
    return AutoloaderSync(config)
