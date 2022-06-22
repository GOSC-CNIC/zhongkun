cp /home/uwsgi/vms/vms.service /usr/lib/systemd/system/ -f
systemctl daemon-reload
systemctl enable vms
