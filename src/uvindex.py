import requests
import json
import boto3
import os
from base64 import b64decode


def lambda_handler(event, context):
    application_id = get_encrypted_data('application_id')
    session_app_id = event['session']['application']['applicationId']
    request_type = event['request']['type']
    request = event['request']
    session = event['session']

    if session_app_id != application_id:
        raise ValueError("Invalid Application ID")

    if request_type == "LaunchRequest":
        return get_welcome_response()
    elif request_type == "IntentRequest":
        return on_intent(request, session)


def get_encrypted_data(key):
    encrypted_key = os.environ[key]
    print encrypted_key
    decrypted_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
                                                encrypted_key))['Plaintext']
    return decrypted_key


def get_welcome_response():
    card_title = "UV Index"
    speech_output = "Welcome to the UV Index skill. You can ask me for the " \
                    "UV index for a zip code"
    reprompt_text = "For examples, get the UV Index by asking, what is the " \
                    "UV index for 88130"
    should_end_session = False
    speechlet_response = build_speechlet_response(card_title, speech_output,
                                                  reprompt_text,
                                                  should_end_session)
    return build_response({}, speechlet_response)


def on_intent(intent_request, session):
    intent_name = intent_request['intent']['name']

    if intent_name == "GetUVIndex":
        zip_code = intent_request['intent']['slots']['ZipCode']['value']
        city, state, uv_index = get_wunderground_data(zip_code)
        return get_response(uv_index, city, state)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif (intent_name == "AMAZON.CancelIntent" or
          intent_name == "AMAZON.StopIntent"):
        return end_session()


def get_wunderground_data(zip_code):
    wunderground_api_key = get_encrypted_data('wunderground_api_key')
    url = "https://api.wunderground.com/api/{0}/forecast/geolookup/" \
          "conditions/q/{1}.json".format(wunderground_api_key, zip_code)
    r = requests.get(url)
    data = json.loads(r.text)
    current_uv = data['current_observation']['UV']
    city = data['location']['city']
    state = data['location']['state']
    return city, state, current_uv


def get_response(uv_index, city, state):
    card_title = "UV Index for {0}, {1}".format(city, state)
    should_end_session = False
    speech_output = "The UV Index for {0}, {1} is currently" \
                    "{2}".format(city, state, uv_index)
    speechlet_response = build_speechlet_response(card_title, speech_output,
                                                  None, should_end_session)
    return build_response({}, speechlet_response)


def end_session():
    card_title = "UV Index - Thanks"
    speech_output = "Thank you for using the UV index skill. See you " \
                    "next time!"
    should_end_session = True
    speechlet_response = build_speechlet_response(card_title, speech_output,
                                                  None, should_end_session)
    return build_response({}, speechlet_response)


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": output
        },
        "card": {
            "type": "Simple",
            "title": title,
            "content": output
        },
        "reprompt": {
            "outSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": speechlet_response
    }
