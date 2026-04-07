"""
모델 직접 로드 및 추론 함수 (TensorFlow 폴백 원천 차단 버전)
"""
import os
import re
import json
import random
import torch
import traceback
from datetime import datetime
from collections import Counter
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForSequenceClassification
from fastapi import FastAPI, Depends, HTTPException

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
    print(f"\n=== [STEP 2-1] 텍스트 파일 {base_filename}.txt 저장완료===")
    paragraphs = text.split('\n')
    print(f"\n=== [STEP 2-2] 문단 분할 완료.( 총 문단개수 : {len(paragraphs)}개 )===")

    parsed_paragraphs = []
    len_p = 0
    try:
        for p in paragraphs:
            clean_p = p.strip()
            if not clean_p: 
                continue

            # 1. 문단 타입 판별 (문장으로 쪼개기 전, 원본 문단 기준)
            p_type = 0
            if clean_p.startswith('"') and clean_p.endswith('"'):
                p_type = 1
            elif clean_p.startswith("'") and clean_p.endswith("'"):
                p_type = 2

            # 2. 문단 내 문장 분리
            sentences = [s.strip() + '.' for s in clean_p.split('.') if s.strip()]
            
            para_sents = []
            for s in sentences:
                # 특수문자 정제
                clean_s = re.sub(r'[^a-zA-Z0-9가-힣\s\'".,!?]', '', s).strip()
                if clean_s: 
                    para_sents.append(clean_s)

            # 문단 타입(p_type)과 문장 리스트를 함께 저장
            if para_sents:
                parsed_paragraphs.append([p_type, para_sents])
            len_p = len_p + len(para_sents)
            print(f"\n 문단타임: {p_type}, 문단내 문장 갯수: {len(para_sents)} (누적 문장 갯수:{len_p})")
        len_s = len(parsed_paragraphs)
        
        print(f"\n=== [STEP 2-3] 모든 문단 타입 판별이 완료되었습니다.( 총 문단개수 : {len(parsed_paragraphs)}개 )===")
    except Exception as e:
        # [핵심 디버깅 구간] 에러 발생 시 터미널에 상세 내역을 붉은 글씨로 쫙 뿌려줍니다.
        print("\n" + "="*50)
        print("🚨 [CRITICAL ERROR] 문단별 문장 분할 중 에러 발생! 🚨")
        traceback.print_exc()  # 에러가 발생한 파일과 줄 번호를 출력합니다.
        print("="*50 + "\n")

        raise HTTPException(status_code=500, detail=f"문단별 문장 분할 중 에러가 발생했습니다: {str(e)}")

    quantized_result = []
    all_orig_keywords = []
    all_trans_keywords = []
    len_t = 0

    try:
        for p_type, sentences in parsed_paragraphs:
            para_translated = []
            trans_sentences = []
            para_orig_text = ""
            para_trans_text = ""

            # 1. [핵심 최적화] 문장 리스트를 통째로 번역 모델에 전달 (Batch Processing)
            # GPU 환경이라면 batch_size를 추가하여 연산 속도를 극대화할 수 있습니다.
            translation_results = translator(sentences, batch_size=8)

            # (방어 코드) 문장이 1개라서 리스트가 아닌 단일 딕셔너리로 반환될 경우 대비
            if not isinstance(translation_results, list):
                translation_results = [translation_results]

            # 2. 원문 문장과 번역 결과를 1:1로 매핑
            for orig_sent, result in zip(sentences, translation_results):
                if isinstance(result, list) and len(result) > 0:
                    trans_sent = result[0].get('translation_text', '')
                elif isinstance(result, dict): # 단일 딕셔너리 구조일 때
                    trans_sent = result.get('translation_text', '')
                else:
                    trans_sent = ""
                len_t = len_t + 1
                if ( len_t % 10 == 0 ):
                    print(f"문장번역 {len_p}개 중 {len_t}개 완료")
                para_translated.append([orig_sent, trans_sent])
                trans_sentences.append(trans_sent)
            
            # 3. [문자열 최적화] += 대신 파이썬 내장 join() 메서드 사용
            para_orig_text = " ".join(sentences)
            para_trans_text = " ".join(trans_sentences)
            print("문단별 태그 추출")
            # 4. 태그 추출 로직 (기존과 동일)
            orig_tags = tagger(para_orig_text, KOREAN_KEYWORDS, multi_label=True)
            trans_tags = tagger(para_trans_text, ENGLISH_KEYWORDS, multi_label=True)

            para_orig_keys = orig_tags['labels'][:3]
            para_trans_keys = trans_tags['labels'][:3]

            all_orig_keywords.extend(para_orig_keys)
            all_trans_keywords.extend(para_trans_keys)

            # 앞서 논의된 [문단타입, 문장리스트, 키워드리스트] 구조로 저장
            quantized_result.append([p_type, para_translated, [para_orig_keys, para_trans_keys]])
    except Exception as e:
        # [핵심 디버깅 구간] 에러 발생 시 터미널에 상세 내역을 붉은 글씨로 쫙 뿌려줍니다.
        print("\n" + "="*50)
        print("🚨 [CRITICAL ERROR] 번역 중 에러 발생! 🚨")
        traceback.print_exc()  # 에러가 발생한 파일과 줄 번호를 출력합니다.
        print("="*50 + "\n")

        raise HTTPException(status_code=500, detail=f"번역작업 중 에러가 발생했습니다: {str(e)}")

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
