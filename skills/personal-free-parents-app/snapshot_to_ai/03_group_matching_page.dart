import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gap/gap.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/router/app_router.dart';
import '../../../core/theme/app_colors.dart';

/// 그룹 매칭/검색 페이지 — 필터 + 지도 우선 배치 + 놀이터 가로 카드 스크롤
class GroupMatchingPage extends ConsumerStatefulWidget {
  final bool showAppBar;
  const GroupMatchingPage({super.key, this.showAppBar = true});

  @override
  ConsumerState<GroupMatchingPage> createState() => _GroupMatchingPageState();
}

class _GroupMatchingPageState extends ConsumerState<GroupMatchingPage> {
  String _timeFilter = '전체';
  String _locationFilter = '전체';
  NaverMapController? _mapController;

  // 실데이터 및 플레이스홀더 결합 (경주 센텀스카이 기준)
  final _affiliations = [
    _AffiliationMock('천년가 센텀스카이 아파트', 'apartment', 35.804879, 129.138367),
    _AffiliationMock('해링턴플레이스 신경주역 아파트', 'apartment', 35.804540, 129.135862),
    _AffiliationMock('신경주 더퍼스트 데시앙 아파트', 'apartment', 35.801884, 129.138390),
    _AffiliationMock('방주 어린이집', 'daycare', 35.842347, 129.111713),
    _AffiliationMock('라라 어린이집', 'daycare', 35.852225, 129.105981),
    _AffiliationMock('미래 어린이집', 'daycare', 35.854261, 129.098250),
  ];

  final _playgrounds = [
    _PlaygroundMock('p1', '센텀스카이 중앙 놀이터', 35.804879, 129.138367, 'active', 3, 6, ['김*준', '이*연', '박*호'], [const Color(0xFF5E7A5C), const Color(0xFFB5654A), const Color(0xFFC9A66B)]),
    _PlaygroundMock('p2', '해링턴플레이스 어린이 놀이터', 35.804540, 129.135862, 'pending', 2, 4, ['최*아', '정*훈'], [const Color(0xFFB5654A)]),
    _PlaygroundMock('p3', '더퍼스트 데시앙 숲속 놀이터', 35.801884, 129.138390, 'full', 6, 6, ['강*우', '임*민', '한*수', '윤*서', '오*준', '신*혜'], []),
    _PlaygroundMock('p4', '건천초 앞 어린이 공원 놀이터', 35.803500, 129.137000, 'empty', 0, 0, [], []),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: widget.showAppBar
          ? AppBar(
              backgroundColor: AppColors.backgroundLight,
              elevation: 0,
              centerTitle: true,
              leading: IconButton(
                icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppColors.textPrimary),
                onPressed: () => context.pop(),
              ),
              title: Text(
                '내 주변 돌봄 찾기',
                style: GoogleFonts.notoSansKr(
                  fontWeight: FontWeight.w900,
                  color: AppColors.textPrimary,
                  fontSize: 18,
                  letterSpacing: -0.5,
                ),
              ),
            )
          : null,
      body: Column(
        children: [
          // 0. 헤더 툴바 (돋보기, 로고, 프로필)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            decoration: BoxDecoration(
              color: AppColors.backgroundLight.withOpacity(0.92),
              border: const Border(
                bottom: BorderSide(color: AppColors.warmGray, width: 1.0),
              ),
            ),
            child: SafeArea(
              bottom: false,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Icon(Icons.search_rounded, color: AppColors.bark, size: 22),
                  Text(
                    '한명만',
                    style: GoogleFonts.notoSansKr(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: AppColors.forest,
                      letterSpacing: -1.0,
                    ),
                  ),
                  const Icon(Icons.person_outline_rounded, color: AppColors.bark, size: 22),
                ],
              ),
            ),
          ),

          // 1. 일러스트 맵과 필터 칩 영역
          Expanded(
            child: Stack(
              children: [
                // 1-1. 일러스트 맵 뷰포트
                Positioned.fill(
                  child: NaverMap(
                    options: const NaverMapViewOptions(
                      mapType: NMapType.basic,
                      initialCameraPosition: NCameraPosition(
                        target: NLatLng(35.804879, 129.138367),
                        zoom: 14.5,
                      ),
                      locationButtonEnable: true,
                      scaleBarEnable: false,
                      indoorEnable: false,
                    ),
                    onMapReady: (controller) {
                      _mapController = controller;
                      _showAllMarkers();
                    },
                  ),
                ),

                // 1-1-b. 지도 소속 색상 범례 (Legend Panel - HTML 규격 이식)
                Positioned(
                  top: 14,
                  left: 16,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFFDF3).withOpacity(0.94),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.warmGray.withOpacity(0.5), width: 1),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.12),
                          blurRadius: 8,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '소속 색상',
                          style: GoogleFonts.notoSansKr(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w900,
                            color: AppColors.ink,
                          ),
                        ),
                        const Gap(6),
                        _buildLegendRow(const Color(0xFF5E7A5C), '라라어린이집 (내 소속)'),
                        const Gap(4),
                        _buildLegendRow(const Color(0xFFB5654A), '해링턴 아파트'),
                        const Gap(4),
                        _buildLegendRow(const Color(0xFFC9A66B), '천년가 아파트'),
                      ],
                    ),
                  ),
                ),

                // 1-2. 상단 우측 놀이터 개수 플로팅 배지 (JSX: 🛝 3곳)
                Positioned(
                  top: 14,
                  right: 16,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF192B1B).withOpacity(0.82),
                      borderRadius: BorderRadius.circular(99),
                    ),
                    child: Text(
                      '🛝 3곳',
                      style: GoogleFonts.notoSansKr(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: AppColors.mist,
                      ),
                    ),
                  ),
                ),

                // 1-3. 범례 표시 오버레이 (JSX 스크린샷 2번의 범례)
                Positioned(
                  left: 14,
                  bottom: 14,
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.white.withOpacity(0.88),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.warmGray, width: 1.0),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildLegendItem(AppColors.amber, '진행중'),
                        const Gap(4),
                        _buildLegendItem(AppColors.canopy, '모집중'),
                        const Gap(4),
                        _buildLegendItem(AppColors.smoke, '빈 곳'),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // 2. 하단 드로어 영역 (근처 놀이터 슬라이더)
          Container(
            decoration: const BoxDecoration(
              color: AppColors.white,
              border: Border(
                top: BorderSide(color: AppColors.warmGray, width: 1.0),
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // 핸들 바
                Container(
                  margin: const EdgeInsets.only(top: 10, bottom: 8),
                  child: Column(
                    children: [
                      Container(
                        width: 36,
                        height: 3,
                        decoration: BoxDecoration(
                          color: AppColors.warmGray,
                          borderRadius: BorderRadius.circular(99),
                        ),
                      ),
                      const Gap(8),
                      Text(
                        '근처 놀이터 ▲',
                        style: GoogleFonts.notoSansKr(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: AppColors.bark,
                        ),
                      ),
                    ],
                  ),
                ),
                // 가로 스크롤 카드 리스트
                SizedBox(
                  height: 124,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.only(left: 20, right: 20, bottom: 14),
                    itemCount: _playgrounds.length,
                    separatorBuilder: (_, __) => const Gap(12),
                    itemBuilder: (context, index) {
                      final pg = _playgrounds[index];
                      return _buildPlaygroundCard(pg);
                    },
                  ),
                ),
                const Gap(80), // 하단 플로팅 탭바 높이 확보를 위한 넉넉한 하단 패딩
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(Color color, String text) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const Gap(6),
        Text(
          text,
          style: GoogleFonts.notoSansKr(
            fontSize: 9,
            fontWeight: FontWeight.w700,
            color: AppColors.bark,
          ),
        ),
      ],
    );
  }

  Widget _buildFilterChip({
    required String label,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    final isActive = !label.endsWith('전체');
    return Material(
      color: isActive ? AppColors.primary : AppColors.white,
      borderRadius: BorderRadius.circular(20),
      elevation: 2,
      shadowColor: AppColors.primary.withValues(alpha: 0.08),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: isActive ? AppColors.primary : AppColors.warmGray,
              width: 1.5,
            ),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 16,
                color: isActive ? AppColors.white : AppColors.primary,
              ),
              const Gap(6),
              Text(
                label,
                style: GoogleFonts.notoSansKr(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: isActive ? AppColors.white : AppColors.textPrimary,
                  letterSpacing: -0.3,
                ),
              ),
              const Gap(4),
              Icon(
                Icons.keyboard_arrow_down_rounded,
                size: 16,
                color: isActive ? AppColors.white : AppColors.textSecondary,
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 지도에 소속 기관 및 놀이터 마커 띄우기
  void _showAllMarkers() async {
    if (_mapController == null) return;
    
    // 네이티브 채널 바인딩 안정성을 위해 미세 딜레이 부여
    await Future.delayed(const Duration(milliseconds: 300));
    if (!mounted) return;

    try {
      _mapController!.clearOverlays();
    } catch (e) {
      debugPrint('[WARNING] NaverMap clearOverlays failed: $e');
    }

    // 1. 소속 기관 마커 (어린이집 🏫 / 아파트 🏢)
    for (final aff in _affiliations) {
      try {
        final isDaycare = aff.type == 'daycare';
        final marker = NMarker(
          id: aff.name,
          position: NLatLng(aff.latitude, aff.longitude),
          icon: isDaycare
              ? const NOverlayImage.fromAssetImage('assets/daycare_marker.png')
              : const NOverlayImage.fromAssetImage('assets/apartment_marker.png'),
        );
        marker.setSize(const Size(38, 38));

        // 6번 규칙: 소속 마커 라벨 축약 및 위계/스타일 통일 (11px, 400 Regular, bark색)
        String shortName = '';
        double minZoom = 16.0; // 기본은 고배율 줌(확대 줌)에서만 노출
        
        if (aff.name.contains('센텀스카이')) {
          shortName = '센텀스카이';
          minZoom = 15.0; // 중간 줌부터 우선 노출!
        } else if (aff.name.contains('해링턴플레이스')) {
          shortName = '해링턴플레이스';
          minZoom = 15.0; // 중간 줌부터 우선 노출!
        } else if (aff.name.contains('데시앙')) {
          shortName = '경주데시앙';
        } else if (aff.name.contains('방주')) {
          shortName = '방주어린이집';
        } else if (aff.name.contains('라라')) {
          shortName = '라라어린이집';
        } else if (aff.name.contains('미래')) {
          shortName = '미래어린이집';
        } else {
          shortName = aff.name.length > 8 ? aff.name.substring(0, 8) : aff.name;
        }

        marker.setCaption(
          NOverlayCaption(
            text: '${isDaycare ? '🏫' : '🏢'} $shortName',
            textSize: 11,
            color: AppColors.bark,
            haloColor: Colors.white.withOpacity(0.92), // 6번 규칙: 가독성 보장용 흰색 피임 후광
            minZoom: minZoom, // 6번 규칙: 줌 레벨별 순차 노출 제어
          ),
        );

        _mapController!.addOverlay(marker);
      } catch (e) {
        debugPrint('[WARNING] Failed to add affiliation marker: $e');
      }
    }

    // 2. 놀이터 마커 (상태별 디자인)
    for (final pg in _playgrounds) {
      try {
        // 0번, 6번 규칙: 놀이터 마커 라벨을 모집이 아닌 담백한 '확인' 상태 텍스트로 치환
        String shortName = '';
        if (pg.status == 'active') {
          shortName = '지금 놀고 있어요';
        } else if (pg.status == 'pending') {
          shortName = '${pg.memberCount}명 있어요';
        } else {
          shortName = '아직 없어요';
        }

        // 6, 7번 규칙: 위젯 기반의 고해상도 커스텀 핀 굽기 (NOverlayImage.fromWidget)
        // 내 소속인 '라라 어린이집'의 컬러: Color(0xFF5E7A5C)
        final markerIcon = await NOverlayImage.fromWidget(
          widget: PlaygroundMarkerWidget(
            status: pg.status,
            shortName: shortName,
            affiliationColors: pg.affiliationColors,
            myAffiliationColor: const Color(0xFF5E7A5C), // 내 소속 강조 대상 색상
          ),
          size: const Size(120, 85),
          context: context,
        );

        final marker = NMarker(
          id: pg.id,
          position: NLatLng(pg.latitude, pg.longitude),
          icon: markerIcon,
        );
        
        // 앵커 포인트를 핀의 정중앙에 매칭
        marker.setAnchor(const NPoint(0.5, 0.35));

        marker.setOnTapListener((_) {
          // 놀이터 마커 탭 시
          _mapController?.updateCamera(
            NCameraUpdate.withParams(
              target: NLatLng(pg.latitude, pg.longitude),
              zoom: 16.0,
            ),
          );
          _showPlaygroundDetailSheet(pg);
        });

        _mapController!.addOverlay(marker);
      } catch (e) {
        debugPrint('[WARNING] Failed to add playground marker: $e');
      }
    }
  }

  /// 하단 가로 스크롤 카드 (radius 16, AppColors.white배경)
  Widget _buildPlaygroundCard(_PlaygroundMock pg) {
    Color statusColor;
    String statusText;
    switch (pg.status) {
      case 'active':
        statusColor = AppColors.amber;
        statusText = '지금 놀고 있어요';
        break;
      case 'pending':
        statusColor = AppColors.canopy;
        statusText = '지금 ${pg.memberCount}명 있어요';
        break;
      case 'full':
        statusColor = AppColors.error;
        statusText = '마감됨';
        break;
      default:
        statusColor = AppColors.smoke;
        statusText = '아직 아무도 없어요';
    }

    final isActive = pg.status == 'active';

    return GestureDetector(
      onTap: () {
        _showPlaygroundDetailSheet(pg);
      },
      child: Container(
        width: 250,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isActive ? AppColors.amber : AppColors.warmGray,
            width: isActive ? 1.8 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        pg.name,
                        style: GoogleFonts.notoSansKr(
                          fontSize: 14,
                          fontWeight: FontWeight.w900,
                          color: AppColors.ink,
                          letterSpacing: -0.3,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const Gap(6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        statusText,
                        style: GoogleFonts.notoSansKr(
                          fontSize: 9,
                          fontWeight: FontWeight.w900,
                          color: statusColor,
                        ),
                      ),
                    ),
                  ],
                ),
                const Gap(6),
                Row(
                  children: [
                    const Icon(Icons.location_on_rounded, size: 13, color: AppColors.forest),
                    const Gap(4),
                    Text(
                      '천년가 센텀스카이 인근',
                      style: GoogleFonts.notoSansKr(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: AppColors.bark,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                pg.status == 'empty'
                    ? Text(
                        '아직 아무도 없어요',
                        style: GoogleFonts.notoSansKr(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: AppColors.smoke,
                        ),
                      )
                    : Row(
                        children: [
                          // 미니 아바타 스택 표시
                          SizedBox(
                            width: 32 + (pg.members.take(3).length * 10.0),
                            height: 20,
                            child: Stack(
                              children: [
                                for (int i = 0; i < pg.members.take(3).length; i++)
                                  Positioned(
                                    left: i * 10.0,
                                    child: Container(
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        border: Border.all(color: AppColors.white, width: 1.5),
                                      ),
                                      child: CircleAvatar(
                                        radius: 8,
                                        backgroundColor: AppColors.amberPale,
                                        child: Text(
                                          pg.members[i].isNotEmpty ? pg.members[i][0] : '부',
                                          style: const TextStyle(fontSize: 6, fontWeight: FontWeight.bold, color: AppColors.amber),
                                        ),
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                          Text(
                            '지금 ${pg.memberCount}명 있어요',
                            style: GoogleFonts.notoSansKr(
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                              color: AppColors.ink,
                            ),
                          ),
                        ],
                      ),
                Container(
                  width: 26,
                  height: 26,
                  decoration: const BoxDecoration(
                    color: AppColors.parchment,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.arrow_forward_ios_rounded,
                    size: 11,
                    color: AppColors.amber,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// 놀이터 마커/카드 탭 시 상세 바텀시트 UI (JSX: PlaygroundSheet 명세 복원)
  void _showPlaygroundDetailSheet(_PlaygroundMock pg) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final isEmpty = pg.status == 'empty';
        final isActive = pg.status == 'active';
        
        return Container(
          height: MediaQuery.of(context).size.height * 0.88,
          decoration: const BoxDecoration(
            color: AppColors.backgroundLight,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          clipBehavior: Clip.antiAlias,
          child: Column(
            children: [
              // 1. 상단 25% 미니 일러스트 맵 영역 (Static)
              SizedBox(
                height: MediaQuery.of(context).size.height * 0.25,
                child: Stack(
                  children: [
                    Positioned.fill(
                      child: NaverMap(
                        options: NaverMapViewOptions(
                          initialCameraPosition: NCameraPosition(
                            target: NLatLng(pg.latitude, pg.longitude),
                            zoom: 15.5,
                          ),
                        ),
                        onMapReady: (controller) {
                          final marker = NMarker(
                            id: 'mini_${pg.id}',
                            position: NLatLng(pg.latitude, pg.longitude),
                            icon: const NOverlayImage.fromAssetImage('assets/playground_marker.png'),
                          );
                          marker.setSize(const Size(44, 44));
                          Color markerColor = pg.status == 'active'
                              ? AppColors.amber
                              : pg.status == 'pending'
                                  ? AppColors.canopy
                                  : AppColors.smoke;
                          marker.setIconTintColor(markerColor);
                          controller.addOverlay(marker);
                        },
                      ),
                    ),
                    Positioned.fill(
                      child: Container(color: Colors.black.withOpacity(0.12)),
                    ),
                    // '← 지도' 뒤로가기 버튼
                    Positioned(
                      top: 16,
                      left: 16,
                      child: GestureDetector(
                        onTap: () => Navigator.pop(ctx),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFFFDF3).withOpacity(0.9),
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.1),
                                blurRadius: 8,
                              ),
                            ],
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.arrow_back_ios_new_rounded, size: 12, color: Color(0xFF192B1B)),
                              const Gap(6),
                              Text(
                                '← 지도',
                                style: GoogleFonts.notoSansKr(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w900,
                                  color: const Color(0xFF192B1B),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    // 🚨 우하단 플로팅 긴급 버튼 (오리지널)
                    Positioned(
                      bottom: 12,
                      right: 12,
                      child: Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: AppColors.error,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.error.withOpacity(0.4),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: IconButton(
                          icon: const Text('🚨', style: TextStyle(fontSize: 18)),
                          onPressed: () => _showEmergencyDialog(context),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // 2. 바텀 시트 내용 영역 (둥글게 겹쳐진 모서리, radius 22)
              Expanded(
                child: Container(
                  transform: Matrix4.translationValues(0, -18, 0),
                  decoration: const BoxDecoration(
                    color: AppColors.white,
                    borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
                  ),
                  child: SingleChildScrollView(
                    physics: const ClampingScrollPhysics(),
                    padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Center(
                          child: Container(
                            width: 36,
                            height: 3,
                            decoration: BoxDecoration(
                              color: AppColors.warmGray,
                              borderRadius: BorderRadius.circular(99),
                            ),
                          ),
                        ),
                        const Gap(18),

                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Text(
                                pg.name,
                                style: GoogleFonts.notoSansKr(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w900,
                                  color: AppColors.ink,
                                  letterSpacing: -0.5,
                                  height: 1.25,
                                ),
                              ),
                            ),
                            const Gap(12),
                            Text(
                              '📍 ${pg.id == "p1" ? "도보 2분" : pg.id == "p2" ? "도보 5분" : "도보 1분"}',
                              style: GoogleFonts.notoSansKr(
                                  fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: AppColors.amber,
                              ),
                            ),
                          ],
                        ),
                        const Gap(12),

                        Row(
                          children: [
                            _buildJSXTrustBadge(pg.id == 'p1' ? '함께하는 부모' : pg.id == 'p2' ? '든든한 이웃' : '새내기 부모'),
                            const Gap(8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: AppColors.warmGray,
                                borderRadius: BorderRadius.circular(99),
                              ),
                              child: Text(
                                '🏷 ${pg.id == "p1" ? "라라어린이집 학부모" : pg.id == "p2" ? "해링턴 학부모" : "소속 등록 필요"}',
                                style: GoogleFonts.notoSansKr(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.bark,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const Gap(20),

                        // 3. 미니 썬/쉐이드 카드 (Active) 또는 비어있음 카드 (Empty)
                        if (isActive)
                          _buildJSXSunShadeCard(pg)
                        else if (isEmpty)
                          _buildJSXEmptyCard()
                        else
                          _buildJSXPendingCard(pg),

                        const Gap(24),

                        // 4. 참여자 목록 (Roster)
                        if (!isEmpty) ...[
                          Text(
                            '지금 ${pg.members.length}명 있어요',
                            style: GoogleFonts.notoSansKr(
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                              color: AppColors.smoke,
                            ),
                          ),
                          const Gap(12),
                          Row(
                            children: pg.members.map((m) {
                              final isSupervisor = pg.members.first == m;
                              return Container(
                                margin: const EdgeInsets.only(right: 10),
                                width: 42,
                                height: 42,
                                decoration: BoxDecoration(
                                  color: isSupervisor ? AppColors.amber : AppColors.warmGray,
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                    color: isSupervisor ? AppColors.amberGlow : AppColors.warmGray,
                                    width: 2,
                                  ),
                                ),
                                alignment: Alignment.center,
                                child: Text(
                                  m.isNotEmpty ? m[0] : '부',
                                  style: GoogleFonts.notoSansKr(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w900,
                                    color: isSupervisor ? AppColors.white : AppColors.bark,
                                  ),
                                ),
                              );
                            }).toList(),
                          ),
                          const Gap(28),
                        ],

                        // 5. 하단 CTA 버튼 영역
                        Row(
                          children: [
                            Expanded(
                              child: SizedBox(
                                height: 54,
                                child: ElevatedButton(
                                  onPressed: () {
                                    Navigator.pop(ctx);
                                    if (isEmpty) {
                                      context.push('/group/create');
                                    } else {
                                      context.push('/supervision/${pg.id}');
                                    }
                                  },
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppColors.amber,
                                    foregroundColor: AppColors.white,
                                    elevation: 0,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                  ),
                                  child: Text(
                                    isEmpty ? '여기서 시작하기' : '나도 갈게요',
                                    style: GoogleFonts.notoSansKr(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            if (!isEmpty) ...[
                              const Gap(10),
                              GestureDetector(
                                onTap: () => Navigator.pop(ctx),
                                child: Container(
                                  height: 54,
                                  padding: const EdgeInsets.symmetric(horizontal: 20),
                                  decoration: BoxDecoration(
                                    color: AppColors.warmGray,
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  alignment: Alignment.center,
                                  child: Text(
                                    '구경만',
                                    style: GoogleFonts.notoSansKr(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700,
                                      color: AppColors.smoke,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                        const Gap(16),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _showTimeFilterSheet() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '시간 필터',
              style: GoogleFonts.notoSansKr(
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
            ),
            const Gap(16),
            ...['전체', '오늘', '내일', '이번 주'].map((label) => ListTile(
                  title: Text(label, style: GoogleFonts.notoSansKr(fontSize: 15)),
                  trailing: _timeFilter == label
                      ? const Icon(Icons.check_rounded, color: AppColors.primary)
                      : null,
                  onTap: () {
                    setState(() => _timeFilter = label);
                    Navigator.pop(ctx);
                  },
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                )),
            const Gap(8),
          ],
        ),
      ),
    );
  }

  void _showLocationFilterSheet() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '위치 필터',
              style: GoogleFonts.notoSansKr(
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
            ),
            const Gap(16),
            ...['전체', '내 주변 500m', '내 주변 1km', '내 주변 3km'].map((label) => ListTile(
                  title: Text(label, style: GoogleFonts.notoSansKr(fontSize: 15)),
                  trailing: _locationFilter == label
                      ? const Icon(Icons.check_rounded, color: AppColors.primary)
                      : null,
                  onTap: () {
                    setState(() => _locationFilter = label);
                    Navigator.pop(ctx);
                  },
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                )),
            const Gap(8),
          ],
        ),
      ),
    );
  }

  Widget _buildAvatarStack(List<String> members) {
    if (members.isEmpty) return const SizedBox.shrink();

    // 표시할 최대 아바타 개수
    final maxToShow = 4;
    final displayMembers = members.take(maxToShow).toList();
    final hasMore = members.length > maxToShow;

    return Row(
      children: [
        SizedBox(
          height: 36,
          width: (displayMembers.length * 20.0) + (hasMore ? 36.0 : 12.0),
          child: Stack(
            children: [
              for (int i = 0; i < displayMembers.length; i++)
                Positioned(
                  left: i * 18.0,
                  child: Container(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.05),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: CircleAvatar(
                      radius: 16,
                      backgroundColor: AppColors.primary.withValues(alpha: 0.1),
                      child: Text(
                        displayMembers[i].isNotEmpty ? displayMembers[i][0] : '부',
                        style: GoogleFonts.notoSansKr(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primary,
                        ),
                      ),
                    ),
                  ),
                ),
              if (hasMore)
                Positioned(
                  left: displayMembers.length * 18.0,
                  child: Container(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                    ),
                    child: CircleAvatar(
                      radius: 16,
                      backgroundColor: AppColors.surfaceLight,
                      child: Text(
                        '+${members.length - maxToShow}',
                        style: GoogleFonts.notoSansKr(
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        const Gap(8),
        Expanded(
          child: Text(
            members.join(', ') + ' 참여 중',
            style: GoogleFonts.notoSansKr(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: AppColors.textSecondary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  Widget _buildRecommendPlace({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String distance,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.warmGray, width: 1),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: iconColor.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: iconColor, size: 22),
          ),
          const Gap(14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.notoSansKr(
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    color: AppColors.ink,
                  ),
                ),
                const Gap(4),
                Text(
                  distance,
                  style: GoogleFonts.notoSansKr(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.bark,
                  ),
                ),
              ],
            ),
          ),
          Container(
            width: 24,
            height: 24,
            decoration: const BoxDecoration(
              color: AppColors.parchment,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.arrow_forward_ios_rounded,
              size: 10,
              color: AppColors.amber,
            ),
          ),
        ],
      ),
    );
  }
  // ── PlaygroundSheet JSX 헬퍼 함수군 ──
  Widget _buildJSXTrustBadge(String level) {
    Color bg;
    Color color;
    Color dot;
    
    if (level == '든든한 이웃') {
      bg = const Color(0xFFD4EDCF);
      color = const Color(0xFF1E4D18);
      dot = const Color(0xFF3A6630);
    } else if (level == '함께하는 부모') {
      bg = const Color(0xFFEDD49A);
      color = const Color(0xFF5C3D08);
      dot = const Color(0xFFC07A22);
    } else {
      bg = const Color(0xFFE4DFD3);
      color = const Color(0xFF5C4B28);
      dot = const Color(0xFF8A8472);
    }
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(99),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(color: dot, shape: BoxShape.circle),
          ),
          const Gap(6),
          Text(
            level,
            style: GoogleFonts.notoSansKr(
              fontSize: 11,
              fontWeight: FontWeight.w900,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildJSXSunShadeCard(_PlaygroundMock pg) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.warmGray, width: 1.5),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFFFAF4E4), Color(0xFFEDD49A)],
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '지금 감독 중 ☀️',
                  style: GoogleFonts.notoSansKr(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: AppColors.bark,
                  ),
                ),
                const Gap(6),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      '12:45',
                      style: GoogleFonts.notoSansKr(
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        color: AppColors.ink,
                        letterSpacing: -1.0,
                      ),
                    ),
                    const Gap(8),
                    Text(
                      '현재 감독: ${pg.members.isNotEmpty ? pg.members.first : "김민준"}',
                      style: GoogleFonts.notoSansKr(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppColors.bark,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: AppColors.forest,
            child: Row(
              children: [
                Text(
                  '다음 🌿',
                  style: GoogleFonts.notoSansKr(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: AppColors.mist,
                  ),
                ),
                const Gap(8),
                Text(
                  pg.members.length > 1 ? pg.members[1] : '대기자 없음',
                  style: GoogleFonts.notoSansKr(
                    fontSize: 13,
                    fontWeight: FontWeight.w900,
                    color: AppColors.mist,
                  ),
                ),
                const Spacer(),
                if (pg.members.length > 1)
                  Row(
                    children: pg.members.skip(1).map((m) => Container(
                      margin: const EdgeInsets.only(left: 6),
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: const Color(0xFFB4D4A8).withOpacity(0.18),
                        border: Border.all(color: AppColors.sage.withOpacity(0.3), width: 1.0),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        m[0],
                        style: GoogleFonts.notoSansKr(
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                          color: AppColors.mist,
                        ),
                      ),
                    )).toList(),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildJSXEmptyCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 18),
      decoration: BoxDecoration(
        color: AppColors.warmGray,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        children: [
          const Text('🌤', style: TextStyle(fontSize: 32)),
          const Gap(8),
          Text(
            '아직 아무도 없어요',
            style: GoogleFonts.notoSansKr(
              fontSize: 14,
              fontWeight: FontWeight.w900,
              color: AppColors.ink,
            ),
          ),
          const Gap(4),
          Text(
            '첫 번째로 시작해볼까요?',
            style: GoogleFonts.notoSansKr(
              fontSize: 12,
              color: AppColors.smoke,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildJSXPendingCard(_PlaygroundMock pg) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 20),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.warmGray, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '지금 ${pg.memberCount}명 있어요 🌿',
                style: GoogleFonts.notoSansKr(
                  fontSize: 13,
                  fontWeight: FontWeight.w900,
                  color: AppColors.canopy,
                ),
              ),
              Text(
                '함께 놀 준비 중',
                style: GoogleFonts.notoSansKr(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.smoke,
                ),
              ),
            ],
          ),
          const Gap(10),
          Text(
            '참가자들이 모여 돌봄 교대가 시작되면 감독 순번이 활성화됩니다.',
            style: GoogleFonts.notoSansKr(
              fontSize: 12,
              color: AppColors.bark,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }

  void _showEmergencyDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFFFFFDF3),
        title: Text(
          '🚨 긴급 비상 경보',
          style: GoogleFonts.notoSansKr(
            fontWeight: FontWeight.w900,
            color: AppColors.error,
          ),
        ),
        content: Text(
          '즉시 다른 부모들에게 비상 알림을 전송하고\n놀이터 지킴이 센터에 신고합니까?',
          style: GoogleFonts.notoSansKr(
            fontWeight: FontWeight.w700,
            color: AppColors.ink,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('취소', style: TextStyle(color: AppColors.smoke)),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('🚨 경보가 전송되었습니다. 즉시 현장으로 대피를 지원해 주세요.'),
                  backgroundColor: AppColors.error,
                ),
              );
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('전송', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Widget _buildLegendRow(Color dotColor, String labelText) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: dotColor,
          ),
        ),
        const Gap(6),
        Text(
          labelText,
          style: GoogleFonts.notoSansKr(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: AppColors.bark,
          ),
        ),
      ],
    );
  }
}

class _AffiliationMock {
  final String name;
  final String type;
  final double latitude;
  final double longitude;

  _AffiliationMock(this.name, this.type, this.latitude, this.longitude);
}

class _PlaygroundMock {
  final String id;
  final String name;
  final double latitude;
  final double longitude;
  final String status;
  final int memberCount;
  final int maxMembers;
  final List<String> members;
  final List<Color> affiliationColors;

  _PlaygroundMock(
    this.id,
    this.name,
    this.latitude,
    this.longitude,
    this.status,
    this.memberCount,
    this.maxMembers,
    this.members,
    this.affiliationColors,
  );
}

// ── 일러스트 맵 위젯 ───────────────────────────────────────────
class _IllustratedMap extends StatelessWidget {
  final List<_PlaygroundMock> playgrounds;
  final Function(_PlaygroundMock) onSelectPlayground;

  const _IllustratedMap({
    required this.playgrounds,
    required this.onSelectPlayground,
  });

  @override
  Widget build(BuildContext context) {
    return InteractiveViewer(
      minScale: 0.8,
      maxScale: 3.5,
      boundaryMargin: const EdgeInsets.all(120),
      constrained: true,
      child: AspectRatio(
        aspectRatio: 390 / 290,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.maxWidth;
            final scale = width / 390.0;

          return Stack(
            clipBehavior: Clip.none,
            children: [
              // 1. 배경 지형 및 도로, 건물 CustomPaint
              Positioned.fill(
                child: CustomPaint(
                  painter: _IllustratedMapPainter(scale: scale),
                ),
              ),

              // 2. 신경주역 캡슐 라벨 (forest 배경, canopy 테두리, mist 글자색)
              Positioned(
                left: 165.0 * scale,
                top: 144.0 * scale,
                width: 62.0 * scale,
                height: 28.0 * scale,
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.forest,
                    border: Border.all(color: AppColors.canopy, width: 1.5),
                    borderRadius: BorderRadius.circular(6.0 * scale),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    '🚄 신경주역',
                    style: GoogleFonts.notoSansKr(
                      fontSize: 8.5 * scale,
                      fontWeight: FontWeight.w900,
                      color: AppColors.mist,
                    ),
                  ),
                ),
              ),

              // 3. 소속 마커들 (🏢 아파트 / 🏫 어린이집)
              ..._buildAffiliationMarkers(scale),

              // 4. 놀이터 마커들
              ...playgrounds.map((pg) => _buildPlaygroundMarker(pg, scale)),
            ],
          );
        },
      ),
    ),
  );
}

  List<Widget> _buildAffiliationMarkers(double scale) {
    final list = [
      _AffiliationMarkerInfo('🏢', 250, 138, true), // 해링턴
      _AffiliationMarkerInfo('🏢', 268, 162, true), // 센텀스카이
      _AffiliationMarkerInfo('🏢', 280, 195, true), // 데시앙
      _AffiliationMarkerInfo('🏫', 100, 82, false), // 방주어린이집
      _AffiliationMarkerInfo('🏫', 88, 106, false), // 라라어린이집
      _AffiliationMarkerInfo('🏫', 74, 132, false), // 미래어린이집
    ];

    return list.map((a) {
      final r = 11.0 * scale;
      return Positioned(
        left: a.mx * scale - r,
        top: a.my * scale - r,
        width: r * 2,
        height: r * 2,
        child: Container(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: a.isApartment ? const Color(0xFFC8B87A) : const Color(0xFFA8C899),
            border: Border.all(color: const Color(0xFF8A7A60), width: 1.0),
          ),
          alignment: Alignment.center,
          child: Text(
            a.emoji,
            style: TextStyle(fontSize: 10 * scale),
          ),
        ),
      );
    }).toList();
  }

  Widget _buildPlaygroundMarker(_PlaygroundMock pg, double scale) {
    double mapX = 0;
    double mapY = 0;
    Color statusColor;

    if (pg.id == 'p1') {
      mapX = 255;
      mapY = 118;
    } else if (pg.id == 'p2') {
      mapX = 145;
      mapY = 175;
    } else if (pg.id == 'p3') {
      mapX = 280;
      mapY = 200;
    } else {
      mapX = 320;
      mapY = 240;
    }

    switch (pg.status) {
      case 'active':
        statusColor = AppColors.amber;
        break;
      case 'pending':
      case 'open':
        statusColor = AppColors.canopy;
        break;
      default:
        statusColor = AppColors.smoke;
    }

    final r = 13.0 * scale;

    return Positioned(
      left: mapX * scale - r,
      top: mapY * scale - r,
      width: r * 2,
      height: r * 2,
      child: GestureDetector(
        onTap: () => onSelectPlayground(pg),
        child: Stack(
          alignment: Alignment.center,
          clipBehavior: Clip.none,
          children: [
            // 진행중일 때 1.8초 앰버 핑 (Ping Effect)
            if (pg.status == 'active')
              _PingEffect(radius: r * 1.5, color: statusColor),

            Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: statusColor,
                border: Border.all(color: AppColors.white, width: 2.5 * scale),
              ),
              alignment: Alignment.center,
              child: Text(
                '🛝',
                style: TextStyle(fontSize: 13 * scale),
              ),
            ),

            if (pg.memberCount > 0)
              Positioned(
                right: -4 * scale,
                top: -4 * scale,
                child: Container(
                  width: 14 * scale,
                  height: 14 * scale,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.white,
                    border: Border.all(color: statusColor, width: 1.2 * scale),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    pg.memberCount.toString(),
                    style: TextStyle(
                      fontSize: 7 * scale,
                      fontWeight: FontWeight.w900,
                      color: statusColor,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _AffiliationMarkerInfo {
  final String emoji;
  final double mx;
  final double my;
  final bool isApartment;

  _AffiliationMarkerInfo(this.emoji, this.mx, this.my, this.isApartment);
}

// ── 일러스트 맵 그리기 Painter ───────────────────────────────
class _IllustratedMapPainter extends CustomPainter {
  final double scale;

  _IllustratedMapPainter({required this.scale});

  @override
  void paint(Canvas canvas, Size size) {
    // 1. 전체 지면 크림색 (#EDE3C8)
    final bgPaint = Paint()..color = const Color(0xFFEDE3C8);
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), bgPaint);

    // 2. 공원 녹지 패치 3곳 (#C8DBA8)
    final parkPaint = Paint()
      ..color = const Color(0xFFC8DBA8).withOpacity(0.7)
      ..style = PaintingStyle.fill;

    _drawRoundRect(canvas, 220, 95, 70, 60, 10, parkPaint);
    _drawRoundRect(canvas, 62, 155, 55, 45, 10, parkPaint);
    _drawRoundRect(canvas, 155, 60, 40, 30, 10, parkPaint);

    // 3. 도로망 그리기 — 따뜻한 크림 황토색 (#D8CDB0)
    final roadPaint = Paint()
      ..color = const Color(0xFFD8CDB0)
      ..style = PaintingStyle.fill;
    final subRoadPaint = Paint()
      ..color = const Color(0xFFDDD3B8).withOpacity(0.7)
      ..style = PaintingStyle.fill;

    // 수평 주도로 (Y=152, H=14)
    canvas.drawRect(Rect.fromLTWH(0, 152 * scale, size.width, 14 * scale), roadPaint);
    // 수직 주도로 (X=191, W=10)
    canvas.drawRect(Rect.fromLTWH(186 * scale, 0, 10 * scale, size.height), roadPaint);

    // 보조 수평도로 (Y=98, H=7) & (Y=198, H=7)
    canvas.drawRect(Rect.fromLTWH(0, 98 * scale, size.width, 7 * scale), subRoadPaint);
    canvas.drawRect(Rect.fromLTWH(0, 198 * scale, size.width, 7 * scale), subRoadPaint);

    // 보조 수직도로 (X=130, W=6) & (X=260, W=6)
    canvas.drawRect(Rect.fromLTWH(130 * scale, 0, 6 * scale, size.height), subRoadPaint);
    canvas.drawRect(Rect.fromLTWH(260 * scale, 0, 6 * scale, size.height), subRoadPaint);

    // 4. 건물 블록 그리기 (9개)
    final buildPaint = Paint()
      ..color = const Color(0xFFD8CEBC)
      ..style = PaintingStyle.fill;
    final buildStroke = Paint()
      ..color = const Color(0xFFC4BAA6)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8 * scale;

    final buildings = [
      [30.0, 30.0, 35.0, 30.0], [70.0, 30.0, 25.0, 22.0], [30.0, 66.0, 28.0, 22.0], [100.0, 30.0, 25.0, 20.0],
      [310.0, 30.0, 40.0, 28.0], [320.0, 65.0, 30.0, 22.0], [310.0, 95.0, 38.0, 24.0],
      [320.0, 170.0, 40.0, 22.0], [305.0, 200.0, 35.0, 24.0]
    ];

    for (final b in buildings) {
      _drawRoundRect(canvas, b[0], b[1], b[2], b[3], 3, buildPaint);
      _drawRoundRect(canvas, b[0], b[1], b[2], b[3], 3, buildStroke);
    }
  }

  void _drawRoundRect(Canvas canvas, double x, double y, double w, double h, double rx, Paint paint) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(x * scale, y * scale, w * scale, h * scale),
        Radius.circular(rx * scale),
      ),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ── 마커용 1.8초 펄스 이펙트 (Ping) ──
class _PingEffect extends StatefulWidget {
  final double radius;
  final Color color;

  const _PingEffect({required this.radius, required this.color});

  @override
  State<_PingEffect> createState() => _PingEffectState();
}

class _PingEffectState extends State<_PingEffect> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final scale = 1.0 + (_controller.value * 0.6);
        final opacity = 0.55 * (1.0 - _controller.value);
        return Transform.scale(
          scale: scale,
          child: Opacity(
            opacity: opacity,
            child: Container(
              width: widget.radius * 2,
              height: widget.radius * 2,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: widget.color,
              ),
            ),
          ),
        );
      },
    );
  }
}

class PlaygroundMarkerWidget extends StatelessWidget {
  final String status;
  final String shortName;
  final List<Color> affiliationColors;
  final Color myAffiliationColor;

  const PlaygroundMarkerWidget({
    super.key,
    required this.status,
    required this.shortName,
    required this.affiliationColors,
    required this.myAffiliationColor,
  });

  @override
  Widget build(BuildContext context) {
    Color statusColor;
    switch (status) {
      case 'active':
        statusColor = const Color(0xFFC07A22); // amber
        break;
      case 'pending':
        statusColor = const Color(0xFF3A6630); // canopy
        break;
      case 'full':
        statusColor = const Color(0xFF8A8472); // smoke
        break;
      default:
        statusColor = const Color(0xFFE8DFC8); // warmGray
    }

    // 전체 위젯을 120 x 85 크기의 바운더리 박스 안에 정렬
    return Container(
      width: 120,
      height: 85,
      color: Colors.transparent,
      child: Stack(
        alignment: Alignment.topCenter,
        children: [
          // 1. 메인 놀이터 핀 원형 (지름 36)
          Positioned(
            top: 12,
            child: SizedBox(
              width: 36,
              height: 36,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  // 메인 핀 바디
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: statusColor,
                      border: Border.all(color: const Color(0xFFFFFDF3), width: 3),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.25),
                          blurRadius: 6,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    alignment: Alignment.center,
                    child: const Text(
                      '🛝',
                      style: TextStyle(fontSize: 16, height: 1.1),
                    ),
                  ),

                  // 소속 구성원 점들 (최대 4개 데코레이션 배치)
                  if (affiliationColors.isNotEmpty)
                    ..._buildDotPositionedWidgets(),
                ],
              ),
            ),
          ),

          // 2. 하단 알약형 라벨
          Positioned(
            top: 54,
            left: 0,
            right: 0,
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFDF3).withOpacity(0.92),
                  borderRadius: BorderRadius.circular(99),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.15),
                      blurRadius: 4,
                      offset: const Offset(0, 1),
                    ),
                  ],
                ),
                child: Text(
                  shortName,
                  style: GoogleFonts.notoSansKr(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF18180E),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildDotPositionedWidgets() {
    final list = <Widget>[];

    for (int i = 0; i < affiliationColors.length && i < 4; i++) {
      final color = affiliationColors[i];
      final isMine = color == myAffiliationColor;

      // HTML 기준 위치 오프셋 매핑
      double? top;
      double? bottom;
      double? left;
      double? right;

      if (i == 0) {
        top = -4;
        left = -4;
      } else if (i == 1) {
        top = -4;
        right = -4;
      } else if (i == 2) {
        bottom = -2;
        left = 13;
      } else {
        bottom = -2;
        right = 13;
      }

      final dotSize = isMine ? 13.0 : 10.0;

      list.add(
        Positioned(
          top: top,
          bottom: bottom,
          left: left,
          right: right,
          child: Container(
            width: dotSize,
            height: dotSize,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color,
              border: Border.all(color: const Color(0xFFFFFDF3), width: 1.5),
              boxShadow: [
                if (isMine)
                  const BoxShadow(
                    color: Color(0xFFC07A22), // 내 소속 강조 amber glow 링!
                    spreadRadius: 2,
                  ),
                BoxShadow(
                  color: Colors.black.withOpacity(0.2),
                  blurRadius: 2,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return list;
  }
}
