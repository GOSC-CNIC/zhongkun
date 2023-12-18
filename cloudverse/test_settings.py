from .security import TEST_CASE_SECURITY


# test case settings
TEST_CASE = {
    'MONITOR_CEPH': {
        'PROVIDER': {
            'endpoint_url': 'http://223.193.36.46:19193',
            'username': '',
            'password': ''
        },
        'JOB_CEPH': {
            'job_tag': 'aiops_ceph_metric'
        }
    },
    'MONITOR_SERVER': {
        'PROVIDER': {
            'endpoint_url': 'http://223.193.36.46:19193',
            'username': '',
            'password': ''
        },
        'JOB_SERVER': {
            'job_tag': 'aiops-node-hosts'
        }
    },
    'MONITOR_VIDEO_MEETING': {
        'PROVIDER': {
            'endpoint_url': 'http://223.193.36.46:19192',
            'username': '',
            'password': ''
        },
        'JOB_MEETING': {
            'job_tag': '45xinxihuadasha503'
        }
    },
    'MONITOR_WEBSITE': {
        'PROVIDER': {
            'endpoint_url': 'http://thanoswrite.cstcloud.cn:19192/',
            'username': '',
            'password': ''
        },
        'WEBSITE_URL': "http://www.acas.ac.cn/",
        'WEBSITE_SCHEME': "http://",
        'WEBSITE_HOSTNAME': "www.acas.ac.cn",
        'WEBSITE_URI': "/"
    },
    'MONITOR_TIDB': {
        'PROVIDER': {
            'endpoint_url': 'http://223.193.36.46:19193',
            'username': '',
            'password': ''
        },
        'JOB_TIDB': {
            'job_tag': 'aiops_tidb_metric'
        }
    },
    'LOG_SITE': {
        'PROVIDER': {
            'endpoint_url': 'http://159.226.91.149:34135',
            'username': '',
            'password': ''
        },
        'JOB_SITE': {
            'job_tag': 'obs'
        }
    }
}

TEST_CASE.update(TEST_CASE_SECURITY)
