#!/usr/bin/env python3
"""
GitHub Actions용 독립적인 NaN 데이터 추출기
PAD_partner_kpi 프로젝트 의존성 없이 동작
"""

import os
import json
import datetime
from collections import defaultdict
import tempfile

# 환경변수 로드
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("📁 .env 파일 로드 완료")
except ImportError:
    print("ℹ️ python-dotenv가 설치되지 않음 - 시스템 환경변수 사용")


def setup_google_credentials():
    """환경변수에서 Google Service Key 설정"""
    service_key_json = os.getenv("GOOGLE_SERVICE_KEY")

    if not service_key_json:
        print("❌ GOOGLE_SERVICE_KEY 환경변수가 설정되지 않았습니다.")
        return False

    try:
        service_key = json.loads(service_key_json)
        temp_key_file = tempfile.mktemp(suffix=".json")
        with open(temp_key_file, "w") as f:
            json.dump(service_key, f)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_key_file
        print("✅ Google Service Key 설정 완료")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ GOOGLE_SERVICE_KEY JSON 파싱 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ Google Service Key 설정 오류: {e}")
        return False


def load_google_drive_data(folder_id, year_month):
    """Google Drive에서 데이터 로드"""
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account

        # 인증 정보 로드
        credentials = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        drive_service = build("drive", "v3", credentials=credentials)

        # 폴더에서 JSON 파일 검색
        query = f"'{folder_id}' in parents and name contains '{year_month}' and name contains '.json'"
        results = drive_service.files().list(q=query).execute()
        files = results.get("files", [])

        if not files:
            print(f"❌ {year_month}에 해당하는 JSON 파일을 찾을 수 없습니다.")
            return []

        all_data = []
        for file_info in files:
            file_id = file_info["id"]
            file_content = drive_service.files().get_media(fileId=file_id).execute()
            data = json.loads(file_content.decode("utf-8"))
            all_data.extend(data if isinstance(data, list) else [data])

        print(f"✅ Google Drive에서 {len(all_data)}개 레코드 로드 완료")
        return all_data

    except Exception as e:
        print(f"❌ Google Drive 데이터 로드 실패: {e}")
        return []


def clean_partner_name(partner_name, mode="mech"):
    """협력사명 정리"""
    if not partner_name:
        return ""

    # 기본 정리
    cleaned = str(partner_name).strip().upper()

    # 협력사별 매핑
    partner_mappings = {
        "mech": {
            "주식회사 비에이티": "BAT",
            "비에이티": "BAT",
            "BAT": "BAT",
            "FNI": "FNI",
            "TMS": "TMS(M)",
            "TMS(M)": "TMS(M)",
        },
        "elec": {"C&A": "C&A", "P&S": "P&S", "TMS": "TMS(E)", "TMS(E)": "TMS(E)"},
    }

    mappings = partner_mappings.get(mode, {})
    for key, value in mappings.items():
        if key.upper() in cleaned:
            return value

    return cleaned


def extract_nan_data_simple(year_month="2025-08"):
    """간단한 NaN 데이터 추출"""
    print(f"🔍 {year_month} NaN 데이터 추출 시작...")

    # Google 인증 설정
    if not setup_google_credentials():
        return None

    # Drive Folder ID 가져오기
    folder_id = os.getenv("DRIVE_FOLDER_ID")
    if not folder_id:
        print("❌ DRIVE_FOLDER_ID 환경변수가 설정되지 않았습니다.")
        return None

    # 데이터 로드
    json_data = load_google_drive_data(folder_id, year_month)
    if not json_data:
        return None

    # 기본 구조 생성
    weekly_stats = {}
    partner_summary = defaultdict(
        lambda: {"total_tasks": 0, "nan_count": 0, "weeks": {}}
    )

    # 데이터 처리
    for record in json_data:
        try:
            file_date = record.get("file_date", "")
            if not file_date:
                continue

            # 주차 정보 계산
            from datetime import datetime

            date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
            week_num = date_obj.isocalendar()[1]
            week_key = f"{week_num}주차"

            if week_key not in weekly_stats:
                weekly_stats[week_key] = {
                    "week_number": week_num,
                    "date": file_date,
                    "weekday": date_obj.strftime("%A"),
                    "is_sunday_data": week_num >= 33,
                    "data_source": "일요일" if week_num >= 33 else "금요일",
                    "total_records": 0,
                    "partners": {"mech": {}, "elec": {}},
                }

            # 기구 협력사 처리
            mech_partner = clean_partner_name(record.get("mech_partner", ""), "mech")
            if mech_partner:
                if mech_partner not in weekly_stats[week_key]["partners"]["mech"]:
                    weekly_stats[week_key]["partners"]["mech"][mech_partner] = {
                        "total_tasks": 0,
                        "nan_count": 0,
                        "nan_ratio": 0.0,
                        "records": [],
                    }

                # 임시 비율 계산 (실제로는 더 복잡한 로직 필요)
                ratios = record.get("ratios", {})
                nan_ratio = ratios.get("mech_nan_ratio", 0.0)
                total_tasks = record.get("total_tasks", 0)
                nan_count = int(total_tasks * nan_ratio / 100) if total_tasks > 0 else 0

                partner_data = weekly_stats[week_key]["partners"]["mech"][mech_partner]
                partner_data["total_tasks"] += total_tasks
                partner_data["nan_count"] += nan_count

                # 상세 레코드 추가
                if nan_count > 0:
                    partner_data["records"].append(
                        {
                            "order_no": record.get("order_no", ""),
                            "order_href": record.get("links", {}).get("order_href", ""),
                            "model_name": record.get("model_name", ""),
                            "nan_count": nan_count,
                            "total_tasks": total_tasks,
                            "nan_ratio": nan_ratio,
                        }
                    )

            # 전장 협력사 처리 (동일한 로직)
            elec_partner = clean_partner_name(record.get("elec_partner", ""), "elec")
            if elec_partner:
                if elec_partner not in weekly_stats[week_key]["partners"]["elec"]:
                    weekly_stats[week_key]["partners"]["elec"][elec_partner] = {
                        "total_tasks": 0,
                        "nan_count": 0,
                        "nan_ratio": 0.0,
                        "records": [],
                    }

                ratios = record.get("ratios", {})
                nan_ratio = ratios.get("elec_nan_ratio", 0.0)
                total_tasks = record.get("total_tasks", 0)
                nan_count = int(total_tasks * nan_ratio / 100) if total_tasks > 0 else 0

                partner_data = weekly_stats[week_key]["partners"]["elec"][elec_partner]
                partner_data["total_tasks"] += total_tasks
                partner_data["nan_count"] += nan_count

                if nan_count > 0:
                    partner_data["records"].append(
                        {
                            "order_no": record.get("order_no", ""),
                            "order_href": record.get("links", {}).get("order_href", ""),
                            "model_name": record.get("model_name", ""),
                            "nan_count": nan_count,
                            "total_tasks": total_tasks,
                            "nan_ratio": nan_ratio,
                        }
                    )

        except Exception as e:
            print(f"⚠️ 레코드 처리 중 오류: {e}")
            continue

    # 비율 재계산
    for week, stats in weekly_stats.items():
        for partner_type in ["mech", "elec"]:
            for partner, data in stats["partners"][partner_type].items():
                if data["total_tasks"] > 0:
                    data["nan_ratio"] = (data["nan_count"] / data["total_tasks"]) * 100

                # partner_summary 업데이트
                partner_summary[partner]["total_tasks"] += data["total_tasks"]
                partner_summary[partner]["nan_count"] += data["nan_count"]
                partner_summary[partner]["weeks"][week] = {
                    "nan_count": data["nan_count"],
                    "total_tasks": data["total_tasks"],
                }

    # 전체 비율 계산
    for partner, data in partner_summary.items():
        if data["total_tasks"] > 0:
            data["nan_ratio"] = (data["nan_count"] / data["total_tasks"]) * 100

    result = {
        "extracted_at": datetime.datetime.now().isoformat(),
        "period": year_month,
        "total_records": len(json_data),
        "weekly_stats": weekly_stats,
        "partner_summary": dict(partner_summary),
        "metadata": {
            "data_source_logic": "33주차부터 일요일, 32주차 이하 금요일",
            "weeks_analyzed": list(weekly_stats.keys()),
            "extraction_method": "github_actions_independent",
            "original_ratios_used": True,
        },
    }

    print(
        f"✅ 데이터 추출 완료: {len(weekly_stats)}주차, {len(partner_summary)}개 협력사"
    )
    return result


def save_data(data, year_month):
    """데이터 저장"""
    if not data:
        return False

    try:
        filename = f"nan_data_{year_month.replace('-', '_')}_improved.json"
        filepath = f"data/{filename}"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 데이터 저장 완료: {filepath}")
        return True
    except Exception as e:
        print(f"❌ 파일 저장 중 오류: {e}")
        return False


if __name__ == "__main__":
    months = ["2025-06", "2025-07", "2025-08"]

    print("🚀 GitHub Actions용 NaN 데이터 추출 시작")
    print("=" * 50)

    for month in months:
        print(f"\n📅 {month} 처리 중...")
        data = extract_nan_data_simple(month)
        if data:
            save_data(data, month)
        else:
            print(f"❌ {month} 데이터 추출 실패")

    print(f"\n✅ 모든 월별 데이터 추출 완료!")
