import re
import time
import traceback
import requests
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------- 翻译模块 ----------
from deep_translator import GoogleTranslator

def translate_to_chinese(text):
    if not text or not isinstance(text, str):
        return ""
    try:
        if len(text) > 4000:
            text = text[:4000]
        result = GoogleTranslator(source='en', target='zh-CN').translate(text)
        return result.strip()
    except Exception as e:
        print(f"⚠️ 翻译失败 '{text[:30]}...': {e}")
        return text

# ---------- 学院固定中文名 ----------
FACULTY_ZH_MAP = {
    "arts": "文学院",
    "business administration": "商学院",
    "education": "教育学院",
    "engineering": "工学院",
    "inter-faculty": "跨学院",
    "law": "法学院",
    "medicine": "医学院",
    "science": "理学院",
    "social science": "社科学院"
}

def get_college_zh(faculty_name):
    key = faculty_name.lower().strip()
    if key in FACULTY_ZH_MAP:
        return FACULTY_ZH_MAP[key]
    translated = translate_to_chinese(faculty_name)
    if translated and not translated.endswith("学院"):
        translated += "学院"
    return translated

HOME_URL = "https://www.gs.cuhk.edu.hk/admissions/"


# ---------- 截止日期抓取 ----------
def clean_deadline_text(raw_text):
    if not raw_text:
        return ""
    text = re.sub(r'\([^)]*\)', '', raw_text)
    sentences = re.split(r'[;\n]', text)
    months = r'Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?'
    date_pattern = re.compile(
        rf'(?:{months})\s+\d{{1,2}}(?:st|nd|rd|th)?\s+\d{{4}}|\d{{1,2}}\s+(?:{months})\s+\d{{4}}|\d{{4}}|\d{{1,2}}\s+[A-Za-z]+\s+\d{{4}}',
        re.IGNORECASE)

    kept = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if "to be confirmed" in sent.lower():
            kept.append("To be confirmed")
            continue
        if date_pattern.search(sent):
            kept.append(sent)
    result = "; ".join(kept)
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def extract_programme_name(prog_div):
    clone = BeautifulSoup(str(prog_div), "html.parser")
    for dl in clone.select(".color-lightblue"):
        dl.decompose()
    for tbl in clone.select("table"):
        tbl.decompose()
    return " ".join(clone.get_text().strip().split())


def extract_deadline(prog_div):
    deadline_div = prog_div.find("div", class_="color-lightblue")
    if not deadline_div:
        return ""
    table = deadline_div.find("table")
    if table:
        rows = []
        for tr in table.find_all("tr"):
            cols = tr.find_all(["th", "td"])
            if cols:
                row_text = " | ".join(" ".join(c.get_text().strip().split()) for c in cols if c.get_text().strip())
                rows.append(row_text)
        deadline_text = "; ".join(rows)
        for tbl in table.find_all():
            tbl.decompose()
        extra = " ".join(deadline_div.get_text().strip().split())
        if extra:
            deadline_text += " " + extra
        return clean_deadline_text(deadline_text)
    else:
        raw = " ".join(deadline_div.get_text(separator="\n").strip().split())
        return clean_deadline_text(raw)


def fetch_deadline_mapping():
    url = "https://www.gs.cuhk.edu.hk/admissions/admissions/application-deadline"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"❌ 获取截止日期页面失败: {e}")
        return {}

    mapping = {}
    sections = soup.find_all("div", class_="section")
    print(f"📅 截止日期页面中找到 {len(sections)} 个学院区块")

    for sec in sections:
        for faq in sec.find_all("div", class_="faqs"):
            answer = faq.find("div", class_="faqs-answer")
            if not answer:
                continue
            prog_divs = answer.find_all("div", class_="application-deadline-tb-txt")
            for prog in prog_divs:
                if "title" in prog.get("class", []):
                    continue
                name = extract_programme_name(prog)
                if not name:
                    continue
                deadline = extract_deadline(prog)
                if name in mapping:
                    if len(deadline) > len(mapping[name]):
                        mapping[name] = deadline
                else:
                    mapping[name] = deadline
    print(f"📅 共获取 {len(mapping)} 个项目的截止日期映射")
    return mapping


# ---------- 详情抓取 ----------
def extract_by_regex(text, keyword, stop_keywords=None, flags=re.DOTALL | re.IGNORECASE):
    if stop_keywords is None:
        stop_keywords = [
            'Study Mode', 'Normative Study Period', 'Minimum Units Required',
            'Tuition Fee', 'Admission Requirements', 'Application Deadline',
            'HKPFS Application Deadline', 'Contact', 'Programme Information',
            'Apply Now', 'Fields of Specialization', 'Contact Us'
        ]
    pattern = re.compile(
        r'{}\s*\n(.*?)(?=\n\s*(?:{}|$))'.format(
            re.escape(keyword),
            '|'.join(re.escape(k) for k in stop_keywords if k != keyword)
        ),
        flags
    )
    match = pattern.search(text)
    if match:
        value = match.group(1).strip()
        value = re.sub(r'\n\s*\n', '\n', value)
        return value
    return ''


def get_division_mapping(soup):
    division_mapping = {}
    division_links = soup.find_all('a', class_='programme-division-link')
    for div_link in division_links:
        division_name = div_link.get_text(strip=True)
        parent_row = div_link.find_parent('div', class_='programme-tb-row')
        if parent_row:
            prog_links = parent_row.find_all('a', class_='programme-tb-link')
        else:
            continue
        for link in prog_links:
            prog_name = link.get_text(strip=True)
            if prog_name:
                division_mapping[prog_name] = division_name
    return division_mapping


def extract_language_requirements_simple(admission_text):
    if not admission_text:
        return "IELTS 6.5 / TOEFL 79"
    text = ' '.join(admission_text.split())
    ielts_match = re.search(r'IELTS.*?(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    toefl_match = re.search(r'TOEFL.*?(\d+).*?(?:internet|iBT|Home)', text, re.IGNORECASE)
    if not toefl_match:
        toefl_match = re.search(r'TOEFL.*?(\d+)', text, re.IGNORECASE)
    parts = []
    if ielts_match:
        parts.append(f"IELTS {ielts_match.group(1)}")
    if toefl_match:
        parts.append(f"TOEFL {toefl_match.group(1)}")
    if parts:
        return " / ".join(parts)
    else:
        return "IELTS 6.5 / TOEFL 79"


def format_faculty_name(raw_name):
    if not raw_name:
        return ""
    if raw_name.lower().startswith("faculty of"):
        return raw_name
    cleaned = re.sub(r'^Faculty\s+of\s+', '', raw_name, flags=re.IGNORECASE).strip()
    return f"Faculty of {cleaned}"


def scrape_faculty(faculty_url, faculty_name, deadline_mapping):
    print(f"\n📂 开始抓取学院: {faculty_name} -> {faculty_url}")
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(faculty_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "programme_content"))
        )
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        division_mapping = get_division_mapping(soup)

        url_map_by_id = {}
        all_links = soup.find_all('a', class_='programme-tb-link')
        for link in all_links:
            href = link.get('href', '')
            prog_id = link.get('data-id')
            if prog_id and href:
                if ',' in str(prog_id):
                    prog_id = str(prog_id).split(',')[0]
                if href.startswith('#'):
                    full_url = faculty_url.rstrip('/') + href
                else:
                    full_url = href
                url_map_by_id[prog_id] = full_url

        programme_blocks = soup.find_all('div', class_='programme_content')
        print(f"   📦 共发现 {len(programme_blocks)} 个专业块")

        faculty_results = []
        for idx, block in enumerate(programme_blocks, 1):
            try:
                block_id = block.get('id', '')
                prog_number = block_id.replace('programme_', '') if block_id.startswith('programme_') else ''
                if ',' in prog_number:
                    prog_number = prog_number.split(',')[0]
                program_url = url_map_by_id.get(prog_number, '')

                text = block.get_text(separator='\n', strip=True)

                title_tag = block.find('div', class_='progamme-details-title')
                program_name = title_tag.get_text(strip=True) if title_tag else ''
                if not program_name:
                    continue

                division = division_mapping.get(program_name, '')

                raw_admission = extract_by_regex(text, 'Admission Requirements')
                language_req = extract_language_requirements_simple(raw_admission)

                deadline_raw = deadline_mapping.get(program_name, '')
                deadline_clean = extract_date_from_text(deadline_raw)

                faculty_results.append({
                    'program_name': program_name,
                    'faculty': faculty_name,
                    'division': division,
                    'language': language_req,
                    'deadline': deadline_clean,
                    'url': program_url
                })
                print(f"      [{idx}/{len(programme_blocks)}] 解析完成: {program_name}")
            except Exception as e:
                print(f"      ⚠️ 解析第 {idx} 个专业时出错: {e}")
                continue

        return faculty_results

    except Exception as e:
        print(f"   ❌ 抓取 {faculty_name} 时出错: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def get_all_faculty_links():
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(HOME_URL)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "home-box-align"))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        container = soup.find('div', class_='home-box-align')
        if not container:
            return []
        links = container.find_all('a', class_='home-link')
        faculties = []
        for a in links:
            href = a.get('href')
            name_div = a.find('div', class_='home-link-txt')
            name = name_div.get_text(strip=True) if name_div else ''
            if href and name:
                if href.startswith('/'):
                    full_url = "https://www.gs.cuhk.edu.hk" + href
                else:
                    full_url = href
                faculties.append({'name': name, 'url': full_url})
        return faculties
    except Exception as e:
        print(f"❌ 获取学院列表失败: {e}")
        return []
    finally:
        driver.quit()


def extract_date_from_text(text):
    if not text:
        return ""
    months = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12',
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'Jun': '06', 'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10',
        'Nov': '11', 'Dec': '12'
    }
    match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text)
    if match:
        day, month_str, year = match.groups()
        month = months.get(month_str, '')
        if month:
            return f"{year}-{month}-{int(day):02d}"
    match = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', text)
    if match:
        month_str, day, year = match.groups()
        month = months.get(month_str, '')
        if month:
            return f"{year}-{month}-{int(day):02d}"
    return text.strip()


def is_taught_master_program(program_name):
    if not program_name:
        return False
    name_lower = program_name.lower()
    exclude_keywords = ['phd', 'doctor', 'pgd', 'postgraduate diploma', 'mphil', 'research']
    for kw in exclude_keywords:
        if kw in name_lower:
            return False
    taught_indicators = ['master', 'msc', 'ma ', 'mba', 'mph', 'mssc', 'llm', 'march', 'mfa']
    for ind in taught_indicators:
        if ind in name_lower:
            return True
    return True


def main():
    print("🔍 正在从截止日期页面抓取项目截止时间...")
    deadline_mapping = fetch_deadline_mapping()
    print(f"✅ 获取到 {len(deadline_mapping)} 条截止日期记录")

    all_programs = []
    faculties = get_all_faculty_links()
    if not faculties:
        print("无法获取学院列表，程序终止。")
        return

    for fac in faculties:
        fac_name = fac['name']
        fac_url = fac['url']
        results = scrape_faculty(fac_url, fac_name, deadline_mapping)
        all_programs.extend(results)
        print(f"✅ {fac_name} 抓取完成，获得 {len(results)} 个专业")
        time.sleep(2)

    print(f"\n📊 共抓取 {len(all_programs)} 个专业，开始过滤并翻译...")

    final_data = []
    idx = 1
    for prog in all_programs:
        program_name = prog['program_name']
        if not is_taught_master_program(program_name):
            print(f"  ⏭️ 跳过非 taught master 项目: {program_name}")
            continue

        name_en = program_name
        name_zh = translate_to_chinese(name_en)

        faculty_original = prog['faculty']
        college_zh = get_college_zh(faculty_original)

        school_en = format_faculty_name(faculty_original)

        division_en = prog['division']
        focus_zh = translate_to_chinese(division_en) if division_en else ""

        item = {
            "id": idx,
            "name": name_en,
            "name_zh": name_zh,
            "name_en": name_en,
            "school": school_en,
            "college": college_zh,
            "deadline": prog['deadline'],
            "language": prog['language'],
            "focus": focus_zh,
            "link": prog['url']
        }
        final_data.append(item)
        print(f"  [{idx}] 保留: {name_en} -> {name_zh}")
        idx += 1

    output_path = 'cuhk_programs_final.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 全部完成！共保留 {len(final_data)} 条 taught master 项目数据，已保存至 {output_path}")


if __name__ == '__main__':
    main()