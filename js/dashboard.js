/**
 * NaN Dashboard JavaScript
 * GST Factory NaN 데이터 시각화 대시보드
 */

class NanDashboard {
    constructor() {
        this.data = null;
        this.charts = {};
        this.currentView = 'mech'; // 'mech' 또는 'elec'
        this.currentMonth = null; // 동적으로 설정될 기본 월
        this.monthlyData = {}; // 월별 데이터 캐시
        this.availableMonths = []; // 사용 가능한 월 목록
        
        this.init();
    }

    async init() {
        try {
            // 사용 가능한 월 자동 감지
            await this.detectAvailableMonths();
            
            // 동적 월 선택기 설정
            this.setupDynamicMonthSelector();
            
            // 데이터 로드
            await this.loadData();
            
            // UI 초기화
            this.initializeUI();
            
            // 차트 생성
            this.createCharts();
            
            // 테이블 생성
            this.createTables();
            
            // 상세 내역 생성
            this.createDetailAccordion();
            
            // 로딩 완료
            this.hideLoading();
            
        } catch (error) {
            console.error('대시보드 초기화 실패:', error);
            this.showError('데이터를 불러오는데 실패했습니다.');
        }
    }

    async detectAvailableMonths() {
        console.log("🔍 사용 가능한 월 자동 감지 중...");
        
        try {
            // 테스트할 월 범위 정의 (2025-01 ~ 2026-12)
            const testMonths = [];
            for (let year = 2025; year <= 2026; year++) {
                for (let month = 1; month <= 12; month++) {
                    const monthStr = `${year}-${month.toString().padStart(2, '0')}`;
                    testMonths.push(monthStr);
                }
            }
            
            const availableMonths = [];
            
            // 각 월의 improved.json 파일 존재 여부 확인
            for (const month of testMonths) {
                const filePath = `data/nan_data_${month.replace('-', '_')}_improved.json`;
                
                try {
                    const response = await fetch(filePath, { method: 'HEAD' });
                    if (response.ok) {
                        availableMonths.push(month);
                        console.log(`✅ ${month} 데이터 발견: ${filePath}`);
                    }
                } catch (error) {
                    // 파일이 없는 경우 무시
                }
            }
            
            if (availableMonths.length === 0) {
                console.warn("⚠️ 사용 가능한 월 데이터가 없습니다. 기본값 사용");
                this.availableMonths = ['2025-08'];
                this.currentMonth = '2025-08';
            } else {
                // 최신 월을 기본값으로 설정
                this.availableMonths = availableMonths.sort();
                this.currentMonth = this.availableMonths[this.availableMonths.length - 1];
                
                console.log(`📅 사용 가능한 월: ${this.availableMonths.join(', ')}`);
                console.log(`🎯 기본 선택 월: ${this.currentMonth}`);
            }
            
        } catch (error) {
            console.error('월 감지 실패:', error);
            // 폴백: 기본값 사용
            this.availableMonths = ['2025-06', '2025-07', '2025-08', '2025-09'];
            this.currentMonth = '2025-09';
        }
    }

    setupDynamicMonthSelector() {
        const monthSelector = document.getElementById('monthSelector');
        if (!monthSelector) {
            console.warn('월 선택기 요소를 찾을 수 없습니다.');
            return;
        }

        // 기존 옵션 제거 (all 옵션 제외)
        const options = monthSelector.querySelectorAll('option');
        options.forEach(option => {
            if (option.value !== 'all') {
                option.remove();
            }
        });

        // 동적으로 월 옵션 추가
        this.availableMonths.forEach(month => {
            const option = document.createElement('option');
            option.value = month;
            
            // 표시 형식: 2025-08 → 2025년 8월
            const [year, monthNum] = month.split('-');
            option.textContent = `${year}년 ${parseInt(monthNum)}월`;
            
            // 현재 선택된 월이면 selected 추가
            if (month === this.currentMonth) {
                option.selected = true;
            }
            
            monthSelector.appendChild(option);
        });

        console.log(`📅 월 선택기 업데이트 완료: ${this.availableMonths.length}개 월`);
    }

    async loadData(month = this.currentMonth) {
        try {
            // 동적 월별 데이터 파일 매핑 생성
            const monthFileMap = {};
            for (const availableMonth of this.availableMonths) {
                const fileName = `nan_data_${availableMonth.replace('-', '_')}_improved.json`;
                monthFileMap[availableMonth] = `data/${fileName}`;
            }
            
            console.log(`📂 동적 파일 매핑:`, monthFileMap);

            if (month === 'all') {
                // 전체 기간 데이터 처리
                await this.loadAllMonthsData();
            } else if (monthFileMap[month]) {
                // 개별 월 데이터 로드
                await this.loadSingleMonthData(month, monthFileMap[month]);
            } else {
                // 기본값으로 8월 데이터 사용 (HTML 임베디드)
                this.data = window.NAN_DATA;
                if (!this.data) {
                    throw new Error('기본 데이터가 정의되지 않았습니다.');
                }
            }
            
            console.log(`${month} 데이터 로드 완료:`, this.data);
        } catch (error) {
            console.error('데이터 로드 실패:', error);
            throw error;
        }
    }

    async loadSingleMonthData(month, filePath) {
        // 캐시 확인
        if (this.monthlyData[month]) {
            this.data = this.monthlyData[month];
            return;
        }

        // 개선된 데이터 파일 우선 시도
        const improvedFilePath = filePath.includes('_improved.json') ? filePath : filePath.replace('.json', '_improved.json');
        
        try {
            console.log(`${month} 개선된 데이터 파일 시도: ${improvedFilePath}`);
            const response = await fetch(improvedFilePath);
            if (response.ok) {
                const data = await response.json();
                console.log(`${month} 개선된 데이터 사용 (partner_kpi.py 로직 기반):`, {
                    total_records: data.total_records,
                    weekly_stats_keys: Object.keys(data.weekly_stats || {}),
                    partner_summary_keys: Object.keys(data.partner_summary || {}),
                    extraction_method: data.metadata?.extraction_method
                });
                this.monthlyData[month] = data;
                this.data = data;
                return;
            }
        } catch (error) {
            console.warn(`${month} 개선된 데이터 파일 로드 실패:`, error);
        }

        // 1순위: 임베디드 데이터 확인
        if (window.ALL_MONTHLY_DATA && window.ALL_MONTHLY_DATA[month]) {
            console.log(`${month} 임베디드 데이터 사용`);
            const data = window.ALL_MONTHLY_DATA[month];
            console.log(`${month} 데이터 구조:`, {
                total_records: data.total_records,
                weekly_stats_keys: Object.keys(data.weekly_stats || {}),
                partner_summary_keys: Object.keys(data.partner_summary || {})
            });
            this.monthlyData[month] = data;
            this.data = data;
            return;
        }

        // 2순위: 기존 파일에서 로드 시도
        try {
            const response = await fetch(filePath);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // 강화된 데이터 로드 로그
            console.log(`✅ ${month} 데이터 로드 성공:`, {
                period: data.period,
                weeks: Object.keys(data.weekly_stats || {}),
                extracted_at: data.extracted_at,
                total_records: data.total_records,
                bat_first_week: data.weekly_stats ? 
                    Object.values(data.weekly_stats)[0]?.partners?.mech?.BAT : 'BAT 데이터 없음',
                file_source: 'improved.json',
                file_path: filePath
            });
            
            // 추가 검증: 실제 주차 확인
            if (month === '2025-07') {
                const weeks = Object.keys(data.weekly_stats || {});
                if (weeks.includes('23주차') || weeks.includes('26주차')) {
                    console.error('⚠️ 잘못된 7월 데이터 로드됨! 23-26주차는 6월 데이터입니다.');
                    console.log('실제 로드된 주차:', weeks);
                } else if (weeks.includes('27주차') || weeks.includes('30주차')) {
                    console.log('✅ 올바른 7월 데이터 로드됨: 27-30주차');
                }
            }
            
            // 캐시에 저장
            this.monthlyData[month] = data;
            this.data = data;
        } catch (error) {
            console.warn(`${month} 파일 로드 실패, 기본 데이터 사용:`, error);
            // 3순위: 기본 데이터 사용
            this.data = window.NAN_DATA;
        }
    }

    async loadAllMonthsData() {
        try {
            // 임베디드 데이터 우선 사용
            if (window.ALL_MONTHLY_DATA) {
                console.log('임베디드 전체 데이터 사용');
                this.data = this.combineMonthlyData(window.ALL_MONTHLY_DATA);
                return;
            }
            
            // 임베디드 데이터가 없으면 파일에서 로드
            const months = this.availableMonths;
            const allData = {};
            
            console.log(`📊 전체 데이터 로드 대상: ${months.join(', ')}`);
            
            for (const month of months) {
                // _improved.json 파일 사용
                console.log(`🔄 ${month} 데이터 로딩 중...`);
                await this.loadSingleMonthData(month, `data/nan_data_${month.replace('-', '_')}_improved.json`);
                const monthData = this.monthlyData[month];
                
                if (monthData && monthData.weekly_stats) {
                    console.log(`✅ ${month} 로드 완료 - 주차:`, Object.keys(monthData.weekly_stats));
                    allData[month] = monthData;
                } else {
                    console.warn(`❌ ${month} 데이터가 올바르지 않습니다:`, monthData);
                }
            }
            
            // 전체 데이터 통합
            console.log('🔀 월별 데이터 통합 중:', Object.keys(allData));
            this.data = this.combineMonthlyData(allData);
            console.log('🎯 통합 완료 - 최종 주차:', Object.keys(this.data.weekly_stats));
        } catch (error) {
            console.warn('전체 데이터 로드 실패:', error);
            this.data = window.NAN_DATA;
        }
    }

    combineMonthlyData(allData) {
        // 여러 월 데이터를 하나로 통합
        const firstMonth = this.availableMonths[0];
        const lastMonth = this.availableMonths[this.availableMonths.length - 1];
        
        const combined = {
            extracted_at: new Date().toISOString(),
            period: `${firstMonth} ~ ${lastMonth}`,
            total_records: 0,
            weekly_stats: {},
            partner_summary: {},
            metadata: {
                data_source_logic: '32주차 포함 이전: 금요일, 33주차부터: 일요일',
                months_included: Object.keys(allData)
            }
        };

        const partnerTotals = {};

        // 각 월의 데이터 통합
        for (const [month, data] of Object.entries(allData)) {
            if (!data) continue;
            
            console.log(`🔄 ${month} 데이터 통합 중 - 주차:`, Object.keys(data.weekly_stats || {}));
            combined.total_records += data.total_records;
            
            // 주차별 통계 병합 (덮어쓰기 대신 누적)
            if (data.weekly_stats) {
                Object.assign(combined.weekly_stats, data.weekly_stats);
                console.log(`📊 ${month} 통합 후 주차:`, Object.keys(combined.weekly_stats));
            }
            
            // 협력사별 통계 병합
            for (const [partner, stats] of Object.entries(data.partner_summary)) {
                if (!partnerTotals[partner]) {
                    partnerTotals[partner] = {
                        total_tasks: 0,
                        nan_count: 0,
                        weeks: {}
                    };
                }
                
                partnerTotals[partner].total_tasks += stats.total_tasks;
                partnerTotals[partner].nan_count += stats.nan_count;
                Object.assign(partnerTotals[partner].weeks, stats.weeks);
            }
        }
        
        // 협력사별 비율 재계산
        for (const [partner, totals] of Object.entries(partnerTotals)) {
            totals.nan_ratio = totals.total_tasks > 0 ? (totals.nan_count / totals.total_tasks) * 100 : 0;
        }
        
        combined.partner_summary = partnerTotals;
        return combined;
    }

    initializeUI() {
        // 요약 정보 업데이트
        document.getElementById('lastUpdate').textContent = 
            `마지막 업데이트: ${new Date(this.data.extracted_at).toLocaleString('ko-KR')}`;
        
        document.getElementById('analysisPeriod').textContent = this.data.period;
        
        // 전체 NaN 발생률 계산
        const partners = Object.values(this.data.partner_summary);
        const totalTasks = partners.reduce((sum, p) => sum + p.total_tasks, 0);
        const totalNan = partners.reduce((sum, p) => sum + p.nan_count, 0);
        const overallRate = totalTasks > 0 ? (totalNan / totalTasks * 100) : 0;
        document.getElementById('overallNanRate').textContent = `${overallRate.toFixed(2)}%`;
        
        // 개선 필요 협력사 (NaN 비율 1% 이상)
        const highNanPartners = partners.filter(p => p.nan_ratio > 1.0).length;
        document.getElementById('highNanPartners').textContent = `${highNanPartners}개`;
        
        document.getElementById('totalPartners').textContent = `${Object.keys(this.data.partner_summary).length}개`;

        // 월 선택기 이벤트 등록
        document.getElementById('monthSelector').addEventListener('change', async (e) => {
            const selectedMonth = e.target.value;
            console.log('월 변경:', selectedMonth);
            
            if (selectedMonth !== this.currentMonth) {
                this.currentMonth = selectedMonth;
                
                // 전체 데이터 로딩 및 UI 업데이트
                await this.changeMonth(selectedMonth);
                
                console.log('월 변경 완료:', selectedMonth);
            }
        });

        // 버튼 이벤트 등록
        document.getElementById('showMechBtn').addEventListener('click', () => {
            this.currentView = 'mech';
            this.updateTableView();
        });

        document.getElementById('showElecBtn').addEventListener('click', () => {
            this.currentView = 'elec';
            this.updateTableView();
        });

        // 초기 버튼 상태
        document.getElementById('showMechBtn').classList.add('active');
    }

    async changeMonth(month) {
        try {
            // 로딩 표시
            this.showLoading();
            
            // 새 데이터 로드
            await this.loadData(month);
            
            // UI 업데이트
            this.updateSummaryCards();
            
            // 차트 재생성
            this.destroyCharts();
            this.createCharts();
            
            // 테이블 업데이트
            this.updateTableView();
            
            // 상세 내역 업데이트 (중요!)
            this.createDetailAccordion();
            
            // 로딩 완료
            this.hideLoading();
            
        } catch (error) {
            console.error('월 변경 중 오류:', error);
            this.showError(`${month} 데이터를 불러오는데 실패했습니다.`);
        }
    }

    updateSummaryCards() {
        document.getElementById('lastUpdate').textContent = 
            `마지막 업데이트: ${new Date(this.data.extracted_at).toLocaleString('ko-KR')}`;
        document.getElementById('analysisPeriod').textContent = this.data.period;
        
        // 전체 NaN 발생률 계산
        const partners = Object.values(this.data.partner_summary);
        const totalTasks = partners.reduce((sum, p) => sum + p.total_tasks, 0);
        const totalNan = partners.reduce((sum, p) => sum + p.nan_count, 0);
        const overallRate = totalTasks > 0 ? (totalNan / totalTasks * 100) : 0;
        document.getElementById('overallNanRate').textContent = `${overallRate.toFixed(2)}%`;
        
        // 개선 필요 협력사 (NaN 비율 1% 이상)
        const highNanPartners = partners.filter(p => p.nan_ratio > 1.0).length;
        document.getElementById('highNanPartners').textContent = `${highNanPartners}개`;
        
        document.getElementById('totalPartners').textContent = `${Object.keys(this.data.partner_summary).length}개`;
    }

    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        });
        this.charts = {};
    }

    showLoading() {
        document.getElementById('loadingSpinner').style.display = 'block';
        document.getElementById('dashboardContent').style.display = 'none';
    }

    createCharts() {
        this.createWeeklyTrendChart();
        this.createPartnerComparisonChart();
    }

    createWeeklyTrendChart() {
        const ctx = document.getElementById('weeklyTrendChart').getContext('2d');
        
        // 주차별 데이터 준비 (숫자 정렬)
        const weeks = Object.keys(this.data.weekly_stats).sort((a, b) => {
            const weekA = parseInt(a.replace('주차', ''));
            const weekB = parseInt(b.replace('주차', ''));
            return weekA - weekB;
        });
        const mechData = [];
        const elecData = [];
        const labels = [];

        console.log('🎯 차트용 주차 데이터:', weeks);
        
        weeks.forEach(week => {
            const stats = this.data.weekly_stats[week];
            if (!stats) {
                console.warn(`❌ 주차 ${week} 데이터가 없습니다`);
                return;
            }
            
            console.log(`✅ ${week} 차트 데이터 처리 중:`, stats.partners ? '파트너 있음' : '파트너 없음');
            labels.push(week);

            // 기구 협력사 평균 NaN 비율
            let mechTotal = 0, mechNan = 0;
            if (stats.partners && stats.partners.mech) {
                console.log(`  🔧 ${week} 기구 파트너:`, Object.keys(stats.partners.mech));
                Object.values(stats.partners.mech).forEach(partner => {
                    mechTotal += partner.total_tasks || 0;
                    mechNan += partner.nan_count || 0;
                });
            } else {
                console.log(`  ❌ ${week} 기구 파트너 없음`);
            }
            const mechRatio = mechTotal > 0 ? (mechNan / mechTotal * 100) : 0;
            mechData.push(mechRatio);
            console.log(`  🔧 ${week} 기구 비율: ${mechRatio.toFixed(2)}% (${mechNan}/${mechTotal})`);

            // 전장 협력사 평균 NaN 비율
            let elecTotal = 0, elecNan = 0;
            if (stats.partners && stats.partners.elec) {
                console.log(`  ⚡ ${week} 전장 파트너:`, Object.keys(stats.partners.elec));
                Object.values(stats.partners.elec).forEach(partner => {
                    elecTotal += partner.total_tasks || 0;
                    elecNan += partner.nan_count || 0;
                });
            } else {
                console.log(`  ❌ ${week} 전장 파트너 없음`);
            }
            const elecRatio = elecTotal > 0 ? (elecNan / elecTotal * 100) : 0;
            elecData.push(elecRatio);
            console.log(`  ⚡ ${week} 전장 비율: ${elecRatio.toFixed(2)}% (${elecNan}/${elecTotal})`);
        });

        this.charts.weeklyTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '🔧 기구 협력사',
                        data: mechData,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: '⚡ 전장 협력사',
                        data: elecData,
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '주차별 평균 NaN 비율 추이 (%)',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: Math.max(...mechData, ...elecData) * 1.2 || 10,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 6,
                        hoverRadius: 8
                    }
                }
            }
        });
    }

    createPartnerComparisonChart() {
        const ctx = document.getElementById('partnerComparisonChart').getContext('2d');
        
        // 협력사별 전체 NaN 비율
        const partners = Object.keys(this.data.partner_summary);
        const nanRatios = partners.map(partner => {
            const summary = this.data.partner_summary[partner];
            return summary.total_tasks > 0 ? summary.nan_ratio : 0;
        });

        const colors = partners.map((_, index) => {
            const hue = (index * 137.508) % 360; // 황금각을 이용한 색상 분배
            return `hsla(${hue}, 70%, 60%, 0.8)`;
        });

        this.charts.partnerComparison = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: partners,
                datasets: [{
                    data: nanRatios,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('0.8', '1')),
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '협력사별 NaN 비율 비교',
                        font: { size: 14, weight: 'bold' }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            generateLabels: (chart) => {
                                const data = chart.data;
                                return data.labels.map((label, index) => {
                                    const value = data.datasets[0].data[index];
                                    return {
                                        text: `${label}: ${value.toFixed(1)}%`,
                                        fillStyle: data.datasets[0].backgroundColor[index],
                                        strokeStyle: data.datasets[0].borderColor[index],
                                        lineWidth: 2,
                                        index: index
                                    };
                                });
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const partner = context.label;
                                const ratio = context.parsed;
                                const summary = this.data.partner_summary[partner];
                                return [
                                    `${partner}: ${ratio.toFixed(2)}%`,
                                    `NaN: ${summary.nan_count}건`,
                                    `전체: ${summary.total_tasks}건`
                                ];
                            }.bind(this)
                        }
                    }
                }
            }
        });
    }

    createTables() {
        this.updateTableView();
    }

    updateTableView() {
        // 버튼 상태 업데이트
        document.getElementById('showMechBtn').classList.toggle('active', this.currentView === 'mech');
        document.getElementById('showElecBtn').classList.toggle('active', this.currentView === 'elec');

        const weeks = Object.keys(this.data.weekly_stats).sort((a, b) => {
            // 주차 번호 추출하여 숫자로 정렬
            const weekA = parseInt(a.replace('주차', ''));
            const weekB = parseInt(b.replace('주차', ''));
            return weekA - weekB;
        });
        
        console.log('정렬된 주차:', weeks);
        const partners = new Set();

        // 협력사 목록 수집
        weeks.forEach(week => {
            const stats = this.data.weekly_stats[week];
            if (stats && stats.partners && stats.partners[this.currentView]) {
                Object.keys(stats.partners[this.currentView]).forEach(partner => {
                    partners.add(partner);
                });
            }
        });

        const partnerList = Array.from(partners).sort();

        // 테이블 헤더 생성
        const header = document.getElementById('tableHeader');
        header.innerHTML = `
            <th>협력사</th>
            ${weeks.map(week => `<th>${week}<br><small class="text-muted">${this.data.weekly_stats[week].date}</small></th>`).join('')}
            <th>전체 평균</th>
        `;

        // 테이블 바디 생성
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = partnerList.map(partner => {
            const cells = weeks.map(week => {
                const stats = this.data.weekly_stats[week];
                const partnerData = stats?.partners?.[this.currentView]?.[partner];
                console.log(`${partner} ${week} 데이터:`, partnerData); // 디버그 로그
                
                if (partnerData) {
                    const ratio = partnerData.nan_ratio || 0;
                    const total_tasks = partnerData.total_tasks || 0;
                    const nan_count = partnerData.nan_count || 0;
                    const colorClass = ratio > 5 ? 'text-danger' : ratio > 2 ? 'text-warning' : 'text-success';
                    
                    return `<td class="${colorClass}">
                        <strong>${ratio.toFixed(1)}%</strong><br>
                        <small>${nan_count}/${total_tasks}</small>
                    </td>`;
                } else {
                    return '<td class="text-muted">-</td>';
                }
            }).join('');

            const overallRatio = this.data.partner_summary[partner]?.nan_ratio || 0;
            const overallColorClass = overallRatio > 5 ? 'text-danger' : overallRatio > 2 ? 'text-warning' : 'text-success';

            return `
                <tr>
                    <td><strong>${partner}</strong></td>
                    ${cells}
                    <td class="${overallColorClass}">
                        <strong>${overallRatio.toFixed(1)}%</strong><br>
                        <small>${this.data.partner_summary[partner]?.nan_count || 0}/${this.data.partner_summary[partner]?.total_tasks || 0}</small>
                    </td>
                </tr>
            `;
        }).join('');
    }

    createDetailAccordion() {
        const accordion = document.getElementById('nanDetailsAccordion');
        
        // 전체기간 선택 시 상세내역 숨기기 (개체수가 너무 많음)
        if (this.currentMonth === 'all') {
            accordion.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i>
                    <strong>전체기간 모드</strong><br>
                    주차별 상세내역은 개별 월 선택 시에만 표시됩니다.
                </div>
            `;
            return;
        }
        const weeks = Object.keys(this.data.weekly_stats).sort((a, b) => {
            const weekA = parseInt(a.replace('주차', ''));
            const weekB = parseInt(b.replace('주차', ''));
            return weekA - weekB;
        });

        accordion.innerHTML = weeks.map((week, index) => {
            const stats = this.data.weekly_stats[week];
            const weekData = [];

            // 기구 및 전장 협력사의 NaN 상세 내역 수집
            ['mech', 'elec'].forEach(type => {
                if (stats.partners && stats.partners[type]) {
                    Object.entries(stats.partners[type]).forEach(([partner, data]) => {
                    if (data.records && data.records.length > 0) {
                        weekData.push({
                            partner: partner,
                            type: type === 'mech' ? '🔧' : '⚡',
                            records: data.records
                        });
                    }
                    });
                }
            });

            if (weekData.length === 0) {
                return `
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${index}">
                                <span class="status-dot good"></span>
                                ${week} (${stats.date}) - NaN 없음 ✅
                            </button>
                        </h2>
                    </div>
                `;
            }

            return `
                <div class="accordion-item">
                    <h2 class="accordion-header">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${index}">
                            <span class="status-dot ${weekData.length > 5 ? 'danger' : 'warning'}"></span>
                            ${week} (${stats.date}) - ${weekData.reduce((sum, item) => sum + item.records.length, 0)}건의 NaN 발생
                            <small class="ms-2 text-muted">${stats.is_sunday_data ? '일요일' : '금요일'} 데이터</small>
                        </button>
                    </h2>
                    <div id="collapse${index}" class="accordion-collapse collapse" data-bs-parent="#nanDetailsAccordion">
                        <div class="accordion-body">
                            ${weekData.map(item => `
                                <h6>${item.type} ${item.partner}</h6>
                                <div class="table-responsive mb-3">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Title Number</th>
                                                <th>모델명</th>
                                                <th>NaN 건수</th>
                                                <th>전체 작업</th>
                                                <th>NaN 비율</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${item.records.map(record => `
                                                <tr>
                                                    <td>
                                                        ${record.order_href ? 
                                                            `<a href="${record.order_href}" target="_blank" class="text-decoration-none">
                                                                <code class="text-primary">${record.order_no}</code>
                                                                <i class="fas fa-external-link-alt ms-1 text-muted" style="font-size: 0.7em;"></i>
                                                            </a>` : 
                                                            `<code>${record.order_no}</code>`
                                                        }
                                                    </td>
                                                    <td>${record.model_name}</td>
                                                    <td class="text-danger"><strong>${record.nan_count}</strong></td>
                                                    <td>${record.total_tasks}</td>
                                                    <td>
                                                        <span class="badge ${record.nan_ratio > 20 ? 'bg-danger' : record.nan_ratio > 10 ? 'bg-warning' : 'bg-info'}">
                                                            ${record.nan_ratio.toFixed(1)}%
                                                        </span>
                                                    </td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    hideLoading() {
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('dashboardContent').style.display = 'block';
        document.getElementById('dashboardContent').classList.add('fade-in');
    }

    async changeMonth(selectedMonth) {
        console.log('월 변경 중:', selectedMonth);
        
        try {
            // 새로운 데이터 로드
            await this.loadData(selectedMonth);
            
            // 모든 UI 구성요소 업데이트
            this.updateSummaryCards();
            
            // 기존 차트 제거
            if (this.charts.weeklyTrend) this.charts.weeklyTrend.destroy();
            if (this.charts.partnerComparison) this.charts.partnerComparison.destroy();
            
            // 새 차트 생성
            this.createWeeklyTrendChart();
            this.createPartnerComparisonChart();
            this.updateTableView();
            
            // 상세 내역 업데이트 (중요!)
            this.createDetailAccordion();
            
            // 월 선택기 값 동기화
            document.getElementById('monthSelector').value = selectedMonth;
            
            console.log('월 변경 완료:', selectedMonth, '데이터 레코드:', this.data.total_records);
        } catch (error) {
            console.error('월 변경 중 오류:', error);
            this.showError(`월 데이터 로딩 실패: ${error.message}`);
        }
    }

    updateSummaryCards() {
        document.getElementById('analysisPeriod').textContent = this.data.period;
        
        // 전체 NaN 발생률 계산
        const partners = Object.values(this.data.partner_summary);
        const totalTasks = partners.reduce((sum, p) => sum + p.total_tasks, 0);
        const totalNan = partners.reduce((sum, p) => sum + p.nan_count, 0);
        const overallRate = totalTasks > 0 ? (totalNan / totalTasks * 100) : 0;
        document.getElementById('overallNanRate').textContent = `${overallRate.toFixed(2)}%`;
        
        // 개선 필요 협력사 (NaN 비율 1% 이상)
        const highNanPartners = partners.filter(p => p.nan_ratio > 1.0).length;
        document.getElementById('highNanPartners').textContent = `${highNanPartners}개`;
        
        document.getElementById('totalPartners').textContent = `${Object.keys(this.data.partner_summary).length}개`;
        
        document.getElementById('lastUpdate').textContent = 
            `마지막 업데이트: ${new Date(this.data.extracted_at).toLocaleString('ko-KR')}`;
    }

    showError(message) {
        document.getElementById('loadingSpinner').innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>오류:</strong> ${message}
            </div>
        `;
    }
}

// 대시보드 초기화
document.addEventListener('DOMContentLoaded', function() {
    new NanDashboard();
});
