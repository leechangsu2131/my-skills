import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gap/gap.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/router/app_router.dart';
import '../../../core/theme/app_colors.dart';
import '../application/auth_notifier.dart';

/// 로그인 페이지 — 이메일(개발용) / Phone OTP 모드 전환 지원
class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _phoneController = TextEditingController();

  bool _isPhoneMode = false;
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    if (!const bool.fromEnvironment('dart.vm.product')) {
      _emailController.text = 'test1@example.com';
      _passwordController.text = 'password123';
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);

    // 인증 상태 변경 감지 → 네비게이션
    ref.listen(authNotifierProvider, (prev, next) {
      next.whenData((status) {
        if (status == AuthStatus.authenticated) {
          context.go(AppRoutes.home);
        } else if (status == AuthStatus.profileIncomplete) {
          context.go(AppRoutes.profileSetup);
        }
      });
    });

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Gap(48),
                // ── 헤더 (로고 및 슬로건) ──
                _buildHeader(),
                const Gap(60),

                // ── 8번 규칙: 화면에서 가장 크고 유일하게 눈에 띄는 구글 로그인 버튼 (유일한 CTA) ──
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32),
                  child: _buildGoogleButton(authState)
                      .animate()
                      .fadeIn(duration: 450.ms, delay: 250.ms)
                      .slideY(begin: 0.05, end: 0),
                ),
                const Gap(100),

                // 디버그 간편 버튼 (테스트 편의성을 위해 작고 투명한 텍스트로 배치)
                if (!const bool.fromEnvironment('dart.vm.product')) ...[
                  SizedBox(
                    height: 40,
                    child: TextButton(
                      onPressed: authState.isLoading
                          ? null
                          : () {
                              _emailController.text = 'test1@example.com';
                              _passwordController.text = 'password123';
                              ref.read(authNotifierProvider.notifier).signUpWithEmail(
                                    email: 'test1@example.com',
                                    password: 'password123',
                                  ).then((_) {
                                    if (!mounted) return;
                                    ref.read(authNotifierProvider.notifier).signInWithEmail(
                                          email: 'test1@example.com',
                                          password: 'password123',
                                        );
                                  });
                            },
                      child: Text(
                        '1초 간편 로그인 (Dev)',
                        style: GoogleFonts.notoSansKr(
                          color: AppColors.smoke.withOpacity(0.5),
                          fontWeight: FontWeight.w400,
                          fontSize: 11.5,
                        ),
                      ),
                    ),
                  ),
                ],
                const Gap(32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// 구글 소셜 로그인 버튼
  Widget _buildGoogleButton(AsyncValue<AuthStatus> authState) {
    final isLoading = authState.isLoading;

    return SizedBox(
      height: 56,
      child: OutlinedButton(
        onPressed: isLoading
            ? null
            : () => ref.read(authNotifierProvider.notifier).signInWithGoogle(),
        style: OutlinedButton.styleFrom(
          backgroundColor: AppColors.white,
          side: const BorderSide(color: AppColors.warmGray, width: 1.8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          elevation: 2,
          shadowColor: Colors.black.withOpacity(0.06),
          padding: const EdgeInsets.symmetric(horizontal: 20),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
              ),
              child: Image.network(
                'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Google_%22G%22_logo.svg/24px-Google_%22G%22_logo.svg.png',
                width: 22,
                height: 22,
                errorBuilder: (context, error, stackTrace) => const Icon(
                  Icons.g_mobiledata_rounded,
                  color: AppColors.amber,
                  size: 24,
                ),
              ),
            ),
            const Gap(12),
            Text(
              'Google로 계속하기',
              style: GoogleFonts.notoSansKr(
                fontSize: 16,
                fontWeight: FontWeight.w900,
                color: AppColors.ink,
                letterSpacing: -0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 헤더 — 앱 로고 + 태그라인
  Widget _buildHeader() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        children: [
          // 🌤 아이콘 및 상단 여백
          const Text(
            '🌤',
            style: TextStyle(fontSize: 48),
          )
              .animate()
              .scale(
                  begin: const Offset(0.5, 0.5),
                  end: const Offset(1, 1),
                  duration: 600.ms,
                  curve: Curves.elasticOut)
              .fadeIn(duration: 300.ms),
          const Gap(24),
          Text(
            '같이 놀자',
            style: GoogleFonts.notoSansKr(
              fontSize: 20,
              fontWeight: FontWeight.w900,
              color: AppColors.forest,
              letterSpacing: -1.0,
            ),
          )
              .animate()
              .fadeIn(duration: 400.ms, delay: 100.ms)
              .slideY(begin: 0.1, end: 0),
          const Gap(4),
          Text(
            '번갈아 돌보고, 제대로 쉬어요',
            style: GoogleFonts.notoSansKr(
              fontSize: 14,
              fontWeight: FontWeight.w400,
              color: AppColors.bark,
            ),
          )
              .animate()
              .fadeIn(duration: 400.ms, delay: 200.ms)
              .slideY(begin: 0.1, end: 0),
        ],
      ),
    );
  }

  /// 개발모드 / Phone OTP 모드 전환 토글
  Widget _buildModeToggle() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.parchment,
        borderRadius: BorderRadius.circular(14),
      ),
      padding: const EdgeInsets.all(4),
      child: Row(
        children: [
          Expanded(
            child: _modeTab(
              label: '이메일 (Dev)',
              icon: Icons.email_outlined,
              selected: !_isPhoneMode,
              onTap: () => setState(() => _isPhoneMode = false),
            ),
          ),
          Expanded(
            child: _modeTab(
              label: '전화번호',
              icon: Icons.phone_android,
              selected: _isPhoneMode,
              onTap: () => setState(() => _isPhoneMode = true),
            ),
          ),
        ],
      ),
    );
  }

  Widget _modeTab({
    required String label,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: 250.ms,
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: selected ? AppColors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: selected
              ? Border.all(color: AppColors.warmGray, width: 1)
              : null,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon,
                size: 18,
                color: selected
                    ? AppColors.amber
                    : AppColors.smoke),
            const Gap(6),
            Text(
              label,
              style: TextStyle(
                fontSize: 13,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
                color: selected
                    ? AppColors.ink
                    : AppColors.smoke,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmailField() {
    return TextFormField(
      controller: _emailController,
      keyboardType: TextInputType.emailAddress,
      decoration: InputDecoration(
        labelText: '이메일',
        hintText: 'test@example.com',
        prefixIcon: GestureDetector(
          onDoubleTap: () {
            debugPrint('[DEBUG] Email prefixIcon double tapped -> auto-filling credentials');
            _emailController.text = 'test1@example.com';
            _passwordController.text = 'password123';
            _handlePrimaryAction();
          },
          child: const Icon(Icons.email_outlined, color: AppColors.primary),
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
      ),
      validator: (v) {
        if (v == null || v.isEmpty) return '이메일을 입력해주세요';
        if (!v.contains('@')) return '올바른 이메일 형식이 아닙니다';
        return null;
      },
    );
  }

  Widget _buildPasswordField() {
    return TextFormField(
      controller: _passwordController,
      obscureText: _obscurePassword,
      decoration: InputDecoration(
        labelText: '비밀번호',
        hintText: '6자 이상',
        prefixIcon:
            const Icon(Icons.lock_outline, color: AppColors.primary),
        suffixIcon: IconButton(
          icon: Icon(
            _obscurePassword
                ? Icons.visibility_off_outlined
                : Icons.visibility_outlined,
            color: AppColors.textSecondary,
          ),
          onPressed: () =>
              setState(() => _obscurePassword = !_obscurePassword),
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
      ),
      validator: (v) {
        if (v == null || v.isEmpty) return '비밀번호를 입력해주세요';
        if (v.length < 6) return '비밀번호는 6자 이상이어야 합니다';
        return null;
      },
    );
  }

  Widget _buildPhoneField() {
    return TextFormField(
      controller: _phoneController,
      keyboardType: TextInputType.phone,
      decoration: InputDecoration(
        labelText: '전화번호',
        hintText: '01012345678',
        prefixIcon:
            const Icon(Icons.phone_outlined, color: AppColors.primary),
        prefixText: '+82 ',
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
      ),
      validator: (v) {
        if (v == null || v.isEmpty) return '전화번호를 입력해주세요';
        if (v.length < 10) return '올바른 전화번호를 입력해주세요';
        return null;
      },
    );
  }

  /// 메인 액션 버튼 — 로그인 또는 OTP 발송
  Widget _buildPrimaryButton(AsyncValue<AuthStatus> authState) {
    final isLoading = authState.isLoading;

    return SizedBox(
      height: 54,
      child: ElevatedButton(
        onPressed: isLoading ? null : _handlePrimaryAction,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          elevation: 2,
          shadowColor: AppColors.primary.withValues(alpha: 0.4),
        ),
        child: isLoading
            ? const SizedBox(
                height: 22,
                width: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: Colors.white,
                ),
              )
            : Text(
                _isPhoneMode ? 'OTP 발송' : '로그인',
                style: GoogleFonts.notoSansKr(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
      ),
    );
  }

  /// 회원가입 버튼 (이메일 모드에서만 표시)
  Widget _buildSecondaryButton(AsyncValue<AuthStatus> authState) {
    final isLoading = authState.isLoading;

    return SizedBox(
      height: 54,
      child: OutlinedButton(
        onPressed: isLoading ? null : _handleSignUp,
        style: OutlinedButton.styleFrom(
          side: const BorderSide(color: AppColors.primary, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
        child: Text(
          '회원가입',
          style: GoogleFonts.notoSansKr(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: AppColors.primary,
          ),
        ),
      ),
    );
  }

  void _handlePrimaryAction() {
    if (!_formKey.currentState!.validate()) return;

    if (_isPhoneMode) {
      // Phone OTP 발송
      final phone = '+82${_phoneController.text.trim()}';
      ref.read(authNotifierProvider.notifier).sendOtp(phone: phone);
      context.push(AppRoutes.otpVerify, extra: phone);
    } else {
      // 이메일 로그인
      ref.read(authNotifierProvider.notifier).signInWithEmail(
            email: _emailController.text.trim(),
            password: _passwordController.text,
          );
    }
  }

  void _handleSignUp() {
    if (!_formKey.currentState!.validate()) return;
    ref.read(authNotifierProvider.notifier).signUpWithEmail(
          email: _emailController.text.trim(),
          password: _passwordController.text,
        );
  }
}
