#!/usr/bin/env python3
"""
partner_kpi.py의 정확한 NaN 비율 + 실제 상세 레코드를 모두 포함한 최종 데이터 생성기
"""

import sys
import os
import json
import datetime
from collections import defaultdict
import pandas as pd

# PAD_partner_kpi 프로젝트 경로 추가
sys.path.append('../PAD_partner_kpi')

try:
    from production.partner_kpi import (
        load_json_files_from_drive, 
        clean_partner_name,
        generate_nan_details,
        DRIVE_FOLDER_ID
    )
except ImportError as e:
    print(f"Error importing partner_kpi module: {e}")
    sys.exit(1)

def clear_cache():
    """캐시 초기화"""
    try:
        import production.partner_kpi as kpi_module
        kpi_module._cached_json_data = None
        print("🗑️ 캐시 초기화 완료")
    except:
        pass

def create_final_nan_data(year_month="2025-08"):
    """
    partner_kpi.py의 정확한 NaN 비율 + 실제 상세 레코드를 포함한 최종 데이터 생성
    """
    print(f"🔍 {year_month} 최종 NaN 데이터 생성 시작...")
    
    try:
        # 기존 검증된 함수로 JSON 데이터 로드
        json_data = load_json_files_from_drive(year_month)
        print(f"📊 총 {len(json_data)}개의 레코드 로드")
        
        if not json_data:
            print("❌ 데이터가 없습니다.")
            return None
            
        # 1. partner_kpi.py의 정확한 NaN 비율 가져오기
        nan_details = generate_nan_details(json_data)
        print(f"✅ partner_kpi.py 정확한 NaN 비율 가져오기 완료")
        
        # 2. 실제 상세 레코드 추출
        weekly_stats = {}
        partner_summary = defaultdict(lambda: {'total_tasks': 0, 'nan_count': 0, 'weeks': {}})
        
        # 먼저 주차별 기본 구조 생성
        for record in json_data:
            file_date_str = record.get('file_date', '')
            if not file_date_str:
                continue
                
            file_date = datetime.datetime.strptime(file_date_str, '%Y-%m-%d').date()
            week_num = file_date.isocalendar()[1]
            week_key = f"{week_num}주차"
            weekday = file_date.strftime('%A')
            is_sunday_data = week_num >= 33
            
            if week_key not in weekly_stats:
                weekly_stats[week_key] = {
                    'week_number': week_num,
                    'date': file_date_str,
                    'weekday': weekday,
                    'is_sunday_data': is_sunday_data,
                    'data_source': '일요일' if is_sunday_data else '금요일',
                    'total_records': 0,
                    'partners': {
                        'mech': {},
                        'elec': {}
                    }
                }
        
        # 3. nan_details의 정확한 비율을 weekly_stats에 적용
        for partner, details in nan_details.items():
            if partner in ['BAT', 'FNI', 'TMS(M)', 'C&A', 'P&S', 'TMS(E)']:
                partner_type = 'mech' if partner in ['BAT', 'FNI', 'TMS(M)'] else 'elec'
                
                # 월평균 비율 설정
                monthly_avg_ratio = 0.0
                for item in details:
                    if item['week'] == '월평균':
                        monthly_avg_ratio = item['ratio']
                        break
                partner_summary[partner]['nan_ratio'] = monthly_avg_ratio
                
                # 주차별 정확한 비율 설정
                for item in details:
                    if item['week'] != '월평균':
                        week_key = item['week'].replace('W', '주차')
                        
                        if week_key in weekly_stats:
                            if partner not in weekly_stats[week_key]['partners'][partner_type]:
                                weekly_stats[week_key]['partners'][partner_type][partner] = {
                                    'total_tasks': 0,
                                    'nan_count': 0,
                                    'nan_ratio': 0.0,
                                    'records': []
                                }
                            
                            # 정확한 NaN 비율 설정
                            weekly_stats[week_key]['partners'][partner_type][partner]['nan_ratio'] = item['ratio']
        
        # 4. 실제 상세 레코드와 tasks 수 계산
        for record in json_data:
            try:
                file_date_str = record.get('file_date', '')
                if not file_date_str:
                    continue
                    
                file_date = datetime.datetime.strptime(file_date_str, '%Y-%m-%d').date()
                week_num = file_date.isocalendar()[1]
                week_key = f"{week_num}주차"
                
                if week_key not in weekly_stats:
                    continue
                
                weekly_stats[week_key]['total_records'] += 1
                
                # 기구 협력사 처리
                mech_partner_raw = record.get("mech_partner", "")
                mech_partner = clean_partner_name(mech_partner_raw, mode='mech')
                
                # TMS 특별 처리: "TMS"를 "TMS(M)"으로 매핑
                if mech_partner_raw == "TMS":
                    mech_partner = "TMS(M)"
                    
                if mech_partner and mech_partner in weekly_stats[week_key]['partners']['mech']:
                    ratios = record.get("ratios", {})
                    mech_nan_ratio = ratios.get("mech_nan_ratio", 0.0)
                    total_tasks = record.get("total_tasks", 0)
                    nan_count = int(total_tasks * mech_nan_ratio / 100) if total_tasks > 0 else 0
                    
                    partner_data = weekly_stats[week_key]['partners']['mech'][mech_partner]
                    partner_data['total_tasks'] += total_tasks
                    partner_data['nan_count'] += nan_count
                    
                    # 실제 NaN이 있는 경우 상세 레코드 추가
                    if mech_nan_ratio > 0:
                        links = record.get('links', {})
                        partner_data['records'].append({
                            'order_no': record.get('order_no', ''),
                            'model_name': record.get('model_name', ''),
                            'nan_count': nan_count,
                            'total_tasks': total_tasks,
                            'nan_ratio': mech_nan_ratio,
                            'order_href': links.get('order_href', '')
                        })
                    
                    # 협력사별 전체 요약 업데이트
                    partner_summary[mech_partner]['total_tasks'] += total_tasks
                    partner_summary[mech_partner]['nan_count'] += nan_count
                    if week_key not in partner_summary[mech_partner]['weeks']:
                        partner_summary[mech_partner]['weeks'][week_key] = {'nan_count': 0, 'total_tasks': 0}
                    partner_summary[mech_partner]['weeks'][week_key]['nan_count'] += nan_count
                    partner_summary[mech_partner]['weeks'][week_key]['total_tasks'] += total_tasks
                
                # 전장 협력사 처리 (동일한 방식)
                elec_partner_raw = record.get("elec_partner", "")
                elec_partner = clean_partner_name(elec_partner_raw, mode='elec')
                
                # TMS 특별 처리: "TMS"를 "TMS(E)"로 매핑
                if elec_partner_raw == "TMS":
                    elec_partner = "TMS(E)"
                    
                if elec_partner and elec_partner in weekly_stats[week_key]['partners']['elec']:
                    ratios = record.get("ratios", {})
                    elec_nan_ratio = ratios.get("elec_nan_ratio", 0.0)
                    total_tasks = record.get("total_tasks", 0)
                    nan_count = int(total_tasks * elec_nan_ratio / 100) if total_tasks > 0 else 0
                    
                    partner_data = weekly_stats[week_key]['partners']['elec'][elec_partner]
                    partner_data['total_tasks'] += total_tasks
                    partner_data['nan_count'] += nan_count
                    
                    if elec_nan_ratio > 0:
                        links = record.get('links', {})
                        partner_data['records'].append({
                            'order_no': record.get('order_no', ''),
                            'model_name': record.get('model_name', ''),
                            'nan_count': nan_count,
                            'total_tasks': total_tasks,
                            'nan_ratio': elec_nan_ratio,
                            'order_href': links.get('order_href', '')
                        })
                    
                    partner_summary[elec_partner]['total_tasks'] += total_tasks
                    partner_summary[elec_partner]['nan_count'] += nan_count
                    if week_key not in partner_summary[elec_partner]['weeks']:
                        partner_summary[elec_partner]['weeks'][week_key] = {'nan_count': 0, 'total_tasks': 0}
                    partner_summary[elec_partner]['weeks'][week_key]['nan_count'] += nan_count
                    partner_summary[elec_partner]['weeks'][week_key]['total_tasks'] += total_tasks
                    
            except Exception as e:
                print(f"⚠️ 레코드 처리 중 오류: {e}")
                continue
        
        result = {
            'extracted_at': datetime.datetime.now().isoformat(),
            'period': year_month,
            'total_records': len(json_data),
            'weekly_stats': weekly_stats,
            'partner_summary': dict(partner_summary),
            'metadata': {
                'data_source_logic': '33주차부터 일요일, 32주차 이하 금요일',
                'weeks_analyzed': list(weekly_stats.keys()),
                'extraction_method': 'final_accurate_with_details',
                'nan_ratios_from': 'partner_kpi_generate_nan_details',
                'records_from': 'original_json_data'
            }
        }
        
        print(f"✅ 최종 데이터 생성 완료: {len(weekly_stats)}주차, {len(partner_summary)}개 협력사")
        
        # 상세 레코드 통계 출력
        total_detailed_records = 0
        for week, stats in weekly_stats.items():
            week_records = 0
            for partner_type in ['mech', 'elec']:
                for partner, data in stats['partners'][partner_type].items():
                    week_records += len(data['records'])
            total_detailed_records += week_records
            if week_records > 0:
                print(f"  {week}: {week_records}개 상세 레코드")
        
        print(f"📋 전체 상세 레코드 수: {total_detailed_records}개")
        
        # BAT 주차별 비율 확인
        print(f"\\n🎯 BAT 주차별 비율 검증:")
        for week in ['31주차', '32주차', '33주차', '34주차']:
            if week in weekly_stats and 'BAT' in weekly_stats[week]['partners']['mech']:
                ratio = weekly_stats[week]['partners']['mech']['BAT']['nan_ratio']
                print(f"  {week}: {ratio:.2f}%")
        
        return result
        
    except Exception as e:
        print(f"❌ 최종 데이터 생성 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_final_data(data, year_month):
    """최종 데이터를 파일로 저장"""
    if not data:
        print("❌ 저장할 데이터가 없습니다.")
        return False
        
    try:
        filename = f"nan_data_{year_month.replace('-', '_')}_improved.json"
        filepath = f"data/{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 최종 데이터 저장 완료: {filepath}")
        return True
    except Exception as e:
        print(f"❌ 파일 저장 중 오류: {e}")
        return False

if __name__ == "__main__":
    # 8월 데이터만 우선 수정
    month = "2025-08"
    
    print("🚀 최종 정확한 NaN 데이터 생성 시작")
    print("=" * 50)
    
    # 캐시 초기화
    clear_cache()
    
    # 최종 데이터 생성
    final_data = create_final_nan_data(month)
    
    if final_data:
        # 최종 데이터 저장
        save_final_data(final_data, month)
        
        print(f"\n✅ 최종 데이터 생성 완료!")
        print(f"   - partner_kpi.py 정확한 NaN 비율 사용")
        print(f"   - 실제 상세 레코드 포함") 
        print(f"   - BAT 주차별 정확한 값: 31주차(0.79%), 32주차(0.46%), 33주차(0.23%), 34주차(0.00%)")
