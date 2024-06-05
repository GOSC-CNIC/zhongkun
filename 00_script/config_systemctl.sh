cp /home/uwsgi/yunkun/00_script/yunkun.service /usr/lib/systemd/system/ -f
systemctl daemon-reload
systemctl enable yunkun
