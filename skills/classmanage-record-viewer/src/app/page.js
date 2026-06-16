"use client";

import { useEffect, useState, useMemo, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import './globals.css';

export default function Home() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    // Filters
    const [studentFilter, setStudentFilter] = useState('');
    const [subjectFilter, setSubjectFilter] = useState('');
    const [dateFilter, setDateFilter] = useState('');
    const [emotionFilter, setEmotionFilter] = useState('');
    const [hideOtherStudents, setHideOtherStudents] = useState(true);

    useEffect(() => {
        async function fetchRecords() {
            setLoading(true);
            const { data: records, error } = await supabase
                .from('class-manage')
                .select('*')
                .order('날짜', { ascending: false });

            if (!error && records) {
                const processed = records.map(record => {
                    const subject = record['과목'];
                    const title = record['기록제목'] || '';
                    const content = record['내용'] || '';
                    const category = record['분야'] || '';
                    
                    const isAttendance = 
                        category.includes('출결') ||
                        title.includes('지각') || title.includes('조퇴') || title.includes('출석') || title.includes('결석') ||
                        content.includes('지각') || content.includes('조퇴') || content.includes('출석') || content.includes('결석');
                        
                    if (!subject && isAttendance) {
                        return { ...record, '과목': '출결' };
                    }
                    return record;
                });
                setData(processed);
            } else if (error) {
                console.error("Supabase fetch error:", error);
            }
            setLoading(false);
        }
        fetchRecords();
    }, []);

    const parseStudentNames = (rawName) => {
        if (!rawName) return [];
        let parsed = [];
        if (typeof rawName === 'string') {
            if (rawName.trim().startsWith('[') && rawName.trim().endsWith(']')) {
                try { parsed = JSON.parse(rawName); }
                catch (e) { parsed = rawName.replace(/[\[\]"']/g, '').split(/[,\s]+/); }
            } else {
                parsed = rawName.split(/[,\s]+/);
            }
        } else if (Array.isArray(rawName)) {
            parsed = rawName;
        }
        return parsed.map(s => s?.toString().trim()).filter(Boolean);
    };

    const filteredData = useMemo(() => {
        return data.filter(item => {
            const parsedNames = parseStudentNames(item['🧑‍🎓 이름']);
            const matchStudent = studentFilter === '' || parsedNames.includes(studentFilter);
            const matchSubject = subjectFilter === '' || (item['과목'] && item['과목'].includes(subjectFilter));
            const matchDate = dateFilter === '' || (item['날짜'] && item['날짜'].startsWith(dateFilter));
            const matchEmotion = emotionFilter === '' || (item['긍정도'] && item['긍정도'].includes(emotionFilter));
            return matchStudent && matchSubject && matchDate && matchEmotion;
        });
    }, [data, studentFilter, subjectFilter, dateFilter, emotionFilter]);

    // Denormalize: 1 student = 1 row
    const denormalizedData = useMemo(() => {
        const rows = [];
        filteredData.forEach(record => {
            const names = parseStudentNames(record['🧑‍🎓 이름']);
            const targetNames = (studentFilter && hideOtherStudents)
                ? names.filter(n => n === studentFilter)
                : names;
            targetNames.forEach(name => {
                rows.push({
                    학생이름: name,
                    기록제목: record['기록제목'] || '',
                    날짜: record['날짜'] || '',
                    과목: record['과목'] || '',
                    분야: record['분야'] || '',
                    긍정도: record['긍정도'] || '',
                    내용: record['내용'] || '',
                    출처: record['출처'] || '직접 기록',
                });
            });
        });
        return rows;
    }, [filteredData, studentFilter, hideOtherStudents]);

    // ── Export helpers ──
    const downloadFile = useCallback((content, filename, mimeType) => {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, []);

    const exportAsCSV = useCallback(() => {
        const headers = ['학생이름', '기록제목', '날짜', '과목', '분야', '긍정도', '내용', '출처'];
        const escapeCSV = (val) => {
            const str = String(val ?? '');
            if (str.includes(',') || str.includes('"') || str.includes('\n')) {
                return '"' + str.replace(/"/g, '""') + '"';
            }
            return str;
        };
        const csvLines = [headers.join(',')];
        denormalizedData.forEach(row => {
            csvLines.push(headers.map(h => escapeCSV(row[h])).join(','));
        });
        const BOM = '\uFEFF';
        const dateStr = new Date().toISOString().slice(0, 10);
        downloadFile(BOM + csvLines.join('\n'), `학생기록_${dateStr}.csv`, 'text/csv;charset=utf-8');
    }, [denormalizedData, downloadFile]);

    const exportAsJSON = useCallback(() => {
        const dateStr = new Date().toISOString().slice(0, 10);
        downloadFile(
            JSON.stringify(denormalizedData, null, 2),
            `학생기록_${dateStr}.json`,
            'application/json;charset=utf-8'
        );
    }, [denormalizedData, downloadFile]);

    const exportAsMarkdown = useCallback(() => {
        const grouped = {};
        denormalizedData.forEach(row => {
            if (!grouped[row.학생이름]) grouped[row.학생이름] = [];
            grouped[row.학생이름].push(row);
        });
        const cols = ['기록제목', '날짜', '과목', '분야', '긍정도', '내용', '출처'];
        let md = '# 학생별 수업 기록\n\n';
        Object.keys(grouped).sort().forEach(name => {
            md += `## ${name}\n\n`;
            md += '| ' + cols.join(' | ') + ' |\n';
            md += '| ' + cols.map(() => '---').join(' | ') + ' |\n';
            grouped[name].forEach(row => {
                const vals = cols.map(c => String(row[c] ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' '));
                md += '| ' + vals.join(' | ') + ' |\n';
            });
            md += '\n';
        });
        const dateStr = new Date().toISOString().slice(0, 10);
        downloadFile(md, `학생기록_${dateStr}.md`, 'text/markdown;charset=utf-8');
    }, [denormalizedData, downloadFile]);

    // Generators for dynamic dropdowns
    const uniqueSubjects = useMemo(() => [...new Set(data.map(d => d['과목']).filter(Boolean))], [data]);
    const uniqueEmotions = useMemo(() => [...new Set(data.map(d => d['긍정도']).filter(Boolean))], [data]);
    const uniqueStudents = useMemo(() => {
        const students = new Set();
        data.forEach(d => {
            parseStudentNames(d['🧑‍🎓 이름']).forEach(s => students.add(s));
        });
        return [...students].sort();
    }, [data]);

    // Handle rendering of badges correctly if the value was stringified JSON
    const renderStudentBadges = (rawName, currentFilter, hideOthers) => {
        let names = parseStudentNames(rawName);
        if (currentFilter && hideOthers) {
            names = names.filter(n => n.includes(currentFilter));
        }
        return names.map((name, idx) => (
            <span key={idx} className="badge badge-student">🧑‍🎓 {name}</span>
        ));
    };

    return (
        <div className="container">
            <div className="header">
                <h1>Class Record Viewer</h1>
                <div className="export-bar">
                    <span className="export-count">📊 {denormalizedData.length}건</span>
                    <button className="export-btn export-btn--csv" onClick={exportAsCSV}>📄 CSV</button>
                    <button className="export-btn export-btn--json" onClick={exportAsJSON}>🗂️ JSON</button>
                    <button className="export-btn export-btn--md" onClick={exportAsMarkdown}>📝 Markdown</button>
                </div>
            </div>

            <div className="filter-bar">
                <div className="filter-group">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <label style={{ margin: 0 }}>🧑‍🎓 학생 이름</label>
                        {studentFilter && (
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', cursor: 'pointer', color: 'var(--text-muted)', fontWeight: '500', margin: 0 }}>
                                <input
                                    type="checkbox"
                                    checked={hideOtherStudents}
                                    onChange={e => setHideOtherStudents(e.target.checked)}
                                    style={{ margin: 0, padding: 0, width: '12px', height: '12px' }}
                                />
                                가리기
                            </label>
                        )}
                    </div>
                    <select value={studentFilter} onChange={e => setStudentFilter(e.target.value)}>
                        <option value="">전체 보기</option>
                        {uniqueStudents.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                </div>

                <div className="filter-group">
                    <label>📚 과목</label>
                    <select value={subjectFilter} onChange={e => setSubjectFilter(e.target.value)}>
                        <option value="">전체 보기</option>
                        {uniqueSubjects.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                </div>

                <div className="filter-group">
                    <label>✨ 긍정도/태그</label>
                    <select value={emotionFilter} onChange={e => setEmotionFilter(e.target.value)}>
                        <option value="">전체 보기</option>
                        {uniqueEmotions.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                </div>

                <div className="filter-group">
                    <label>📅 날짜 (선택)</label>
                    <input type="date" value={dateFilter} onChange={e => setDateFilter(e.target.value)} />
                </div>
            </div>

            {loading ? (
                <div className="loading">⏳ 기록을 불러오는 중입니다...</div>
            ) : (
                <div className="records-grid">
                    {filteredData.length === 0 ? (
                        <div className="empty-state">검색 조건에 맞는 기록이 없습니다. 필터를 조정해보세요.</div>
                    ) : (
                        filteredData.map(record => (
                            <div key={record.id} className="record-card">
                                <div className="record-header">
                                    <h3 className="record-title">{record['기록제목'] || '무제 기록'}</h3>
                                    <span className="record-date">{record['날짜'] || '미상'}</span>
                                </div>

                                <div className="record-badges">
                                    {renderStudentBadges(record['🧑‍🎓 이름'], studentFilter, hideOtherStudents)}
                                    {record['과목'] && <span className="badge badge-subject">📚 {record['과목']}</span>}
                                    {record['분야'] && <span className="badge badge-category">🏷️ {record['분야']}</span>}
                                    {record['긍정도'] && <span className="badge badge-emotion">{record['긍정도']}</span>}
                                </div>

                                <div className="record-content">
                                    {record['내용'] || '(내용이 없습니다)'}
                                </div>

                                <div className="record-source">
                                    {record['출처'] ? `출처: ${record['출처']}` : '직접 기록'}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
