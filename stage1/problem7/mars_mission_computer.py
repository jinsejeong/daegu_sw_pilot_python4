"""Mars mission computer that reports sensor readings periodically."""
# 이 모듈 전체의 역할을 설명하는 docstring
# "화성 기지의 미션 컴퓨터가 주기적으로 센서 값을 보고한다"는 뜻

import json      # 딕셔너리(dict) 데이터를 JSON 문자열로 변환하기 위해 사용
import random    # 랜덤한 센서 값을 만들어내기 위해 사용 (실제 센서가 없으니 가짜 값 생성)
import time      # time.sleep()으로 일정 시간 대기시키기 위해 사용


class DummySensor:
    """A dummy sensor that produces randomized Mars base env values."""
    # 실제 센서 장치가 없을 때, 그 역할을 흉내내는 "가짜(dummy) 센서" 클래스

    def __init__(self):
        # 클래스가 객체로 생성될 때 자동으로 실행되는 생성자(constructor)
        # self는 "이 객체 자기 자신"을 가리키는 참조
        self.env_values = {
            # 6가지 환경 값을 저장할 딕셔너리, 초기값은 전부 0
            'mars_base_internal_temperature': 0,   # 기지 내부 온도
            'mars_base_external_temperature': 0,   # 기지 외부 온도
            'mars_base_internal_humidity': 0,      # 기지 내부 습도
            'mars_base_external_illuminance': 0,   # 기지 외부 광량(조도)
            'mars_base_internal_co2': 0,           # 기지 내부 이산화탄소 농도
            'mars_base_internal_oxygen': 0,        # 기지 내부 산소 농도
        }

    def set_env(self):
        """Fill env_values with random values within their valid range."""
        # 각 항목에 대해 "그럴듯한 범위" 안에서 랜덤 값을 생성해 채워 넣는 메서드

        self.env_values['mars_base_internal_temperature'] = (
            random.randint(18, 30))
        # randint(18, 30): 18~30 사이 정수 중 하나를 뽑음 (사람이 살기 적당한 실내온도 범위 흉내)

        self.env_values['mars_base_external_temperature'] = (
            random.randint(0, 21))
        # 화성 표면은 기지 내부보다 더 춥고 변화가 크다고 가정한 범위

        self.env_values['mars_base_internal_humidity'] = (
            random.randint(50, 60))
        # 실내 습도는 50~60% 사이로 비교적 좁은 범위로 설정 (쾌적한 습도대)

        self.env_values['mars_base_external_illuminance'] = (
            random.randint(500, 715))
        # 조도(lux) 값, 정수 단위이므로 randint 사용

        self.env_values['mars_base_internal_co2'] = (
            round(random.uniform(0.02, 0.1), 4))
        # uniform(0.02, 0.1): 0.02~0.1 사이의 "실수(float)"를 랜덤으로 뽑음
        # round(..., 4): 소수점 4자리까지 반올림 (CO2 농도는 %로 표현 시 매우 작은 값이라 정밀도가 필요)

        self.env_values['mars_base_internal_oxygen'] = (
            round(random.uniform(4, 7), 2))
        # 산소 농도는 4~7% 사이 실수, 소수점 2자리까지 반올림

    def get_env(self):
        """Return the current env_values dictionary."""
        return self.env_values
        # 현재 저장된 env_values 딕셔너리를 그대로 반환 (getter 역할)


class MissionComputer:
    """Collects sensor data and reports it in JSON every 5 seconds."""
    # 실제로 센서 값을 "수집해서 출력"하는 역할을 하는 클래스

    def __init__(self):
        # MissionComputer도 자기만의 env_values를 하나 가짐 (DummySensor와는 별개의 저장소)
        self.env_values = {
            'mars_base_internal_temperature': 0,
            'mars_base_external_temperature': 0,
            'mars_base_internal_humidity': 0,
            'mars_base_external_illuminance': 0,
            'mars_base_internal_co2': 0,
            'mars_base_internal_oxygen': 0,
        }

    def get_sensor_data(self):
        """Read ds's values, print them as JSON, and repeat every 5s."""
        try:
            # try 블록: 예외(에러)가 발생할 수 있는 코드를 감싸서 처리하기 위함
            while True:
                # 무한 루프: Ctrl+C로 멈추기 전까지 계속 반복 실행
                ds.set_env()
                # 전역 변수 ds(DummySensor 객체)의 set_env()를 호출해 새로운 랜덤 값 생성

                self.env_values = ds.get_env()
                # ds가 만든 값을 가져와서 MissionComputer 자신의 env_values에 저장

                print(json.dumps(self.env_values, indent=4))
                # json.dumps(): 파이썬 딕셔너리를 JSON 형식의 "문자열"로 변환
                # indent=4: 들여쓰기 4칸으로 예쁘게(pretty) 출력되도록 설정

                time.sleep(5)
                # 5초 동안 프로그램 실행을 멈춤 (5초마다 한 번씩 보고하는 효과)

        except KeyboardInterrupt:
            # 사용자가 Ctrl+C를 눌러 강제 종료를 시도했을 때 발생하는 예외를 처리
            print('System stopped….')
            # 에러 메시지 대신 깔끔하게 종료 메시지를 출력


ds = DummySensor()
# DummySensor 클래스의 인스턴스(객체)를 하나 생성, 전역 변수 ds에 저장
# 이 ds 객체가 MissionComputer.get_sensor_data() 안에서 사용됨

RunComputer = MissionComputer()
# MissionComputer 클래스의 인스턴스를 생성

RunComputer.get_sensor_data()
# 실제로 센서 데이터 수집 및 출력을 시작 (무한 루프 진입)