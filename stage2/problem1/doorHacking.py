"""
door_hacking.py

emergency_storage_key.zip 파일의 암호를 무차별 대입(brute-force) 방식으로 찾는 프로그램.
암호는 숫자(0-9)와 소문자 알파벳(a-z)으로 구성된 6자리 문자열이다.

사용 라이브러리: zipfile, itertools, string, time, datetime (모두 파이썬 표준 라이브러리)
"""

import zipfile
import itertools
import string
import time
from datetime import datetime


def unlock_zip():
    """
    emergency_storage_key.zip 의 암호를 브루트포스로 찾는다.
    - 시도 문자 집합: 숫자 + 소문자 알파벳 (36종류), 길이 6자리 -> 최대 36^6(약 21억) 회 시도
    - 진행 상황(시작 시각, 시도 횟수, 경과 시간)을 주기적으로 출력한다.
    - 암호를 찾으면 password.txt 에 저장한다.
    """
    zip_filename = "emergency_storage_key.zip"
    password_filename = "password.txt"

    charset = string.digits + string.ascii_lowercase  # '0123456789abcdefghijklmnopqrstuvwxyz'
    password_length = 6
    report_interval = 10000  # 몇 번 시도마다 진행상황을 출력할지

    # 1. zip 파일 열기 (예외처리)
    try:
        target_zip = zipfile.ZipFile(zip_filename)
    except FileNotFoundError:
        print(f"[오류] '{zip_filename}' 파일을 찾을 수 없습니다. 파일 위치를 확인해주세요.")
        return
    except zipfile.BadZipFile:
        print(f"[오류] '{zip_filename}' 파일이 올바른 zip 형식이 아닙니다.")
        return
    except PermissionError:
        print(f"[오류] '{zip_filename}' 파일에 접근할 권한이 없습니다.")
        return
    except Exception as e:
        print(f"[오류] zip 파일을 여는 중 알 수 없는 예외가 발생했습니다: {e}")
        return

    # 2. zip 내부 파일 목록 확인 (암호 검증용으로 하나 필요)
    try:
        name_list = target_zip.namelist()
        if not name_list:
            print("[오류] zip 파일 내부에 파일이 존재하지 않습니다.")
            target_zip.close()
            return
        target_name = name_list[0]
    except Exception as e:
        print(f"[오류] zip 내부 파일 목록을 읽는 중 예외가 발생했습니다: {e}")
        target_zip.close()
        return

    start_time = time.time()
    start_datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print("암호 해독을 시작합니다.")
    print(f"대상 파일     : {zip_filename}")
    print(f"시작 시각     : {start_datetime_str}")
    print(f"문자 집합     : {charset} (총 {len(charset)}종)")
    print(f"암호 길이     : {password_length}자리")
    print(f"최대 시도 횟수: {len(charset) ** password_length:,}회")
    print("=" * 60)

    attempt_count = 0
    found_password = None

    try:
        for combo in itertools.product(charset, repeat=password_length):
            attempt_count += 1
            candidate = "".join(combo)

            try:
                # 파일 내용을 실제로 읽어 CRC 검증까지 통과해야 성공으로 판단한다.
                target_zip.read(target_name, pwd=candidate.encode("utf-8"))
                found_password = candidate
            except RuntimeError:
                # 암호가 틀렸을 때 발생 (예: "Bad password for file")
                pass
            except zipfile.BadZipFile:
                pass
            except Exception:
                # 그 외 예상치 못한 예외는 무시하고 다음 시도로 넘어간다.
                pass

            if attempt_count % report_interval == 0:
                elapsed = time.time() - start_time
                print(
                    f"[진행 중] 시도 횟수: {attempt_count:>12,}회 | "
                    f"경과 시간: {elapsed:>8.2f}초 | 현재 시도값: {candidate}"
                )

            if found_password is not None:
                elapsed = time.time() - start_time
                print("=" * 60)
                print(f"암호를 찾았습니다! -> '{found_password}'")
                print(f"총 시도 횟수 : {attempt_count:,}회")
                print(f"총 소요 시간 : {elapsed:.2f}초")
                print("=" * 60)

                try:
                    with open(password_filename, "w", encoding="utf-8") as f:
                        f.write(found_password)
                    print(f"암호가 '{password_filename}' 파일에 저장되었습니다.")
                except (PermissionError, OSError) as e:
                    print(f"[오류] 암호 파일을 저장하는 중 예외가 발생했습니다: {e}")
                break
        else:
            elapsed = time.time() - start_time
            print("=" * 60)
            print("모든 조합을 시도했지만 암호를 찾지 못했습니다.")
            print(f"총 시도 횟수: {attempt_count:,}회, 총 소요 시간: {elapsed:.2f}초")
            print("=" * 60)

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print("사용자에 의해 작업이 중단되었습니다.")
        print(f"중단 시점까지 시도 횟수: {attempt_count:,}회, 경과 시간: {elapsed:.2f}초")
        print("=" * 60)
    finally:
        try:
            target_zip.close()
        except Exception:
            pass


if __name__ == "__main__":
    unlock_zip()