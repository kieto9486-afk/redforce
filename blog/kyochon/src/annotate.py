# 앱 캡처에 빨간 강조 박스를 그려 블로그용 STEP 이미지로 저장
import sys
from PIL import Image, ImageDraw
SRC = sys.argv[1]
RED = (226, 35, 26)
boxes = {  # 파일번호: (출력이름, [(x1,y1,x2,y2), ...])
    '2': ('step1_app_home.jpg', [(440, 1730, 593, 1900)]),
    '3': ('step2_pickup.jpg',   [(538, 1540, 727, 1720)]),
    '4': ('step3_store.jpg',    [(278, 638, 455, 718)]),
    '6': ('step4_menu.jpg',     [(30, 1040, 830, 1255), (40, 1755, 935, 1875)]),
    '5': ('step5_coupon.jpg',   [(42, 465, 980, 825)]),
}
for n, (out, rects) in boxes.items():
    im = Image.open(f'{SRC}/{n}.jpg').convert('RGB')
    d = ImageDraw.Draw(im)
    for r in rects:
        d.rounded_rectangle(r, radius=22, outline=RED, width=9)
    im.save(f'images/steps/{out}', quality=90)
    print(out)
