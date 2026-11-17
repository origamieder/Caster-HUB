' Lanza Caster Hub sin mostrar la ventana de PowerShell (la usa el acceso directo).
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & dir & "\lanzador.ps1""", 0, False
