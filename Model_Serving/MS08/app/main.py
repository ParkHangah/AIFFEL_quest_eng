"""
FastAPI 서버 정의
"""
import re
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

# 이전에 작성해둔 인증 모듈과 스키마 파일 로드
from app.auth import verify_api_key
from app.schemas import NarrativeRequest, NarrativeResponse
from app.model_service import load_model, predict

# 1. FastAPI 앱 생성
app = FastAPI(
    title="Localization Pipeline API",
    description="다국어 번역과 핵심 키워드(태그) 추출을 동시에 수행하는 지능형 파이프라인 API",
    version="1.0.0"
)

# 블로킹 방지를 위한 추론 전용 스레드풀 (Colab L4 환경 고려)
inference_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="inference")

# 전역 모델 변수
pipeline_models = None


 # 1. root 추가
@app.get("/")
def read_root():
    return {"message": "Welcome to Global Narrative to Tag API!"}

# 2. startup 이벤트에서 모델 로드
@app.on_event("startup")
async def startup_event():
    global pipeline_models
    try:
        print("모델 다운로드 중...")
        pipeline_models = load_model()
        print("✅ 모델 로드 완료")
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        print("--- 상세 에러 트레이스 ---")
        traceback.print_exc() # 상세 에러 스택 로깅
        print("----------------------")
        pipeline_models = None

# 3. GET /health 엔드포인트
@app.get("/health", tags=["System"])
async def health_check():
    """서버 상태와 모델 로드 여부를 확인합니다."""
    return {
        "status": "healthy" if pipeline_models is not None else "loading",
        "model_loaded": pipeline_models is not None
    }

# 4. POST /predict 엔드포인트
@app.post("/predict", response_model=NarrativeResponse, tags=["Inference"])
async def predict_endpoint(
    request: NarrativeRequest,            # Pydantic 스키마로 5000자 길이 등 입력 검증
    user: str = Depends(verify_api_key)   # X-API-Key 헤더 인증 적용 및 username 획득
):
    """최대 5000자의 서사 텍스트를 분석하여 번역 및 키워드를 추출합니다."""

    if pipeline_models is None:
        raise HTTPException(
            status_code=503,
            detail="모델이 아직 로드되지 않았습니다. 서버 상태를 확인해주세요."
        )

    # 1) 추론 서비스로 넘길 입력 데이터 구성 (청킹 적용)
    input_data = {
        "title": request.title,
        "text": request.text, # 문자열을 쪼갠 리스트(List)로 변환하여 삽입,
        "username": user
    }

    try:
        print("\n=== [STEP 1] 데이터 준비 완료 ===")
        print(f"- 제목: {input_data['title']}")
        print(f"- 텍스트 길이: {len(input_data['text'])}")

        # 2) run_in_executor로 비동기 추론 (get_running_loop 권장 반영)
        loop = asyncio.get_event_loop()

        print("\n=== [STEP 2] 추론 시작 ===")
        inference_result = await loop.run_in_executor(
            inference_executor,
            predict,
            pipeline_models,
            input_data
        )
        print("=== [STEP 3] 모델 추론 완료 ===")
        print(f"- 반환된 데이터 타입: {type(inference_result)}")
        
        # 3) 결과값이 리스트로 반환될 경우 딕셔너리를 추출 (500 에러 해결책)
        if isinstance(inference_result, list):
            if not inference_result:
                raise ValueError("추론 결과가 비어있습니다.")
            result_dict = inference_result[0]
        else:
            result_dict = inference_result

        print("=== [STEP 4] 딕셔너리 추출 완료 ===")
        # 딕셔너리가 맞는지, 어떤 키(key)들을 가지고 있는지 출력
        if isinstance(result_dict, dict):
            print(f"- 딕셔너리 키 목록: {list(result_dict.keys())}")
            print(f"- data 항목 존재 여부: {'data' in result_dict}")
        else:
            print(f"- ⚠️ 경고: result_dict가 딕셔너리가 아닙니다! 타입: {type(result_dict)}")

        # 4) 반환 딕셔너리를 Pydantic 스키마 구조에 맞게 안전하게 매핑
        formatted_data = []

        # 여기서 에러가 날 확률이 높으므로 직전에 로그 출력
        print("=== [STEP 5] Pydantic 스키마 매핑 시작 ===")
        for para_info in result_dict.get("data", []):
            # 💡 1. para_info 구조 변경 반영: [문단타입, 문장리스트, 키워드리스트]
            p_type = para_info[0] if len(para_info) > 0 else 0
            sentences_list = para_info[1] if len(para_info) > 1 else [] 
            keywords_list = para_info[2] if len(para_info) > 2 else None 

            formatted_sentences = []
            for sent_info in sentences_list:
                # 💡 2. sent_info 구조 변경 반영: [원문문장, 번역문장] (문장 타입 제거됨)
                orig = sent_info[0] if len(sent_info) > 0 else ""
                trans = sent_info[1] if len(sent_info) > 1 else None

                # SentenceDetail 스키마 규격에 맞춤
                formatted_sentences.append({
                    "original_text": orig,
                    "translated_text": trans
                })

            # 💡 3. ParagraphDetail 스키마 규격에 맞춤 (sentence_type -> paragraph_type 필드명 변경)
            formatted_data.append({
                "paragraph_type": p_type,
                "sentences": formatted_sentences,
                "keywords": keywords_list
            })
        print("=== [STEP 6] 매핑 완료, 최종 응답 반환 ===")
        # 5) 최종 응답 객체 반환 (NarrativeResponse 스키마 규격에 맞춤)
        return NarrativeResponse(
            title=result_dict.get("title", request.title), # 모델 결과에 없으면 요청 title 사용
            origin_txt=result_dict.get("origin_txt"),      # Optional (없으면 None)
            keyword=result_dict.get("keyword"),            # Optional (없으면 None)
            data=formatted_data
        )

    except Exception as e:
        # [핵심 디버깅 구간] 에러 발생 시 터미널에 상세 내역을 붉은 글씨로 쫙 뿌려줍니다.
        print("\n" + "="*50)
        print("🚨 [CRITICAL ERROR] 파이프라인 처리 중 예외 발생! 🚨")
        traceback.print_exc()  # 에러가 발생한 파일과 줄 번호를 출력합니다.
        print("="*50 + "\n")

        raise HTTPException(status_code=500, detail=f"파이프라인 처리 중 에러가 발생했습니다: {str(e)}")
