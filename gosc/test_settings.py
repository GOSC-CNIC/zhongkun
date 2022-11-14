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
            'job_tag': 'aiops-ceph'
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
    }
}

TEST_CASE.update(TEST_CASE_SECURITY)
