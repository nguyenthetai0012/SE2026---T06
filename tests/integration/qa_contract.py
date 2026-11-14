"""QA fixture oracle for the PROPOSED MQTT contract; not a Backend validator."""
from datetime import datetime, timedelta
import json
import math
import re
from uuid import UUID

ID = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
UTC = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z')
REGISTRY = {'A-01': 'BLD-A', 'A-02': 'BLD-A', 'B-01': 'BLD-B'}
REQUIRED = {'schema_version', 'message_id', 'building_id', 'device_id',
            'event_time', 'metric', 'value'}


def timestamp(value):
    if not isinstance(value, str) or not UTC.fullmatch(value):
        raise ValueError('INVALID_TIMESTAMP')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('INVALID_TIMESTAMP') from error


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError('INVALID_VALUE')


def validate(raw, topic, received_at):
    if len(raw) > 4096:
        raise ValueError('PAYLOAD_TOO_LARGE')
    try:
        payload = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_keys,
                             parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('INVALID_JSON') from error
    if not isinstance(payload, dict):
        raise ValueError('INVALID_SCHEMA')
    metric = payload.get('metric')
    expected = REQUIRED | ({'interval_start'} if metric == 'energy_kwh' else set())
    if set(payload) != expected or payload.get('schema_version') != '1.0':
        raise ValueError('INVALID_SCHEMA')
    if metric not in ('power_kw', 'energy_kwh'):
        raise ValueError('INVALID_METRIC')
    for key in ('building_id', 'device_id'):
        if not isinstance(payload[key], str) or not ID.fullmatch(payload[key]):
            raise ValueError('INVALID_ID')
    try:
        UUID(payload['message_id'])
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError('INVALID_MESSAGE_ID') from error
    value = payload['value']
    if type(value) not in (float, int) or value < 0:
        raise ValueError('INVALID_VALUE')
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError('INVALID_VALUE')
    end = timestamp(payload['event_time'])
    if end > timestamp(received_at) + timedelta(seconds=5):
        raise ValueError('FUTURE_TIMESTAMP')
    if metric == 'energy_kwh' and timestamp(payload['interval_start']) >= end:
        raise ValueError('INVALID_INTERVAL')
    expected_topic = f"campus/v1/{payload['building_id']}/{payload['device_id']}/readings"
    if topic != expected_topic:
        raise ValueError('TOPIC_MISMATCH')
    if REGISTRY.get(payload['device_id']) != payload['building_id']:
        raise ValueError('UNKNOWN_DEVICE_OR_MAPPING')
    return payload
