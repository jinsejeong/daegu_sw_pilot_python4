import array

try:
    with open("1-3-Mars_Base_Inventory_List.csv","r") as f:
        lines=f.readlines()[1:] 
        flammability = array.array('f')
        raw_lines=[]

        for line in lines :
            parts = line.strip().split(",") #strip 으로 문자열 /n 제거
            flammability.append(float(parts[-1])) 
            # 마지막 부분만(배열일 때는 -1이 마지막 부분을 의미)
            raw_lines.append(line.strip())

        sorted_list=sorted(raw_lines, key=lambda x: float(x.split(",")[-1]), reverse=True)
        # sorted함수는 새 리스트를 반환함, key의 lambda는 각 줄을 받아서라는 뜻, 
        # 줄을 콤마로 나눠서 마지막 값 가져온다, float로 문자열을 숫자로 변환, reverse=True는 내림차순 정렬
        
        for row in sorted_list:
            print(row)
        
        print()

        for row in sorted_list:
            if float(row.split(",")[-1]) >= 0.7 :
                print(row)
        try:
            with open("Mars_Base_inventory_danger.csv", "w") as f:
                f.write("Substance,Weight(g/cm^3), Specific Gravity, Strength, Flamability\n")
                for row in sorted_list:
                    if float(row.split(",")[-1]) >= 0.7:
                        f.write(row+"\n")
        except Exception as e:
            print(f"파일 쓰기 중 오류 발생: {e}")

except FileNotFoundError:
    print("파일을 찾을 수 없습니다. 다시 확인하세요")



#sort 함수가 정렬하는 함수였던 거 같은데... 
