import json
import time
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# 是否启用翻译（True=翻译成中文，False=保留英文）
ENABLE_TRANSLATION = True

if ENABLE_TRANSLATION:
    try:
        translator = GoogleTranslator(source='en', target='zh-CN')
        print("翻译器初始化成功")
    except Exception as e:
        print(f"翻译器初始化失败: {e}")
        ENABLE_TRANSLATION = False

def translate_text(text):
    if not text or not ENABLE_TRANSLATION:
        return text
    try:
        if len(text) > 5000:
            text = text[:5000]
        time.sleep(0.5)
        return translator.translate(text)
    except Exception as e:
        print(f"翻译出错: {e}，保留原文")
        return text

def clean_text(text):
    if not text:
        return ""
    lines = text.splitlines()
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return " ".join(cleaned_lines)

def parse_faqs():
    url = "https://www.gs.cuhk.edu.hk/admissions/faqs"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    faqs_data = []
    faq_id = 1

    categories = soup.find_all("div", class_="faqs_cat")
    for cat in categories:
        title_elem = cat.find("div", class_="about-us-subtitle")
        category_en = title_elem.get_text(strip=True) if title_elem else "General"
        category_zh = translate_text(category_en) if ENABLE_TRANSLATION else category_en

        faq_blocks = cat.find_all("div", class_="faqs")
        for block in faq_blocks:
            question_elem = block.find("div", class_="faqs-question-txt")
            question_en = question_elem.get_text(strip=True) if question_elem else ""
            question_zh = translate_text(question_en) if ENABLE_TRANSLATION else question_en

            answer_elem = block.find("div", class_="faqs-answer-txt")
            if answer_elem:
                answer_html = str(answer_elem)
                answer_html = answer_html.replace("<br/>", "\n").replace("<br>", "\n").replace("</p>", "\n")
                soup_answer = BeautifulSoup(answer_html, "html.parser")
                answer_en = soup_answer.get_text()
                answer_en = clean_text(answer_en)
                answer_zh = translate_text(answer_en) if ENABLE_TRANSLATION else answer_en
            else:
                answer_en = ""
                answer_zh = ""

            if question_en and answer_en:
                faqs_data.append({
                    "id": faq_id,
                    "category": category_zh,
                    "question": question_zh,
                    "answer": answer_zh
                })
                faq_id += 1

    return faqs_data

def save_to_json(data, filename="faq.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON文件已保存为 {filename}，共 {len(data)} 条记录")

def save_to_txt(data, filename="faq.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for item in data:
            f.write(f"Category: {item['category']}\n")
            f.write(f"Q: {item['question']}\n")
            f.write(f"A: {item['answer']}\n")
            f.write("-" * 50 + "\n")
    print(f"TXT文件已保存为 {filename}，共 {len(data)} 条记录")

if __name__ == "__main__":
    print("正在抓取FAQ页面...")
    if ENABLE_TRANSLATION:
        print("翻译功能已开启，由于需要调用外部API，速度可能较慢，请耐心等待...")
    faq_items = parse_faqs()
    print(f"共抓取到 {len(faq_items)} 个问答")
    save_to_json(faq_items)
    save_to_txt(faq_items)
    print("完成！")