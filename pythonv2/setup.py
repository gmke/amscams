#!/usr/bin/python3 

import os

os.system("mkdir /mnt/ams2/SD/proc2")
os.system("mkdir /mnt/ams2/SD/proc2/json")
os.system("mkdir /mnt/ams2/SD/proc2/daytime")
os.system("mkdir /mnt/ams2/latest")
os.system("mkdir /mnt/ams2/CAMS")
os.system("mkdir /mnt/ams2/CAMS/queue")
os.system("mkdir /mnt/ams2/tmp/")
os.system("mkdir /mnt/ams2/trash/")
os.system("mkdir /mnt/ams2/cal/")
os.system("mkdir /mnt/ams2/cal/freecal/")
os.system("mkdir /mnt/ams2/cal/tmp/")
os.system("mkdir /mnt/ams2/cal/fit_pool/")
os.system("mkdir /mnt/ams2/cal/tmp/")
os.system("mkdir /var/www/html/js")
os.system("ln -s /home/ams/amscams/pythonv2/webUI.py /var/www/html/pycgi/")
os.system("ln -s /home/ams/amscams/pythonv2/templates/as6nav.png /var/www/html/")
os.system("ln -s /home/ams/amscams/pythonv2/templates/contextMenu.js /var/www/html/js/")
os.system("ln -s /home/ams/amscams/pythonv2/templates/fabric.min.js /var/www/html/js/")
os.system("ln -s /home/ams/amscams/pythonv2/templates/freecal-ajax.js /var/www/html/js/")
os.system("ln -s /home/ams/amscams/pythonv2/templates/freecal-canvas.js /var/www/html/js/")
os.system("ln -s /home/ams/amscams/pythonv2/templates/videopopup.js /var/www/html/js/")
os.system("ln -s /home/ams/amscams/pythonv2/templates/videopopup.js /var/www/html/")
