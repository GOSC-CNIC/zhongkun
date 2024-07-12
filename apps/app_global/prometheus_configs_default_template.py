# 定义 prometheus 相关内容的模板信息


prometheus_base_default = """global:
  scrape_interval: 30s
  evaluation_interval: 30s

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alert.cstcloud.cn
      #- xxxxzk.cstcloud.cn
    scheme: https
  - static_configs:
    - targets:
      - localhost:9093

rule_files:
- rules-vm.yml
- rules-host.yml
- rules-ceph.yml
- rules-tidb.yml
- rules-web.yml

scrape_config_files:
- prometheus_exporter_node.yml
- prometheus_exporter_ceph.yml
- prometheus_exporter_tidb.yml
- prometheus_blackbox_http.yml

remote_write:
- url: http://localhost:9009/api/v1/push
"""
prometheus_blackbox_http_default = """- job_name: '{url_hash}'
  metrics_path: /probe
  params:
    module: [http_2xx]
  static_configs:
  - targets:
    - '{url}'
    labels:
      group: web
  relabel_configs:
  - source_labels: [__address__]
    target_label: __param_target
  - source_labels: [__param_target]
    target_label: url
  - target_label: __address__
    replacement: {local_ip}
"""

prometheus_blackbox_tcp_default = """- job_name: '{tcp_hash}'
  metrics_path: /probe
  params:
    module: [tcp_connect]
  static_configs:
  - targets:
    - '{tcp_url}'
    labels:
      group: tcp
      url: {tcp_url}
  relabel_configs:
  - source_labels: [__address__]
    target_label: __param_target
  - target_label: __address__
    replacement: {local_ip}
"""

prometheus_exporter_node_default = """scrape_configs:
- job_name: xxxx_hosts_node_metric
  static_configs:
  - targets:
    - 10.16.x.1:9100
    - 10.16.x.2:9100
    - 10.16.x.3:9100
    - 10.16.x.4:9100
    - 10.16.x.5:9100

- job_name: xxxx_vms_node_metric
  static_configs:
  - targets:
    - 10.16.x.24:9100
    - 10.16.x.25:9100
    - 10.16.x.26:9100
    - 10.16.x.27:9100
    - 10.16.x.28:9100"""
prometheus_exporter_ceph_default = """scrape_configs:
- job_name: xxxx_ceph_metric
  static_configs:
  - targets:
    - 10.16.x.1:9283
"""
prometheus_exporter_tidb_default = """scrape_configs:
- job_name: xxxx_tidb_metric
  static_configs:
  - targets:
    - 10.16.x.28:12020
    - 10.16.x.26:9100
    - 10.16.x.27:9100
    - 10.16.x.28:9100
  - targets:
    - 10.16.x.26:2379
    - 10.16.x.27:2379
    - 10.16.x.28:2379
    labels:
      group_type: pd
  - targets:
    - 10.16.x.26:10080
    - 10.16.x.27:10080
    - 10.16.x.28:10080
    labels:
      group_type: tidb
  - targets:
    - 10.16.x.26:20180
    - 10.16.x.27:20180
    - 10.16.x.28:20180
    labels:
      group_type: tikv
"""
