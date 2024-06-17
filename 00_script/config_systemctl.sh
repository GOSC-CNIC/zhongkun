cp /home/uwsgi/zhongkun/00_script/zhongkun.service /usr/lib/systemd/system/ -f
systemctl daemon-reload
systemctl enable zhongkun
