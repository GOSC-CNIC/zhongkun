cp /home/uwsgi/cloudverse/cloudverse.service /usr/lib/systemd/system/ -f
systemctl daemon-reload
systemctl enable cloudverse
