import random

class DummySensor: # 마치 붕어빵 틀과 같음
    def __init__(self): # plus :: 파이선에서 앞뒤에 __붙으면 특별한 매서드임, 객체 생성시 자동으로 호출되는 매서드(이름 바꾸면 x)
        # 함수인데, 클래스 안에 있으면 매서드 즉 기능을 넣는 것
         # init은 초기화 역할을 하는 매서드임
         # 객체를 호출하자 마자 0으로 차 있는 딕셔너리를 만든다 (호출 : ds=DummySensor())
         # 클래스 안의 모든 메소드는 첫 번째 매개변수로 self를 받아야 한다는 규칙 때문에 괄호 안에 self 
         #  -> 객체를 2개 만들면 지금 누구를 초기화해야하는지 알려줘야함, 그걸 self가 해줌 :: 지금 만들어지는 이 객체를 초기화해라. 
        
        self.env_values = { # (self : 지금 실행되는 놈 / . : 의 / env_values : 속성)
            'mars_base_internal_temperature': 0,
            'mars_base_external_temperature': 0,
            'mars_base_internal_humidity': 0,
            'mars_base_external_illuminance': 0,
            'mars_base_internal_co2': 0,
            'mars_base_internal_oxygen': 0,
        }

    def set_env(self): # (self : 지금 실행되는 놈 / . : 의 / set_env : 기능)
        self.env_values['mars_base_internal_temperature'] = (
            random.randint(18, 30)) # random.randint(a, b) : a와 b 사이의 정수 난수 생성
        self.env_values['mars_base_external_temperature'] = (
            random.randint(0, 21))
        self.env_values['mars_base_internal_humidity'] = (
            random.randint(50, 60))
        self.env_values['mars_base_external_illuminance'] = (
            random.randint(500, 715))
        self.env_values['mars_base_internal_co2'] = (
            round(random.uniform(0.02, 0.1), 4)) # random.uniform(a, b) : a와 b 사이의 실수 난수 생성
            # round(x, n) : x를 소수점 n자리까지 반올림
        self.env_values['mars_base_internal_oxygen'] = (
            round(random.uniform(4, 7), 2))

    def get_env(self): # self.env_values를 그대로 반환(return)하는 매서드 ** 읽기 전용 메서드
        # 자바의 getter와 비슷한 역할을 함
        # 캡슐화(내부 데이터는 무조건 메서드를 통해서만 접근하자) 를 위해서, 
        # 나중에 메서드 안에 기능 추가 쉬움 
        return self.env_values


ds = DummySensor()
ds.set_env()
print(ds.get_env())

