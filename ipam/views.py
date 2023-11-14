
import ipaddress

net = ipaddress.IPv4Network('10.0.1.0/24')
subnets = list(net.subnets(new_prefix=26))
print(subnets)
