# 📊 NaN 데이터 대시보드

[![Netlify Status](https://api.netlify.com/api/v1/badges/your-badge-id/deploy-status)](https://app.netlify.com/sites/your-site-name/deploys)

GST Factory의 협력사별 NaN(누락) 데이터를 시각화하는 인터랙티브 웹 대시보드입니다.

## 🌐 Live Demo

🔗 **[대시보드 보기](https://your-site-name.netlify.app)**

## 🎯 주요 기능

### 📊 다중 월별 데이터 지원
- **월별 선택**: 2025년 6월, 7월, 8월 개별 선택
- **전체 기간**: 6-8월 통합 데이터 분석
- **실시간 데이터 전환**: 드롭다운으로 즉시 전환

### 📈 시각화 차트
- **주차별 NaN 추이**: 기구/전장 협력사별 NaN 비율 변화 추이
- **협력사별 비교**: 도넛 차트로 협력사별 전체 NaN 비율 비교

### 📋 상세 데이터 분석
- **주차별 상세 테이블**: 기구/전장 협력사별 주차별 NaN 현황
- **NaN 상세 내역**: 각 주차별 구체적인 누락 항목 목록 (Title Number 링크 포함)
- **협력사별 필터링**: 기구/전장 협력사 별도 보기

### 🔄 스마트 데이터 소스 로직
- **33주차부터**: 일요일 데이터 사용 
- **32주차 이하**: 금요일 데이터 사용
- **TMS 협력사 구분**: TMS(M) 기구, TMS(E) 전장 분리 관리

## 🏗️ 프로젝트 구조

```
nan-dashboard/
├── 🌐 index.html                     # 메인 대시보드 페이지
├── 🐍 create_final_data.py           # 메인 데이터 추출 스크립트
├── 📄 README.md                      # 프로젝트 문서
├── 📁 css/
│   └── dashboard.css                 # 대시보드 스타일
├── 📁 js/
│   └── dashboard.js                  # 대시보드 로직
├── 📁 data/
│   ├── nan_data_2025_06_improved.json  # 6월 데이터
│   ├── nan_data_2025_07_improved.json  # 7월 데이터
│   ├── nan_data_2025_08_improved.json  # 8월 데이터
│   └── nan_data.json                    # 기본 8월 데이터
├── 📁 backup_legacy_scripts/         # 레거시 스크립트 백업
└── 📁 backup_old_data/              # 백업 JSON 파일들
```

## 🚀 사용 방법

### 🔧 로컬 개발

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/nan-dashboard.git
cd nan-dashboard

# 2. 데이터 추출 (필요시)
python3 create_final_data.py

# 3. 로컬 서버 실행
python3 -m http.server 8000

# 4. 브라우저에서 접속
open http://localhost:8000
```

### 🌐 GitHub + Netlify 배포

1. **GitHub 저장소 생성 및 업로드**
   ```bash
   git init
   git add .
   git commit -m "🚀 Initial commit: NaN Dashboard"
   git branch -M main
   git remote add origin https://github.com/your-username/nan-dashboard.git
   git push -u origin main
   ```

2. **GitHub Secrets 설정** (데이터 자동 업데이트용)
   ```
   Repository Settings > Secrets and variables > Actions
   
   📋 추가할 Secrets:
   - GOOGLE_SERVICE_KEY: Google Service Account JSON 키 전체 내용
   - DRIVE_FOLDER_ID: Google Drive 폴더 ID
   ```

3. **Netlify 배포**
   - [Netlify](https://netlify.com)에서 GitHub 저장소 연결
   - Build settings: **빌드 불필요** (정적 사이트)
   - Publish directory: `/` (루트)
   - 자동 배포 완료! 🎉

## 📊 데이터 구조

### JSON 데이터 형식
```json
{
  "extracted_at": "2025-08-25T13:28:01.353140",
  "period": "2025-07",
  "total_records": 126,
  "weekly_stats": {
    "27주차": {
      "week_number": 27,
      "date": "2025-07-04",
      "weekday": "Friday",
      "is_sunday_data": false,
      "data_source": "금요일",
      "total_records": 33,
      "partners": {
        "mech": {
          "BAT": {
            "total_tasks": 611,
            "nan_count": 3,
            "nan_ratio": 0.49,
            "records": [
              {
                "order_no": "G2501002",
                "order_href": "https://docs.google.com/spreadsheets/d/..."
              }
            ]
          }
        },
        "elec": { /* 전장 협력사 데이터 */ }
      }
    }
  },
  "partner_summary": {
    "BAT": {
      "total_tasks": 2849,
      "nan_count": 28,
      "nan_ratio": 0.98,
      "weeks": { /* 주차별 세부 데이터 */ }
    }
  }
}
```

## 🎨 주요 시각화 요소

### 📈 주차별 추이 차트
- **Line Chart**: 시간 흐름에 따른 NaN 비율 변화
- **색상 구분**: 기구 협력사(파란색), 전장 협력사(빨간색)
- **인터랙티브**: 호버 시 상세 정보 표시

### 🍩 협력사별 도넛 차트
- **비율 비교**: 각 협력사의 전체 NaN 비율
- **자동 색상**: 협력사별 고유 색상 할당
- **범례**: 협력사명과 비율 표시

### 📋 상세 테이블 & 아코디언
- **매트릭스 형태**: 주차별 × 협력사별 교차 분석
- **색상 코딩**: 
  - 🟢 **2% 이하**: 양호 (초록색)
  - 🟡 **2-5%**: 주의 (노란색)  
  - 🔴 **5% 초과**: 위험 (빨간색)
- **링크 연결**: Title Number → Google Sheets 직접 연결

## 🔧 기술 스택

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **차트 라이브러리**: Chart.js 4.x
- **UI 프레임워크**: Bootstrap 5
- **아이콘**: Font Awesome 6
- **데이터 형식**: JSON
- **배포**: Netlify (정적 사이트)
- **버전 관리**: Git & GitHub
- **백엔드**: Python (데이터 추출 전용)

## 📱 반응형 디자인

- ✅ **모바일 최적화** (320px 이상)
- ✅ **태블릿 지원** (768px 이상)  
- ✅ **데스크톱 풀스크린** (1200px 이상)
- ✅ **다크 모드 대응**

## 🔄 업데이트 주기

- **주간 단위**: 새로운 주차 데이터 추가
- **월간 단위**: 월별 데이터 파일 생성
- **수동 배포**: 필요시 GitHub → Netlify 자동 배포

## 🛠️ 데이터 추출 프로세스

```bash
# PAD_partner_kpi 프로젝트와 연동
python3 create_final_data.py

# 생성되는 파일들:
# - data/nan_data_2025_06_improved.json
# - data/nan_data_2025_07_improved.json  
# - data/nan_data_2025_08_improved.json
```

## 🔐 보안 고려사항

- ✅ **클라이언트 사이드 렌더링**: 서버리스 아키텍처
- ✅ **정적 파일**: HTML/CSS/JS만 배포
- ⚠️ **데이터 접근**: JSON 파일은 공개적으로 접근 가능
- 🔒 **권장**: 민감한 데이터의 경우 접근 제한 설정

## 📞 문의 및 지원

- **개발자**: GST Factory 시스템 관리자
- **데이터 소스**: PAD_partner_kpi 프로젝트 연동
- **이슈 제보**: GitHub Issues 활용

## 🔗 관련 링크

- 🌐 **Live Demo**: [your-site-name.netlify.app](https://your-site-name.netlify.app)
- 📊 **Google Sheets**: [데이터 소스](https://docs.google.com/spreadsheets/d/your-sheet-id)
- 🔄 **PAD_partner_kpi**: 연동 프로젝트

---

## 📋 TODO

- [ ] GitHub Actions 자동 배포 설정
- [ ] 8월 데이터 완성 시 업데이트  
- [ ] 전체기간 모드 UI/UX 개선
- [ ] 데이터 캐싱 최적화

---

**⚠️ 주의사항**: 
- 실제 운영 환경에서는 Google Drive API 인증 정보를 안전하게 관리하세요
- 민감한 데이터가 포함되어 있으므로 접근 권한을 적절히 설정하세요
- JSON 데이터 파일들은 `.gitignore`에 추가하여 민감 정보 보호를 고려하세요

---

🎉 **Made with ❤️ for GST Factory**