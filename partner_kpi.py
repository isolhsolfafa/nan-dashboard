import os
import pandas as pd
import json
from datetime import datetime
import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from github import Github
from collections import defaultdict
import math
import re

# 옵션 키
SELECTED_MONTH = "2025-08"  # 변경할 월 지정 (형식: "YYYY-MM")

TEST_MODE = False  # True: 로컬 저장만, False: 로컬 저장 + GitHub 업로드

# GitHub 설정 (첫 번째 저장소)
GITHUB_USERNAME_1 = "isolhsolfafa"
GITHUB_REPO_1 = "GST_Factory_Dashboard"
GITHUB_BRANCH_1 = "main"
GITHUB_TOKEN_1 = os.getenv("GITHUB_TOKEN", "")
HTML_FILENAME_1 = "partner_kpi.html"

# GitHub 설정 (두 번째 저장소)
GITHUB_USERNAME_2 = "isolhsolfafa"
GITHUB_REPO_2 = "gst-factory"
GITHUB_BRANCH_2 = "main"
GITHUB_TOKEN_2 = os.getenv("GITHUB_TOKEN", "")
HTML_FILENAME_2 = "public/partner_kpi.html"

# Google API 설정
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
# 환경변수 기반 인증 (GitHub Actions 호환)
SHEETS_JSON_KEY_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/Users/kdkyu311/Downloads/gst-manegemnet-e6c4e7bd79e2.json",
)
DRIVE_JSON_KEY_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/Users/kdkyu311/Downloads/gst-manegemnet-8e112ff4f64e.json",
)
DRIVE_FOLDER_ID = "13FdsniLHb4qKmn5M4-75H8SvgEyW2Ck1"
SPREADSHEET_ID = "1sb-qKK0OiHnP8HHaffD9FVOzlrfYa_bD9QQDyvnHnrI"
SHEET_RANGE = "불량이력!A1:AJ1000"  # 불량 데이터 시트
PRODUCTION_SHEET_RANGE = "공정검사이력!A1:AJ1000"  # 생산대수 데이터 시트


def get_drive_service():
    """Google Drive API 서비스 초기화"""
    try:
        credentials = Credentials.from_service_account_file(
            DRIVE_JSON_KEY_PATH, scopes=SCOPES
        )
        print(f"Google Drive 자격 증명 로드 성공: {DRIVE_JSON_KEY_PATH}")
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        print(f"Google Drive API 초기화 실패: {str(e)}")
        raise


def get_sheets_service():
    """Google Sheets API 서비스 초기화"""
    try:
        credentials = Credentials.from_service_account_file(
            SHEETS_JSON_KEY_PATH, scopes=SCOPES
        )
        print(f"Google Sheets 자격 증명 로드 성공: {SHEETS_JSON_KEY_PATH}")
        return build("sheets", "v4", credentials=credentials)
    except Exception as e:
        print(f"Google Sheets API 초기화 실패: {str(e)}")
        raise


# 서비스 초기화
drive_service = get_drive_service()
sheets_service = get_sheets_service()

# 캐싱 변수
_cached_json_data = None


def load_json_files_from_drive(year_month, drive_folder_id=DRIVE_FOLDER_ID):
    """Google Drive에서 특정 연도-월의 JSON 파일 로드 (33주차부터 일요일, 32주차 이하는 금요일)"""
    global _cached_json_data
    if _cached_json_data is not None:
        print("캐싱된 JSON 데이터 사용")
        return _cached_json_data

    print(f"지정된 연도-월: {year_month}")
    yyyy_mm = year_month.replace("-", "")
    try:
        query = f"'{drive_folder_id}' in parents and name contains 'nan_ot_results_{yyyy_mm}'"
        print(f"Google Drive 조회 - 폴더 ID: {drive_folder_id}, 쿼리: {query}")
        files = (
            drive_service.files()
            .list(
                q=query,
                fields="files(id, name, modifiedTime)",
                orderBy="modifiedTime desc",
            )
            .execute()
            .get("files", [])
        )
        if not files:
            print(f"⚠️ {year_month}에 해당하는 JSON 파일이 없습니다.")
            return []

        # 주차별 요일 선택 로직: 33주차부터 일요일, 32주차 이하는 금요일
        target_files = []
        sunday_files = [f for f in files if "_일_" in f["name"]]
        friday_files = [f for f in files if "_금_" in f["name"]]

        # 모든 파일에서 주차 정보 추출하여 조건부 선택
        for file in files:
            try:
                # 파일명에서 날짜 추출 (예: nan_ot_results_20250817_130753_일_7회차.json)
                parts = file["name"].split("_")
                if len(parts) >= 4:
                    date_str = parts[3]  # 20250817
                    if len(date_str) == 8:
                        year = int(date_str[:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])

                        file_date = datetime.date(year, month, day)
                        week_num = file_date.isocalendar()[1]

                        # 33주차부터 일요일, 32주차 이하는 금요일
                        if week_num >= 33 and "_일_" in file["name"]:
                            target_files.append(file)
                        elif week_num <= 32 and "_금_" in file["name"]:
                            target_files.append(file)
            except (ValueError, IndexError) as e:
                continue

        if not target_files:
            print(f"⚠️ {year_month}에 조건에 맞는 JSON 파일이 없습니다.")
            print(f"   - 일요일 파일: {len(sunday_files)}개")
            print(f"   - 금요일 파일: {len(friday_files)}개")
            return []

        weekday_type = (
            "일요일" if any("_일_" in f["name"] for f in target_files) else "금요일"
        )
        print(
            f"총 {len(target_files)}개의 {weekday_type} JSON 파일 로드 (33주차부터 일요일, 32주차 이하 금요일)"
        )
        data_list = []
        for file in target_files:
            file_id = file["id"]
            file_name = file["name"]
            print(f"📁 JSON 파일 로드 중: {file_name}")
            try:
                request = drive_service.files().get_media(fileId=file_id)
                content = request.execute().decode("utf-8")
                data = json.loads(content)
                if "results" not in data:
                    print(
                        f"⚠️ 파일 {file_name}: 'results' 키가 없습니다. JSON 구조: {list(data.keys())}"
                    )
                    continue
                try:
                    date_str = file_name.split("_")[3]
                    file_date = pd.to_datetime(date_str, format="%Y%m%d").date()
                except (IndexError, ValueError) as e:
                    print(f"⚠️ 파일 {file_name}: 날짜 파싱 실패: {str(e)}")
                    continue
                for result in data["results"]:
                    result["file_date"] = file_date.isoformat()
                    result["group_month"] = file_date.strftime("%Y-%m")
                data_list.extend(data["results"])
            except Exception as e:
                print(f"⚠️ 파일 {file_name} 처리 실패: {str(e)}")
                continue

        _cached_json_data = data_list
        print(f"📂 총 {len(data_list)}개의 로그 데이터를 로드했습니다.")
        return data_list
    except Exception as e:
        print(f"Google Drive API 호출 실패: {str(e)}")
        return []


def load_sheets_data():
    """Google Sheets에서 불량 데이터 로드"""
    try:
        result = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=SHEET_RANGE)
            .execute()
        )
        values = result.get("values", [])
        if not values:
            print("❌ 불량 시트 데이터 없음")
            return None
        columns = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=columns)
        if "비고" in df.columns:
            df = df[
                ~df["비고"].astype(str).str.contains("제조\\(He미보증\\)", na=False)
            ]
            print(f"DEBUG: '제조(He미보증)' 제외 후 불량 데이터 크기: {len(df)}")
        return df
    except Exception as e:
        print(f"불량 데이터 로드 실패: {str(e)}")
        return None


def load_production_data():
    """Google Sheets에서 생산대수 데이터 로드"""
    try:
        result = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=PRODUCTION_SHEET_RANGE)
            .execute()
        )
        values = result.get("values", [])
        if not values:
            print("❌ 생산대수 시트 데이터 없음")
            return None
        columns = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=columns)
        print(f"DEBUG: 생산대수 데이터 로드 완료 - 총 {len(df)}건")
        print(f"DEBUG: 사용 가능한 컬럼: {list(df.columns)}")

        # 필요한 컬럼 확인
        required_columns = ["제품명", "협력사(기구)명", "협력사(전장)명"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"⚠️ 누락된 컬럼: {missing_columns}")
        else:
            print("✅ 필요한 컬럼 모두 존재")

        return df
    except Exception as e:
        print(f"생산대수 데이터 로드 실패: {str(e)}")
        return None


# 협력사 이름 매핑 사전
mech_partner_map = {
    "주식회사 비에이티": "BAT",
    "에프앤아이(FnI)": "FNI",
    "(주)티엠에스이엔지": "TMS(M)",
}
elec_partner_map = {
    "(주)티엠에스이엔지": "TMS(E)",
    "피엔에스 시스템": "P&S",
    "(주)씨앤에이시스템": "C&A",
}
# 반제품 매핑 사전 (기구와 동일)
semi_product_partner_map = {
    "주식회사 비에이티": "BAT",
    "에프앤아이(FnI)": "FNI",
    "(주)티엠에스이엔지": "TMS(M)",
}


def clean_partner_name(name, mode="mech"):
    name = (name or "").strip()
    if mode == "mech":
        return mech_partner_map.get(name, name)
    elif mode == "elec":
        return elec_partner_map.get(name, name)
    elif mode == "semi":
        return semi_product_partner_map.get(name, name)
    else:
        return name


def extract_partner_from_action(action, 대분류, 중분류):
    """
    '작업자' 문자열에서 협력사를 추출.
    - action에 'TMS' 포함 시
      * 대분류가 '기구작업불량' 또는 (대분류가 '작업불량' & 중분류에 '기구') → 'TMS(M)'
      * 대분류가 '전장작업불량' 또는 (대분류가 '작업불량' & 중분류에 '전장') → 'TMS(E)'
    - 그 외 'BAT', 'FNI', 'P&S', 'C&A', 'TMS(M)', 'TMS(E)' 포함 시 바로 반환
    - 그 외에는 "미기재" 반환
    """
    if not action or pd.isna(action):
        return "미기재"
    action = str(action).strip()

    # 1) action 문자열 안에 'TMS'가 있으면
    if "TMS" in action:
        # 기구작업불량인 경우는 기구
        if 대분류 == "기구작업불량":
            return "TMS(M)"
        # 전장작업불량인 경우는 전장
        if 대분류 == "전장작업불량":
            return "TMS(E)"
        # 작업불량인 경우 중분류에 '기구' 또는 '전장'으로 구분
        if 대분류 == "작업불량":
            if "기구" in 중분류:
                return "TMS(M)"
            if "전장" in 중분류:
                return "TMS(E)"
        # 그 외 상황에서는 미기재
        return "미기재"

    # 2) 'TMS'가 아닐 때, 다른 키워드(BAT, FNI, P&S, C&A, TMS(M), TMS(E)) 검사
    for partner in ["BAT", "FNI", "P&S", "C&A", "TMS(M)", "TMS(E)"]:
        if partner in action:
            return partner

    return "미기재"


def get_partner_for_row(row):
    """
    1️⃣ 작업자가 있으면 extract_partner_from_action(action, 대분류, 중분류) 사용 → 우선 매핑
    2️⃣ 없으면 대분류/중분류 기준으로 mech/elect 파트너 매핑
    3️⃣ 대분류 == '부품불량'인 경우에도 중분류로 분기
    4️⃣ 그 외는 '미기재'
    """
    대분류 = row.get("대분류", "")
    중분류 = row.get("중분류", "")
    mech_name = row.get("협력사(기구)명", "")
    elec_name = row.get("협력사(전장)명", "")
    action = row.get("작업자", "")

    # 1️⃣ 작업자에 협력사가 명시된 경우 먼저 검사
    action_partner = extract_partner_from_action(action, 대분류, 중분류)
    if action_partner != "미기재":
        return action_partner

    # 2️⃣ 작업자가 미기재된 경우, 대분류/중분류로 mech/elect 협력사 결정
    mech_partner = clean_partner_name(mech_name, mode="mech")
    elec_partner = clean_partner_name(elec_name, mode="elec")

    if 대분류 == "작업불량":
        if "전장" in 중분류:
            return elec_partner if elec_partner else "미기재"
        elif "기구" in 중분류:
            return mech_partner if mech_partner else "미기재"
        else:
            return "미기재"

    elif 대분류 == "기구작업불량":
        return mech_partner if mech_partner else "미기재"

    elif 대분류 == "전장작업불량":
        return elec_partner if elec_partner else "미기재"

    elif 대분류 == "부품불량":
        if "기구" in 중분류:
            return mech_partner if mech_partner else "미기재"
        elif "전장" in 중분류:
            return elec_partner if elec_partner else "미기재"
        else:
            return "미기재"

    else:
        return "미기재"


def calculate_production_counts(production_df, target_month):
    """생산대수 카운팅 함수 - DUAL 제품 2배, TMS(M) 특별 처리"""
    # 협력사별 카운트 초기화
    counts = {"BAT": 0, "FNI": 0, "TMS(M)": 0, "P&S": 0, "C&A": 0, "TMS(E)": 0}
    tms_semi_product_count = 0  # TMS(M) 반제품 기여분

    # 월별 필터링
    original_count = len(production_df)
    date_col = None
    for col in ["발생일", "월", "일자", "등록일", "날짜", "공정검사일"]:
        if col in production_df.columns:
            date_col = col
            break

    if date_col:
        print(f"DEBUG: 날짜 컬럼 '{date_col}' 사용하여 월별 필터링")
        production_df[date_col] = pd.to_datetime(
            production_df[date_col], errors="coerce"
        )
        production_df = production_df.dropna(subset=[date_col])
        production_df["month"] = production_df[date_col].dt.strftime("%Y-%m")
        production_df = production_df[production_df["month"] == target_month]
        print(
            f"DEBUG: {target_month} 필터링 - {original_count}건 → {len(production_df)}건"
        )
    else:
        print(
            f"DEBUG: 날짜 컬럼을 찾을 수 없음. 사용 가능한 컬럼: {list(production_df.columns)}"
        )
        print("DEBUG: 월별 필터링 없이 전체 데이터 사용")

    print(f"DEBUG: 생산대수 카운팅 시작 - 총 {len(production_df)}건")

    for idx, row in production_df.iterrows():
        product_name = str(row.get("제품명", "")).strip()
        if not product_name:
            continue

        # DUAL 제품 처리: chamber 2개 = 2대 카운트
        count = 2 if "DUAL" in product_name.upper() else 1

        # 협력사별 카운팅 (매핑 기준)
        mech_partner_raw = str(row.get("협력사(기구)명", "")).strip()
        elec_partner_raw = str(row.get("협력사(전장)명", "")).strip()

        mech_partner = clean_partner_name(mech_partner_raw, "mech")
        elec_partner = clean_partner_name(elec_partner_raw, "elec")

        # 디버그 출력 (모든 제품 출력으로 변경)
        if "DRAGON" in product_name.upper():
            print(
                f"DEBUG DRAGON: {product_name} -> 기구:{mech_partner_raw}->{mech_partner}, 전장:{elec_partner_raw}->{elec_partner}, 카운트:{count}"
            )
        elif idx < 10:  # 처음 10개 출력
            print(
                f"DEBUG: {product_name} -> 기구:{mech_partner_raw}->{mech_partner}, 전장:{elec_partner_raw}->{elec_partner}, 카운트:{count}"
            )

        # 각 협력사에 카운팅 (기본 매핑)
        if mech_partner in counts:
            counts[mech_partner] += count
        if elec_partner in counts:
            counts[elec_partner] += count

        # TMS(M) 반제품 기여분 별도 계산
        semi_product_partner_raw = str(row.get("협력사(반제품)명", "")).strip()
        semi_product_partner = clean_partner_name(semi_product_partner_raw, "semi")

        if semi_product_partner == "TMS(M)":
            tms_semi_product_count += count
            if idx < 10:  # 디버깅용
                print(
                    f"DEBUG 반제품: {product_name} -> 반제품:{semi_product_partner_raw}->{semi_product_partner}, 카운트:{count}"
                )

    # TMS(M)에 반제품 기여분 추가
    counts["TMS(M)"] += tms_semi_product_count

    print(f"\n📊 생산대수 카운팅 결과:")
    for partner, count in counts.items():
        if partner == "TMS(M)":
            direct_count = count - tms_semi_product_count
            print(
                f"  {partner}: {count}대 (직접작업: {direct_count}대 + 반제품기여: {tms_semi_product_count}대)"
            )
        else:
            print(f"  {partner}: {count}대")

    # 전체 제품 카운트 분석
    print(f"\n📋 전체 제품 카운트 분석:")
    total_products = len(production_df)

    # 제품명별 중복 제거 분석
    unique_products = production_df["제품명"].value_counts()
    print(f"  총 데이터 행 수: {total_products}개")
    print(f"  고유 제품명 수: {len(unique_products)}개")

    # 제품명별 상세 분석
    print(f"\n📋 제품명별 상세 분석:")
    dual_unique_count = 0
    non_dual_unique_count = 0
    dual_total_units = 0
    non_dual_total_units = 0

    for product_name, count in unique_products.items():
        is_dual = "DUAL" in product_name.upper()
        units_per_item = 2 if is_dual else 1
        total_units_for_product = count * units_per_item

        if is_dual:
            dual_unique_count += 1
            dual_total_units += total_units_for_product
        else:
            non_dual_unique_count += 1
            non_dual_total_units += total_units_for_product

        print(
            f"  {product_name}: {count}개 × {units_per_item}대 = {total_units_for_product}대"
        )

    print(f"\n📊 요약:")
    print(f"  고유 DUAL 제품명: {dual_unique_count}개 → 총 {dual_total_units}대")
    print(
        f"  고유 일반 제품명: {non_dual_unique_count}개 → 총 {non_dual_total_units}대"
    )
    print(f"  전체 생산대수: {dual_total_units + non_dual_total_units}대")

    # DRAGON 제품 상세 분석
    dragon_products = production_df[
        production_df["제품명"].str.contains("DRAGON", case=False, na=False)
    ]
    if not dragon_products.empty:
        print(f"\n🐉 DRAGON 제품 상세 분석:")
        dragon_summary = dragon_products["제품명"].value_counts()
        dragon_total_units = 0
        for product, count in dragon_summary.items():
            dual_multiplier = 2 if "DUAL" in product.upper() else 1
            total_units_for_product = count * dual_multiplier
            dragon_total_units += total_units_for_product
            print(
                f"  {product}: {count}개 제품 × {dual_multiplier}대 = {total_units_for_product}대"
            )
        print(f"  DRAGON 총계: {dragon_total_units}대")

    return counts


def assign_nan_grade(nan_ratio):
    """NaN 비율 등급 부여 (새로운 엄격한 기준)"""
    if nan_ratio < 1.0:
        return "A"  # 1% 미만 (우수)
    elif nan_ratio < 3.0:
        return "B"  # 1~3% (양호)
    elif nan_ratio < 6.0:
        return "C"  # 3~6% (보통)
    else:
        return "D"  # 6% 이상 (개선필요)


# 불량률 기준 등급 (REV2 기준)
DEFECT_RATE_THRESHOLDS = {
    "MECH": {  # 기구 협력사 (BAT, FNI, TMS(M))
        "A": 6.0,  # 6.0% 미만
        "B": 16.5,  # 6.0~16.5%
        "C": 27.6,  # 16.5~27.6%
        "D": float("inf"),  # 27.6% 이상
    },
    "ELEC": {  # 전장 협력사 (TMS(E), P&S, C&A)
        "A": 1.0,  # 1.0% 미만
        "B": 3.6,  # 1.0~3.6%
        "C": 6.2,  # 3.6~6.2%
        "D": 7.5,  # 6.2~7.5%
        "E": float("inf"),  # 7.5% 이상
    },
}


def calculate_defect_rate(defect_count, production_count):
    """불량률 계산 - (불량건수 ÷ 생산대수) × 100"""
    if production_count == 0:
        print(f"⚠️ 생산대수가 0입니다. 불량률을 계산할 수 없습니다.")
        return 0.0

    defect_rate = (defect_count / production_count) * 100
    return round(defect_rate, 2)


def assign_defect_grade_by_rate(defect_rate, partner_type):
    """불량률 기준 등급 부여"""
    partner_category = "MECH" if partner_type in ["BAT", "FNI", "TMS(M)"] else "ELEC"
    thresholds = DEFECT_RATE_THRESHOLDS[partner_category]

    for grade in ["A", "B", "C", "D", "E"]:
        if grade in thresholds and defect_rate < thresholds[grade]:
            return grade
    return "E"  # 최하등급


def assign_defect_grade(count, partner_type):
    """불량 건수 등급 부여 (기존 방식 - 하위호환성용)"""
    if partner_type in ["BAT", "FNI", "TMS(M)"]:
        if count <= 5:
            return "A"
        elif count <= 10:
            return "B"
        elif count <= 15:
            return "C"
        else:
            return "D"
    else:  # 전장: C&A, P&S, TMS(E)
        if count <= 1:
            return "A"
        elif count <= 3:
            return "B"
        elif count <= 6:
            return "C"
        elif count <= 9:
            return "D"
        else:
            return "E"


def grade_to_score(grade):
    """등급을 10점 만점 점수로 변환"""
    grade_map = {"A": 10, "B": 7.5, "C": 5, "D": 2.5, "E": 0}
    return grade_map.get(grade, 0)


def score_to_grade(score):
    """평균 점수를 등급으로 변환 (내림)"""
    if score >= 8.75:
        return "A"
    elif score >= 6.25:
        return "B"
    elif score >= 3.75:
        return "C"
    elif score >= 1.25:
        return "D"
    else:
        return "E"


def upload_to_github(file_path, repo_name, branch, file_in_repo, token):
    """GitHub에 파일 업로드"""
    try:
        print(f"GitHub 업로드 시작: {repo_name}/{file_in_repo}")
        g = Github(token)
        repo = g.get_repo(repo_name)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            contents = repo.get_contents(file_in_repo, ref=branch)
            repo.update_file(
                contents.path,
                f"Update {file_in_repo}",
                content,
                contents.sha,
                branch=branch,
            )
            print(f"✅ GitHub 파일 업데이트 성공: {repo_name}/{file_in_repo}")
        except:
            repo.create_file(
                file_in_repo, f"Create {file_in_repo}", content, branch=branch
            )
            print(f"✅ GitHub 파일 생성 성공: {repo_name}/{file_in_repo}")
        return f"https://raw.githubusercontent.com/{repo_name}/{branch}/{file_in_repo}"
    except Exception as e:
        print(f"❌ GitHub 업로드 실패: {repo_name}/{file_in_repo} - {str(e)}")
        return None


def generate_nan_details(json_data):
    """주간별 NaN 디테일 데이터 생성"""
    nan_details = {
        "BAT": [],
        "FNI": [],
        "TMS(M)": [],
        "C&A": [],
        "P&S": [],
        "TMS(E)": [],
    }

    # 메인 로직과 동일한 방식으로 데이터 처리
    all_nan_data = []
    for d in json_data:
        try:
            ratios = d.get("ratios", {})
            mech_partner_clean = clean_partner_name(
                d.get("mech_partner", ""), mode="mech"
            )
            elec_partner_clean = clean_partner_name(
                d.get("elec_partner", ""), mode="elec"
            )

            entry = {
                "group_month": d["group_month"],
                "file_date": d.get("file_date", ""),
                "mech_partner": mech_partner_clean,
                "elec_partner": elec_partner_clean,
                "bat_nan_ratio": (
                    ratios.get("mech_nan_ratio", 0.0)
                    if mech_partner_clean == "BAT"
                    else 0.0
                ),
                "fni_nan_ratio": (
                    ratios.get("mech_nan_ratio", 0.0)
                    if mech_partner_clean == "FNI"
                    else 0.0
                ),
                "tms_m_nan_ratio": (
                    ratios.get("mech_nan_ratio", 0.0)
                    if mech_partner_clean == "TMS(M)"
                    else 0.0
                ),
                "cna_nan_ratio": (
                    ratios.get("elec_nan_ratio", 0.0)
                    if elec_partner_clean == "C&A"
                    else 0.0
                ),
                "pns_nan_ratio": (
                    ratios.get("elec_nan_ratio", 0.0)
                    if elec_partner_clean == "P&S"
                    else 0.0
                ),
                "tms_e_nan_ratio": (
                    ratios.get("elec_nan_ratio", 0.0)
                    if elec_partner_clean == "TMS(E)"
                    else 0.0
                ),
            }
            all_nan_data.append(entry)
        except Exception as e:
            print(f"⚠️ 데이터 처리 중 오류: {e}")
            continue

    # pandas DataFrame으로 변환하여 메인 로직과 동일한 처리
    import pandas as pd

    df = pd.DataFrame(all_nan_data)

    # 날짜별로 그룹핑하여 평균 계산 (메인 로직과 동일)
    for file_date in df["file_date"].unique():
        date_data = df[df["file_date"] == file_date]

        # 주차 정보 추출 - 동적 계산으로 개선
        try:
            date_obj = pd.to_datetime(file_date).date()
            week_num = date_obj.isocalendar()[1]  # ISO 주차 계산
            week = f"{week_num}W"
            print(f"DEBUG: {file_date} -> {week}")
        except Exception as e:
            print(f"⚠️ 날짜 {file_date} 주차 계산 실패: {e}")
            continue

        # 각 협력사별 평균 계산
        partners = {
            "BAT": date_data["bat_nan_ratio"].mean(),
            "FNI": date_data["fni_nan_ratio"].mean(),
            "TMS(M)": date_data["tms_m_nan_ratio"].mean(),
            "C&A": date_data["cna_nan_ratio"].mean(),
            "P&S": date_data["pns_nan_ratio"].mean(),
            "TMS(E)": date_data["tms_e_nan_ratio"].mean(),
        }

        for partner, avg_ratio in partners.items():
            nan_details[partner].append({"week": week, "ratio": round(avg_ratio, 2)})

    # 월평균 계산
    for partner in nan_details:
        if nan_details[partner]:
            monthly_avg = sum(item["ratio"] for item in nan_details[partner]) / len(
                nan_details[partner]
            )
            nan_details[partner].append(
                {"week": "월평균", "ratio": round(monthly_avg, 2)}
            )

    return nan_details


def generate_html(
    mech_df, elec_df, month, defect_details, nan_details=None, production_counts=None
):
    """현대 대시보드 형식 HTML 생성 (기구/전장 그룹 분리, 클릭 이벤트 추가, 불량률 기반)"""
    defect_details_json = json.dumps(defect_details, ensure_ascii=False)
    nan_details_json = json.dumps(nan_details or {}, ensure_ascii=False)
    production_counts = production_counts or {}
    print(f"DEBUG: defect_details_json: {defect_details_json}")

    css = """
    <style>
        .chart-section { margin: 10px; }
        .kpi-container { display: flex; flex-wrap: wrap; justify-content: center; }
        .kpi-card { 
            width: 130px; height: 130px; margin: 10px; 
            background: #f8f9fa; border-radius: 8px; 
            display: flex; flex-direction: column; align-items: center; justify-content: center; 
            position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            cursor: pointer; transition: transform 0.2s;
        }
        .kpi-card:hover { transform: translateY(-2px); }
        .emoji { font-size: 2em; }
        .label { font-size: 1.2em; font-weight: bold; margin-top: 5px; }
        .tooltip { 
            visibility: hidden; width: 200px; background-color: #555; color: #fff; 
            text-align: center; border-radius: 6px; padding: 8px; 
            position: absolute; z-index: 1; top: 100%; left: 50%; 
            transform: translateX(-50%); opacity: 0; transition: opacity 0.3s; 
            font-size: 12px; white-space: nowrap;
        }
        .kpi-card:hover .tooltip { visibility: visible; opacity: 1; }
        .defect-table, .nan-table { 
            width: 100%; max-width: 800px; margin: 10px auto; border-collapse: collapse; 
            background: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-radius: 8px;
            overflow: hidden;
        }
        .defect-table th, .defect-table td, .nan-table th, .nan-table td { 
            border: 1px solid #ddd; padding: 12px; text-align: left; 
        }
        .defect-table th { 
            background-color: #f2f2f2; font-weight: bold; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .nan-table th { 
            background-color: #f2f2f2; font-weight: bold; 
            background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
            color: white;
        }
        .defect-table tbody tr:nth-child(even), .nan-table tbody tr:nth-child(even) { background-color: #f9f9f9; }
        .defect-table tbody tr:hover, .nan-table tbody tr:hover { background-color: #e8f4f8; }
        .hidden { display: none; }
        .download-btn { 
            margin: 10px 0; padding: 8px 16px; 
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white; border: none; border-radius: 4px; 
            cursor: pointer; font-weight: bold; transition: all 0.3s;
        }
        .download-btn:hover { 
            background: linear-gradient(135deg, #45a049, #3d8b40);
            transform: translateY(-1px);
        }
        .section-title {
            text-align: center; margin: 20px 0;
            font-size: 24px; font-weight: bold;
            color: #333; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }
        .grade-a { border-left: 4px solid #4CAF50; }
        .grade-b { border-left: 4px solid #2196F3; }
        .grade-c { border-left: 4px solid #FF9800; }
        .grade-d { border-left: 4px solid #f44336; }
        .grade-e { border-left: 4px solid #9C27B0; }
        .evaluation-overview {
            max-width: 1200px; margin: 30px auto; padding: 20px;
            background: #f8f9fa; border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .overview-table {
            width: 100%; border-collapse: collapse; margin: 15px 0;
            background: white; border-radius: 8px; overflow: hidden;
        }
        .overview-table th, .overview-table td {
            border: 1px solid #ddd; padding: 12px; text-align: center;
        }
        .overview-table th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; font-weight: bold;
        }
        .overview-table tbody tr:nth-child(even) { background-color: #f9f9f9; }
        .grade-detail { font-size: 0.9em; color: #666; }
        .weight-info { 
            background: #e3f2fd; padding: 15px; border-radius: 8px; 
            margin: 15px 0; border-left: 4px solid #2196F3;
        }
        .main-title {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        .main-title-tooltip {
            visibility: hidden;
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #fff;
            border: 2px solid #667eea;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            z-index: 1000;
            width: 800px;
            max-width: 90vw;
            opacity: 0;
            transition: all 0.3s ease;
            font-size: 14px;
            text-align: left;
            color: #333;
        }
        .main-title:hover .main-title-tooltip {
            visibility: visible;
            opacity: 1;
        }
        .tooltip-section {
            margin-bottom: 15px;
        }
        .tooltip-section h4 {
            margin: 0 0 8px 0;
            color: #1976d2;
            font-size: 16px;
        }
        .tooltip-section p {
            margin: 5px 0;
            line-height: 1.4;
        }
        .tooltip-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 12px;
        }
        .tooltip-table th, .tooltip-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .tooltip-table th {
            background: #f5f5f5;
            font-weight: bold;
        }
        .tooltip-grade-detail {
            font-size: 11px;
            line-height: 1.3;
        }
    </style>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>협력사 평가 대시보드 - {month}</title>
        {css}
        <script>
            const defectDetails = {defect_details_json};
            const nanDetails = {nan_details_json};
            console.log("DEBUG: defectDetails:", defectDetails);
            console.log("DEBUG: nanDetails:", nanDetails);

            const partnerToIdMap = {{
                'BAT': 'bat',
                'FNI': 'fni',
                'TMS(M)': 'tmsm',
                'P&S': 'pns',
                'TMS(E)': 'tmse',
                'C&A': 'cna'
            }};

            const idToPartnerMap = Object.fromEntries(
                Object.entries(partnerToIdMap).map(([partner, id]) => [id, partner])
            );

            function toggleDefectTable(partnerId) {{
                const partner = idToPartnerMap[partnerId];
                console.log("Toggling table for partner:", partner);
                const table = document.getElementById(`defect-table-${{partnerId}}`);
                
                // 현재 테이블이 이미 표시되어 있으면 숨기기
                if (!table.classList.contains('hidden')) {{
                    table.classList.add('hidden');
                    return;
                }}
                
                // 모든 테이블 숨기기 (다른 테이블이 열려있을 수 있음)
                document.querySelectorAll('.defect-table').forEach(t => t.classList.add('hidden'));
                
                // 선택된 테이블 표시
                table.classList.remove('hidden');
                const details = defectDetails[partner] || [];
                console.log("Details for partner:", partner, details);
                
                let tableBody = '';
                if (details.length === 0) {{
                    tableBody = '<tr><td colspan="4" style="text-align: center; color: #666;">불량 데이터 없음</td></tr>';
                }} else {{
                    details.forEach((item, index) => {{
                        tableBody += `<tr>
                            <td>${{item.productInfo}}</td>
                            <td>${{item.defect}}</td>
                            <td>${{item.action}}</td>
                            <td>${{item.occurDate}}</td>
                        </tr>`;
                    }});
                }}
                table.querySelector('tbody').innerHTML = tableBody;
                
                // 테이블로 스크롤
                table.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}

            function toggleNanTable(partnerId) {{
                const partner = idToPartnerMap[partnerId];
                console.log("Toggling NaN table for partner:", partner);
                const table = document.getElementById(`nan-table-${{partnerId}}`);
                
                // 현재 테이블이 이미 표시되어 있으면 숨기기
                if (!table.classList.contains('hidden')) {{
                    table.classList.add('hidden');
                    return;
                }}
                
                // 모든 NaN 테이블 숨기기
                document.querySelectorAll('.nan-table').forEach(t => t.classList.add('hidden'));
                
                // 선택된 테이블 표시
                table.classList.remove('hidden');
                const details = nanDetails[partner] || [];
                console.log("NaN details for partner:", partner, details);
                
                let tableBody = '';
                if (details.length === 0) {{
                    tableBody = '<tr><td colspan="2" style="text-align: center; color: #666;">NaN 데이터 없음</td></tr>';
                }} else {{
                    details.forEach((item, index) => {{
                        tableBody += `<tr>
                            <td>${{item.week}}</td>
                            <td>${{item.ratio}}%</td>
                        </tr>`;
                    }});
                }}
                table.querySelector('tbody').innerHTML = tableBody;
                
                // 테이블로 스크롤
                table.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}

            function downloadCSV(partnerId) {{
                const partner = idToPartnerMap[partnerId];
                const details = defectDetails[partner] || [];
                console.log("DEBUG: Downloading CSV for partner:", partner, details);
                if (details.length === 0) {{
                    alert('다운로드할 데이터가 없습니다.');
                    return;
                }}

                let csvContent = '\ufeff';
                csvContent += '제품정보,상세불량내용,상세조치내용,발생일\\n';

                details.forEach(item => {{
                    const row = [
                        `"${{item.productInfo.replace(/"/g, '""')}}"`,
                        `"${{item.defect.replace(/"/g, '""')}}"`,
                        `"${{item.action.replace(/"/g, '""')}}"`,
                        `"${{item.occurDate.replace(/"/g, '""')}}"`
                    ];
                    csvContent += row.join(',') + '\\n';
                }});

                const today = new Date();
                const dateStr = today.getFullYear() + '' + 
                               String(today.getMonth() + 1).padStart(2, '0') + '' + 
                               String(today.getDate()).padStart(2, '0');

                const fileName = `${{partner}}_불량내역_${{dateStr}}.csv`;

                const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8' }});
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.setAttribute('href', url);
                link.setAttribute('download', fileName);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
            }}
        </script>
    </head>
    <body>
        <div style="text-align: center; margin: 20px 0;">
            <div class="main-title">
                <h1 style="color: #333; margin-bottom: 10px;">🏭 협력사 평가 대시보드</h1>
                <div class="main-title-tooltip">
                    <div class="tooltip-section">
                        <h4>🎯 평가 목적</h4>
                        <p>① 기구·전장 협력사의 품질 수준을 불량률과 데이터 완성성(누락 비율)으로 객관적으로 평가</p>
                        <p>② 생산량 배경·인센티브·개선 과제 부여 기준 마련</p>
                    </div>
                    
                    <div class="tooltip-section">
                        <h4>📊 평가 지표</h4>
                        <table class="tooltip-table">
                            <tr>
                                <th>지표</th>
                                <th>정의</th>
                                <th>가중치</th>
                                <th>등급 구간</th>
                            </tr>
                            <tr>
                                <td><strong>불량률</strong></td>
                                <td>(월간 불량 건수 ÷ 월간 생산대수) ×100</td>
                                <td><strong style="color: #d32f2f;">70%</strong></td>
                                <td>
                                    <div class="tooltip-grade-detail">
                                        <strong>기구:</strong> A(&lt;6.0%) B(6.0~16.5%) C(16.5~27.6%) D(≥27.6%)<br>
                                        <strong>전장:</strong> A(&lt;1.0%) B(1.0~3.6%) C(3.6~6.2%) D(6.2~7.5%) E(≥7.5%)
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td><strong>NaN 비율</strong></td>
                                <td>(누락 건수 ÷ 전체 대상 건수) ×100</td>
                                <td><strong style="color: #1976d2;">30%</strong></td>
                                <td>
                                    <div class="tooltip-grade-detail">
                                        A(&lt;1%) B(&lt;3%) C(&lt;6%) D(≥6%)
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="tooltip-section">
                        <h4>🏭 생산대수 카운팅 기준</h4>
                        <p><strong>기본 원칙:</strong> Chamber 수 기준 카운트</p>
                        <table class="tooltip-table">
                            <tr>
                                <th>구분</th>
                                <th>카운팅 방식</th>
                                <th>예시</th>
                            </tr>
                            <tr>
                                <td><strong>일반 제품</strong></td>
                                <td>1 Chamber = 1대</td>
                                <td>GAIA-I = 1대</td>
                            </tr>
                            <tr>
                                <td><strong>DUAL 제품</strong></td>
                                <td>2 Chamber = 2대</td>
                                <td>GAIA-I DUAL = 2대</td>
                            </tr>
                            <tr>
                                <td><strong>TMS(M)</strong></td>
                                <td>직접 작업 + 반제품 기여</td>
                                <td>DRAGON 직접작업 + 모든 제품 반제품 도킹</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="tooltip-section">
                        <h4>📈 최종 평가점수 계산</h4>
                        <p><strong>최종점수 = (불량률 점수 × 70%) + (NaN 비율 점수 × 30%)</strong></p>
                        <p style="color: #666; font-size: 12px;">
                            • 기구/전장 협력사별로 분리하여 순위 산정<br>
                            • 동점시 불량률이 낮은 협력사가 상위 순위
                        </p>
                    </div>
                </div>
            </div>
            <p style="color: #666; font-size: 16px;">기준월: {month}</p>
        </div>
        <div class="chart-section">
            <h2 class="section-title">🔧 기구 협력사 평가 지수</h2>
            <div class="kpi-container">
    """

    for _, row in mech_df.iterrows():
        partner = row["partner"]
        weighted_score = row["weighted_score"]
        final_grade = row["final_grade"]
        defect_count = row["defect_count"]
        defect_rate = row["defect_rate"]  # 불량률 추가
        nan_ratio = row["nan_ratio"]
        emoji = row["emoji"]
        production_count = production_counts.get(partner, 0)  # 생산대수 추가

        # 등급별 CSS 클래스
        grade_class = f"grade-{final_grade.lower()}"

        # 파트너 ID 생성 (특수문자 제거)
        partner_id = partner.lower().replace("&", "n").replace("(", "").replace(")", "")

        html += f"""
                <div class="kpi-card {grade_class}" onclick="toggleDefectTable('{partner_id}')">
                    <div class="emoji">{emoji}</div>
                    <div class="label">{partner}</div>
                    <div class="tooltip">
                        평가점수: {weighted_score:.1f}점 ({final_grade}등급)<br>
                        불량률: {defect_rate:.2f}%<br>
                        불량건수: {defect_count}건<br>
                        생산대수: {production_count}대<br>
                        누락비율: <span onclick="event.stopPropagation(); toggleNanTable('{partner_id}')" style="color: #ffeb3b; cursor: pointer; text-decoration: underline;">{nan_ratio:.1f}%</span><br>
                        <small>클릭하여 상세보기</small>
                    </div>
                </div>
        """

    html += """
            </div>
            <table id="defect-table-bat" class="defect-table hidden">
                <thead>
                    <tr>
                        <th colspan="4">
                            <button class="download-btn" onclick="downloadCSV('bat')">CSV 다운로드</button>
                        </th>
                    </tr>
                    <tr><th>제품정보</th><th>상세불량내용</th><th>상세조치내용</th><th>발생일</th></tr>
                </thead>
                <tbody></tbody>
            </table>
            <table id="defect-table-fni" class="defect-table hidden">
                <thead>
                    <tr>
                        <th colspan="4">
                            <button class="download-btn" onclick="downloadCSV('fni')">CSV 다운로드</button>
                        </th>
                    </tr>
                    <tr><th>제품정보</th><th>상세불량내용</th><th>상세조치내용</th><th>발생일</th></tr>
                </thead>
                <tbody></tbody>
            </table>
            <table id="defect-table-tmsm" class="defect-table hidden">
                <thead>
                    <tr>
                        <th colspan="4">
                            <button class="download-btn" onclick="downloadCSV('tmsm')">CSV 다운로드</button>
                        </th>
                    </tr>
                    <tr><th>제품정보</th><th>상세불량내용</th><th>상세조치내용</th><th>발생일</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        <div class="chart-section">
            <h2 class="section-title">⚡ 전장 협력사 평가 지수</h2>
            <div class="kpi-container">
    """

    for _, row in elec_df.iterrows():
        partner = row["partner"]
        weighted_score = row["weighted_score"]
        final_grade = row["final_grade"]
        defect_count = row["defect_count"]
        defect_rate = row["defect_rate"]  # 불량률 추가
        nan_ratio = row["nan_ratio"]
        emoji = row["emoji"]
        production_count = production_counts.get(partner, 0)  # 생산대수 추가

        # 등급별 CSS 클래스
        grade_class = f"grade-{final_grade.lower()}"

        # 파트너 ID 생성 (특수문자 제거)
        partner_id = partner.lower().replace("&", "n").replace("(", "").replace(")", "")

        html += f"""
                <div class="kpi-card {grade_class}" onclick="toggleDefectTable('{partner_id}')">
                    <div class="emoji">{emoji}</div>
                    <div class="label">{partner}</div>
                    <div class="tooltip">
                        평가점수: {weighted_score:.1f}점 ({final_grade}등급)<br>
                        불량률: {defect_rate:.2f}%<br>
                        불량건수: {defect_count}건<br>
                        생산대수: {production_count}대<br>
                        누락비율: <span onclick="event.stopPropagation(); toggleNanTable('{partner_id}')" style="color: #ffeb3b; cursor: pointer; text-decoration: underline;">{nan_ratio:.1f}%</span><br>
                        <small>클릭하여 상세보기</small>
                    </div>
                </div>
        """

    html += """
            </div>
            <table id="defect-table-pns" class="defect-table hidden">
                <thead>
                    <tr>
                        <th colspan="4">
                            <button class="download-btn" onclick="downloadCSV('pns')">CSV 다운로드</button>
                        </th>
                    </tr>
                    <tr><th>제품정보</th><th>상세불량내용</th><th>상세조치내용</th><th>발생일</th></tr>
                </thead>
                <tbody></tbody>
            </table>
            <table id="defect-table-tmse" class="defect-table hidden">
                <thead>
                    <tr>
                        <th colspan="4">
                            <button class="download-btn" onclick="downloadCSV('tmse')">CSV 다운로드</button>
                        </th>
                    </tr>
                    <tr><th>제품정보</th><th>상세불량내용</th><th>상세조치내용</th><th>발생일</th></tr>
                </thead>
                <tbody></tbody>
            </table>
            <table id="defect-table-cna" class="defect-table hidden">
                <thead>
                    <tr>
                        <th colspan="4">
                            <button class="download-btn" onclick="downloadCSV('cna')">CSV 다운로드</button>
                        </th>
                    </tr>
                    <tr><th>제품정보</th><th>상세불량내용</th><th>상세조치내용</th><th>발생일</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <div style="margin-top: 40px;">
            <h2 class="section-title">📊 누락률 주간별 추이</h2>
            
            <table id="nan-table-bat" class="nan-table hidden">
                <thead>
                    <tr>
                        <th colspan="2" style="text-align: center; padding: 15px;">
                            <strong>BAT 누락률 주간별 추이</strong>
                        </th>
                    </tr>
                    <tr>
                        <th style="width: 50%;">주차</th>
                        <th style="width: 50%;">누락률</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- 동적으로 생성됨 -->
                </tbody>
            </table>
            
            <table id="nan-table-fni" class="nan-table hidden">
                <thead>
                    <tr>
                        <th colspan="2" style="text-align: center; padding: 15px;">
                            <strong>FNI 누락률 주간별 추이</strong>
                        </th>
                    </tr>
                    <tr>
                        <th style="width: 50%;">주차</th>
                        <th style="width: 50%;">누락률</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- 동적으로 생성됨 -->
                </tbody>
            </table>
            
            <table id="nan-table-tmsm" class="nan-table hidden">
                <thead>
                    <tr>
                        <th colspan="2" style="text-align: center; padding: 15px;">
                            <strong>TMS(M) 누락률 주간별 추이</strong>
                        </th>
                    </tr>
                    <tr>
                        <th style="width: 50%;">주차</th>
                        <th style="width: 50%;">누락률</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- 동적으로 생성됨 -->
                </tbody>
            </table>
            
            <table id="nan-table-pns" class="nan-table hidden">
                <thead>
                    <tr>
                        <th colspan="2" style="text-align: center; padding: 15px;">
                            <strong>P&S 누락률 주간별 추이</strong>
                        </th>
                    </tr>
                    <tr>
                        <th style="width: 50%;">주차</th>
                        <th style="width: 50%;">누락률</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- 동적으로 생성됨 -->
                </tbody>
            </table>
            
            <table id="nan-table-tmse" class="nan-table hidden">
                <thead>
                    <tr>
                        <th colspan="2" style="text-align: center; padding: 15px;">
                            <strong>TMS(E) 누락률 주간별 추이</strong>
                        </th>
                    </tr>
                    <tr>
                        <th style="width: 50%;">주차</th>
                        <th style="width: 50%;">누락률</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- 동적으로 생성됨 -->
                </tbody>
            </table>
            
            <table id="nan-table-cna" class="nan-table hidden">
                <thead>
                    <tr>
                        <th colspan="2" style="text-align: center; padding: 15px;">
                            <strong>C&A 누락률 주간별 추이</strong>
                        </th>
                    </tr>
                    <tr>
                        <th style="width: 50%;">주차</th>
                        <th style="width: 50%;">누락률</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- 동적으로 생성됨 -->
                </tbody>
            </table>
        </div>
        
        <div style="text-align: center; margin: 40px 0; color: #666; font-size: 14px;">
            <p>🏆 등급: A(우수) → B(양호) → C(보통) → D(개선필요) → E(불량)</p>
            <p>📋 협력사 카드를 클릭하면 해당 월의 불량 상세 내역을 확인할 수 있습니다.</p>
            <p>📊 누락률(노란색)을 클릭하면 주간별 추이를 확인할 수 있습니다.</p>
        </div>
    </body>
    </html>
    """
    return html


def print_kpi_grades(start_month=SELECTED_MONTH):
    """협력사 KPI 등급 출력 (불량률 기반)"""
    print(f"=== 협력사 KPI 분석 시작 ({start_month}) - 불량률 기반 ===")

    # 1. 생산대수 데이터 로드
    production_df = load_production_data()
    if production_df is None:
        print("❌ 생산대수 데이터를 로드할 수 없습니다.")
        return

    production_counts = calculate_production_counts(production_df, start_month)
    print(f"✅ 생산대수 데이터 로드 완료")

    # 2. 불량 데이터 로드
    df_defect = load_sheets_data()
    if df_defect is None:
        print("❌ 불량 데이터를 로드할 수 없습니다.")
        return

    # 컬럼명 확인
    print(f"DEBUG: 사용 가능한 컬럼명: {list(df_defect.columns)}")

    # 날짜 컬럼 찾기 (발견일, 일자, 날짜 등 가능한 컬럼명들)
    date_columns = ["발견일", "일자", "날짜", "등록일", "작성일", "발생일", "검사일"]
    date_col = None
    for col in date_columns:
        if col in df_defect.columns:
            date_col = col
            break

    if date_col is None:
        print(
            f"❌ 날짜 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df_defect.columns)}"
        )
        return

    print(f"DEBUG: 날짜 컬럼으로 '{date_col}' 사용")

    # 월별 필터링
    df_defect[date_col] = pd.to_datetime(df_defect[date_col], errors="coerce")
    df_defect = df_defect.dropna(subset=[date_col])
    df_defect["month"] = df_defect[date_col].dt.strftime("%Y-%m")
    df_filtered = df_defect[df_defect["month"] == start_month]

    # 협력사별 불량 건수 계산
    partner_counts = defaultdict(int)
    defect_details = defaultdict(list)

    # 협력사별 불량률 계산을 위한 딕셔너리
    partner_defect_rates = {}

    for _, row in df_filtered.iterrows():
        partner = get_partner_for_row(row)
        if partner != "미기재":
            partner_counts[partner] += 1
            defect_details[partner].append(
                {
                    "date": row[date_col].strftime("%Y-%m-%d"),
                    "category": f"{row.get('대분류', '')}/{row.get('중분류', '')}",
                    "description": row.get("상세불량내용", ""),
                    "productInfo": f"{row.get('제품S/N', '')}/{row.get('제품명', '')}",
                    "defect": row.get("상세불량내용", ""),
                    "action": row.get("상세조치내용", ""),
                    "occurDate": (
                        row.get("발생일", "").strftime("%Y-%m-%d")
                        if pd.notna(row.get("발생일", ""))
                        else ""
                    ),
                }
            )

    # 3. 협력사별 불량률 계산
    all_partners = ["BAT", "FNI", "TMS(M)", "P&S", "TMS(E)", "C&A"]
    for partner in all_partners:
        defect_count = partner_counts.get(partner, 0)
        production_count = production_counts.get(partner, 0)
        defect_rate = calculate_defect_rate(defect_count, production_count)
        partner_defect_rates[partner] = defect_rate

    # defect_details를 올바른 형식으로 변환
    formatted_defect_details = {}
    for partner, details in defect_details.items():
        formatted_defect_details[partner] = [
            {
                "productInfo": detail["productInfo"],
                "defect": detail["defect"],
                "action": detail["action"],
                "occurDate": detail["occurDate"],
            }
            for detail in details
        ]

    print(f"📊 {start_month} 협력사별 불량률 분석:")
    print(f"{'협력사':<10} {'생산대수':<8} {'불량건수':<8} {'불량률(%)':<10}")
    print("-" * 40)
    for partner in all_partners:
        production_count = production_counts.get(partner, 0)
        defect_count = partner_counts.get(partner, 0)
        defect_rate = partner_defect_rates[partner]
        print(
            f"{partner:<10} {production_count:<8} {defect_count:<8} {defect_rate:<10}"
        )
    print("-" * 40)

    # JSON 데이터 로드
    json_data = load_json_files_from_drive(year_month=start_month)
    if not json_data:
        print(f"⚠️ {start_month} 데이터가 없습니다.")
        return

    # NaN 디테일 데이터 생성
    nan_details = generate_nan_details(json_data)
    print(f"📊 NaN 디테일 데이터 생성 완료: {len(nan_details)} 협력사")

    # 주간별 데이터를 먼저 정리 (중복 제거)
    # JSON 데이터 처리 (원래 단순 로직으로 복원)
    all_nan_data = []
    for d in json_data:
        try:
            ratios = d.get("ratios", {})
            mech_partner_clean = clean_partner_name(
                d.get("mech_partner", ""), mode="mech"
            )
            elec_partner_clean = clean_partner_name(
                d.get("elec_partner", ""), mode="elec"
            )

            entry = {
                "group_month": d["group_month"],
                "mech_partner": mech_partner_clean,
                "elec_partner": elec_partner_clean,
                "bat_nan_ratio": (
                    ratios.get("mech_nan_ratio", 0.0)
                    if mech_partner_clean == "BAT"
                    else 0.0
                ),
                "fni_nan_ratio": (
                    ratios.get("mech_nan_ratio", 0.0)
                    if mech_partner_clean == "FNI"
                    else 0.0
                ),
                "tms_m_nan_ratio": (
                    ratios.get("mech_nan_ratio", 0.0)
                    if mech_partner_clean == "TMS(M)"
                    else 0.0
                ),
                "cna_nan_ratio": (
                    ratios.get("elec_nan_ratio", 0.0)
                    if elec_partner_clean == "C&A"
                    else 0.0
                ),
                "pns_nan_ratio": (
                    ratios.get("elec_nan_ratio", 0.0)
                    if elec_partner_clean == "P&S"
                    else 0.0
                ),
                "tms_e_nan_ratio": (
                    ratios.get("elec_nan_ratio", 0.0)
                    if elec_partner_clean == "TMS(E)"
                    else 0.0
                ),
            }
            all_nan_data.append(entry)
        except Exception as e:
            print(f"⚠️ JSON 데이터 항목 처리 실패: {str(e)}")
            continue

    if not all_nan_data:
        print("⚠️ JSON 데이터가 없습니다.")
        return

    df_nan = pd.DataFrame(all_nan_data)
    df_nan["date"] = pd.to_datetime(df_nan["group_month"])
    df_nan.set_index("date", inplace=True)
    df_monthly = df_nan.groupby("group_month").mean(numeric_only=True)

    partner_columns = [
        ("bat_nan_ratio", "BAT"),
        ("fni_nan_ratio", "FNI"),
        ("tms_m_nan_ratio", "TMS(M)"),
        ("cna_nan_ratio", "C&A"),
        ("pns_nan_ratio", "P&S"),
        ("tms_e_nan_ratio", "TMS(E)"),
    ]
    df_monthly = df_monthly[[col[0] for col in partner_columns]].rename(
        columns={col[0]: col[1] for col in partner_columns}
    )

    results = []
    for month, row in df_monthly.iterrows():
        for partner in df_monthly.columns:
            nan_ratio = row[partner]
            nan_grade = assign_nan_grade(nan_ratio)
            defect_count = partner_counts.get(partner, 0)
            defect_rate = partner_defect_rates.get(partner, 0.0)
            defect_grade = assign_defect_grade_by_rate(
                defect_rate, partner
            )  # 불량률 기준 등급으로 변경
            nan_score = grade_to_score(nan_grade)
            defect_score = grade_to_score(defect_grade)
            weighted_score = (defect_score * 0.7) + (nan_score * 0.3)
            weighted_score = round(weighted_score, 1)
            final_grade = score_to_grade(weighted_score)

            results.append(
                {
                    "month": month,
                    "partner": partner,
                    "nan_ratio": nan_ratio,
                    "nan_grade": nan_grade,
                    "defect_count": defect_count,
                    "defect_rate": defect_rate,  # 불량률 추가
                    "defect_grade": defect_grade,
                    "final_grade": final_grade,
                    "weighted_score": weighted_score,
                }
            )

    df_results = pd.DataFrame(results)
    mech_partners = ["BAT", "FNI", "TMS(M)"]
    elec_partners = ["P&S", "TMS(E)", "C&A"]

    mech_df = df_results[df_results["partner"].isin(mech_partners)]
    mech_df = mech_df.sort_values(
        by=["weighted_score", "defect_rate"], ascending=[False, True]
    )  # 불량률로 정렬
    mech_df["emoji"] = ""
    top_3_mech = mech_df.head(3).index
    if len(top_3_mech) > 0:
        mech_df.loc[top_3_mech[0], "emoji"] = "🥇"
    if len(top_3_mech) > 1:
        mech_df.loc[top_3_mech[1], "emoji"] = "🥈"
    if len(top_3_mech) > 2:
        mech_df.loc[top_3_mech[2], "emoji"] = "🥉"

    elec_df = df_results[df_results["partner"].isin(elec_partners)]
    elec_df = elec_df.sort_values(
        by=["weighted_score", "defect_rate"], ascending=[False, True]
    )  # 불량률로 정렬
    elec_df["emoji"] = ""
    top_3_elec = elec_df.head(3).index
    if len(top_3_elec) > 0:
        elec_df.loc[top_3_elec[0], "emoji"] = "🥇"
    if len(top_3_elec) > 1:
        elec_df.loc[top_3_elec[1], "emoji"] = "🥈"
    if len(top_3_elec) > 2:
        elec_df.loc[top_3_elec[2], "emoji"] = "🥉"

    html_content = generate_html(
        mech_df,
        elec_df,
        start_month,
        formatted_defect_details,
        nan_details,
        production_counts,
    )
    html_file = "partner_kpi.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ HTML 파일 생성 완료: {html_file}")

    if not TEST_MODE:
        print("GitHub 업로드 프로세스 시작")
        # 첫 번째 저장소 업로드
        repo_name_1 = f"{GITHUB_USERNAME_1}/{GITHUB_REPO_1}"
        github_url_1 = upload_to_github(
            html_file, repo_name_1, GITHUB_BRANCH_1, HTML_FILENAME_1, GITHUB_TOKEN_1
        )
        if github_url_1:
            iframe_tag = (
                f'<iframe src="{github_url_1}" width="800" height="600"></iframe>'
            )
            print(f"\n대시보드용 iframe 태그 (GST_Factory_Dashboard):")
            print(iframe_tag)
        # 두 번째 저장소 업로드
        repo_name_2 = f"{GITHUB_USERNAME_2}/{GITHUB_REPO_2}"
        github_url_2 = upload_to_github(
            html_file, repo_name_2, GITHUB_BRANCH_2, HTML_FILENAME_2, GITHUB_TOKEN_2
        )
        if github_url_2:
            iframe_tag = (
                f'<iframe src="{github_url_2}" width="800" height="600"></iframe>'
            )
            print(f"\n대시보드용 iframe 태그 (gst-factory):")
            print(iframe_tag)
        print("GitHub 업로드 프로세스 완료")
    else:
        print("🟡 TEST_MODE=True: GitHub 업로드 건너뛰기, 로컬 저장만 수행")

    print("\n📊 월별 협력사 KPI 등급 (기구 협력사) - 불량률 기준")
    print("협력사    NaN 비율(%)  NaN 등급  불량률(%)  불량 등급  최종 등급  평가 점수")
    print("-" * 72)
    for _, row in mech_df.iterrows():
        print(
            f"{row['partner']:<10} {row['nan_ratio']:>10.1f}  {row['nan_grade']:>8}  {row['defect_rate']:>8.2f}  {row['defect_grade']:>8}  {row['final_grade']:>8}  {row['weighted_score']:>8.1f}"
        )

    print("\n📊 월별 협력사 KPI 등급 (전장 협력사) - 불량률 기준")
    print("협력사    NaN 비율(%)  NaN 등급  불량률(%)  불량 등급  최종 등급  평가 점수")
    print("-" * 72)
    for _, row in elec_df.iterrows():
        print(
            f"{row['partner']:<10} {row['nan_ratio']:>10.1f}  {row['nan_grade']:>8}  {row['defect_rate']:>8.2f}  {row['defect_grade']:>8}  {row['final_grade']:>8}  {row['weighted_score']:>8.1f}"
        )

    print("\n📊 [협력사별 총 불량 카운트 누적 결과]")
    all_partners = ["BAT", "FNI", "TMS(M)", "P&S", "TMS(E)", "C&A"]
    for partner in all_partners:
        count = partner_counts.get(partner, 0)
        print(f"{partner:<15} : {count}건")


def test_defect_rate_calculation(test_month=SELECTED_MONTH):
    """불량률 계산 테스트 함수"""
    print(f"🧪 불량률 계산 테스트 시작 - {test_month}")
    print("=" * 80)

    # 1. 생산대수 데이터 로드
    production_df = load_production_data()
    if production_df is None:
        print("❌ 생산대수 데이터 로드 실패")
        return False

    production_counts = calculate_production_counts(production_df, test_month)

    # 2. 불량 데이터 로드
    df_defect = load_sheets_data()
    if df_defect is None:
        print("❌ 불량 데이터 로드 실패")
        return False

    # 컬럼명 확인
    date_columns = ["발견일", "일자", "날짜", "등록일", "작성일", "발생일", "검사일"]
    date_col = None
    for col in date_columns:
        if col in df_defect.columns:
            date_col = col
            break

    if date_col is None:
        print(
            f"❌ 날짜 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df_defect.columns)}"
        )
        return False

    # 월별 필터링
    df_defect[date_col] = pd.to_datetime(df_defect[date_col], errors="coerce")
    df_defect = df_defect.dropna(subset=[date_col])
    df_defect["month"] = df_defect[date_col].dt.strftime("%Y-%m")
    df_filtered = df_defect[df_defect["month"] == test_month]

    # 3. 협력사별 불량 건수 계산
    partner_defect_counts = defaultdict(int)
    for _, row in df_filtered.iterrows():
        partner = get_partner_for_row(row)
        if partner != "미기재":
            partner_defect_counts[partner] += 1

    # 4. 불량률 계산 및 등급 부여
    print(f"\n📊 {test_month} 불량률 분석 결과:")
    print("-" * 80)
    print(
        f"{'협력사':<10} {'생산대수':<8} {'불량건수':<8} {'불량률(%)':<10} {'건수등급':<8} {'불량률등급':<10}"
    )
    print("-" * 80)

    all_partners = ["BAT", "FNI", "TMS(M)", "P&S", "TMS(E)", "C&A"]

    for partner in all_partners:
        production_count = production_counts.get(partner, 0)
        defect_count = partner_defect_counts.get(partner, 0)

        # 불량률 계산
        defect_rate = calculate_defect_rate(defect_count, production_count)

        # 등급 계산
        count_grade = assign_defect_grade(defect_count, partner)
        rate_grade = assign_defect_grade_by_rate(defect_rate, partner)

        print(
            f"{partner:<10} {production_count:<8} {defect_count:<8} {defect_rate:<10} {count_grade:<8} {rate_grade:<10}"
        )

    print("-" * 80)
    print("🎯 불량률 기준:")
    print("  기구 (BAT, FNI, TMS(M)): A<6.0% | B:6.0-16.5% | C:16.5-27.6% | D≥27.6%")
    print(
        "  전장 (P&S, TMS(E), C&A): A<1.0% | B:1.0-3.6% | C:3.6-6.2% | D:6.2-7.5% | E≥7.5%"
    )

    return True


def test_production_data_loading(test_month=SELECTED_MONTH):
    """생산대수 데이터 로딩 및 카운팅 테스트"""
    print(f"🧪 생산대수 데이터 테스트 시작 - {test_month}")
    print("=" * 60)

    # 생산대수 데이터 로드
    production_df = load_production_data()
    if production_df is None:
        print("❌ 생산대수 데이터 로드 실패")
        return False

    print(f"✅ 생산대수 데이터 로드 성공: {len(production_df)}건")

    # 샘플 데이터 출력
    print("\n📋 생산 데이터 샘플 (처음 5건):")
    for i in range(min(5, len(production_df))):
        row = production_df.iloc[i]
        print(f"  {i+1}. 제품명: {row.get('제품명', 'N/A')}")
        print(f"     기구: {row.get('협력사(기구)명', 'N/A')}")
        print(f"     전장: {row.get('협력사(전장)명', 'N/A')}")
        print()

    # 생산대수 카운팅 테스트
    production_counts = calculate_production_counts(production_df, test_month)

    print(f"\n🎯 {test_month} 생산대수 카운팅 완료!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    print(f"TEST_MODE 상태: {TEST_MODE}")

    # 불량률 기반 KPI 등급 출력 및 HTML 생성
    print("\n🚀 불량률 기반 KPI 분석 및 HTML 생성")
    print_kpi_grades(start_month=SELECTED_MONTH)
