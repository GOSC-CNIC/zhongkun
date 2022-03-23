class BaseConfig:
    def to_dict(self):
        raise NotImplemented('to_dict')


class ServerConfig:
    def __init__(self, vm_cpu: int, vm_ram: int, systemdisk_size: int, public_ip: bool):
        """
        :param vm_cpu
        :param vm_ram: MiB
        :param systemdisk_size: Gib
        """
        self.vm_cpu = vm_cpu
        self.vm_ram = vm_ram
        self.vm_systemdisk_size = systemdisk_size
        self.vm_public_ip = public_ip

    def to_dict(self):
        return {
            'vm_cpu': self.vm_cpu,
            'vm_ram': self.vm_ram,
            'vm_systemdisk_size': self.vm_systemdisk_size,
            'vm_public_ip': self.vm_public_ip
        }


class DiskConfig:
    def __init__(self, disk_size: int):
        """
        :param disk_size: Gib
        """
        self.disk_size = disk_size

    def to_dict(self):
        return {
            'disk_size': self.disk_size
        }


class BucketConfig:
    def to_dict(self):
        return {}
