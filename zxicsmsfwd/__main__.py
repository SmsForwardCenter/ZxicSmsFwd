import sms_forwarder
import config_utils

if __name__ == '__main__':
    conf = config_utils.get_config('config.json')
    forwarder = sms_forwarder.SmsForwarder(conf)
    forwarder.start()
    #forwarder.do_loop_get_sms_task()