$ErrorActionPreference = "Stop"

function Esperar-Resultado {
    param([string]$EventoId)

    for ($i = 0; $i -lt 40; $i++) {
        try {
            return Invoke-RestMethod "http://localhost:8002/movimientos/$EventoId"
        }
        catch {
            if ($_.Exception.Response.StatusCode.value__ -ne 404) {
                throw
            }
        }
        Start-Sleep -Milliseconds 300
    }

    throw "El evento $EventoId no fue procesado dentro del tiempo esperado."
}

Write-Host "== Can I Park? - Demo =="
Write-Host "Registrando ENTRADA de P123456..."

$entrada = Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8001/movimientos" `
    -ContentType "application/json" `
    -Body '{"placa":"P123456","tipo":"ENTRADA"}'

$resultadoEntrada = Esperar-Resultado $entrada.evento_id
$resultadoEntrada | ConvertTo-Json

Write-Host ""
Write-Host "Disponibilidad despues de la entrada:"
Invoke-RestMethod "http://localhost:8002/disponibilidad" | ConvertTo-Json

Write-Host ""
Write-Host "Registrando SALIDA de P123456..."
$salida = Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8001/movimientos" `
    -ContentType "application/json" `
    -Body '{"placa":"P123456","tipo":"SALIDA"}'

$resultadoSalida = Esperar-Resultado $salida.evento_id
$resultadoSalida | ConvertTo-Json

Write-Host ""
Write-Host "Disponibilidad despues de la salida:"
Invoke-RestMethod "http://localhost:8002/disponibilidad" | ConvertTo-Json
