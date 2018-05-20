import psutil
from flask import Flask, request
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS, cross_origin
import json
import time
import threading

app = Flask(__name__)
CORS(app)
api = Api(app)


parser = reqparse.RequestParser()
parser.add_argument('type', action='append')
parser.add_argument('pid', action='append')
parser.add_argument('process_name', action='append')
parser.add_argument('duration')
parser.add_argument('percpu')
parser.add_argument('system_cpu_interval')
parser.add_argument('process_cpu_interval')
parser.add_argument('process_cpu_init')

parser.add_argument('info')

parser.add_argument('count')
parser.add_argument('action')

parser.add_argument('testfile')
parser.add_argument('test_flag')
parser.add_argument('app_used')
parser.add_argument('doc_used')



def get_pid_from_name(p_name):
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name'])
        except psutil.NoSuchProcess:
            pass
        else:
            if p_name == pinfo['name']:
                return pinfo['pid']
    return None

class ProcessHandle (threading.Thread):
    def __init__(self, pid, p, interval, p_name=None):
        threading.Thread.__init__(self)
        self.p = p
        self.pid = pid
        self.interval = interval
        self.process_name = p_name
        self.process_info = {}
        
    def run(self):
        if self.p == None:
            self.process_info = {'name' : self.process_name, \
                             'pid' : 0, \
                             'thread_nums' : 0, \
                             'cpu_percent' : 0, \
                             'handle_nums' : 0, \
                             'memory' : 0}
            return
        if self.interval != -1:
            cpu_percent = self.p.cpu_percent(self.interval)
        else:
            cpu_percent = -1
        mem_info = self.p.memory_info()
        thread_nums = self.p.num_threads()
        handle_nums = self.p.num_handles()
        self.process_info = {'name' : self.p.name(), \
                             'pid' : self.pid, \
                             'thread_nums' : thread_nums, \
                             'cpu_percent' : cpu_percent, \
                             'handle_nums' : handle_nums, \
                             'memory' : mem_info}

    @property
    def info(self):
        return self.process_info

g_p = {}
def process_info_get(pid, p_interval, p_name=None):
    global g_p
    thread_l = []
    if pid not in g_p.keys():
        if pid != None:
            g_p[pid] = psutil.Process(int(pid))
            p = g_p[pid]
            p_interval = 0
    if pid == None:
        p = None
    else:
        p = g_p[pid]

    thread1 = ProcessHandle(pid, p, p_interval, p_name)
    return thread1


class FXPsutil(Resource):
    def get(self):
        return {'a':'b'}

    def post(self):
        info = {}
        info['time'] = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())
        interval = 0
        percpu = False
        
        args = parser.parse_args()
        if args['info'] != None:
            info['info'] = args['info']

        if args['testfile'] != None:
            info['testfile'] = args['testfile']
            
        type_list = args['type']
        if type_list == None:
            info['error'] = 'type is null'
            return info, 201
        for type_s in type_list:
            if args['percpu'] != None:
                percpu = True
            if type_s == 'cpu_info':
                cpu_cnt = psutil.cpu_count()
                info['cpu_count'] = cpu_cnt
            elif type_s == 'cpu_percent':
                if args['system_cpu_interval'] != None:
                    interval = int(args['system_cpu_interval'])
                cpu_percent = psutil.cpu_percent(interval, percpu)
                info['cpu_percent'] = cpu_percent
            elif type_s == 'cpu_times':
                pass
            elif type_s == 'memory':
                virtual_memory = psutil.virtual_memory()
                swap_memory = psutil.swap_memory()
                info['memory'] = {'vitrual':virtual_memory, 'swap':swap_memory}
            elif type_s == 'process':
                process_interval = 0
                if args['process_cpu_interval'] != None:
                    process_interval = int(args['process_cpu_interval'])

                if args['process_cpu_init'] != None:
                    global g_p
                    g_p = {}

                process_info_l = []
                thread_l = []
                if args['pid'] != None:
                    for p_pid in args['pid']:
                        thread_l.append(process_info_get(p_pid, process_interval))
                else:
                    if args['process_name'] == None:
                        return info
                    for p_name in args['process_name']:
                        pid = get_pid_from_name(p_name)
                        thread_l.append(process_info_get(pid, process_interval, p_name))
                        
                for process_p in thread_l:
                    process_p.start()
                for process_p in thread_l:
                    process_p.join()

                for process_p in thread_l:
                    process_info_l.append(process_p.info)
                info['process'] = process_info_l
                
        return info, 200


class FXPsutilSort(Resource):
    p_dic = {}
    def get(self):
        return {'a':'b'}

    def post(self):
        info = {}
        info['time'] = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())
        interval = 0
        percpu = False
        
        args = parser.parse_args()
                        
        if args['action'] == 'start':
            FXPsutilSort.p_dic = {}
            for proc in psutil.process_iter():
                try:
                    pinfo = proc.as_dict(attrs=['pid', 'name'])
                except psutil.NoSuchProcess:
                    pass
                else:
                    pid = pinfo['pid']
                    FXPsutilSort.p_dic[pid] = psutil.Process(pid)
                pc_d = FXPsutilSort.p_dic[pid].cpu_percent(0)
                print(pc_d)
        elif args['action'] == 'end':
            for p_k in FXPsutilSort.p_dic.keys():
                try:
                    pc_d = FXPsutilSort.p_dic[p_k].cpu_percent(0)
                    info[p_k] = {'name':FXPsutilSort.p_dic[p_k].name(), 'percent':pc_d}
                except:
                    info[p_k] = {'percent':-1}
        return info, 200

class FXAppTime(Resource):
    _ret_open_info = []
    _ret_close_info = []
    _ret_flag_info = []
    def get(self):
        info = {}
        info['time'] = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())
        if len(FXAppTime._ret_open_info) == 0:
            info['open'] = {}
        else:
            info['open'] = FXAppTime._ret_open_info.pop()
    
        if len(FXAppTime._ret_close_info) == 0:
            info['close'] = {}
        else:
            info['close'] = FXAppTime._ret_close_info.pop()

        if len(FXAppTime._ret_flag_info) == 0:
            info['test_flag'] = {}
        else:
            info['close'] = {}
            info['open'] = {}
            info['test_flag'] = FXAppTime._ret_flag_info.pop()
        print(info)
        return info, 200
        

    def post(self):
        info = {}
        interval = 0
        percpu = False
        
        args = parser.parse_args()
        info['app_used'] = args['app_used']
        info['doc_used'] = args['doc_used']
        info['testfile'] = args['testfile']
        
        if args['action'] == 'open':
            FXAppTime._ret_open_info.append(info)
        elif args['action'] == 'close':
            FXAppTime._ret_close_info.append(info)
        else:
            info['flag'] = args['test_flag']
            FXAppTime._ret_flag_info.append(info)

        return {'ret':0}, 200

api.add_resource(FXPsutil, '/psutil')
api.add_resource(FXPsutilSort, '/cpu-all')
api.add_resource(FXAppTime, '/fxapp-time')

if __name__ == '__main__':
    app.run(debug=True, port=9092, host="0.0.0.0")
