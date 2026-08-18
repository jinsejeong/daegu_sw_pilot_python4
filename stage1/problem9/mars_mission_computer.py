import json               # 딕셔너리를 JSON 문자열로 변환할 때 사용
import multiprocessing    # 프로세스 단위 병렬 실행을 위해 사용
import os                 # OS 정보, CPU 코어 수 조회 등에 사용
import platform           # OS 종류, 버전, CPU 종류 등 시스템 정보 조회
import random              # 랜덤 센서 값 생성
import threading          # 스레드 단위 동시 실행을 위해 사용
import time                # sleep으로 대기 시간 조절

try:
    import psutil          # CPU/메모리 사용량, 메모리 총량 등을 가져오는 외부 라이브러리
except ImportError:
    psutil = None
    # psutil이 설치되어 있지 않은 환경에서도 프로그램이 죽지 않도록
    # import 실패 시 None으로 대체하고, 이후 코드에서 None 체크로 우회 처리


class DummySensor:
    """A dummy sensor that produces randomized Mars base env values."""
    # 실제 센서가 없는 상태에서 화성 기지 환경값을 흉내내는 가짜 센서

    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': 0,
            'mars_base_external_temperature': 0,
            'mars_base_internal_humidity': 0,
            'mars_base_external_illuminance': 0,
            'mars_base_internal_co2': 0,
            'mars_base_internal_oxygen': 0,
        }
        # 6개 환경 지표를 0으로 초기화

    def set_env(self):
        """Fill env_values with random values within their valid range."""
        self.env_values['mars_base_internal_temperature'] = (
            random.randint(18, 30))
        self.env_values['mars_base_external_temperature'] = (
            random.randint(0, 21))
        self.env_values['mars_base_internal_humidity'] = (
            random.randint(50, 60))
        self.env_values['mars_base_external_illuminance'] = (
            random.randint(500, 715))
        self.env_values['mars_base_internal_co2'] = (
            round(random.uniform(0.02, 0.1), 4))
        self.env_values['mars_base_internal_oxygen'] = (
            round(random.uniform(4, 7), 2))
        # 항목별로 정해둔 범위 안에서 랜덤값 생성
        # 정수는 randint, 소수는 uniform + round로 자릿수 제한

    def get_env(self):
        """Return the current env_values dictionary."""
        return self.env_values


class MissionComputer:
    """Collects sensor data and system status, reporting both as JSON
    on their own time intervals."""
    # 센서 데이터 + 시스템(OS/CPU/메모리) 정보를 각각 다른 주기로 출력하는 클래스

    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': 0,
            'mars_base_external_temperature': 0,
            'mars_base_internal_humidity': 0,
            'mars_base_external_illuminance': 0,
            'mars_base_internal_co2': 0,
            'mars_base_internal_oxygen': 0,
        }
        self.ds = DummySensor()
        # 이전 버전과 달리 ds를 전역 변수가 아니라
        # 인스턴스 속성(self.ds)으로 만듦
        # → run_with_processes()에서 인스턴스를 3개 만들 때
        #   서로 독립된 센서 객체를 갖게 하기 위함

    def get_sensor_data(self):
        """Read ds's values, print them as JSON, and repeat every 5s."""
        try:
            while True:
                self.ds.set_env()
                self.env_values = self.ds.get_env()
                print(json.dumps(self.env_values, indent=4))
                time.sleep(5)
                # 5초마다 센서값 갱신 + 출력
        except KeyboardInterrupt:
            print('System stopped….')

    def get_mission_computer_info(self):
        """Print OS, CPU, and memory info as JSON every 20 seconds."""
        try:
            while True:
                info = {}
                try:
                    info['os'] = platform.system()
                    # 운영체제 이름 (예: 'Linux', 'Windows')
                    info['os_version'] = platform.version()
                    # OS 세부 버전 문자열
                    info['cpu_type'] = (
                        platform.processor() or platform.machine())
                    # processor()가 빈 문자열을 줄 때가 있어서
                    # or로 machine()(아키텍처명, 예: 'x86_64')을 대체값으로 사용
                    info['cpu_cores'] = os.cpu_count()
                    # 논리 CPU 코어 개수

                    if psutil is not None:
                        info['memory_size'] = psutil.virtual_memory().total
                        # 전체 메모리 용량(byte 단위)
                    else:
                        info['memory_size'] = (
                            'unavailable (psutil not installed)')
                        # psutil 없으면 대체 메시지
                except Exception as error:
                    info['error'] = (
                        f'Failed to retrieve mission computer info: {error}')
                    # 정보 조회 중 어떤 예외가 나도 프로그램이 죽지 않고
                    # 에러 메시지를 담아 JSON으로 출력하도록 처리
                print(json.dumps(info, indent=4, ensure_ascii=False))
                # ensure_ascii=False: 한글 등 비-ASCII 문자를 유니코드 이스케이프 없이 그대로 출력
                time.sleep(20)
                # 20초마다 시스템 정보 출력 (센서보다 느린 주기)
        except KeyboardInterrupt:
            print('System stopped….')

    def get_mission_computer_load(self):
        """Print real-time CPU and memory load as JSON every 20 seconds."""
        try:
            while True:
                load = {}
                try:
                    if psutil is not None:
                        load['cpu_usage_percent'] = (
                            psutil.cpu_percent(interval=1))
                        # interval=1: 1초간 CPU 사용률을 측정해서 % 반환
                        load['memory_usage_percent'] = (
                            psutil.virtual_memory().percent)
                        # 현재 메모리 사용률(%)
                    else:
                        load['error'] = 'unavailable (psutil not installed)'
                except Exception as error:
                    load['error'] = (
                        f'Failed to retrieve mission computer load: {error}')
                print(json.dumps(load, indent=4, ensure_ascii=False))
                time.sleep(20)
        except KeyboardInterrupt:
            print('System stopped….')


def run_with_threads():
    """Run one MissionComputer's three reporting methods concurrently
    using multi-threading."""
    runComputer = MissionComputer()
    # MissionComputer 객체 1개만 생성

    thread_info = threading.Thread(
        target=runComputer.get_mission_computer_info)
    thread_load = threading.Thread(
        target=runComputer.get_mission_computer_load)
    thread_sensor = threading.Thread(target=runComputer.get_sensor_data)
    # 같은 객체의 서로 다른 메서드 3개를 각각 별도 스레드에 할당
    # → 세 메서드가 "동시에" 실행되는 것처럼 보이지만
    #   실제로는 GIL(Global Interpreter Lock) 때문에
    #   CPU 연산은 한 번에 하나씩만 처리되고 번갈아 실행됨
    #   (단, time.sleep()이나 I/O 대기 구간에서는 다른 스레드가 실행될 수 있어
    #    이런 "대기 위주" 작업엔 스레드가 잘 맞음)

    thread_info.start()
    thread_load.start()
    thread_sensor.start()
    # 세 스레드를 각각 시작 (start 호출 즉시 병렬적으로 실행 시작)

    thread_info.join()
    thread_load.join()
    thread_sensor.join()
    # join(): 해당 스레드가 끝날 때까지 메인 스레드가 기다리게 함
    # 여기선 각 스레드가 while True 무한 루프라 사실상 프로그램이 끝나지 않음
    # (Ctrl+C로 종료하기 전까지 계속 대기)


def run_with_processes():
    """Run three separate MissionComputer instances, each reporting
    its three methods concurrently using multi-processing."""
    runComputer1 = MissionComputer()
    runComputer2 = MissionComputer()
    runComputer3 = MissionComputer()
    # 완전히 독립된 MissionComputer 객체 3개 생성
    # → 스레드와 달리 프로세스는 메모리 공간을 서로 공유하지 않고
    #   각자 자기만의 메모리를 가진 별도의 파이썬 인터프리터로 실행됨
    #   → GIL의 영향을 받지 않아 진짜 CPU 병렬 처리가 가능

    processes = []
    for computer in (runComputer1, runComputer2, runComputer3):
        processes.append(multiprocessing.Process(
            target=computer.get_mission_computer_info))
        processes.append(multiprocessing.Process(
            target=computer.get_mission_computer_load))
        processes.append(multiprocessing.Process(
            target=computer.get_sensor_data))
    # 인스턴스 3개 × 메서드 3개 = 총 9개의 프로세스를 리스트에 담음

    for process in processes:
        process.start()
    # 9개 프로세스를 순서대로 전부 시작

    for process in processes:
        process.join()
    # 9개 프로세스가 모두 끝날 때까지(=Ctrl+C로 종료될 때까지) 대기


if __name__ == '__main__':
    # 이 파일이 "직접 실행"될 때만 아래 코드가 동작
    # (다른 파일에서 import될 때는 실행 안 됨)
    # run_with_threads()  # single instance, multi-thread demonstration
    run_with_processes()  # 3 instances, multi-process demonstration
    # 현재는 멀티프로세싱 버전만 실행하도록 설정되어 있음