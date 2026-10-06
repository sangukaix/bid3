"""Lossless repeated-row packing, adapted from the reviewed TP2-5 method."""
import json

TABLE = '__bid3_table_v1__'
MAPPING = '__bid3_mapping_v1__'
READING_RULE = ('근거의 __bid3_table_v1__는 무손실 표입니다. columns는 열 이름이며 rows의 배열은 '
                '같은 순서의 셀 값입니다. __bid3_mapping_v1__는 원래 객체의 [키, 값] 쌍입니다. '
                '문자열·수치·null·출처를 원래 값으로 읽으세요. 생략이나 요약이 아닙니다. ')


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def pack(value):
    if isinstance(value, dict):
        if TABLE in value or MAPPING in value:
            return {MAPPING: [[key, pack(item)] for key, item in value.items()]}
        return {key: pack(item) for key, item in value.items()}
    if not isinstance(value, list): return value
    encoded = [pack(item) for item in value]
    if len(value) < 3 or not all(isinstance(item, dict) for item in value): return encoded
    columns = list(value[0])
    if not columns or any(set(item) != set(columns) for item in value): return encoded
    table = {TABLE: {'columns': columns, 'rows': [[pack(item[key]) for key in columns] for item in value]}}
    return table if len(dumps(table).encode()) + 80 < len(dumps(encoded).encode()) else encoded


def unpack(value):
    if isinstance(value, list): return [unpack(item) for item in value]
    if not isinstance(value, dict): return value
    if TABLE in value:
        table = value[TABLE]
        return [{key: unpack(cell) for key, cell in zip(table['columns'], row, strict=True)} for row in table['rows']]
    if MAPPING in value: return {key: unpack(item) for key, item in value[MAPPING]}
    return {key: unpack(item) for key, item in value.items()}


def packed_json(value):
    encoded = pack(value)
    if unpack(encoded) != value: raise ValueError('근거 압축 검증에 실패했습니다.')
    return dumps(encoded)
