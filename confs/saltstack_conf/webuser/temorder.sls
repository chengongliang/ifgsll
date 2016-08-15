/home/webuser/tem-order/webapps/:
  file.recurse:
    - source: salt://files/tem-order/webapps/
    - makedir: True
    - include_empty: True
    - clean: True
stop:
  cmd.run:
    - name: /home/webuser/tem-order/bin/shutdown.sh
    - user: root
start:
  cmd.run:
    - name: /home/webuser/tem-order/bin/startup.sh
    - user: root
