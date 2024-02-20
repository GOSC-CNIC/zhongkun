from ..models import VtReport, VtTask
from django.urls import reverse
from utils.test import (
    get_or_create_user,
    MyAPITestCase,
)
import hashlib
import collections
import io
import random
from string import printable


def random_string(length: int = 10):
    return random.choices(printable, k=length)


def random_bytes_io(mb_num: int):
    bio = io.BytesIO()
    for i in range(1):  # B
        s = "".join(random_string(mb_num))
        b = s.encode() * 10  # B
        bio.write(b)

    bio.seek(0)
    return bio


def calculate_md5(file):
    if hasattr(file, "seek"):
        file.seek(0)

    md5obj = hashlib.md5()
    if isinstance(file, collections.Iterable):
        for data in file:
            md5obj.update(data)
    else:
        for data in chunks(file):
            md5obj.update(data)

    _hash = md5obj.hexdigest()
    return _hash


def chunks(f, chunk_size=2 * 2**20):
    """
    Read the file and yield chunks of ``chunk_size`` bytes (defaults to
    ``File.DEFAULT_CHUNK_SIZE``).
    """
    try:
        f.seek(0)
    except AttributeError:
        pass

    while True:
        data = f.read(chunk_size)
        if not data:
            break
        yield data


class ScanReportTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password="password")
        self.user2 = get_or_create_user(username="tom@cnic.cn", password="password")

    def test_report(self):
        # NotAuthenticated
        base_url = reverse("scan-api:report-detail", kwargs={"task_id": "xx"})
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=401, code="NotAuthenticated", response=r)
        # add data
        user_scan_task1 = VtTask(
            name="user_task1",
            target="http://test.com/",
            type="web",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid1",
        )
        user_scan_task1.save(force_insert=True)

        file = random_bytes_io(mb_num=2)
        file_byte = file.getvalue()

        # create report
        report = VtReport(filename="test1.html", type="html", content=file.read())
        report.save(force_insert=True)
        user_scan_task2 = VtTask(
            name="user_task2",
            target="http://test2.com/",
            type="web",
            user=self.user,
            remark="user task test",
            payment_history_id="testpaymenthistoryid2",
            task_status="done",
            report=report,
        )
        user_scan_task2.save(force_insert=True)

        # InvalidTaskID
        base_url = reverse("scan-api:report-detail", kwargs={"task_id": "xx"})
        self.client.force_login(self.user)
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=400, code="InvalidTaskID", response=r)

        # InvalidTaskID
        base_url = reverse(
            "scan-api:report-detail", kwargs={"task_id": user_scan_task1.id}
        )
        self.client.force_login(self.user2)
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=400, code="InvalidTaskID", response=r)

        # ScanTaskNotDone
        self.client.force_login(self.user)
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=400, code="ScanTaskNotDone", response=r)

        # ok
        base_url = reverse(
            "scan-api:report-detail", kwargs={"task_id": user_scan_task2.id}
        )
        self.client.force_login(self.user)
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/octet-stream")
        self.assertEqual(r["Content-Disposition"], 'attachment; filename="test1.html"')
        # actual_content = io.BytesIO(r.content).getvalue()
        actual_content = b"".join(r.streaming_content)
        self.assertEqual(actual_content, file_byte)
