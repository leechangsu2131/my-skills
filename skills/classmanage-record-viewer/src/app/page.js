"use client";

import { useEffect, useState, useMemo } from 'react';
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
                setData(records);
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
