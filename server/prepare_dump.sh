#!/bin/sh
# Empaqueta la carpeta del juego para que el runner la descargue de una sola vez.
# Uso: ./prepare_dump.sh [ruta-a-la-carpeta-del-juego]
set -eu
SRC=${1:-"/home/alioli/Documents/Project/Animal-Crossing-New-Horizons-Switch-BASE-GAME"}
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
test -d "$SRC"
tar -cf "$ROOT/dump.tar" -C "$(dirname "$SRC")" "$(basename "$SRC")"
ls -lh "$ROOT/dump.tar"
echo "Listo. Vuelve a ejecutar esto si anades el update 3.0.3 o el DLC."
