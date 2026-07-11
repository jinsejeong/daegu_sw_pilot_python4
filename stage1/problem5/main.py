import numpy as np

try:
    arr1 = np.genfromtxt("1-5-mars_base_main_parts-001.csv", delimiter=",",
                          dtype=str, skip_header=1, encoding="utf-8-sig")
    arr2 = np.genfromtxt("1-5-mars_base_main_parts-002.csv", delimiter=",",
                          dtype=str, skip_header=1, encoding="utf-8-sig")
    arr3 = np.genfromtxt("1-5-mars_base_main_parts-003.csv", delimiter=",",
                          dtype=str, skip_header=1, encoding="utf-8-sig")
except OSError as e:
    print(f"파일을 읽는 중 오류가 발생했습니다: {e}")
else:
    # 세 파일 모두 부품 이름이 같은 순서로 나열되어 있으므로,
    # 이름은 arr1 기준으로 사용하고 강도(strength) 값만 합친다.
    parts_name = arr1[:, 0]
    strength1 = arr1[:, 1].astype(float)
    strength2 = arr2[:, 1].astype(float)
    strength3 = arr3[:, 1].astype(float)

    parts = np.array([strength1, strength2, strength3])

    average = parts.mean(axis=0)

    mask = average < 50
    weak_parts_name = parts_name[mask]
    weak_parts_average = average[mask]

    for name, avg in zip(weak_parts_name, weak_parts_average):
        print(f"{name}: {avg:.2f}")

    try:
        with open("parts_to_work_on.csv", "w", encoding="utf-8") as f:
            f.write("parts,average_strength\n")
            for name, avg in zip(weak_parts_name, weak_parts_average):
                f.write(f"{name},{avg:.2f}\n")
    except Exception as e:
        print(f"파일 저장 중 오류가 발생했습니다: {e}")
