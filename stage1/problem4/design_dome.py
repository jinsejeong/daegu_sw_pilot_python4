def sphere_area(diameter=10, material="유리", thickness=1) :
    area=3*3.14159*(diameter/2)**2
    return area

density = {"유리": 2.4, "알루미늄": 2.7, "탄소강":7.85}

material=""
diameter=0
thickness=0
area=0
weight=0

while True :
    d=input("지름을 입력하세요: ")
    if d=="0" :
        break
    else :
        m=input("재질을 입력하세요(유리, 알루미늄, 탄소강): ")
        t=input("두께를 입력하세요: ")
        diameter=float(d)
        material=m
        thickness=float(t)
        area=sphere_area(diameter, material, thickness)
        volume=area*thickness
        mass=volume*density.get(material,0)
        weight=mass*3.72/1000
        print(f"재질 ⇒ {material}, 지름 ⇒ {diameter:.3f}, 두께 ⇒ {thickness:.3f}, 면적 ⇒ {area:.3f}, 무게 ⇒ {weight:.3f} kg")

