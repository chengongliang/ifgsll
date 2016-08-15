/home/wwwroot/order.iclassedu.com/:
  file.recurse:
    - source: salt://files/order.iclassedu.com/
    - file_mode: 644
    - dir_mode: 755
    - makedir: True
    - include_empty: True
    - clean: True
