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
    }
}

TEST_CASE.update(TEST_CASE_SECURITY)
