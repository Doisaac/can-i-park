from __future__ import annotations

import os
import time
import urllib.request

INTERFAZ = os.getenv("INTERFAZ_URL", "http://localhost:8080")


def main() -> None:
    for _ in range(40):
        try:
            with urllib.request.urlopen(INTERFAZ, timeout=5) as response:
                contenido = response.read().decode("utf-8")
                if response.status == 200 and "Can I Park?" in contenido:
                    print("OK: la interfaz respondio correctamente.")
                    return
        except Exception:
            time.sleep(0.5)

    raise RuntimeError("La interfaz no respondio correctamente dentro del tiempo esperado.")


if __name__ == "__main__":
    main()
