# 基于中兴方案的 LTE USB Dongle 的短信转发器

## 配置文件

配置文件以 JSON 为主要结构，下面是一个配置文件的范本。

```
{
    "telegram_host": "api.telegram.org",
    "bot_token": "1234567890:VGhpcyBib3QgdG9rZW4gaXMgaW52YWxpZC4",
    "telegram_chat_id": "1145141919",
    "trust_command_from": [
        1145141919
    ],
    "modems": [
        {
            "type": "zxic_web_new",
            "name": "13800138000",
            "modem_ip": "172.17.0.1",
            "login_password": "admin"
        },
        {
            "type": "zxic_web_old",
            "name": "15666666666",
            "modem_ip": "172.17.0.5",
            "login_password": "admin"
        }
    ]
}

```

### 配置文件键说明

|         键         |                            说明                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------------- |
| telegram_host      | Telegram Bot API 的主机头，对于处于中国的用户可能有帮助。                                           |
| bot_token          | Telegram Bot 的 Token，用于转发短信至 Telegram。                                                  |
| telegram_chat_id   | 需要转发至的聊天 ID，可以是用户 ID、群组 ID 或频道 ID。建议不要转发到除用户以外的地方，以避免隐私泄露。 |
| trust_command_from | 可信任命令来源的发送者的 ID，只能是用户 ID，只有处于这个列表里面的用户才能使用机器人命令，例如发送短信。 |
| modems             | 接受短信的设备，支持多个设备，以设备名（name）区分                                                  |

### Modems 配置键说明

|         键         |                            说明                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------------- |
| type               | 设备固件类型，只能是 `zxic_web_new` 或者 `zxic_web_old` 两个值。                                   |
| name               | 设备名称，用于在发送短信是区别不同的设备。                                                          |
| modem_ip           | Modem 的后台管理界面的 IP。                                                                       |
| login_password     | 登录 Modem 后台管理界面的密码。                                                                   |

Modem 的 type 用于区分不同的固件类型，因为两种固件访问的 URL 不一样。
需要确认设备是哪种固件类型只需要用浏览器打开后台管理界面，
然后按下 F12 按钮打开开发者工具，点到网络 Tab，
查看刷出来的内容是 `proc_get` 还是 `goform_get_cmd_process`。
如果是 `proc_get`，type 则填写 `zxic_web_new`，
如果是 `goform_get_cmd_process`，type 则填写 `zxic_web_old`。


## 机器人命令参考

`/get_devices`：无参数，用于获取设备列表及设备状态。

`/send_sms`：发送短信，格式为 `/send_sms[空格]设备名称[空格]接收人手机号[空格]短信内容`，例如 `/send_sms 13800138000 10086 cxll` 是使用名为“13800138000”的设备向“10086”发送“cxll”