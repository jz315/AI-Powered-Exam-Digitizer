Set shell = CreateObject("WScript.Shell")

Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)

pythonw = root & "\.venv-gpu\Scripts\pythonw.exe"
If Not fso.FileExists(pythonw) Then
  pythonw = root & "\.venv\Scripts\pythonw.exe"
End If
If Not fso.FileExists(pythonw) Then
  pythonw = "pythonw"
End If

cmd = """" & pythonw & """ """ & root & "\main.py"""
shell.Run cmd, 0, False
