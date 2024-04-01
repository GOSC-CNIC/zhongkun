from io import StringIO

from django.core.management import call_command
import responses

from apps.app_scan.managers import ScanManager
from utils.test import (
    get_or_create_user,
    MyAPITestCase, 
)


class ScanPriceTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.user2 = get_or_create_user(username='tom@cnic.cn', password='password')

    @responses.activate
    def test_add_scanner(self):
        # fail
        responses.add(responses.GET, 'http://127.0.0.1:9394/gvm/hello',
                    json={'ok': False, 'errmsg': 'not found'}, status=200)
        out = StringIO()
        call_command('scan', 'addscanner', name='testscanner', ipaddr='127.0.0.1', stdout=out)
        self.assertIn('Scanner information not provide.', out.getvalue())      
        out.truncate(0)  
        call_command('scan', 'addscanner', name='testscanner', ipaddr='127.0.0.1', port='9394', engine='gvm', 
                     key='testkey', type='fail', status='enable', stdout=out)
        self.assertIn('Scanner type invalid.', out.getvalue())        
        out.truncate(0)         
        call_command('scan', 'addscanner', name='testscanner', ipaddr='127.0.0.1', port='9394', engine='gvm', 
                     key='testkey', type='host', status='fail', stdout=out)
        self.assertIn('Scanner status invalid.', out.getvalue())  
        out.truncate(0)  
        call_command('scan', 'addscanner', name='testscanner', ipaddr='127.0.1', port='9394', engine='gvm', 
                     key='testkey', type='host', status='enable', stdout=out)
        self.assertIn('Scanner address invalid.', out.getvalue())  
        out.truncate(0)  
        call_command('scan', 'addscanner', name='testscanner', ipaddr='127.0.0.1', port='93ss', engine='gvm', 
                     key='testkey', type='host', status='enable', max_concurrency='1', stdout=out)
        self.assertIn('Scanner number invalid.', out.getvalue())  
        out.truncate(0)  
        call_command('scan', 'addscanner', name='testscanner', ipaddr='127.0.0.1', port='9394', engine='gvm', 
                     key='testkey', type='host', status='enable', max_concurrency='1', stdout=out)
        self.assertIn('not access.', out.getvalue())  
        out.truncate(0)  
        # success
        # disable
        call_command('scan', 'addscanner', name='testscanner', ipaddr='127.0.0.1', port='9394', engine='gvm', 
                     key='testkey', type='host', status='disable', max_concurrency='1', stdout=out)
        scanners = ScanManager.get_disabled_scanners()
        self.assertEqual(1, len(scanners))
        scanner = scanners[0]
        self.assertEqual(scanner.name, 'testscanner')
        self.assertEqual(scanner.max_concurrency, 1)
        # enable
        responses.reset()
        responses.add(responses.GET, 'http://127.0.0.1:9394/gvm/hello',
                    json={'ok': True, 'errmsg': None}, status=200)
        call_command('scan', 'addscanner', name='testscanner', ipaddr='127.0.0.1', port='9394', engine='gvm', 
                     key='testkey', type='host', status='enable', max_concurrency='1', stdout=out)
        self.assertIn('Create scanner failed.', out.getvalue())
        out.truncate(0)  
        call_command('scan', 'addscanner', name='testscanner2', ipaddr='127.0.0.1', port='9394', engine='gvm', 
                     key='testkey', type='host', status='enable', max_concurrency='5', stdout=out)
        self.assertIn('created.', out.getvalue())
        scanners = ScanManager.get_enabled_scanners()
        self.assertEqual(1, len(scanners))
        scanner = scanners[0]
        self.assertEqual(scanner.name, 'testscanner2')
        self.assertEqual(scanner.max_concurrency, 5)
    
    def test_set_scanner(self):
        responses.add(responses.GET, 'http://127.0.0.1:9394/gvm/hello',
                    json={'ok': True, 'errmsg': None}, status=200) 
        out = StringIO()
        call_command('scan', 'addscanner', name='testscanner3', ipaddr='127.0.0.1', port='9394', engine='gvm', 
                     key='testkey', type='host', status='disable', max_concurrency='3', stdout=out)
        self.assertIn('created.', out.getvalue())
        scanners = ScanManager.get_disabled_scanners()
        self.assertEqual(1, len(scanners))
        scanner = scanners[0]
        self.assertEqual(scanner.name, 'testscanner3')
        self.assertEqual(scanner.max_concurrency, 3)
        # enable 
        call_command('scan', 'enablescanner', name='testscanner3')
        scanners = ScanManager.get_enabled_scanners()
        self.assertEqual(1, len(scanners))
        scanner = scanners[0]
        self.assertEqual(scanner.name, 'testscanner3')
        self.assertEqual(scanner.max_concurrency, 3)
        scanners = ScanManager.get_disabled_scanners()
        self.assertEqual(0, len(scanners))
        # disable
        call_command('scan', 'disablescanner', name='testscanner3')
        scanners = ScanManager.get_disabled_scanners()
        self.assertEqual(1, len(scanners))
        scanner = scanners[0]
        self.assertEqual(scanner.name, 'testscanner3')
        self.assertEqual(scanner.max_concurrency, 3)
        scanners = ScanManager.get_enabled_scanners()
        self.assertEqual(0, len(scanners))
    
    def test_add_task(self):
        # fail
        out = StringIO()
        call_command('scan', 'addtask', name='testtask', ipaddr='127.0.0.1', type='fail', stdout=out)
        self.assertIn('Task type invalid.', out.getvalue())
        out.truncate(0)  
        call_command('scan', 'addtask', name='testtask', type='host', stdout=out)
        self.assertIn('Task target invalid.', out.getvalue())
        out.truncate(0)  
        call_command('scan', 'addtask', name='testtask', ipaddr='127.0.0.1', type='web', stdout=out)
        self.assertIn('Task target invalid.', out.getvalue())
        out.truncate(0)  
        call_command('scan', 'addtask', name='testtask', url='http://test.c', type='web', stdout=out)
        self.assertIn('Task information invalid.', out.getvalue())
        out.truncate(0)  
        # success
        call_command('scan', 'addtask', name='testtask', ipaddr='127.0.0.1', type='host', stdout=out)
        self.assertIn('success.', out.getvalue())
        tasks = ScanManager.get_queued_tasks(scan_type='host', num=10)
        self.assertEqual(1, len(tasks))
        task = tasks[0]
        self.assertEqual(task.name, 'testtask')
        self.assertEqual(task.target, '127.0.0.1')