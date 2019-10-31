#!/usr/bin/env python3

import configparser
import io
import paho.mqtt.client as mqtt
import json

CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIG_INI = "config.ini"

class SnipsConfigParser(configparser.ConfigParser):
    def to_dict(self):
        return {section: {option_name: option for option_name, option in self.items(section)} for section in self.sections()}


def read_configuration_file(configuration_file):
    try:
        with io.open(configuration_file, encoding=CONFIGURATION_ENCODING_FORMAT) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.read_file(f)
            return conf_parser.to_dict()
    except (IOError, ConfigParser.Error):
        return dict()


conf = read_configuration_file(CONFIG_INI)
print("Conf:", conf)

# MQTT client to connect to the bus
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    client.subscribe("hermes/intent/#")


def message(client, userdata, msg):
    data = json.loads(msg.payload.decode("utf-8"))
    session_id = data['sessionId']
    try:
        slots = {slot['slotName']: slot['value']['value'] for slot in data['slots']}
        intentname = data['intent']['intentName'].split(':')[1]

        module = slots['MODULE']

        if module == 'ALL':
            mode = 'ALL'
        elif 'PAGE' in module:
            mode = 'PAGE'
        else:
            mode = 'STANDARD'

        if intentname == 'MM_Hide' and (mode == 'STANDARD' or mode == 'ALL'):
            action = {'module':module}
        elif intentname == 'MM_Show' and (mode == 'STANDARD' or mode == 'PAGE') :
            action = {'module':module}
        elif intentname == 'MM_Move' and mode == 'STANDARD':
            position = slots['POSITION']
            action = {'module':module, 'position':position}
        else:
            raise UnboundLocalError("Das kann ich leider nicht")
        say(session_id, "Mache ich")
        MM2(intentname, action)
    except UnboundLocalError, e:
        say(session_id, e.message)

    except KeyError:
        say(session_id, "Ich habe dich leider nicht verstanden.")

def MM2(intentname, action):
    mqtt_client.publish(('external/MagicMirror2/HideShowMove/' + intentname),
                        json.dumps(action))

def say(session_id, text):
    mqtt_client.publish('hermes/dialogueManager/endSession',
                        json.dumps({'text': text, "sessionId": session_id}))


if __name__ == "__main__":
    mqtt_client.on_connect = on_connect
    mqtt_client.message_callback_add("hermes/intent/maxbachmann:MM_Hide/#", message)
    mqtt_client.message_callback_add("hermes/intent/maxbachmann:MM_Show/#", message)
    mqtt_client.message_callback_add("hermes/intent/maxbachmann:MM_Move/#", message)
    mqtt_client.connect("localhost", "1883")
    mqtt_client.loop_forever()
