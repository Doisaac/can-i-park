$ErrorActionPreference = "Stop"

function Ejecutar-Docker {
    param([string[]]$Argumentos)

    & docker @Argumentos
    if ($LASTEXITCODE -ne 0) {
        throw "Docker fallo al ejecutar: docker $($Argumentos -join ' ')"
    }
}

Write-Host "== 0. Verificando Docker =="
Ejecutar-Docker @("info")

Write-Host "== 1. Construyendo entorno reproducible de pruebas =="
Ejecutar-Docker @("compose", "--profile", "tools", "build", "pruebas")

Write-Host "== 2. Validacion de sintaxis dentro de Docker =="
Ejecutar-Docker @("compose", "--profile", "tools", "run", "--rm", "pruebas", "python", "-m", "compileall", "-q", ".")

Write-Host "== 3. Pruebas automatizadas dentro de Docker =="
Ejecutar-Docker @("compose", "--profile", "tools", "run", "--rm", "pruebas", "python", "-m", "pytest")

Write-Host "== 4. Preparando prueba real con Kafka =="
Ejecutar-Docker @("compose", "down", "--remove-orphans")

$env:CAPACIDAD_ESTACIONAMIENTO = "3"
$env:UMBRAL_POCOS_ESPACIOS = "1"
$validacionCompleta = $false

try {
    Ejecutar-Docker @("compose", "up", "-d", "--build")

    Write-Host "== 5. Flujo real Acceso -> Kafka -> Disponibilidad =="
    Ejecutar-Docker @("compose", "--profile", "tools", "run", "--rm", "pruebas", "python", "scripts/test_e2e.py")

    Write-Host "== 6. Flujo real Disponibilidad -> Kafka -> Notificaciones =="
    Ejecutar-Docker @("compose", "--profile", "tools", "run", "--rm", "pruebas", "python", "scripts/test_notificaciones_e2e.py")

    Write-Host "== 7. Interfaz =="
    Ejecutar-Docker @("compose", "--profile", "tools", "run", "--rm", "pruebas", "python", "scripts/test_interfaz.py")

    Write-Host "== 8. Estado de contenedores durante la prueba =="
    Ejecutar-Docker @("compose", "ps")

    $validacionCompleta = $true
}
finally {
    Remove-Item Env:CAPACIDAD_ESTACIONAMIENTO -ErrorAction SilentlyContinue
    Remove-Item Env:UMBRAL_POCOS_ESPACIOS -ErrorAction SilentlyContinue

    if ($validacionCompleta) {
        Write-Host "== 9. Restaurando configuracion normal (100 / 10) =="
        Ejecutar-Docker @("compose", "down", "--remove-orphans")
        Ejecutar-Docker @("compose", "up", "-d")

        Write-Host ""
        Write-Host "VALIDACION COMPLETA: OK" -ForegroundColor Green
        Write-Host "Los contenedores quedaron nuevamente con la configuracion normal."
        Write-Host "Interfaz: http://localhost:8080"
        Write-Host "Swagger Acceso: http://localhost:8001/docs"
        Write-Host "Swagger Disponibilidad: http://localhost:8002/docs"
        Write-Host "Swagger Notificaciones: http://localhost:8003/docs"
    }
}
