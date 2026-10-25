#!/usr/bin/env bash
# voronv0-filament-loader – uninstaller
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
exec "$(dirname "$(readlink -f "$0")")/install.sh" --uninstall "$@"
