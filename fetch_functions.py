import subprocess
import psutil

from pysnmp.hlapi import *

def fetch_snmp_data():
    network_data = {}
    faulty_nodes = []
    faulty_connections = []

    switches = ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4', '192.168.1.5', '192.168.1.6']
    community_string = 'public'  # Replace with your SNMP community string

    for switch in switches:
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(SnmpEngine(),
                   CommunityData(community_string),
                   UdpTransportTarget((switch, 161)),
                   ContextData(),
                   ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0)),
                   ObjectType(ObjectIdentity('IF-MIB', 'ifDescr')),
                   ObjectType(ObjectIdentity('IF-MIB', 'ifOperStatus')))
        )

        if errorIndication:
            print(f"Error retrieving data from {switch}: {errorIndication}")
            continue

        if errorStatus:
            print(f"Error in response from {switch}: {errorStatus} at {errorIndex}")
            continue

        switch_data = {'neighbors': {}, 'ports': {}}

        for varBind in varBinds:
            if varBind[0].prettyPrint() == 'SNMPv2-MIB::sysDescr.0':
                switch_data['sysDescr'] = varBind[1].prettyPrint()

            elif varBind[0].prettyPrint().startswith('IF-MIB::ifDescr.'):
                port_index = varBind[0].prettyPrint().split('.')[-1]
                port_name = varBind[1].prettyPrint()
                switch_data['ports'][port_index] = {'name': port_name}

            elif varBind[0].prettyPrint().startswith('IF-MIB::ifOperStatus.'):
                port_index = varBind[0].prettyPrint().split('.')[-1]
                oper_status = varBind[1].prettyPrint()
                switch_data['ports'][port_index]['status'] = 'Up' if oper_status == '1' else 'Down'

        network_data[switch] = switch_data

        for port_index, port_data in switch_data['ports'].items():
            if port_data['status'] == 'Down':
                faulty_connections.append((switch, port_index, port_data['name']))
        
        if any(port_data['status'] == 'Down' for port_data in switch_data['ports'].values()):
            faulty_nodes.append((switch, switch_data['ports']))

    return network_data, faulty_nodes, faulty_connections


def fetch_ping_results(ip_range):
    ping_results = {}

    for ip in ip_range:
        ip = str(ip)  # Ensure IP is a string
        command = ['ping', '-c', '1', ip]  # Adjust for your OS, e.g., '-n' for Windows

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                ping_time = result.stdout.split('\n')[-2].split(' ')[-2]
                status = 'Up'
            else:
                ping_time = 'N/A'
                status = 'Down'

            ping_results[ip] = {'ping': ping_time, 'status': status}

        except subprocess.TimeoutExpired:
            ping_results[ip] = {'ping': 'Timeout', 'status': 'Down'}

    return ping_results

def fetch_performance_metrics():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    disk = psutil.disk_usage('/')
    disk_usage = disk.percent
    network = psutil.net_io_counters()
    network_traffic = network.bytes_sent + network.bytes_recv

    performance_metrics = {
        'CPU Usage': f'{cpu_usage}%',
        'Memory Usage': f'{memory_usage}%',
        'Disk Usage': f'{disk_usage}%',
        'Network Traffic': f'{network_traffic} bytes'
    }

    return performance_metrics

import datetime

def fetch_logs():
    logs = []
    
    # Calculate timestamp for one hour ago
    one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
    
    # Read the log file and filter entries from the last hour
    log_file_path = '/path/to/network_monitor.log'  # Replace with your actual log file path
    
    try:
        with open(log_file_path, 'r') as log_file:
            for line in log_file:
                log_entry = line.strip()
                # Assuming log entries are in format: 'YYYY-MM-DD HH:mm:ss - LEVEL - Message'
                log_timestamp_str = log_entry.split(' - ')[0]
                log_timestamp = datetime.datetime.strptime(log_timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                if log_timestamp >= one_hour_ago:
                    logs.append(log_entry)
    
    except FileNotFoundError:
        print(f"Log file '{log_file_path}' not found.")
    
    return logs