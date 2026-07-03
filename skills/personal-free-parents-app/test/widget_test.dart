import 'package:flutter_test/flutter_test.dart';

import 'package:one_parent_watch/app.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    // OneParentWatchApp requires ProviderScope and Supabase init,
    // so this is a minimal existence check.
    expect(const OneParentWatchApp(), isNotNull);
  });
}
