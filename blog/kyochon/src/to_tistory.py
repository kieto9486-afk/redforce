# index.html 본문을 티스토리 HTML 모드에 붙여넣을 수 있는 인라인 스타일 HTML로 변환
from bs4 import BeautifulSoup, Comment

GOLD, SOFT, RED, MUTED, LINE = '#b8862b', '#f6ecd6', '#c8211b', '#6f6556', '#e6dccb'
STYLE = {
    'hook': 'font-size:24px;font-weight:900;line-height:1.5;margin:0 0 18px',
    'red': f'color:{RED}',
    'hl': f'background:linear-gradient(transparent 58%,{SOFT} 58%);font-weight:700',
    'note': f'font-size:13px;color:{MUTED}',
    'tbl': 'overflow-x:auto;margin:16px 0',
    'num': 'text-align:right',
    'tips': 'list-style:none;padding:0;margin:0',
    'cta': 'font-size:22px;font-weight:900;text-align:center;margin:28px 0 0',
    'promo': f'margin-top:48px;border:2px solid {GOLD};border-radius:10px;padding:24px;background:{SOFT}',
    'tags': f'margin-top:36px;color:{GOLD};font-size:14px',
}
UPLOAD = {  # 이미지 경로 -> 업로드할 파일 이름
    'images/thumbnail.jpg': '01_thumbnail.jpg (대표 이미지로도 지정)',
    'images/compare.jpg': '02_compare.jpg',
    'images/steps/step1_app_home.jpg': '03_step1_app_home.jpg',
    'images/steps/step2_pickup.jpg': '04_step2_pickup.jpg',
    'images/steps/step3_store.jpg': '05_step3_store.jpg',
    'images/steps/step4_menu.jpg': '06_step4_menu.jpg',
    'images/steps/step5_coupon.jpg': '07_step5_coupon.jpg',
    'images/chicken_web.jpg': '08_chicken.jpg',
}

def placeholder(soup, label):
    d = soup.new_tag('p', style=f'border:2px dashed {GOLD};background:{SOFT};border-radius:8px;'
                                 'padding:22px 12px;text-align:center;font-weight:700;color:#221d16')
    d.string = f'📷 여기에 {label} 업로드 후 이 칸 삭제'
    return d

soup = BeautifulSoup(open('index.html', encoding='utf-8').read(), 'html.parser')
art = soup.find('article')
art.find('h1').decompose()
art.find('p', class_='meta').decompose()
for fig in art.find_all('figure'):
    img, vid = fig.find('img'), fig.find('video')
    if img:
        fig.replace_with(placeholder(soup, UPLOAD[img['src']]))
    elif vid:
        fig.replace_with(placeholder(soup, '09_reels.mp4 (또는 인스타그램 릴스 링크)'))
for slot in art.find_all(class_='slot'):
    slot.replace_with(placeholder(soup, 'K-스피커스 13기 공식 모집 포스터(출처 표기)'))
for el in art.find_all(class_=True):
    styles = [STYLE[c] for c in el['class'] if c in STYLE]
    if 'total' in el['class']:
        styles.append('font-weight:900')
    del el['class']
    if styles:
        el['style'] = ';'.join(styles)
for t in art.find_all('table'):
    t['style'] = 'width:100%;border-collapse:collapse;font-size:15px'
for c in art.find_all(['th', 'td']):
    c['style'] = (c.get('style', '') + f';padding:9px 10px;border-bottom:1px solid {LINE}').lstrip(';')
for th in art.find_all('th'):
    th['style'] += f';background:{SOFT};text-align:left'
for li in art.find_all('li'):
    li['style'] = 'padding:6px 0'
    li.insert(0, '✔ ')
for h in art.find_all('h2'):
    h['style'] = f'border-bottom:2px solid {GOLD};padding-bottom:8px;margin-top:44px'
dl = art.find('dl')
if dl:
    ul = soup.new_tag('ul', style='list-style:none;padding:0;margin:14px 0 0')
    for dt in dl.find_all('dt'):
        li = soup.new_tag('li', style='padding:3px 0')
        b = soup.new_tag('b', style=f'color:{GOLD}'); b.string = f'✔ {dt.get_text()}: '
        li.append(b); li.append(dt.find_next_sibling('dd').get_text())
        ul.append(li)
    dl.replace_with(ul)
body = ''.join(str(x) for x in art.contents).strip()
title = '아직도 치킨 배달시켜요? 교촌 포장하면 8,600원 아껴요｜교촌앱 포장 10% 할인 후기'
out = f'<!-- 제목: {title} -->\n<div style="font-size:16px;line-height:1.85;color:#221d16">\n{body}\n</div>\n'
open('tistory_post.html', 'w', encoding='utf-8').write(out)
print(len(out))
