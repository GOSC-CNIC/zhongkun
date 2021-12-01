from .security import TEST_CASE_SECURITY


# test case settings
TEST_CASE = {
    'MONITOR_CEPH': {
        'PROVIDER': {
            'endpoint_url': 'http://159.226.98.184:19192/',
            'username': '',
            'password': ''
        },
        'JOB_CEPH': {
            'job_tag': 'Fed-ceph'
        }
    },
    'MONITOR_SERVER': {
        'PROVIDER': {
            'endpoint_url': 'http://159.226.98.184:19192/',
            'username': '',
            'password': ''
        },
        'JOB_SERVER': {
            'job_tag': 'AIOPS-node'
        }
    },
    'MONITOR_VIDEO_MEETING': {
        'PROVIDER': {
            'endpoint_url': 'http://159.226.98.184:19192/',
            'username': '',
            'password': ''
        },
        'JOB_MEETING': {
            'job_tag': 'wangluozhongxin'
        }
    }
}

TEST_CASE.update(TEST_CASE_SECURITY)
