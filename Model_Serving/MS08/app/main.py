"""
FastAPI 서버 정의
"""
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Depends, HTTPException

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

    # 추론 서비스로 넘길 입력 데이터 구성
    input_data = {
        "title": request.title,
        "text": request.text,
        "username": user
    }

    try:
        # run_in_executor로 비동기 추론 (이벤트 루프 블로킹 방지)
        loop = asyncio.get_event_loop()
        result_dict = await loop.run_in_executor(
            inference_executor,
            predict,
            pipeline_models,
            input_data
        )

        # model_service.py의 반환 딕셔너리를 NarrativeResponse 스키마 구조에 맞게 매핑
        formatted_data = []
        for para_info in result_dict["data"]:
            sentences_list = para_info[0] # [[문장타입, 원문문장, 번역문장], ...]
            keywords_list = para_info[1]  # [원문키워드, 번역문장키워드]

            formatted_sentences = [
                {
                    "sentence_type": s_type,
                    "original_text": orig,
                    "translated_text": trans
                }
                for s_type, orig, trans in sentences_list
            ]

            formatted_data.append({
                "sentences": formatted_sentences,
                "keywords": keywords_list
            })

        # 최종 응답 객체 반환
        return NarrativeResponse(
            title=result_dict["title"],
            origin_txt=result_dict["origin_txt"],
            keyword=result_dict["keyword"],
            data=formatted_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파이프라인 처리 중 에러가 발생했습니다: {str(e)}")
