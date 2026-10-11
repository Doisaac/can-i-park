#!/usr/bin/env sh
set -eu

esperar_resultado() {
  evento_id="$1"
  intento=0
  while [ "$intento" -lt 40 ]; do
    codigo="$(curl -sS -o /tmp/canipark_resultado.json -w '%{http_code}' "http://localhost:8002/movimientos/$evento_id")"
    if [ "$codigo" = "200" ]; then
      cat /tmp/canipark_resultado.json
      return 0
    fi
    if [ "$codigo" != "404" ]; then
      echo "Error consultando el evento: HTTP $codigo" >&2
      return 1
    fi
    intento=$((intento + 1))
    sleep 0.3
  done
  echo "El evento no fue procesado dentro del tiempo esperado." >&2
  return 1
}

echo "== Can I Park? - Demo =="
entrada="$(curl -sS -X POST http://localhost:8001/movimientos \
  -H 'Content-Type: application/json' \
  -d '{"placa":"P123456","tipo":"ENTRADA"}')"
echo "$entrada"
evento_entrada="$(printf '%s' "$entrada" | python3 -c 'import json,sys; print(json.load(sys.stdin)["evento_id"])')"

echo "\nResultado de la ENTRADA:"
esperar_resultado "$evento_entrada"
echo "\nDisponibilidad:"
curl -sS http://localhost:8002/disponibilidad

salida="$(curl -sS -X POST http://localhost:8001/movimientos \
  -H 'Content-Type: application/json' \
  -d '{"placa":"P123456","tipo":"SALIDA"}')"
echo "\n\n$salida"
evento_salida="$(printf '%s' "$salida" | python3 -c 'import json,sys; print(json.load(sys.stdin)["evento_id"])')"

echo "\nResultado de la SALIDA:"
esperar_resultado "$evento_salida"
echo "\nDisponibilidad final:"
curl -sS http://localhost:8002/disponibilidad
echo
