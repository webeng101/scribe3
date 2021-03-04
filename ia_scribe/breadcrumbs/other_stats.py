import os
import shlex
import subprocess
import psutil

from ia_scribe import scribe_globals


def get_fs_stats():
    def df_to_dict(tokenList):
        result = {}
        fsSize = tokenList[1]
        fsUsed = tokenList[2]
        fsMountPoint = tokenList[5]
        result["percent"] = round((float(fsUsed) / float(fsSize)) * 100, 2)
        result["size"] = fsSize
        result["used"] = fsUsed
        result["mount_point"] = fsMountPoint
        return result

    try:
        df_array = [
            shlex.split(x) for x in
            subprocess.check_output(["df"]).decode('utf-8').rstrip().split('\n')
        ]
        df_num_lines = df_array[:].__len__()
        df_json = []
        for row in range(1, df_num_lines):
            df_json.append(df_to_dict(df_array[row]))
        return df_json
    except Exception as e:
        print('Error {} retrieving disk telemetry'.format(e))
        return [{'error': str(e)}]


def get_dir_stats():
    def du(path):
        """disk usage in human readable format (e.g. '2,1GB')"""
        return subprocess.check_output(
            ['du', '-sh', path]
        ).decode('utf-8').split()[0]

    try:
        logs_path = os.path.expanduser('~/.kivy/logs')

        logs_size = du(logs_path)
        scribe_books_size = du(scribe_globals.BOOKS_DIR)
        return {'logs': logs_size,
                'scribe_books': scribe_books_size}
    except Exception as e:
        print('Error {} retrieving {} directory telemetry'.format(e, dir))
        return [{'error': str(e)}]


def get_uptime_stats():
    uptime_seconds = "none"
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = str(float(f.readline().split()[0]))
    return uptime_seconds


def get_temperature_stats():
    try:
        ret = [(x[0], x[1]) for x in psutil.sensors_temperatures()['coretemp']]
        return ret
    except Exception as e:
        return {'error': str(e)}


def get_cpu_stats():
    res = os.getloadavg()
    ret = [x for x in res]
    return ret


def get_nic_stats():
    lines = open("/proc/net/dev", "r").readlines()

    columnLine = lines[1]
    _, receiveCols, transmitCols = columnLine.split("|")
    receiveCols = ["recv_" + a for a in receiveCols.split()]
    transmitCols = ["trans_" + a for a in transmitCols.split()]

    cols = receiveCols + transmitCols

    faces = {}
    for line in lines[2:]:
        if line.find(":") < 0: continue
        face, data = line.split(":")
        faceData = dict(list(zip(cols, data.split())))
        faces[face] = faceData
    return faces


def get_ip_addresses():
    ips = subprocess.check_output(['hostname', '--all-ip-addresses'])
    ips = ips.decode('utf-8')
    ret = [x for x in ips.strip('\n').split(' ') if x != '']
    return ret
