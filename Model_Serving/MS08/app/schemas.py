"""
입력/출력 스키마.

"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# ---------------------------------------------------------
# [요청 스키마]
# ---------------------------------------------------------
class NarrativeRequest(BaseModel):
    """
    사용자로부터 텍스트를 입력받는 요청 모델 (단계 1의 입력)
    """
    title: str = Field(..., description="작품 제목 (필수)")
    # min_length, max_length로 길이를 엄격히 검증
    text: str = Field(..., min_length=1, max_length=5000, description="분석할 서사 텍스트 (최대 5000자) (필수)")


# ---------------------------------------------------------
# [응답 데이터 세부 구조]
# ---------------------------------------------------------
class SentenceDetail(BaseModel):
    """
    개별 문장 분석 결과 구조
    """
    # ge(greater or equal), le(less or equal)를 사용하여 범위 검증 추가
    sentence_type: int = Field(..., ge=0, le=2, description="0: 일반, 1: 대사, 2: 생각 (필수)")
    original_text: str = Field(..., description="원문 문장 (필수)")
    # 번역에 실패하거나 번역이 제공되지 않을 경우를 대비한 선택 필드 처리
    translated_text: Optional[str] = Field(default=None, description="번역된 문장 (선택)")


class ParagraphDetail(BaseModel):
    """
    문단별 분석 결과 구조 (단계 4의 quantized_result 단위)
    """
    sentences: List[SentenceDetail] = Field(..., description="문단 내 문장들 (필수)")
    # 모델 추론 결과에 따라 키워드가 없을 수도 있으므로 선택 필드 처리
    keywords: Optional[List[List[str]]] = Field(default=None, description="[원문키워드 리스트, 영문키워드 리스트] (선택)")


# ---------------------------------------------------------
# [최종 응답 스키마]
# ---------------------------------------------------------
class NarrativeResponse(BaseModel):
    """
    API의 최종 응답 모델 (단계 5, 6의 딕셔너리 구조)
    """
    title: str = Field(..., description="작품 제목 (필수)")
    # 파일 저장을 선택적 기능으로 처리할 경우를 가정한 선택 필드 처리
    origin_txt: Optional[str] = Field(default=None, description="data 폴더 안에 생성된 txt 파일 path (선택)")
    keyword: Optional[List[List[str]]] = Field(default=None, description="전체 상위 5개 추출 키워드 [[원문키워드], [영문키워드]] (선택)")
    data: List[ParagraphDetail] = Field(..., description="문단별 상세 분석 데이터 (quantized_result) (필수)")
