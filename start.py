from subprocess import Popen

while True:
	print("Enshrouded Serverlog is started")
	p = Popen("py serverlog.py", shell=True)
	p.wait()