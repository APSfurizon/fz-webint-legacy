import psutil
import time
import sys

from sanic import Sanic
from sanic import response as res

DEV_MODE = False
ACCESS_LOG = False

app = Sanic(__name__)

@app.route("/")
async def main(req):
	return res.text("I\'m a teapot", status=418)

@app.route("/metrics")
async def metrics(req):
	out = []

	cpus = psutil.cpu_percent(percpu=True)
	totalCpu = 0
	for i in range(len(cpus)):
		out.append(f'monitor_cpu_core_usage_percent{{core="{i}"}} {cpus[i]}')
		totalCpu += cpus[i]
	out.append(f'monitor_cpu_core_usage_percent{{core="avg"}} {"%.2f" % (totalCpu / len(cpus))}')

	diskIo = psutil.disk_io_counters(nowrap=True)
	out.append(f'monitor_diskio{{value="read_count"}} {diskIo.read_count}')
	out.append(f'monitor_diskio{{value="write_count"}} {diskIo.write_count}')
	out.append(f'monitor_diskio{{value="read_bytes"}} {diskIo.read_bytes}')
	out.append(f'monitor_diskio{{value="write_bytes"}} {diskIo.write_bytes}')
	out.append(f'monitor_diskio{{value="read_time"}} {diskIo.read_time}')
	out.append(f'monitor_diskio{{value="write_time"}} {diskIo.write_time}')

	disks = psutil.disk_partitions()
	for disk in disks:
		try:
			dUsage = psutil.disk_usage(disk.mountpoint)
			out.append(f'monitor_disk_usage_percent{{partition="{disk.mountpoint}"}} {dUsage.percent}')
		except: 
			pass

	mem = psutil.virtual_memory()
	out.append(f'monitor_memory{{value="total"}} {mem.total}')
	out.append(f'monitor_memory{{value="available"}} {mem.available}')
	out.append(f'monitor_memory{{value="percent"}} {mem.percent}')
	out.append(f'monitor_memory{{value="used"}} {mem.used}')
	out.append(f'monitor_memory{{value="free"}} {mem.free}')

	swap = psutil.swap_memory()
	out.append(f'monitor_swap{{value="total"}} {swap.total}')
	out.append(f'monitor_swap{{value="used"}} {swap.used}')
	out.append(f'monitor_swap{{value="free"}} {swap.free}')
	out.append(f'monitor_swap{{value="percent"}} {swap.percent}')
	out.append(f'monitor_swap{{value="sin"}} {swap.sin}')
	out.append(f'monitor_swap{{value="sout"}} {swap.sout}')

	bootTime = psutil.boot_time()
	out.append(f'monitor_boot_time{{}} {int(time.time() - bootTime)}')

	netioConnections = psutil.net_connections()
	out.append(f'monitor_netio_connections{{}} {len(netioConnections)}')
	netioCounters = psutil.net_io_counters(nowrap=True)
	out.append(f'monitor_netio_counters{{value="bytes_sent"}} {netioCounters.bytes_sent}')
	out.append(f'monitor_netio_counters{{value="bytes_recv"}} {netioCounters.bytes_recv}')
	out.append(f'monitor_netio_counters{{value="packets_sent"}} {netioCounters.packets_sent}')
	out.append(f'monitor_netio_counters{{value="packets_recv"}} {netioCounters.packets_recv}')
	out.append(f'monitor_netio_counters{{value="errin"}} {netioCounters.errin}')
	out.append(f'monitor_netio_counters{{value="errout"}} {netioCounters.errout}')
	out.append(f'monitor_netio_counters{{value="dropin"}} {netioCounters.dropin}')
	out.append(f'monitor_netio_counters{{value="dropout"}} {netioCounters.dropout}')

	return res.text("\n".join(out), status=200)


if __name__ == '__main__':
	ip = "127.0.0.1"
	port = 2611
	if(len(sys.argv) > 1):
		ip = sys.argv[1]
	if(len(sys.argv) > 2):
		try:
			port = int(sys.argv[2])
		except:
			print("Port must be a numeric value!")
			exit(1)
		if(port < 1 or port > 0xffff):
			print("Port must be in [1, 65535] range!")
			exit(1)
	app.run(host=ip, port=port, dev=DEV_MODE, access_log=ACCESS_LOG)
