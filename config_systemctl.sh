cp /home/uwsgi/yunkun/yunkun.service /usr/lib/systemd/system/ -f
systemctl daemon-reload
systemctl enable yunkun
