import time
import requests
import json
import zxic_utils
#import traceback
import threading

class SmsForwarder:
    UPDATE_ID = 0
    TIMEOUT = 5
    __MSG_IDS = {}

    def __init__(self, config):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        self.config = config
        self.telegram_url = f"https://{self.config['telegram_host']}/bot{self.config['bot_token']}/"
        self.LOOP_ENABLED = True
        self.init_modems()

    def init_modems(self):
        self.sms_modems = []
        for i in self.config['modems']:
            if ' ' in i['name']:
                raise RuntimeError('Device name can not contains space.')
            controller = zxic_utils.ZxicUtils(i['modem_ip'], modem_type=i['type'])
            i['modem_status'] = 'online'
            i['controller'] = controller
            try:
                self.do_modem_init(i)
            except:
                i['modem_status'] = 'offline'
                self.send_telegram_message(self.config['telegram_chat_id'], f"[设备掉线]\n设备名称：{i['name']}，Modem IP：{i['modem_ip']}")
            self.sms_modems.append(i)

    def start(self):
        cmd_recv_thread = threading.Thread(target=self.do_process_commands_task)
        cmd_recv_thread.start()
        self.do_loop_get_sms_task()

    def get_telegram_commands(self):
        resp = self.session.get(
            self.telegram_url + 'getUpdates',
            timeout=self.TIMEOUT
        )
        commands = json.loads(resp.text)
        if commands['ok']:
            return commands
        else:
            raise RuntimeError('Unknown error from Telegram api server: ' + resp.text)

    def send_telegram_message(self, chat_id, content):
        try:
            resp = self.session.post(
                self.telegram_url + 'sendMessage',
                timeout=self.TIMEOUT,
                data=json.dumps({
                'chat_id': chat_id,
                'text': content
            }))
            result = json.loads(resp.text)
        except:
            print('Send Telegram message failed.')
            return None
        if result['ok']:
            return result
        else:
            raise RuntimeError('Unknown error from Telegram api server: ' + resp.text)
    
    def do_modem_init(self, modem_controller):
        modem_controller['controller'].login(modem_controller['login_password'])
        modem_controller['controller'].common_disable_network()

    def do_get_sms_task(self):
        for ctrl in self.sms_modems:
            try:
                if not ctrl['controller'].check_login():
                    self.do_modem_init(ctrl)
                sms_list = ctrl['controller'].get_sms_list()
            except:
                if ctrl['modem_status'] == 'online':
                    ctrl['modem_status'] = 'offline'
                    self.send_telegram_message(self.config['telegram_chat_id'], f"[设备掉线]\n设备名称：{ctrl['name']}，Modem IP：{ctrl['modem_ip']}")
                continue
            if ctrl['modem_status'] == 'offline':
                ctrl['modem_status'] = 'online'
                self.do_modem_init(ctrl)
                self.send_telegram_message(self.config['telegram_chat_id'], f"[设备上线]\n设备名称：{ctrl['name']}，Modem IP：{ctrl['modem_ip']}")
            for sms in sms_list:
                if sms['tag'] == '2':
                    msg = f"✅通过 {ctrl['name']} 发送短信给 {sms['number']} 成功。"
                else:
                    msgid = f"{ctrl['name']}-{sms['id']}"
                    try:
                        msg_previous_length = self.__MSG_IDS[msgid]
                    except KeyError:
                        self.__MSG_IDS[msgid] = len(sms['content'])
                        continue
                    if msg_previous_length != len(sms['content']):
                        self.__MSG_IDS[msgid] = len(sms['content'])
                        continue
                    self.__MSG_IDS.pop(msgid)
                    msg = f"[收到短信]\n接收设备：{ctrl['name']}\n来自：{sms['number']}\n收到日期：{sms['date']}\n{sms['content']}"
                if self.send_telegram_message(self.config['telegram_chat_id'], msg) != None:
                    ctrl['controller'].delete_sms(sms['id'])
    
    def do_process_commands_task(self):
        while self.LOOP_ENABLED:
            try:
                commands = self.get_telegram_commands()
            except:
                time.sleep(5)
                continue
            for i in commands['result']:
                if i['update_id'] > self.UPDATE_ID:
                    self.UPDATE_ID = i['update_id']
                    message = i['message']
                    if message['from']['id'] not in self.config['trust_command_from']:
                        print(f"Sender {message['from']['id']} is not in trust db.")
                        continue
                    try:
                        commands_pos = message['entities']
                    except KeyError:
                        continue
                    chat_id = message['chat']['id']
                    command = None
                    for cmd in commands_pos:
                        if cmd['offset'] == 0 and cmd['type'] == 'bot_command':
                            command = message['text'][cmd['offset']:cmd['length']]
                    if command == None:
                        continue
                    elif command == '/stop':
                        self.LOOP_ENABLED = False
                    elif command == '/get_devices':
                        self.send_devices_message(chat_id)
                    elif command == '/send_sms':
                        command_params = message['text'][cmd['offset'] + cmd['length']:]
                        if len(command_params) > 2:
                            command_params = command_params[1:]
                        command_params = command_params.split(' ')
                        if len(command_params) < 3:
                            self.send_telegram_message(chat_id, 'Usage: /send_sms <device_name> <target_phone> <content>')
                            continue
                        device_name = command_params[0]
                        target_phone = command_params[1]
                        if not target_phone.isdigit():
                            self.send_telegram_message(chat_id, 'Usage: /send_sms <device_name> <target_phone> <content>')
                            continue
                        current_pos = 0
                        content = ''
                        for i in command_params:
                            current_pos += 1
                            if current_pos < 3:
                                continue
                            if current_pos == 3:
                                content = i
                            else:
                                content += ' ' + i
                        #self.send_telegram_message(chat_id, f'{device_name}, {target_phone}, {content}')
                        self.do_send_sms_task(chat_id, device_name, target_phone, content)
            time.sleep(2)

    def do_send_sms_task(self, chat_id, device_name, target_phone, content):
        has_this_modem = False
        for i in self.sms_modems:
            if i['name'] == device_name:
                has_this_modem = True
                i['controller'].send_sms(target_phone, content)
                break
        if not has_this_modem:
            self.send_telegram_message(chat_id, f'❗️发送短信失败，找不到指定的 Modem： {device_name}\n请使用 /get_devices 查看所有 Modem 的名称')

    def send_devices_message(self, chat_id):
        msg = '[设备列表]\n'
        for i in self.sms_modems:
            msg += f"📱设备名称： {i['name']}\n"
            msg += f"📟设备状态： {i['modem_status']}\n"
            msg += f"🔌IP 地址： {i['modem_ip']}\n"
            try:
                if i['modem_status'] == 'online':
                    device_status = i['controller'].get_network_status()
                    msg += f"📶运营商：{device_status['network_provider']}\n"
                    signal_num = int(device_status['signalbar'])
                    signal = ''
                    for i in range(0, signal_num):
                        signal += '⚫️'
                    for i in range(0, 5 - signal_num):
                        signal += '⚪️'
                    msg += f"📶设备信号：{signal}\n"
                    msg += f"📶网络类型：{device_status['network_type']}, {device_status['sub_network_type']}\n"
            except:
                msg += '设备状态无法取得数据。\n'
            msg += '\n'
        self.send_telegram_message(chat_id, msg)

    def do_loop_get_sms_task(self):
        while self.LOOP_ENABLED:
            try:
                self.do_get_sms_task()
                time.sleep(2)
            except KeyboardInterrupt:
                self.LOOP_ENABLED = False
                break