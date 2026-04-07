"""
모델 직접 로드 및 추론 함수 (TensorFlow 폴백 원천 차단 버전)
"""
import os
import re
import json
import random
import torch
from datetime import datetime
from collections import Counter
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForSequenceClassification

try:
    with open('data/keyword.txt', 'r', encoding='utf-8') as file:
        content = file.read()
        KOREAN_KEYWORDS = [keyword.strip() for keyword in content.split(',')]
except FileNotFoundError:
    KOREAN_KEYWORDS = ["로맨스", "판타지", "액션", "무협", "스릴러"]

ENGLISH_KEYWORDS = ["Romance Fantasy", "Modern Romance", "Traditional Fantasy", "Modern Fantasy", "Martial Arts", "Mystery", "Thriller", "Apocalypse", "Slice of Life", "RomCom", "Revenge", "Coming-of-age", "Healing", "Angst", "Comedy", "Calm", "Contract Dating", "Arranged Marriage", "First Love", "Mutual Salvation", "Misunderstanding", "Reverse Harem", "Harem", "Status Difference", "Capable FL", "Girl Crush FL", "Regression FL", "Reincarnation FL", "Possession FL", "Sweet ML", "Tsundere ML", "Cold Handsome ML", "Obsessive ML", "Crazy Obsessive ML", "Regretful ML", "Pure Love ML", "Straightforward ML", "Sly ML", "Scarred FL", "Mastermind ML", "Genius ML", "Satisfying Plot", "Brain Battle", "Psychological", "Plot Twist", "Solid World-building", "Foreshadowing Retrieval", "Solid Emotional Line", "Dark Fantasy", "Noir"]

def load_model():
    """
    AutoModel로 직접 PyTorch 모델을 로드하여 파이프라인에 주입합니다.
    """
    # 0번 GPU 사용, 없으면 CPU(-1)
    device = 0 if torch.cuda.is_available() else -1

    # ==========================================
    # 1. 번역 모델 (강제 PyTorch 로드)
    # ==========================================
    trans_model_id = "Helsinki-NLP/opus-mt-ko-en"
    trans_tokenizer = AutoTokenizer.from_pretrained(trans_model_id)
    trans_model = AutoModelForSeq2SeqLM.from_pretrained(trans_model_id)

    translator = pipeline(
        "translation",
        model=trans_model,
        tokenizer=trans_tokenizer,
        device=device
    )

    # ==========================================
    # 2. 제로샷 태깅 모델 (강제 PyTorch 로드)
    # ==========================================
    tagger_model_id = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
    tagger_tokenizer = AutoTokenizer.from_pretrained(tagger_model_id)
    tagger_model = AutoModelForSequenceClassification.from_pretrained(tagger_model_id)

    tagger = pipeline(
        "zero-shot-classification",
        model=tagger_model,
        tokenizer=tagger_tokenizer,
        device=device
    )

    return {"translator": translator, "tagger": tagger}

def predict(model: dict, input_data: dict) -> dict:
    """
    입력을 받아 로직을 수행하고 추론 결과를 반환합니다.
    """
    translator = model["translator"]
    tagger = model["tagger"]

    text = input_data["text"]
    title = input_data["title"]
    username = input_data["username"]

    os.makedirs(f"data/{username}", exist_ok=True)
    base_filename = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))
    txt_path = f"data/{username}/{base_filename}.txt"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    paragraphs = text.split('\n')
    parsed_paragraphs = []

    for p in paragraphs:
        if not p.strip(): continue
        sentences = [s.strip() + '.' for s in p.split('.') if s.strip()]
        para_sents = []
        for s in sentences:
            clean_s = re.sub(r'[^a-zA-Z0-9가-힣\s\'".,!?]', '', s).strip()
            if not clean_s: continue

            s_type = 0
            if clean_s.startswith('"') and clean_s.endswith('"'):
                s_type = 1
            elif clean_s.startswith("'") and clean_s.endswith("'"):
                s_type = 2
            para_sents.append([s_type, clean_s])

        if para_sents:
            parsed_paragraphs.append(para_sents)

    quantized_result = []
    all_orig_keywords = []
    all_trans_keywords = []

    for para in parsed_paragraphs:
        para_translated = []
        para_orig_text = ""
        para_trans_text = ""

        for s_type, orig_sent in para:
            trans_sent = translator(orig_sent)['translation_text']
            para_translated.append([s_type, orig_sent, trans_sent])
            para_orig_text += orig_sent + " "
            para_trans_text += trans_sent + " "

        orig_tags = tagger(para_orig_text, KOREAN_KEYWORDS, multi_label=True)
        trans_tags = tagger(para_trans_text, ENGLISH_KEYWORDS, multi_label=True)

        para_orig_keys = orig_tags['labels'][:3]
        para_trans_keys = trans_tags['labels'][:3]

        all_orig_keywords.extend(para_orig_keys)
        all_trans_keywords.extend(para_trans_keys)

        quantized_result.append([para_translated, [para_orig_keys, para_trans_keys]])

    top_orig = [k for k, v in Counter(all_orig_keywords).most_common(5)]
    top_trans = [k for k, v in Counter(all_trans_keywords).most_common(5)]

    final_dict = {
        "title": title,
        "origin_txt": txt_path,
        "keyword": [top_orig, top_trans],
        "data": quantized_result
    }

    json_path = f"data/{username}/{base_filename}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_dict, f, ensure_ascii=False, indent=2)

    return final_dict
