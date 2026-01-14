Option Explicit

Dim shell, fso, root, py, scriptPath, logPath, q, cmd

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root

scriptPath = root & "\main.py"
logPath = root & "\run.log"
q = Chr(34)

' Prefer python.exe so exceptions can be logged reliably (still no console via windowStyle=0)
py = root & "\.venv-gpu\Scripts\python.exe"
If Not fso.FileExists(py) Then
  py = root & "\.venv\Scripts\python.exe"
End If
If Not fso.FileExists(py) Then
  py = "python"
End If

' Run and capture stdout/stderr to run.log
cmd = "cmd.exe /c " & q & q & py & q & " " & q & scriptPath & q & " > " & q & logPath & q & " 2>&1" & q
shell.Run cmd, 0, False
