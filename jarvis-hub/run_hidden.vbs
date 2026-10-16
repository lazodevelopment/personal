' Runs a .bat with no window and hands its exit code back to Task Scheduler (so "Last Run Result" shows real failures)
Set sh = CreateObject("WScript.Shell")
WScript.Quit sh.Run("""" & WScript.Arguments(0) & """", 0, True)
