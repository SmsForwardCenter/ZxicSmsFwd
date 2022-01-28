#!/usr/bin/python3

import requests
import json
import urllib
import threading
import time
import base64
import time

def convert_sms_content_to_string(content_bytes_string):
    result = ''
    for i in range(0, len(content_bytes_string), 4):
        result += chr(int(content_bytes_string[i:i+4], 16))
    return result

def convert_string_to_sms_content(pending_str):
    result = ''
    for i in pending_str:
        chr_hex = hex(ord(i))[2:].upper()
        padding = 4 - len(chr_hex)
        if padding > 0:
            for i in range(0, padding):
                chr_hex = '0' + chr_hex
        result += chr_hex
    return result

def get_current_time(split_char = ','):
    current_time = time.localtime()
    timezone_offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
    timezone_int = int(timezone_offset / 60 / 60 * -1)
    timezone = str(timezone_int) if (timezone_int < 0) else f'+{timezone_int}'
    t = time.strftime(f'%y{split_char}%m{split_char}%d{split_char}%H{split_char}%M{split_char}%S{split_char}{timezone}', current_time)
    return t

def parse_zxic_datetime(time, split_char = ','):
    time = time.split(split_char)
    return f'20{time[0]}-{time[1]}-{time[2]} {time[3]}:{time[4]}:{time[5]}'

class ZxicUtils:

    __CURRENT_PASSWORD__ = list()
    SAVEFILE = 'pwdchk-savefile.txt'
    TIMEOUT = 5

    def __init__(self, target_ip, modem_type = 'zxic_web_new', min_length = 4) -> None:
        self.TARGET_IP = target_ip
        if modem_type == 'zxic_web_new':
            self.PROC_URL = f'http://{target_ip}/reqproc/proc_post'
            self.PROC_GET_URL = f'http://{target_ip}/reqproc/proc_get'
        elif modem_type == 'zxic_web_old':
            self.PROC_URL = f'http://{target_ip}/goform/goform_set_cmd_process'
            self.PROC_GET_URL = f'http://{target_ip}/goform/goform_get_cmd_process'
        else:
            raise RuntimeError(f'Unknown modem type: {modem_type}')
        self.lock = threading.Lock()
        self.session = requests.Session()
        self.IS_STARTED = False
        self.IS_LOGGED = False
        self.avaliable_chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_=+{[]}\\|;:\'",<.>/?`~!@#$%^&*()'
        savefile = self.load_savefile()
        if savefile == None:
            for i in range(0, min_length):
                self.__CURRENT_PASSWORD__.append(self.avaliable_chars[0])
        else:
            self.__CURRENT_PASSWORD__ = list(savefile)
        self.session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0'
        })

    def load_savefile(self):
        try:
            f = open(self.SAVEFILE, 'r')
            content = f.read()
            f.close()
        except:
            return None
        return content

    def save_to_file(self):
        f = open(self.SAVEFILE, 'w')
        f.write(''.join(self.__CURRENT_PASSWORD__))
        f.close()

    def check_password(self, password) -> bool:
        resp = self.session.post(
            self.PROC_URL,
            timeout=self.TIMEOUT,
            data=urllib.parse.urlencode({
                'goformId': 'ALK_SIM_SELECT_WITH_PWD',
                'sim_select': '1',
                'admin_pwd': password
            })
        )
        resu = json.loads(resp.text)
        return resu['result'] != 'failure'
    
    def login(self, password = None) -> bool:
        if password == None:
            password = self.__password
        else:
            self.__password = password
        resp = self.session.post(
            self.PROC_URL,
            timeout=self.TIMEOUT,
            data=urllib.parse.urlencode({
                'goformId': 'LOGIN',
                'password': base64.b64encode(password.encode('utf-8'))
            })
        )
        resu = json.loads(resp.text)
        return resu['result'] == '0'
    
    def check_login(self) -> bool:
        params = urllib.parse.urlencode({
            'multi_data': '1',
            'sms_received_flag_flag': '0',
            'sts_received_flag_flag': '0',
            'cmd': 'loginfo',
        })
        resp = self.session.get(
            self.PROC_GET_URL + '?' + params,
            timeout=self.TIMEOUT
        )
        resu = json.loads(resp.text)
        is_login = resu['loginfo'] == 'ok'
        self.IS_LOGGED = is_login
        return is_login
    
    def get_network_status(self) -> bool:
        params = urllib.parse.urlencode({
            'multi_data': '1',
            'sms_received_flag_flag': '0',
            'sts_received_flag_flag': '0',
            'cmd': 'network_provider,signalbar,network_type,sub_network_type',
        })
        resp = self.session.get(
            self.PROC_GET_URL + '?' + params,
            timeout=self.TIMEOUT
        )
        resu = json.loads(resp.text)
        return resu

    def check_login(self) -> bool:
        params = urllib.parse.urlencode({
            'multi_data': '1',
            'sms_received_flag_flag': '0',
            'sts_received_flag_flag': '0',
            'cmd': 'loginfo',
        })
        resp = self.session.get(
            self.PROC_GET_URL + '?' + params,
            timeout=self.TIMEOUT
        )
        resu = json.loads(resp.text)
        is_login = resu['loginfo'] == 'ok'
        self.IS_LOGGED = is_login
        return is_login

    def get_sms_count(self):
        params = urllib.parse.urlencode({
            'cmd': 'sms_capacity_info',
        })
        resp = self.session.get(
            self.PROC_GET_URL + '?' + params,
            timeout=self.TIMEOUT
        )
        resu = json.loads(resp.text)
        return {
            'max_sms_storage': resu['sms_nv_total'],
            'max_sim_sms_storage': resu['sms_sim_total'],
            'sms_inbox_total': resu['sms_nv_rev_total'],
            'sms_sim_inbox_total': resu['sms_sim_rev_total'],
            'sms_send_total': resu['sms_nv_send_total'],
            'sms_sim_send_total': resu['sms_sim_send_total'],
            'sms_draft_total': resu['sms_nv_draftbox_total'],
            'sms_sim_draft_total': resu['sms_sim_draftbox_total']
        }

    def get_sms_list(self):
        params = urllib.parse.urlencode({
            'cmd': 'sms_data_total',
            'page': '0',
            'data_per_page': '500',
            'mem_store': '1',
            'tags': '10',
            'order_by': 'order by id desc'
        })
        resp = self.session.get(
            self.PROC_GET_URL + '?' + params,
            timeout=self.TIMEOUT
        )
        resu = json.loads(resp.text)['messages']
        for i in resu:
            i['content'] = convert_sms_content_to_string(i['content'])
            i['date'] = parse_zxic_datetime(i['date'])
        return resu

    def send_sms(self, phone_number, content):
        params = urllib.parse.urlencode({
            'goformId': 'SEND_SMS',
            'notCallback': 'true',
            'Number': phone_number,
            'sms_time': get_current_time(';'),
            'MessageBody': convert_string_to_sms_content(content),
            'ID': '-1',
            'encode_type': 'UNICODE'
        })
        resp = self.session.post(
            self.PROC_URL,
            timeout=self.TIMEOUT,
            data=params
        )
        resu = json.loads(resp.text)
        return resu['result'] == 'success'

    def mark_sms_as_read(self, sms_id):
        params = urllib.parse.urlencode({
            'goformId': 'SET_MSG_READ',
            'msg_id': sms_id,
            'tag': '0'
        })
        resp = self.session.post(
            self.PROC_URL,
            timeout=self.TIMEOUT,
            data=params
        )
        resu = json.loads(resp.text)
        return resu['result'] == 'success'

    def delete_sms(self, sms_id):
        params = urllib.parse.urlencode({
            'goformId': 'DELETE_SMS',
            'msg_id': sms_id,
            'notCallback': 'true'
        })
        resp = self.session.post(
            self.PROC_URL,
            timeout=self.TIMEOUT,
            data=params
        )
        resu = json.loads(resp.text)
        return resu['result'] == 'success'

    def disable_wifi_ap(self):
        return self.change_wifi_ap(False)

    def enable_wifi_ap(self):
        return self.change_wifi_ap(True)

    def change_wifi_ap(self, enable_wifi):
        if enable_wifi:
            enable_wifi = 0
        else:
            enable_wifi = 1
        params = urllib.parse.urlencode({
            'goformId': 'SET_WIFI_INFO',
            'wifiEnabled': enable_wifi
        })
        resp = self.session.post(
            self.PROC_URL,
            timeout=self.TIMEOUT,
            data=params
        )
        resu = json.loads(resp.text)
        return resu['result'] == 'success'

    def change_network_auto_connect(self, auto_connect):
        if auto_connect:
            auto_connect = 'auto_dial'
        else:
            auto_connect = 'manual_dial'
        params = urllib.parse.urlencode({
            'goformId': 'SET_WIFI_INFO',
            'wifiEnabled': auto_connect
        })
        resp = self.session.post(
            self.PROC_URL,
            timeout=self.TIMEOUT,
            data=params
        )
        resu = json.loads(resp.text)
        return resu['result'] == 'success'

    def change_network_status(self, is_connect):
        if is_connect:
            is_connect = 'CONNECT_NETWORK'
        else:
            is_connect = 'DISCONNECT_NETWORK'
        params = urllib.parse.urlencode({
            'goformId': is_connect,
            'notCallback': 'true'
        })
        resp = self.session.post(
            self.PROC_URL,
            timeout=self.TIMEOUT,
            data=params
        )
        resu = json.loads(resp.text)
        return resu['result'] == 'success'

    def get_next_password(self):
        with self.lock:
            current_password = ''.join(self.__CURRENT_PASSWORD__)
            current_pos = 0
            while True:
                if not self.IS_LOGGED:
                    time.sleep(1)
                    continue
                if current_pos > len(self.__CURRENT_PASSWORD__) - 1:
                    self.__CURRENT_PASSWORD__ += self.avaliable_chars[0]
                    break
                if self.__CURRENT_PASSWORD__[current_pos] == self.avaliable_chars[-1]:
                    self.__CURRENT_PASSWORD__[current_pos] = self.avaliable_chars[0]
                    current_pos += 1
                    continue
                is_matched = False
                for i in self.avaliable_chars:
                    if is_matched:
                        self.__CURRENT_PASSWORD__[current_pos] = i
                        break
                    if self.__CURRENT_PASSWORD__[current_pos] == i:
                        is_matched = True
                break
        return current_password

    def check_password_loop(self) -> None:
        while self.IS_STARTED:
            current_password = self.get_next_password()
            print(f'current password: {current_password}')
            while self.IS_STARTED:
                try:
                    if self.check_password(current_password):
                        print(f'correct password: {current_password}')
                        self.IS_STARTED = False
                        return
                    break
                except:
                    pass

    def check_login_loop(self) -> None:
        wait_times = 0
        while self.IS_STARTED:
            if wait_times >= 10:
                wait_times = 0
                self.save_to_file()
            try:
                if self.check_login():
                    self.login()
            except:
                pass
            time.sleep(1)
            wait_times += 1

    def start(self, threads = 6):
        self.IS_STARTED = True
        check_login_thread = threading.Thread(target=self.check_login_loop)
        check_login_thread.start()
        check_threads = []
        for i in range(0, threads):
            print(f'Starting Thread {i}...')
            _thr = threading.Thread(target=self.check_password_loop)
            check_threads.append(_thr)
            _thr.start()
            print(f'Thread {i} started.')
            time.sleep(0.3)
        try:
            while self.IS_STARTED:
                time.sleep(1)
        except KeyboardInterrupt:
            self.IS_STARTED = False
            print('Please wait for all threads to finish their work...')
            for i in check_threads:
                i.join()
            self.save_to_file()
    
    def common_disable_network(self):
        self.change_wifi_ap(False)
        self.change_network_auto_connect(False)
        self.change_network_status(False)

if __name__ == '__main__':
    host_ip = '172.17.0.1'
    checker = ZxicUtils(host_ip)
    checker.login('admin')
    checker.common_disable_network()
    print(checker.get_sms_list())
    #checker.start()