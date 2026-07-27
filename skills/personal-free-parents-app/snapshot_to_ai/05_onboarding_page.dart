import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:gap/gap.dart';

import '../../../core/theme/app_colors.dart';

/// 온보딩 탭 페이지 — JSX OnboardingScreen 멀티 스텝 완벽 이식
class OnboardingPage extends StatefulWidget {
  final VoidCallback onNext;

  const OnboardingPage({super.key, required this.onNext});

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  int _step = 4; // 8번 규칙: 첫 실행 시 슬라이드 없이 바로 소속선택 로그인 연계 단계만 노출
  final TextEditingController _phoneController = TextEditingController();
  String? _pickedAffiliationId;

  final List<Map<String, String>> _slides = [
    {
      'icon': '☀️',
      'head': '한명만',
      'sub': '한 명이 감독하는 동안\n나머지 부모는 제대로 쉽니다'
    },
    {
      'icon': '🌿',
      'head': '번갈아 쉬어요',
      'sub': '자동 순번으로 돌아가며\n감독하고 커피 한 잔 마셔요'
    },
    {
      'icon': '🛝',
      'head': '우리 동네 놀이터',
      'sub': '같은 어린이집·단지\n학부모끼리만 매칭됩니다'
    },
  ];

  final List<Map<String, String>> _affiliations = [
    {'id': 'a1', 'icon': '🏢', 'name': '천년가 센텀스카이', 'type': '아파트 단지'},
    {'id': 'a2', 'icon': '🏢', 'name': '해링턴플레이스 신경주역', 'type': '아파트 단지'},
    {'id': 'a3', 'icon': '🏢', 'name': '신경주 더퍼스트 데시앙', 'type': '아파트 단지'},
    {'id': 'a4', 'icon': '🏫', 'name': '방주 어린이집', 'type': '교육 기관 소속'},
    {'id': 'a5', 'icon': '🏫', 'name': '라라 어린이집', 'type': '교육 기관 소속'},
    {'id': 'a6', 'icon': '🏫', 'name': '미래 어린이집', 'type': '교육 기관 소속'},
  ];

  @override
  void dispose() {
    _phoneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight, // #F6EFD8 양피지색
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            children: [
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: _buildCurrentStepView(),
                ),
              ),
              const Gap(16),
              // 하단 버튼 제어 영역
              _buildBottomButton(),
              const Gap(76), // 플로팅 탭바 높이 확보
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCurrentStepView() {
    if (_step < 3) {
      // ── 인트로 슬라이드 (0, 1, 2) ──
      final slide = _slides[_step];
      return Column(
        key: ValueKey<int>(_step),
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(),
          // 3D 느낌의 벡터 태양 장식
          SizedBox(
            width: 140,
            height: 140,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CustomPaint(
                  size: const Size(140, 140),
                  painter: _SunFlamePainter(color: const Color(0xFFE08E39)),
                ),
                Container(
                  width: 86,
                  height: 86,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFFFFEE77), Color(0xFFE89A30)],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFFC07A22).withOpacity(0.4),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    slide['icon']!,
                    style: const TextStyle(fontSize: 42),
                  ),
                ),
              ],
            ),
          ),
          const Gap(32),
          Text(
            slide['head']!,
            style: GoogleFonts.notoSansKr(
              fontSize: 28,
              fontWeight: FontWeight.w900,
              color: AppColors.ink,
              letterSpacing: -1.0,
            ),
          ),
          const Gap(16),
          Text(
            slide['sub']!,
            textAlign: TextAlign.center,
            style: GoogleFonts.notoSansKr(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: AppColors.bark,
              height: 1.5,
              letterSpacing: -0.5,
            ),
          ),
          const Gap(36),
          // 도트 인디케이터
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(3, (index) {
              final isSelected = index == _step;
              return AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: isSelected ? 20 : 6,
                height: 6,
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.amber : AppColors.warmGray,
                  borderRadius: BorderRadius.circular(99),
                ),
              );
            }),
          ),
          const Spacer(),
        ],
      );
    } else if (_step == 3) {
      // ── 전화번호 인증 단계 (3) ──
      return Column(
        key: const ValueKey<int>(3),
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '전화번호 인증',
            style: GoogleFonts.notoSansKr(
              fontSize: 24,
              fontWeight: FontWeight.w900,
              color: AppColors.ink,
              letterSpacing: -0.5,
            ),
          ),
          const Gap(6),
          Text(
            '본인 인증을 위해 전화번호를 입력해주세요',
            style: GoogleFonts.notoSansKr(
              fontSize: 13,
              color: AppColors.smoke,
            ),
          ),
          const Gap(32),
          TextField(
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            decoration: InputDecoration(
              hintText: '010-0000-0000',
              filled: true,
              fillColor: AppColors.white,
              contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: AppColors.warmGray, width: 1.5),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: AppColors.amber, width: 1.5),
              ),
            ),
            style: GoogleFonts.notoSansKr(
              fontSize: 17,
              color: AppColors.ink,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      );
    } else {
      // ── 소속 선택 단계 (4) ──
      return Column(
        key: const ValueKey<int>(4),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Gap(20),
          Text(
            '어느 곳에 속해 계신가요?',
            style: GoogleFonts.notoSansKr(
              fontSize: 24,
              fontWeight: FontWeight.w900,
              color: AppColors.ink,
              letterSpacing: -0.5,
            ),
          ),
          const Gap(6),
          Text(
            '같은 소속 학부모끼리 그룹이 매칭됩니다',
            style: GoogleFonts.notoSansKr(
              fontSize: 13,
              color: AppColors.smoke,
            ),
          ),
          const Gap(20),
          Expanded(
            child: ListView.separated(
              itemCount: _affiliations.length,
              separatorBuilder: (_, __) => const Gap(8),
              itemBuilder: (context, index) {
                final aff = _affiliations[index];
                final isSelected = _pickedAffiliationId == aff['id'];
                return GestureDetector(
                  onTap: () {
                    setState(() {
                      _pickedAffiliationId = aff['id'];
                    });
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                    decoration: BoxDecoration(
                      color: isSelected ? AppColors.amberPale : AppColors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: isSelected ? AppColors.amber : AppColors.warmGray,
                        width: 1.5,
                      ),
                    ),
                    child: Row(
                      children: [
                        Text(
                          aff['icon']!,
                          style: const TextStyle(fontSize: 24),
                        ),
                        const Gap(14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                aff['name']!,
                                style: GoogleFonts.notoSansKr(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.ink,
                                ),
                              ),
                              Text(
                                aff['type']!,
                                style: GoogleFonts.notoSansKr(
                                  fontSize: 11,
                                  color: AppColors.smoke,
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (isSelected)
                          const Text(
                            '✓',
                            style: TextStyle(
                              color: AppColors.amber,
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      );
    }
  }

  Widget _buildBottomButton() {
    String btnText;
    VoidCallback onPressed;

    if (_step < 2) {
      btnText = '다음 ➔';
      onPressed = () => setState(() => _step++);
    } else if (_step == 2) {
      btnText = '시작하기';
      onPressed = () => setState(() => _step = 3);
    } else if (_step == 3) {
      btnText = '인증번호 받기';
      onPressed = () {
        if (_phoneController.text.trim().isEmpty) {
          _phoneController.text = '010-1234-5678';
        }
        setState(() => _step = 4);
      };
    } else {
      btnText = '완료';
      onPressed = () {
        if (_pickedAffiliationId == null) {
          _pickedAffiliationId = 'a1'; // 센텀스카이 기본값 선택
        }
        widget.onNext();
      };
    }

    return SizedBox(
      width: double.infinity,
      height: 54,
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.amber,
          foregroundColor: AppColors.white,
          elevation: 0,
          shape: const StadiumBorder(),
        ),
        child: Text(
          btnText,
          style: GoogleFonts.notoSansKr(
            fontSize: 16,
            fontWeight: FontWeight.w900,
            letterSpacing: -0.5,
          ),
        ),
      ),
    );
  }
}

/// 아기자기한 12개의 꽃잎형 태양 플레어 외곽선 Painter
class _SunFlamePainter extends CustomPainter {
  final Color color;

  _SunFlamePainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    final center = Offset(size.width / 2, size.height / 2);
    final outerRadius = size.width * 0.44;
    final innerRadius = size.width * 0.35;
    final path = Path();

    const int steps = 12;
    for (int i = 0; i < steps; i++) {
      final double angle1 = (i * (360.0 / steps)) * math.pi / 180.0;
      final double angleMid = ((i + 0.5) * (360.0 / steps)) * math.pi / 180.0;
      final double angle2 = ((i + 1) * (360.0 / steps)) * math.pi / 180.0;

      final p1 = Offset(
        center.dx + innerRadius * math.cos(angle1),
        center.dy + innerRadius * math.sin(angle1),
      );
      final pMid = Offset(
        center.dx + outerRadius * math.cos(angleMid),
        center.dy + outerRadius * math.sin(angleMid),
      );
      final p2 = Offset(
        center.dx + innerRadius * math.cos(angle2),
        center.dy + innerRadius * math.sin(angle2),
      );

      if (i == 0) {
        path.moveTo(p1.dx, p1.dy);
      }
      path.quadraticBezierTo(pMid.dx, pMid.dy, p2.dx, p2.dy);
    }
    path.close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
