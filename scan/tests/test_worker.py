import base64
import time

from django.urls import reverse
from scan.scan_worker import HostGvmScanner, ScanWorker, WebZapScanner
from ..models import VtScanner, VtTask
import responses
from utils.test import (
    get_or_create_user,
    MyAPITestCase,
)


class ScanWorkerTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password="password")
        self.user2 = get_or_create_user(username="tom@cnic.cn", password="password")

    @responses.activate
    def test_scanner_get(self):
        # add scanner
        scanner1 = VtScanner(
            name="scanner1",
            type="web",
            engine="zaproxy",
            ipaddr="127.0.0.1",
            port=9390,
            status="enable",
            key="testkey1",
            max_concurrency=1,
        )
        scanner1.save(force_insert=True)
        scanner2 = VtScanner(
            name="scanner2",
            type="web",
            engine="zaproxy",
            ipaddr="127.0.0.2",
            port=9391,
            status="disable",
            key="testkey2",
            max_concurrency=1,
        )
        scanner2.save(force_insert=True)
        scanner3 = VtScanner(
            name="scanner3",
            type="host",
            engine="gvm",
            ipaddr="127.0.0.3",
            port=9392,
            status="enable",
            key="testkey3",
            max_concurrency=2,
        )
        scanner3.save(force_insert=True)

        scanworker = ScanWorker()
        self.assertEqual(len(scanworker.scanners), 2)
        self.assertEqual(scanworker.scanners[0].name, "scanner1")
        self.assertEqual(scanworker.scanners[0].ipaddr, "127.0.0.1")
        self.assertEqual(scanworker.scanners[0].port, 9390)
        self.assertEqual(scanworker.scanners[0].max_concurrency, 1)
        self.assertEqual(scanworker.scanners[1].name, "scanner3")
        self.assertEqual(scanworker.scanners[1].ipaddr, "127.0.0.3")
        self.assertEqual(scanworker.scanners[1].port, 9392)
        self.assertEqual(scanworker.scanners[1].max_concurrency, 2)
        self.assertEqual(isinstance(scanworker.scanners[0], WebZapScanner), True)
        self.assertEqual(isinstance(scanworker.scanners[1], HostGvmScanner), True)
        self.assertEqual(scanworker.scanners[0].tasks, [])
        self.assertEqual(scanworker.scanners[1].tasks, [])

        # add task
        user_scan_task1 = VtTask(
            name="user_task1",
            target="http://test.com/",
            type="web",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid1",
        )
        user_scan_task1.save(force_insert=True)
        user_scan_task2 = VtTask(
            name="user_task2",
            target="127.0.0.1",
            type="host",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid2",
        )
        user_scan_task2.save(force_insert=True)
        user_scan_task3 = VtTask(
            name="user_task3",
            target="127.0.0.1",
            type="host",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid2",
        )
        user_scan_task3.save(force_insert=True)
        user_scan_task4 = VtTask(
            name="user_task4",
            target="http://test.com/",
            type="web",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid1",
        )
        user_scan_task4.save(force_insert=True)
        self.assertEqual(user_scan_task2.task_status, "queued")

        # test process_new_tasks
        # failed
        responses.add(
            responses.POST,
            "http://127.0.0.1:9390/zap/create_task",
            json={"ok": False, "errmsg": "not found"},
            status=200,
        )
        responses.add(
            responses.POST,
            "http://127.0.0.3:9392/gvm/create_task",
            json={"ok": False, "errmsg": "not found"},
            status=200,
        )
        scanworker.process_new_tasks()
        scanworker.process_new_tasks()
        self.assertEqual(scanworker.scanners[0].tasks, [])
        self.assertEqual(scanworker.scanners[1].tasks, [])

        # success
        responses.reset()
        responses.add(
            responses.POST,
            "http://127.0.0.1:9390/zap/create_task",
            json={"ok": True, "running_status": "spider"},
            status=200,
        )
        responses.add(
            responses.POST,
            "http://127.0.0.3:9392/gvm/create_task",
            json={"ok": True, "running_id": "123456789"},
            status=200,
        )
        scanworker.process_new_tasks()
        scanworker.process_new_tasks()
        self.assertEqual(len(scanworker.scanners[0].tasks), 1)
        self.assertEqual(len(scanworker.scanners[1].tasks), 2)
        user_scan_task1.refresh_from_db()
        self.assertEqual(user_scan_task1.task_status, "running")
        self.assertEqual(user_scan_task1.scanner.id, scanner1.id)
        self.assertEqual(user_scan_task1.running_status, "spider")
        user_scan_task2.refresh_from_db()
        self.assertEqual(user_scan_task2.task_status, "running")
        self.assertEqual(user_scan_task2.scanner.id, scanner3.id)
        self.assertEqual(user_scan_task2.running_id, "123456789")
        user_scan_task3.refresh_from_db()
        self.assertEqual(user_scan_task3.task_status, "running")
        self.assertEqual(user_scan_task3.scanner.id, scanner3.id)
        self.assertEqual(user_scan_task3.running_id, "123456789")

        # test process_running_task
        # get status fail, Nothing happend
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_task",
            json={"ok": False, "errmsg": "spider"},
            status=200,
        )
        responses.add(
            responses.GET,
            "http://127.0.0.3:9392/gvm/get_task",
            json={"ok": False, "errmsg": "123456789"},
            status=200,
        )
        update_time1 = user_scan_task1.update_time
        update_time2 = user_scan_task2.update_time
        update_time3 = user_scan_task3.update_time
        scanworker.process_running_tasks()
        user_scan_task1.refresh_from_db()
        after_time1 = user_scan_task1.update_time
        user_scan_task2.refresh_from_db()
        after_time2 = user_scan_task2.update_time
        user_scan_task3.refresh_from_db()
        after_time3 = user_scan_task3.update_time
        self.assertEqual(after_time1, update_time1)
        self.assertEqual(after_time2, update_time2)
        self.assertEqual(after_time3, update_time3)

        # get status success, update task
        responses.reset()
        # not Done
        responses.add(
            responses.GET,
            "http://127.0.0.3:9392/gvm/get_task",
            json={"ok": True, "running_status": "Running"},
            status=200,
        )
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_task",
            json={"ok": True, "running_status": "spider"},
            status=200,
        )
        scanworker.process_running_tasks()
        user_scan_task1.refresh_from_db()
        after_time1 = user_scan_task1.update_time
        user_scan_task2.refresh_from_db()
        after_time2 = user_scan_task2.update_time
        user_scan_task3.refresh_from_db()
        after_time3 = user_scan_task3.update_time
        self.assertEqual(after_time1, update_time1)
        self.assertEqual(after_time2, update_time2)
        self.assertEqual(after_time3, update_time3)

        # zap ajaxspider
        responses.reset()
        responses.add(
            responses.GET,
            "http://127.0.0.3:9392/gvm/get_task",
            json={"ok": True, "running_status": "Running"},
            status=200,
        )
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_task",
            json={"ok": True, "running_status": "ajaxspider"},
            status=200,
        )
        scanworker.process_running_tasks()
        user_scan_task1.refresh_from_db()
        self.assertEqual(user_scan_task1.running_status, "ajaxspider")

        # zap active
        responses.reset()
        responses.add(
            responses.GET,
            "http://127.0.0.3:9392/gvm/get_task",
            json={"ok": True, "running_status": "Running"},
            status=200,
        )
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_task",
            json={"ok": True, "running_status": "active"},
            status=200,
        )
        scanworker.process_running_tasks()
        user_scan_task1.refresh_from_db()
        self.assertEqual(user_scan_task1.running_status, "active")

        # zap passive
        responses.reset()
        responses.add(
            responses.GET,
            "http://127.0.0.3:9392/gvm/get_task",
            json={"ok": True, "running_status": "Running"},
            status=200,
        )
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_task",
            json={"ok": True, "running_status": "passive"},
            status=200,
        )
        scanworker.process_running_tasks()
        user_scan_task1.refresh_from_db()
        self.assertEqual(user_scan_task1.running_status, "passive")

        # gvm get failed or interapted
        responses.reset()
        responses.add(
            responses.GET,
            "http://127.0.0.3:9392/gvm/get_task",
            json={"ok": True, "running_status": "Interapted"},
            status=200,
        )
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_task",
            json={"ok": True, "running_status": "passive"},
            status=200,
        )
        scanworker.process_running_tasks()
        user_scan_task2.refresh_from_db()
        user_scan_task3.refresh_from_db()
        self.assertEqual(user_scan_task2.task_status, "queued")
        self.assertEqual(user_scan_task3.task_status, "queued")
        self.assertEqual(user_scan_task2.scanner, None)
        self.assertEqual(user_scan_task3.scanner, None)

        # readd tasks in scanner
        responses.reset()
        responses.add(
            responses.POST,
            "http://127.0.0.1:9390/zap/create_task",
            json={"ok": True, "running_status": "spider"},
            status=200,
        )
        responses.add(
            responses.POST,
            "http://127.0.0.3:9392/gvm/create_task",
            json={"ok": True, "running_id": "123456789"},
            status=200,
        )
        scanworker.process_new_tasks()
        scanworker.process_new_tasks()
        self.assertEqual(len(scanworker.scanners[1].tasks), 2)
        user_scan_task2.refresh_from_db()
        self.assertEqual(user_scan_task2.task_status, "running")
        self.assertEqual(user_scan_task2.scanner.id, scanner3.id)
        self.assertEqual(user_scan_task2.running_id, "123456789")
        user_scan_task3.refresh_from_db()
        self.assertEqual(user_scan_task3.task_status, "running")
        self.assertEqual(user_scan_task3.scanner.id, scanner3.id)
        self.assertEqual(user_scan_task3.running_id, "123456789")
        
        # Done and save report
        responses.reset()
        # zap
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_task",
            json={"ok": True, "running_status": "done"},
            status=200,
        )
        content = "xxxxxxxx"
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_report",
            json={"ok": True, "content": content},
            status=200,
        )
        # gvm
        responses.add(
            responses.GET,
            "http://127.0.0.3:9392/gvm/get_task",
            json={"ok": True, "running_status": "Done"},
            status=200,
        )
        responses.add(
            responses.GET,
            "http://127.0.0.3:9392/gvm/get_report",
            json={"ok": True, "content": content},
            status=200,
        )
        responses.add(
            responses.DELETE,
            "http://127.0.0.3:9392/gvm/delete_task",
            json={"ok": True},
            status=200,
        )
        scanworker.process_running_tasks()
        user_scan_task1.refresh_from_db()
        self.assertEqual(user_scan_task1.task_status, "done")
        self.assertNotEqual(user_scan_task1.report, None)
        self.assertEqual(user_scan_task1.report.content, content.encode("utf-8"))
        user_scan_task2.refresh_from_db()
        self.assertEqual(user_scan_task2.task_status, "done")
        self.assertNotEqual(user_scan_task2.report, None)
        new_content = base64.b64encode(user_scan_task2.report.content)
        size = user_scan_task2.report.size
        self.assertEqual(size, len(base64.b64decode(content)))
        self.assertEqual(new_content, content.encode("utf-8"))
        user_scan_task3.refresh_from_db()
        self.assertEqual(user_scan_task3.task_status, "done")
        self.assertNotEqual(user_scan_task3.report, None)

        # zap
        # get status fail, change status to failed
        responses.reset()
        responses.add(
            responses.POST,
            "http://127.0.0.1:9390/zap/create_task",
            json={"ok": True, "running_status": "spider"},
            status=200,
        )
        responses.add(
            responses.GET,
            "http://127.0.0.1:9390/zap/get_task",
            json={"ok": True, "running_status": "failed", "errmsg": "Url not found."},
            status=200,
        )
        scanworker.process_new_tasks()
        scanworker.process_running_tasks()
        scanworker.process_running_tasks()
        self.assertEqual(len(scanworker.scanners[0].tasks), 0)
        user_scan_task4.refresh_from_db()
        self.assertEqual(user_scan_task4.task_status, "failed")
        self.assertEqual(user_scan_task4.scanner.id, scanner1.id)
        self.assertEqual(user_scan_task4.errmsg, "Url not found.")
    # def test_real_scanner(self):
    #     # add scanner
    #     scanner1 = VtScanner(name='scanner1', type='host', engine='gvm', ipaddr='223.193.36.206', port=9394, status='enable' ,key="3jucg&f-t^zy6z0zs0@(&j)@@b^ppay%c)9yvk8l8i+j0dh#sv", max_concurrency=1)
    #     scanner1.save(force_insert=True)
    #     scanner2 = VtScanner(name='scanner2', type='web', engine='zaproxy', ipaddr='223.193.36.207', port=9394, status='enable', key="3jucg&f-t^zy6z0zs0@(&j)@@b^ppay%c)9yvk8l8i+j0dh#sv", max_concurrency=1)
    #     scanner2.save(force_insert=True)
    #     # add task
    #     user_scan_task1 = VtTask(name='user_task1', target='https://service.cstcloud.cn/', type='web', user=self.user,
    #                              remark='user task test', payment_history_id='testpaymenthistoryid1')
    #     user_scan_task1.save(force_insert=True)
    #     user_scan_task2 = VtTask(name='user_task2', target='127.0.0.1', type='host', user=self.user,
    #                              remark='user task test', payment_history_id='testpaymenthistoryid2')
    #     user_scan_task2.save(force_insert=True)
    #     # worker run
    #     for i in range(15):
    #         ScanWorker().run()
    #         user_scan_task1.refresh_from_db()
    #         user_scan_task2.refresh_from_db()
    #         print('user_scan_task1:', user_scan_task1.task_status)
    #         print('user_scan_task2:', user_scan_task2.task_status)
    #         if user_scan_task1.task_status == 'done' and user_scan_task2.task_status == 'done':
    #             base_url = reverse('scan-api:report-detail', kwargs={'task_id': user_scan_task1.id})
    #             self.client.force_login(self.user)
    #             r = self.client.get(path=base_url)
    #             self.assertEqual(r.status_code, 200)
    #             self.assertEqual(r['Content-Type'], 'application/octet-stream')
    #             # actual_content = io.BytesIO(r.content).getvalue()
    #             actual_content = b"".join(r.streaming_content)
    #             with open('testzaproxy.html', 'wb') as f:
    #                 f.write(actual_content)
    #             base_url = reverse('scan-api:report-detail', kwargs={'task_id': user_scan_task2.id})
    #             self.client.force_login(self.user)
    #             r = self.client.get(path=base_url)
    #             self.assertEqual(r.status_code, 200)
    #             self.assertEqual(r['Content-Type'], 'application/octet-stream')
    #             # actual_content = io.BytesIO(r.content).getvalue()
    #             actual_content = b"".join(r.streaming_content)
    #             with open('testgvm.pdf', 'wb') as f:
    #                 f.write(actual_content)
    #             break
    #         time.sleep(2*60)
