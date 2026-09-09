from django.urls import path # URL주소 등록하는 장고 기능 가지고 오기

from .import views # 같은 bids 폴더의 views.py를 가져오기

urlpatterns = [
    path("proposal-templates/<str:template_id>/slides/<int:slide_number>/", views.proposal_template_slide_preview), #제안서 템플릿 슬라이드 이미지
    path("bids/", views.bid_list), #bids 주소로 요청하면 bid_list 함수 실행
    path("bids/sync/", views.sync_bid_notices), #나라장터 공고를 현재 시점으로 다시 수집
    path("bids/<str:bid_ntce_no>/chat/", views.bid_chat), #공고별 AI 질문과 답변
    path("bids/<str:bid_ntce_no>/chat/<int:message_id>/", views.bid_chat_message_delete), #대화 내용 삭제 표시
    path("bids/<str:bid_ntce_no>/analysis/", views.bid_analysis), #공고별 AI 분석 생성과 조회
    path("bids/<str:bid_ntce_no>/analysis/pdf/", views.bid_analysis_pdf), #저장된 분석 PDF 내려받기
    path("bids/<str:bid_ntce_no>/proposal/", views.bid_proposal), #공고별 제안서 생성과 조회
    path("bids/<str:bid_ntce_no>/proposal/preview/", views.bid_proposal_preview), #현재 제안서 PDF 미리보기
    path("bids/<str:bid_ntce_no>/proposal/feedback/", views.bid_proposal_feedback), #미리보기 채팅 수정
    path("bids/<str:bid_ntce_no>/proposal/finalize/", views.bid_proposal_finalize), #검토한 제안서를 최종본으로 확정
    path("bids/<str:bid_ntce_no>/proposal/download/", views.bid_proposal_download), #생성 제안서 내려받기
    path("bids/<str:bid_ntce_no>/quantitative-proposal/", views.bid_quantitative_proposal), #정량평가 요구사항 분석과 작성안
    path("bids/<str:bid_ntce_no>/quantitative-proposal/download/", views.bid_quantitative_proposal_download), #정량평가 Word 내려받기
    path("bids/<str:bid_ntce_no>/", views.bid_detail), #공고번호에 해당하는 공고 한 건 조회
    path("saved-bids/", views.saved_bid_list), #내 저장 공고 조회와 새 공고 저장
    path("saved-bids/<str:bid_ntce_no>/", views.saved_bid_delete), #공고번호로 저장 취소
    path("saved-bids/<str:bid_ntce_no>/proposal-project/", views.start_bid_proposal_project), #제안서 프로젝트 시작
    path("saved-bids/<str:bid_ntce_no>/proposal-project/restore/", views.restore_bid_proposal_project), #휴지통 프로젝트 복원
    path("saved-bids/<str:bid_ntce_no>/proposal-project/permanent/", views.permanently_delete_bid_proposal_project), #휴지통 프로젝트 영구삭제
    path("proposal-trash/", views.proposal_trash_list), #휴지통 프로젝트 목록
    path("bids/<str:bid_ntce_no>/reference-documents/", views.project_reference_document_list), #프로젝트별 유사 제안서
    path("bids/<str:bid_ntce_no>/reference-documents/<int:document_id>/", views.project_reference_document_delete), #유사 제안서 삭제
    path("recommended-bids/", views.recommended_bid_list), #기존 주소 호환용, 화면에서는 사용하지 않음
    path("recommendations/", views.stored_recommendation_list), #매일 저장된 회원별 추천 공고
    path("company-profile/", views.company_profile), #회사 프로필 조회와 최초 저장
    path("company-profile/website-knowledge/", views.company_website_knowledge), #회사 홈페이지 지식 조회와 새로 수집
    path("company-profile/business-registration/", views.business_registration_extract), #사업자등록증 기본정보 추출
    path("company-documents/", views.company_document_list), #회사 제안서와 소개서 조회·업로드
    path("company-documents/<int:document_id>/", views.company_document_delete), #회사 문서 삭제
    path("auth/signup/", views.signup), #회원가입 요청을 처리하는 주소
    path("auth/login/", views.login), #로그인 후 Token을 발급하는 주소
    path("auth/logout/", views.logout), #로그인 Token을 삭제하는 주소
]
