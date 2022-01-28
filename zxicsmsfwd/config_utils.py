import json

def get_config(filename):
    f = open(filename, 'r')
    content = f.read()
    f.close()
    conf = json.loads(content)
    return fill_default_config(conf)

def set_config_default_value(config, key, value):
    try:
        config[key]
    except KeyError:
        config[key] = value

def fill_default_config(config):
    set_config_default_value(config, 'telegram_host', 'api.telegram.org')
    set_config_default_value(config, 'bot_token', '')
    set_config_default_value(config, 'telegram_chat_id', '')
    set_config_default_value(config, 'trust_command_from', [])
    set_config_default_value(config, 'modems', [])
    return config