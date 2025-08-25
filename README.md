# 협력사 평가 대시보드 (Partner KPI Dashboard)

GST 공장의 협력사별 품질 평가 지표를 실시간으로 모니터링하고 시각화하는 대시보드 시스템입니다.

## 📊 프로젝트 개요

이 프로젝트는 Google Sheets와 Google Drive의 데이터를 기반으로 협력사별 KPI를 자동 계산하고, 웹 기반 대시보드를 생성하여 GitHub Pages에 자동 배포하는 시스템입니다.

### 주요 기능
- 📈 **실시간 데이터 수집**: Google Sheets 불량/생산 데이터 및 Google Drive NaN 비율 데이터 자동 수집
- 🎯 **불량률 기반 KPI**: 불량률(70%) + 누락비율(30%) 가중평균 기반 평가 점수 산출
- 🏭 **생산대수 카운팅**: Chamber 수 기준 정확한 생산량 집계 (DUAL=2대, TMS(M) 반제품 기여 포함)
- 🏆 **스마트 순위 매김**: 동일 점수 시 불량률 낮은 협력사 우선순위 적용
- 📱 **반응형 웹 대시보드**: 모던하고 직관적인 UI/UX (불량률/생산대수 표시)
- 🔄 **자동 배포**: GitHub Pages를 통한 실시간 대시보드 업데이트
- 📋 **상세 불량 내역**: 협력사별 불량 데이터 클릭 시 상세 정보 표시 (제품S/N, 발생일 포함)
- 📊 **NaN 디테일뷰**: 누락률 클릭 시 주간별 추이 테이블 표시
- ☁️ **클라우드 백업**: Google Drive를 통한 자동 데이터 백업
- 🗄️ **데이터베이스 시스템**: 월별 KPI 결과 및 대시보드 히스토리 관리
- ⏰ **자동 스케줄링**: 매월 마지막 평일 자동 실행 옵션
- 💾 **CSV 다운로드**: 협력사별 불량 내역 CSV 다운로드 기능

## 🏗️ 프로젝트 구조

### 최신 프로젝트 구조 (2025.08.25)
```
PAD_partner_kpi/
├── 📁 production/                    # 🎯 메인 실행 환경 (통합 시스템)
│   ├── 📄 partner_kpi.py             # 불량률 기반 메인 실행 파일 (환경변수 기반)
│   ├── 📄 create_final_data.py       # NaN 대시보드 데이터 생성기
│   ├── 📄 requirements.txt           # Python 의존성 패키지
│   ├── 📄 env.template              # 환경변수 템플릿
│   ├── 📄 .env                      # 로컬 환경변수 설정 (비공개)
│   └── 📁 nan_dashboard/            # 🚀 NaN 대시보드 모듈
│       ├── 📄 index.html            # NaN 대시보드 UI
│       ├── 📁 js/dashboard.js       # 인터랙티브 차트 및 테이블
│       ├── 📁 css/dashboard.css     # 모던 스타일링
│       └── 📁 data/                 # JSON 데이터 저장소
│           ├── nan_data_2025_06_improved.json
│           ├── nan_data_2025_07_improved.json
│           └── nan_data_2025_08_improved.json
├── 📁 backup_legacy_scripts/         # 레거시 스크립트 백업
│   ├── 📄 data_extractor.py         # 구 데이터 추출기
│   ├── 📄 generate_monthly_data.py  # 구 월별 데이터 생성기
│   └── 📄 multi_month_extractor.py  # 구 다중 월 추출기
├── 📁 backup_old_data/              # 구 데이터 파일 백업
│   └── nan_data_2025_*.json         # 구 데이터 파일들
├── 📁 modular/                      # 모듈화된 구조 (개발 중)
│   ├── 📁 config.py                 # 설정 관리
│   ├── 📁 data_loader.py            # Google API 데이터 로드
│   ├── 📁 partner_mapper.py         # 협력사 매핑 및 KPI 계산
│   └── 📁 html_generator.py         # HTML 대시보드 생성
├── 📁 backup/                       # 백업 및 유틸리티
│   ├── 📁 partner_kpi_backup.py     # 백업 파일들
│   ├── 📁 backup_manager.py         # 백업 관리
│   └── 📁 drive_backup_manager.py   # Google Drive 백업
├── 📁 backup_legacy/                # 레거시 파일 백업
│   ├── 📁 partner_kpi.py            # 기존 버전
│   └── 📁 partner_kpi_REV2.py       # REV2 버전
├── 📁 .env                          # 🔐 환경변수 설정 (메인)
├── 📁 requirements.txt              # 의존성 패키지
└── 📁 README.md                     # 프로젝트 문서
```

### 메인 실행 파일
- `production/partner_kpi.py`: **불량률 기반 KPI 시스템** (현재 운영 버전, 환경변수 기반)
  - 생산대수 자동 계산, 불량률 등급, HTML 대시보드 생성 완전 지원
  - GitHub 자동 업로드 (GST_Factory_Dashboard, gst-factory repo)
- `production/create_final_data.py`: **NaN 대시보드 데이터 생성기** 
  - partner_kpi.py의 정확한 NaN 비율 로직 사용
  - GitHub nan-dashboard repo 자동 업로드
  - 동적 월별 추출 시스템

## 🚀 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
`production/.env` 파일을 생성하고 다음 환경변수를 설정하세요:

```bash
# Google Service Account Keys (로컬 파일 경로)
SHEETS_JSON_KEY_PATH=/Users/user/Downloads/gst-sheets-credentials.json
GOOGLE_SERVICE_KEY=/Users/user/Downloads/gst-drive-credentials.json

# Google Drive 및 Sheets 설정
DRIVE_FOLDER_ID=your_google_drive_folder_id
SPREADSHEET_ID=your_google_sheets_id
SHEET_RANGE=불량이력!A1:AJ1000
PRODUCTION_SHEET_RANGE=공정검사이력!A1:AJ1000

# GitHub Token (모든 시스템 공통 사용)
GH_TOKEN=your_github_personal_access_token

# GitHub 설정 - partner_kpi.py용 (첫 번째 - GST_Factory_Dashboard)
GH_USERNAME_1=your_github_username
GH_REPO_1=GST_Factory_Dashboard
GH_BRANCH_1=main
GH_HTML_FILENAME_1=partner_kpi.html

# GitHub 설정 - partner_kpi.py용 (두 번째 - gst-factory)
GH_USERNAME_2=your_github_username
GH_REPO_2=gst-factory
GH_BRANCH_2=main
GH_HTML_FILENAME_2=public/partner_kpi.html

# create_final_data.py는 GH_TOKEN과 GH_USERNAME_1을 사용하여
# nan-dashboard repo의 data/ 폴더에 자동 업로드
```

### 3. Google API 인증 설정
1. Google Cloud Console에서 프로젝트 생성
2. Google Sheets API 및 Google Drive API 활성화
3. 서비스 계정 생성 및 JSON 키 파일 다운로드
4. 환경변수에 키 파일 경로 설정

### 4. GitHub 토큰 설정
1. GitHub Settings > Developer settings > Personal access tokens
2. `repo` 권한으로 토큰 생성
3. 환경변수에 토큰 설정

## 📈 KPI 계산 방식 (불량률 기반)

### 평가 기준
| 구분 | A등급 | B등급 | C등급 | D등급 | E등급 |
|------|-------|-------|-------|-------|-------|
| **NaN 비율** | <1% | 1-3% | 3-6% | ≥6% | - |
| **기구 불량률** | <6.0% | 6.0-16.5% | 16.5-27.6% | ≥27.6% | - |
| **전장 불량률** | <1.0% | 1.0-3.6% | 3.6-6.2% | 6.2-7.5% | ≥7.5% |

### 점수 체계
- A등급: 10.0점 (최우수)
- B등급: 8.2점 (우수)  
- C등급: 6.5점 (보통)
- D등급: 2.5점 (개선필요)

### 최종 평가 점수
```
최종 점수 = (불량률 점수 × 70%) + (NaN 비율 점수 × 30%)
```

### 생산대수 카운팅 방식
- **기본 원칙**: Chamber 수 기준 카운트
- **일반 제품**: 1 Chamber = 1대 (예: GAIA-I = 1대)
- **DUAL 제품**: 2 Chamber = 2대 (예: GAIA-I DUAL = 2대)
- **TMS(M) 특수 처리**: 직접 작업 + 반제품 기여 (DRAGON 직접작업 + 모든 제품 반제품 도킹)
- **데이터 소스**: "공정검사이력" 시트의 "제품명", "협력사(기구)명", "협력사(전장)명" 컬럼

### 불량률 계산 방식
```
불량률(%) = (월간 불량 건수 ÷ 월간 생산대수) × 100
```

### NaN 비율 계산 방식
- **정확한 방식**: `(총 누락 task 수) / (총 task 수) × 100`
- **데이터 소스**: JSON 파일의 `nan_ratio` 값 직접 사용
- **주간별 추이**: 금요일 데이터 기준 주간별 누락률 계산
- **주차 계산**: `date.isocalendar()[1]` 방식으로 동적 ISO 주차 계산 (2025.07.30 개선)

### 순위 결정 로직
1. **1차**: 최종 평가 점수 높은 순
2. **2차**: 점수 동일 시 불량률 낮은 순

## 🖥️ 사용법

### 메인 애플리케이션 실행
```bash
# 통합 production 환경으로 이동
cd production

# 1. 불량률 기반 KPI 시스템 (HTML 대시보드)
python partner_kpi.py

# 2. NaN 대시보드 데이터 생성 (JSON 데이터)
python create_final_data.py

# 3. NaN 대시보드 확인 (로컬 서버)
python -m http.server 8000
# 브라우저에서 http://localhost:8000/nan_dashboard/ 접속
```

### 레거시 버전 실행 (백업됨)
```bash
# 기존 불량건수 기반 버전
python backup_legacy/partner_kpi.py

# REV2 버전
python backup_legacy/partner_kpi_REV2.py
```

### 데이터 백업 관리
```bash
# 로컬 백업 정보 조회
python backup_manager.py info

# 특정 월 로컬 백업
python backup_manager.py backup --month 2025-07

# Google Drive 백업 정보 조회
python drive_backup_manager.py info

# 특정 월 Google Drive 백업
python drive_backup_manager.py backup --month 2025-07
```

### 월별 스케줄러
```bash
# 스케줄러 정보 확인
python monthly_scheduler.py info

# 자동 실행 (마지막 평일 체크)
python monthly_scheduler.py run

# 강제 실행
python monthly_scheduler.py run --force

# 테스트 모드
python monthly_scheduler.py run --test
```

### 데이터 정합성 테스트
```bash
# 기본 테스트
python test_data_integrity.py

# 특정 월 테스트
python test_data_integrity.py --month 2025-07

# 상세 테스트
python test_data_integrity.py --verbose
```

## 🗄️ 데이터베이스 시스템

### 디렉토리 구조
```
kpi_database/
├── monthly_results/          # 월별 KPI 결과
│   └── 202507/              # 연월별 폴더
│       ├── partner_kpi_final_202507_latest.json
│       └── partner_kpi_final_202507_20250712_140000.json
├── dashboards/              # 월별 대시보드
│   └── 202507/
│       ├── partner_kpi_202507_latest.html
│       └── partner_kpi_202507_20250712_140000.html
└── archives/                # 아카이브 데이터
```

### JSON 데이터 구조
```json
{
  "metadata": {
    "target_month": "2025-07",
    "generation_time": "2025-07-12T14:00:00",
    "total_partners": 6
  },
  "kpi_results": {
    "mech_partners": [...],
    "elec_partners": [...]
  },
  "defect_counts": {...},
  "nan_ratios": {...},
  "monthly_statistics": {...}
}
```

## ☁️ Google Drive 백업 시스템

### 백업 기능
- 📤 **자동 업로드**: 월별 JSON 및 HTML 파일 자동 백업
- 📁 **폴더 관리**: 월별 폴더 자동 생성 및 관리
- 🔄 **버전 관리**: latest 및 타임스탬프 버전 동시 저장
- 🔗 **직접 링크**: 업로드된 파일 직접 접근 링크 제공

### 백업 폴더 구조
```
Google Drive/partner_kpi/
└── 202507/                 # 월별 폴더
    ├── partner_kpi_final_202507_latest.json
    ├── partner_kpi_final_202507_20250712_140000.json
    ├── partner_kpi_202507_latest.html
    └── partner_kpi_202507_20250712_140000.html
```

## 📊 대시보드 기능

### 메인 대시보드
- 🏭 **협력사 평가 카드**: 등급별 색상 구분, 점수 및 KPI 표시
- 📈 **평가지수 개요**: 호버 툴팁으로 평가 기준 상세 정보 제공
- 🎯 **등급 시스템**: A(우수) → B(양호) → C(보통) → D(개선필요)

### 상세 정보 기능
- 📋 **불량 내역 테이블**: 
  - 제품S/N/제품명
  - 상세불량내용
  - 상세조치내용
  - 발생일
  - CSV 다운로드 기능
- 📊 **NaN 디테일뷰**:
  - 주간별 누락률 추이
  - 월평균 누락률
  - 자동 주차 계산 (금요일 기준)

### 인터랙티브 기능
- 🖱️ **카드 클릭**: 불량 내역 상세 테이블 표시
- 🟡 **누락률 클릭**: 주간별 누락률 추이 테이블 표시
- 📥 **CSV 다운로드**: 협력사별 불량 내역 엑셀 다운로드
- 📱 **반응형 디자인**: 모바일/태블릿 최적화

## 📊 협력사 분류

### 기구 협력사 (3개사)
- **BAT**: 주식회사 비에이티 (기구 제작 전문)
- **FNI**: 에프앤아이 (기구 조립 전문)
- **TMS(M)**: 티엠에스이엔지 (기구 유지보수 전문)

### 전장 협력사 (3개사)
- **C&A**: 씨앤에이시스템 (전장 제어 시스템)
- **P&S**: 피엔에스 시스템 (전장 시스템 통합)
- **TMS(E)**: 티엠에스이엔지 (전장 설계/제작 전문)

## 🔧 최신 업데이트 (2025-08)

### v4.0.0 통합 시스템 (2025.08.25)
- 🎯 **production 통합 환경**: partner_kpi.py + nan-dashboard 통합 관리
- 🔐 **환경변수 기반**: 모든 하드코딩 제거, .env 파일 기반 설정 관리
- 🚀 **GitHub 자동 업로드**: 두 시스템 모두 GitHub repo 자동 업로드 지원
- 📊 **NaN 데이터 정합성**: partner_kpi.py 검증된 로직으로 create_final_data.py 통일
- 🔧 **동적 로깅 시스템**: 하드코딩 제거, 모든 협력사/주차 동적 처리
- 📈 **강화된 비교 로깅**: partner_kpi.py vs create_final_data.py 데이터 일치성 확인
- 🗂️ **백업 체계화**: 레거시 스크립트/데이터 별도 백업 폴더 관리
- ⚙️ **GitHub Actions 호환**: 로컬/GitHub 환경 모두 지원하는 인증 시스템

### v3.0.0 불량률 기반 KPI 시스템 (2025.07.31)
- 🎯 **불량률 기반 평가**: 불량건수 → 불량률로 KPI 계산 방식 전면 개편
- 🏭 **생산대수 자동 계산**: 공정검사이력 시트에서 Chamber 수 기준 생산량 집계
- ⚙️ **DUAL 제품 처리**: DUAL 키워드 제품 2배 카운트 자동 적용
- 🔧 **TMS(M) 특수 로직**: 직접 작업 + 반제품 기여 분리 계산
- 📊 **불량률 등급 기준**: REV2 기준 적용 (기구 A<6.0%, 전장 A<1.0%)
- 🎨 **대시보드 개선**: hover창에 불량률, 생산대수 정보 추가 표시
- 📋 **정렬 기준 변경**: 동점시 불량건수 → 불량률 기준으로 순위 결정
- 🗂️ **디렉토리 정리**: production, backup_legacy 등 체계적 구조 개편

### v2.3.0 주요 개선사항
- ✅ **제품정보 개선**: 제품코드 → 제품S/N 변경으로 추적성 향상
- ✅ **발생일 추가**: 불량 테이블에 발생일 컬럼 추가
- ✅ **NaN 디테일뷰**: 누락률 클릭 시 주간별 추이 테이블 표시
- ✅ **계산 방식 통일**: 호버창과 디테일뷰 누락률 계산 로직 일치
- ✅ **데이터 정확성**: JSON nan_ratio 값 직접 사용으로 정확도 향상
- ✅ **UI/UX 개선**: 평가지수 개요 툴팁 최적화

### 기술적 개선사항
- 🔄 **계산 로직 최적화**: pandas groupby().mean() 방식 적용
- 🎯 **데이터 매핑 개선**: clean_partner_name() 함수 통일 적용
- 📊 **동적 주차 계산**: `date.isocalendar()[1]` 방식으로 ISO 주차 자동 계산 (2025.07.30 개선)
- 📅 **확장성 향상**: 하드코딩 제거로 향후 모든 주차 자동 처리 가능
- 💾 **JSON 직렬화 개선**: Timestamp 객체 문자열 변환 처리

## 📝 변경 이력

자세한 변경 이력은 [CHANGELOG.md](./CHANGELOG.md)를 참조하세요.

### 최근 업데이트 (2025.07.31) - v3.0.0 불량률 기반 시스템
- 🎯 **불량률 KPI 시스템 완성**: 불량건수 → 불량률 기반 평가로 전면 전환
- 🏭 **생산대수 카운팅 자동화**: 공정검사이력 시트 데이터 자동 집계 (Chamber 수 기준)
- ⚙️ **TMS(M) 특수 로직 구현**: 직접 작업 8대 + 반제품 기여 210대 = 총 218대 정확 계산
- 📊 **불량률 등급 시스템**: REV2 기준 (기구 A<6.0%, 전장 A<1.0%) 완전 적용
- 🎨 **대시보드 UI 개선**: hover창에 불량률, 생산대수, 생산대수 카운팅 설명 추가
- 📋 **정렬 로직 개선**: 동점시 불량률 기준 순위 결정으로 변경
- 🗂️ **프로젝트 구조 정리**: production 메인, backup_legacy 백업 체계 구축

### 이전 업데이트 (2025.07.30)
- 🔧 **29W 데이터 누락 해결**: hover창에서 29주차 데이터 정상 표시
- ✅ **동적 주차 계산 도입**: 하드코딩된 날짜 조건을 ISO 주차 계산으로 개선
- ✅ **7월 27-29주 데이터 검증**: 모든 주차 데이터 정상 입력 확인
- ✅ **NaN 데이터 우려사항 해결**: 재확인 결과 정상 처리 완료
- ✅ **주간별 추이 정상 작동**: 디테일뷰 표시 기능 검증 완료

## 🚀 향후 계획

### 단기 계획
- 📱 **모바일 앱**: React Native 기반 모바일 대시보드
- 🔔 **알림 시스템**: 등급 변동 시 Slack/Teams 알림
- 📈 **트렌드 분석**: 월별 성과 추이 분석 기능

### 중기 계획
- 🤖 **AI 예측**: 머신러닝 기반 불량률 예측 모델
- 📊 **고급 분석**: 통계적 품질 관리 (SPC) 기능
- 🔄 **실시간 업데이트**: WebSocket 기반 실시간 데이터 업데이트

## 📞 문의 및 지원

프로젝트 관련 문의사항이나 개선 제안이 있으시면 GitHub Issues를 통해 연락 주시기 바랍니다.

---

**© 2025 GST Factory Partner KPI Dashboard System** 
