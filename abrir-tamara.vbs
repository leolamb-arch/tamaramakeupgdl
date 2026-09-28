Option Explicit

Dim shell, files, folder, origin, command, script, attempt, ready, diagnostic
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
origin = "http://127.0.0.1:8765"
diagnostic = "No hay respuesta del servidor."

If Not files.FileExists(files.BuildPath(folder, "start-local.ps1")) Then
    MsgBox "Coloca Abrir-Tamara.vbs en la misma carpeta que start-local.ps1 y app.py.", 48, "Tamara"
    WScript.Quit 1
End If

If Not files.FileExists(files.BuildPath(folder, ".venv\Scripts\python.exe")) Then
    MsgBox "Primero completa la instalacion ejecutando start-local.ps1. Despues podras abrir Tamara con este acceso.", 48, "Tamara"
    WScript.Quit 1
End If

ready = ServerReady(origin)
If Not ready Then
    shell.Environment("PROCESS")("TAMARA_LAUNCH_DIR") = folder
    script = "try { ('Inicio por doble clic: ' + (Get-Date).ToString('s')) | Out-File -LiteralPath (Join-Path $env:TAMARA_LAUNCH_DIR 'tamara-inicio.log'); & (Join-Path $env:TAMARA_LAUNCH_DIR 'start-local.ps1') *>> (Join-Path $env:TAMARA_LAUNCH_DIR 'tamara-inicio.log') } catch { $_ | Out-File -Append -LiteralPath (Join-Path $env:TAMARA_LAUNCH_DIR 'tamara-inicio.log'); exit 1 }"
    command = "powershell.exe -NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -Command " & Chr(34) & script & Chr(34)
    shell.Run command, 0, False

    For attempt = 1 To 60
        WScript.Sleep 500
        If ServerReady(origin) Then
            ready = True
            Exit For
        End If
    Next
End If

If ready Then
    shell.Run origin & "/login?inicio=" & CStr(CLng(Timer)), 1, False
Else
    MsgBox "No se abrio el navegador porque el servidor de Tamara no esta listo." & vbCrLf & diagnostic & vbCrLf & "Revisa tamara-inicio.log en:" & vbCrLf & folder, 48, "Tamara"
    WScript.Quit 1
End If

Function ServerReady(baseUrl)
    Dim request, contentType, responseBody, shape
    ServerReady = False
    On Error Resume Next
    Set request = CreateObject("WinHttp.WinHttpRequest.5.1")
    request.SetTimeouts 500, 500, 500, 1000
    request.Open "GET", baseUrl & "/login", False
    request.Send
    If Err.Number <> 0 Then
        diagnostic = "No se pudo conectar con " & baseUrl & "."
        Err.Clear
        Exit Function
    End If
    If request.Status <> 200 Or InStr(request.ResponseText, "/admin-assets/login.js") = 0 Then
        diagnostic = "La ruta /login no devuelve el login esperado de Tamara."
        Exit Function
    End If

    ' A static server can return a login page without implementing the API.
    ' Use a fresh request, without the browser's session, and inspect the API.
    Set request = CreateObject("WinHttp.WinHttpRequest.5.1")
    request.SetTimeouts 500, 500, 500, 1000
    request.Open "GET", baseUrl & "/api/session", False
    request.SetRequestHeader "Accept", "application/json"
    request.Send
    If Err.Number <> 0 Then
        diagnostic = "La ruta /api/session no responde."
        Err.Clear
        Exit Function
    End If
    contentType = LCase(request.GetResponseHeader("Content-Type"))
    responseBody = Trim(Replace(Replace(Replace(request.ResponseText, vbCr, ""), vbLf, ""), vbTab, " "))
    If Err.Number <> 0 Then
        diagnostic = "La respuesta de /api/session no contiene Content-Type."
        Err.Clear
        Exit Function
    End If
    diagnostic = "/api/session: HTTP " & request.Status & "; tipo " & contentType
    If InStr(contentType, "application/json") = 0 Then Exit Function
    If Left(responseBody, 1) <> "{" Or Right(responseBody, 1) <> "}" Then Exit Function
    Set shape = New RegExp
    If request.Status = 401 Then
        shape.Pattern = """error""\s*:"
    ElseIf request.Status = 200 Then
        shape.Pattern = """authenticated""\s*:\s*(true|false)"
    Else
        Exit Function
    End If
    ServerReady = shape.Test(responseBody)
    On Error GoTo 0
End Function